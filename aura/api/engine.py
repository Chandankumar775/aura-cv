"""Application engine for the demo build: seeding, assessment pipeline, verdicts,
decisions, reports, live runs and audit access. The API layer is a thin wrapper.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from aura import TOOL_NAME, __version__
from aura.config import HOSTED, Settings
from aura.core.canonical import canonicalize
from aura.core.checks import AssessmentContext, Scheduler
from aura.core.hashing import sha256_bytes, sha256_canonical
from aura.core.ids import derived_id, format_ts, new_id, utc_now
from aura.core.policy import (
    DEFAULT_POLICY,
    asset_verdicts,
    effective_disposition,
    is_unresolved,
    most_severe,
)
from aura.core.types import (
    AccessLevel,
    Actor,
    AssetRef,
    AssetType,
    AuditEvent,
    Decision,
    Disposition,
    Finding,
    FindingStatus,
    KeyPurpose,
    ModuleId,
)
from aura.demo import DEMO_NOTICE
from aura.demo.catalog import ASSETS, BATTERY, CHECK_META, CONTRIBUTORS, USERS
from aura.demo.records import verify_single, verify_stream, build_stream
from aura.demo.scenario import build_registry
from aura.demo.views import data_view, model_view, shift_view
from aura.m3_provenance.keys import KeyStore, UnknownKeyError
from aura.m5_governance.audit_log import AuditLog, verify_log_file
from aura.m5_governance.coverage import COVERAGE
from aura.api.store import Store

MODULE_NAMES = {"M1": "Data integrity", "M2": "Model integrity", "M3": "Inference provenance", "M4": "Distribution shift"}
MODULE_INPUTS = {"M1": ["dataset"], "M2": ["model"], "M3": ["records"], "M4": ["input_batch", "reference"]}
INPUT_FIELD = {"dataset": "dataset_id", "model": "model_id", "records": "record_stream_id", "input_batch": "input_batch_id", "reference": "reference_id"}
TILE_GROUPS = {
    "dataset": ("Dataset", {"dataset", "sample"}, "M1"),
    "contributors": ("Contributors", {"contributor", "batch", "source"}, "M1"),
    "model": ("Model", {"model"}, "M2"),
    "records": ("Inference records", {"inference_record", "record_stream"}, "M3"),
    "input_batch": ("Input batch", {"input_batch", "reference"}, "M4"),
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status, self.code, self.message, self.details = status, code, message, details or {}


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2_sha256$200000${salt.hex()}${dk.hex()}"


def _check_password(password: str, stored: str) -> bool:
    _, iters, salt, digest = stored.split("$")
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters))
    return hmac.compare_digest(dk.hex(), digest)


def _session_secret() -> bytes:
    """Sessions are HMAC-signed tokens, so any serverless instance can validate them.

    Set AURA_SESSION_SECRET in production. Without it, a hosted demo derives a per-deployment
    secret (its demo credentials are public anyway) and a local run uses a random one.
    """
    explicit = os.environ.get("AURA_SESSION_SECRET")
    if explicit:
        return hashlib.sha256(explicit.encode()).digest()
    if HOSTED:
        basis = os.environ.get("VERCEL_DEPLOYMENT_ID") or os.environ.get("VERCEL_URL") or os.environ.get("VERCEL_GIT_COMMIT_SHA") or "aura-demo"
        return hashlib.sha256(f"aura-cv-demo-session::{basis}".encode()).digest()
    return secrets.token_bytes(32)


class _AuditTap:
    """Audit sink that also feeds live progress events (and paces live runs)."""

    def __init__(self, engine: "Engine", asm_id: str, live: bool):
        self.engine, self.asm_id, self.live = engine, asm_id, live

    def append(self, event, payload=None, actor=None):
        entry = self.engine.audit.append(event, payload, actor)
        cid = (payload or {}).get("check_id")
        if event is AuditEvent.CHECK_STARTED:
            self.engine._emit(self.asm_id, {"type": "check_started", "check_id": cid, "name": CHECK_META.get(cid, (cid,))[0]})
            if self.live:
                time.sleep(0.35 + (hash(cid) % 7) * 0.09)
        elif event is AuditEvent.CHECK_COMPLETED:
            self.engine._emit(self.asm_id, {"type": "check_completed", "check_id": cid, "findings": len(payload.get("finding_ids", [])), "duration_ms": payload.get("duration_ms", 0)})
        elif event is AuditEvent.CHECK_UNAVAILABLE:
            self.engine._emit(self.asm_id, {"type": "check_unavailable", "check_id": cid, "reason": payload.get("reason"), "fallback_used": payload.get("fallback_used"), "status": payload.get("status")})
            if self.live:
                time.sleep(0.25)
        return entry


class Engine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = Store(settings.db_path)
        self.keys = KeyStore(settings.keys_dir)
        self.hosted = HOSTED
        self.audit = AuditLog(settings.audit_log_path, self.keys, fsync=not HOSTED)
        self._session_secret = _session_secret()
        self._revoked: set[str] = set()
        self._run_lock = threading.Lock()
        self.registry = build_registry()
        self._events: dict[str, list[dict]] = {}
        self._cond = threading.Condition()
        self._verify_cache: tuple[float, dict] | None = None
        self._ensure_keys()
        if self.store.get("meta", "seed") is None:
            self.seed()
        self.audit.append(AuditEvent.SESSION_START, {"component": "api", "version": __version__, "demo": True, "hosted": HOSTED})

    # ------------------------------------------------------------------ setup

    def _ensure_keys(self) -> None:
        created = []
        for purpose in (KeyPurpose.AUDIT, KeyPurpose.INFERENCE, KeyPurpose.REPORT):
            if self.keys.active(purpose) is None:
                created.append(self.keys.generate(purpose))
        for k in created:
            self.audit.append(AuditEvent.KEY_CREATED, {"key_id": k.key_id, "purpose": k.purpose.value, "public_key": k.public_key})

    def seed(self) -> None:
        now = datetime.now(timezone.utc)
        for u in USERS:
            self.store.put("user", u["id"], {"id": u["id"], "username": u["username"], "role": u["role"], "display": u["display"],
                                               "password_hash": _hash_password(u["password"]), "created_at": format_ts(now - timedelta(days=30)), "disabled": False})
        for a in ASSETS:
            doc = {**a, "registered_at": format_ts(now - timedelta(days=20))}
            self.store.put("asset", a["id"], doc)
            ev = AuditEvent.REFERENCE_REGISTERED if a["type"] == "reference" else AuditEvent.ASSET_REGISTERED
            self.audit.append(ev, {"asset_id": a["id"], "type": a["type"], "name": a["name"], "digest": a.get("digest"), "demo_seed": True})
        self.store.put("meta", "battery", BATTERY)
        self.audit.append(AuditEvent.BATTERY_BUILT, {"version": BATTERY["version"], "digest": BATTERY["digest"], "reference_id": BATTERY["built_from"]})

        stream = build_stream(self.keys)
        verification = verify_stream(self.keys, stream)
        self.store.put("stream", "rs_uav07_front", {"records": stream, "verification": verification})
        asset = self.store.get("asset", "rs_uav07_front")
        asset.update(n_records=len(stream), digest=sha256_canonical(stream), signer_key_ids=sorted({r["signer"]["key_id"] for r in stream}))
        self.store.put("asset", "rs_uav07_front", asset)

        admin, analyst = "usr_admin", "usr_analyst"
        plan = [
            ("Baseline intake · Vehicles v2 (trusted)", {"dataset_id": "ds_vehicles_v2"}, ["M1"], None, admin, 5 * 24 * 60),
            ("Supplier update check · VehNet v2.2", {"model_id": "mdl_vehnet_v22"}, ["M2"], None, analyst, 2 * 24 * 60),
            ("Black-box re-check · VehNet v2.1 ONNX export", {"model_id": "mdl_vehnet_v21_onnx"}, ["M2"], None, analyst, 26 * 60),
            ("Sector-9 relay feed · shift screen", {"input_batch_id": "ib_sector9_relay", "reference_id": "ref_plains_summer", "model_id": "mdl_vehnet_v21"}, ["M4"], None, analyst, 6 * 60),
            ("Vendor drop 17 · intake screen", {"dataset_id": "ds_vehicles_nometa"}, ["M1"], None, analyst, 3 * 60),
            ("Pre-deployment assurance · VehNet v2.1 + Vehicles v3",
             {"dataset_id": "ds_vehicles_v3", "model_id": "mdl_vehnet_v21", "record_stream_id": "rs_uav07_front", "input_batch_id": "ib_sector7_dawn", "reference_id": "ref_plains_summer"},
             ["M1", "M2", "M3", "M4"], None, analyst, 38),
        ]
        asm_ids = []
        for n, (name, inputs, modules, access, user, minutes_ago) in enumerate(plan):
            # Derived ids: every instance of a hosted deployment seeds the identical world.
            asm = self.create_assessment({"name": name, **inputs, "modules": modules, "access_level_override": access, "seed": 1337}, user,
                                         created_at=now - timedelta(minutes=minutes_ago + 4), asm_id=derived_id("asm", "demo-seed", n))
            self._run(asm["id"], live=False, started=now - timedelta(minutes=minutes_ago + 3), finished=now - timedelta(minutes=minutes_ago))
            asm_ids.append(asm["id"])

        # Baseline: everything ACCEPT -> FINAL report.
        rep = self.generate_report(asm_ids[0], admin, at=now - timedelta(days=5) + timedelta(minutes=20), report_id=derived_id("rep", "demo-seed", 0))
        self.finalise_report(rep["id"], admin)
        # Supplier update: decisions made, draft report.
        for f in self.findings_for(asm_ids[1]):
            if f["recommended_disposition"] != "ACCEPT":
                self.decide(f["id"], "QUARANTINE", "Supplier could not explain the weight change. Model v2.2 rejected pending re-submission through the registered channel.", analyst,
                            at=now - timedelta(days=2) + timedelta(minutes=35))
        self.generate_report(asm_ids[1], analyst, at=now - timedelta(days=2) + timedelta(minutes=40), report_id=derived_id("rep", "demo-seed", 1))
        # Latest: a few decisions already taken, most still open.
        latest = self.findings_for(asm_ids[-1])
        wanted = {
            "M1.trigger.patch_repeat": ("QUARANTINE", "Patch visible on inspection of 12 samples. Quarantine all contributor C images pending source review."),
            "M1.dup.phash": ("REVIEW", "Duplicates confirmed; asked Arcadia Labs whether augmentation was applied before submission."),
            "M2.param_stats": ("ACCEPT", "Weak signal on its own; covered by the trigger-reconstruction finding."),
        }
        for f in latest:
            if f["check_id"] in wanted and not any(d["finding_id"] == f["id"] for d in self.store.list("decision")):
                d, j = wanted[f["check_id"]]
                self.decide(f["id"], d, j, analyst, at=now - timedelta(minutes=20))
        self.generate_report(asm_ids[-1], analyst, at=now - timedelta(minutes=12), report_id=derived_id("rep", "demo-seed", 2))

        for sc, seed, outs, mins in [("D1", 1337, ["ds_vehicles_v3"], 9 * 24 * 60), ("M1", 1337, ["mdl_vehnet_v21"], 8 * 24 * 60), ("I1", 1337, ["rs_uav07_front"], 7 * 24 * 60)]:
            self._record_attack_run(sc, seed, outs, "usr_admin", now - timedelta(minutes=mins))
        self.store.put("meta", "seed", {"seeded_at": utc_now(), "notice": DEMO_NOTICE})

    # ------------------------------------------------------------------ auth

    def login(self, username: str, password: str) -> tuple[str, dict]:
        user = next((u for u in self.store.list("user") if u["username"] == username), None)
        if not user or user.get("disabled") or not _check_password(password, user["password_hash"]):
            raise ApiError(401, "INVALID_CREDENTIALS", "Username or password is incorrect.")
        token = self._issue_token(user["id"])
        self.audit.append(AuditEvent.USER_LOGIN, {"username": username}, Actor(type="user", id=user["id"]))
        return token, self.public_user(user)

    def _issue_token(self, user_id: str, ttl_s: int = 12 * 3600) -> str:
        exp = int(time.time()) + ttl_s
        body = f"{user_id}.{exp}"
        sig = hmac.new(self._session_secret, body.encode(), hashlib.sha256).hexdigest()[:40]
        return f"{body}.{sig}"

    def session_user(self, token: str | None) -> dict | None:
        """Validate a signed session token (works on any instance; no server-side session table)."""
        if not token or token in self._revoked or token.count(".") != 2:
            return None
        user_id, exp, sig = token.split(".")
        good = hmac.new(self._session_secret, f"{user_id}.{exp}".encode(), hashlib.sha256).hexdigest()[:40]
        if not hmac.compare_digest(sig, good) or not exp.isdigit() or int(exp) < time.time():
            return None
        user = self.store.get("user", user_id)
        return user if user and not user.get("disabled") else None

    def logout(self, token: str) -> None:
        user = self.session_user(token)
        self._revoked.add(token)
        if user:
            self.audit.append(AuditEvent.USER_LOGOUT, {"username": user["username"]}, Actor(type="user", id=user["id"]))

    @staticmethod
    def public_user(u: dict) -> dict:
        return {k: u[k] for k in ("id", "username", "role", "display", "created_at", "disabled")}

    # --------------------------------------------------------------- assets

    def asset(self, asset_id: str) -> dict:
        a = self.store.get("asset", asset_id)
        if not a:
            raise ApiError(404, "NOT_FOUND", f"Asset {asset_id} not found.")
        return a

    def assets(self, type_: str | None = None) -> list[dict]:
        return [a for a in self.store.list("asset") if type_ is None or a["type"] == type_]

    # ---------------------------------------------------------- assessments

    def _context(self, asm: dict) -> AssessmentContext:
        inputs: dict[str, Any] = {"battery": BATTERY}
        refs: dict[str, AssetRef] = {}
        type_map = {"dataset": AssetType.DATASET, "model": AssetType.MODEL, "records": AssetType.RECORD_STREAM, "input_batch": AssetType.INPUT_BATCH, "reference": AssetType.REFERENCE}
        for name, field in INPUT_FIELD.items():
            aid = asm["inputs"].get(field)
            if not aid:
                continue
            a = self.asset(aid)
            inputs[name] = a
            refs[name] = AssetRef(type=type_map[name], id=aid, digest=a.get("digest"))
            if name == "records":
                inputs[name] = {"asset": a, "verification": self.store.get("stream", aid)["verification"]}
        return AssessmentContext(assessment_id=asm["id"], access_level=AccessLevel(asm["access_level_used"]), inputs=inputs, assets=refs,
                                 seed=asm["seed"], policy=DEFAULT_POLICY)

    def _access_for(self, inputs: dict, override: str | None) -> tuple[str, str | None]:
        if not inputs.get("model_id"):
            return "NONE", None
        detected = self.asset(inputs["model_id"])["detected_access_level"]
        if override:
            if AccessLevel(override).rank > AccessLevel(detected).rank:
                raise ApiError(400, "ACCESS_TOO_HIGH", f"Declared access {override} exceeds the detected {detected}; access can only be lowered.")
            return override, detected
        return detected, detected

    def preview(self, body: dict) -> dict:
        inputs = {f: body.get(f) for f in INPUT_FIELD.values() if body.get(f)}
        access, detected = self._access_for(inputs, body.get("access_level_override"))
        modules = []
        fake = {"id": "asm_preview", "inputs": inputs, "access_level_used": access, "seed": body.get("seed", 1337)}
        ctx = self._context(fake)
        sched = Scheduler(self.registry)
        for m in ["M1", "M2", "M3", "M4"]:
            missing = [i for i in MODULE_INPUTS[m] if i not in ctx.inputs]
            plan = [
                {"check_id": p.check_id, "name": CHECK_META[p.check_id][0], "will_run": p.will_run, "reason": p.reason, "fallback_check_id": p.fallback_check_id}
                for p in sched.preview(ModuleId(m), ctx)
            ] if not missing else []
            modules.append({"module": m, "name": MODULE_NAMES[m], "available": not missing,
                            "reason": "" if not missing else f"{MODULE_NAMES[m]} needs: {', '.join(missing).replace('_', ' ')}", "checks": plan})
        return {"access_level": access, "detected_access_level": detected, "modules": modules}

    def create_assessment(self, body: dict, user_id: str, created_at: datetime | None = None, asm_id: str | None = None) -> dict:
        name = (body.get("name") or "").strip()
        if not name:
            raise ApiError(400, "VALIDATION", "Assessment name is required.")
        inputs = {f: body.get(f) for f in INPUT_FIELD.values() if body.get(f)}
        for aid in inputs.values():
            self.asset(aid)
        modules = [m for m in body.get("modules", []) if m in MODULE_NAMES]
        if not modules:
            raise ApiError(400, "VALIDATION", "Select at least one module.")
        for m in modules:
            missing = [i for i in MODULE_INPUTS[m] if not inputs.get(INPUT_FIELD[i])]
            if missing:
                raise ApiError(400, "MODULE_INPUTS_MISSING", f"{MODULE_NAMES[m]} needs: {', '.join(missing)}.")
        access, detected = self._access_for(inputs, body.get("access_level_override"))
        asm_id = asm_id or new_id("asm")
        ts = format_ts(created_at) if created_at else utc_now()
        doc = {
            "id": asm_id, "name": name, "created_by": user_id, "created_at": ts, "status": "DRAFT", "inputs": inputs, "modules": modules,
            "access_level_used": access, "detected_access_level": detected, "access_level_override": body.get("access_level_override"),
            "seed": int(body.get("seed", 1337)), "started_at": None, "finished_at": None, "error": None, "module_runs": [], "views": {},
            "config_snapshot": {"seed": int(body.get("seed", 1337)), "policy_version": DEFAULT_POLICY.version, "policy_digest": DEFAULT_POLICY.digest(),
                                "thresholds_version": 1, "tool_version": __version__, "battery_digest": BATTERY["digest"], "demo": True},
            "demo": True,
        }
        self.store.put("assessment", asm_id, doc)
        self.audit.append(AuditEvent.ASSESSMENT_CREATED, {"assessment_id": asm_id, "name": name, "inputs": inputs, "modules": modules}, Actor(type="user", id=user_id))
        return doc

    def assessment(self, asm_id: str) -> dict:
        a = self.store.get("assessment", asm_id)
        if not a:
            raise ApiError(404, "NOT_FOUND", f"Assessment {asm_id} not found.")
        return a

    def start(self, asm_id: str, user_id: str) -> dict:
        asm = self.assessment(asm_id)
        if asm["status"] not in ("DRAFT",):
            raise ApiError(409, "INVALID_STATE", f"Assessment is {asm['status']}; only DRAFT assessments can be started.")
        asm["status"] = "QUEUED"
        asm["queued_by"] = user_id
        self.store.put("assessment", asm_id, asm)
        with self._cond:
            self._events[asm_id] = []
        # Serverless hosts freeze background threads once a response is sent, so there the
        # run is executed inside the streaming events request instead (claim_run).
        if not self.hosted:
            self.claim_run(asm_id)
        return asm

    def claim_run(self, asm_id: str) -> bool:
        """Start the run for a QUEUED assessment exactly once. Returns True if this call started it."""
        with self._run_lock:
            asm = self.assessment(asm_id)
            if asm["status"] != "QUEUED" or asm.get("claimed"):
                return False
            asm["claimed"] = True
            self.store.put("assessment", asm_id, asm)
        with self._cond:
            self._events.setdefault(asm_id, [])
        threading.Thread(target=self._run, args=(asm_id,), kwargs={"live": True, "user_id": asm.get("queued_by")}, daemon=True).start()
        return True

    def cancel(self, asm_id: str) -> dict:
        asm = self.assessment(asm_id)
        if asm["status"] in ("QUEUED", "RUNNING"):
            asm["cancel_requested"] = True
            self.store.put("assessment", asm_id, asm)
        return asm

    def _emit(self, asm_id: str, event: dict) -> None:
        with self._cond:
            self._events.setdefault(asm_id, []).append({**event, "t": utc_now()})
            self._cond.notify_all()

    def events_since(self, asm_id: str, index: int, timeout: float = 15.0) -> list[dict]:
        with self._cond:
            if len(self._events.get(asm_id, [])) <= index:
                self._cond.wait(timeout)
            return self._events.get(asm_id, [])[index:]

    def _run(self, asm_id: str, live: bool, started: datetime | None = None, finished: datetime | None = None, user_id: str | None = None) -> None:
        asm = self.assessment(asm_id)
        asm.update(status="RUNNING", started_at=format_ts(started) if started else utc_now())
        asm["module_runs"] = [{"module": m, "name": MODULE_NAMES[m], "status": "PENDING", "progress": 0.0, "checks": []} for m in asm["modules"]]
        self.store.put("assessment", asm_id, asm)
        actor = Actor(type="user", id=user_id) if user_id else None
        self.audit.append(AuditEvent.ASSESSMENT_STARTED, {"assessment_id": asm_id}, actor)
        self.audit.append(AuditEvent.ACCESS_LEVEL_SET, {"assessment_id": asm_id, "access_level": asm["access_level_used"], "detected": asm["detected_access_level"], "override": asm["access_level_override"]})
        self._emit(asm_id, {"type": "assessment_started", "modules": asm["modules"]})
        try:
            ctx = self._context(asm)
            sched = Scheduler(self.registry, _AuditTap(self, asm_id, live))
            for mr in asm["module_runs"]:
                if self.assessment(asm_id).get("cancel_requested"):
                    raise InterruptedError
                m = mr["module"]
                mr["status"] = "RUNNING"
                self.store.put("assessment", asm_id, asm)
                self._emit(asm_id, {"type": "module_started", "module": m, "checks": [{"id": c.id, "name": CHECK_META[c.id][0]} for c in self.registry.for_module(ModuleId(m))]})
                result = sched.run_module(ModuleId(m), ctx)
                findings = [f.model_copy(update={"created_at": format_ts(finished)}) if finished else f for f in result.findings]
                for f in findings:
                    self.store.put("finding", f.id, f.model_dump(mode="json"))
                    self.audit.append(AuditEvent.FINDING_CREATED, {"assessment_id": asm_id, "finding_id": f.id, "check_id": f.check_id,
                                                                   "status": f.status.value, "recommended_disposition": f.recommended_disposition.value})
                per_check = {}
                for f in findings:
                    per_check[f.check_id] = per_check.get(f.check_id, 0) + (f.status is FindingStatus.FLAGGED)
                mr.update(status=result.status.value, progress=1.0, checks=[
                    {"check_id": r.check_id, "name": CHECK_META[r.check_id][0], "requirement": CHECK_META[r.check_id][2], "version": r.version,
                     "status": r.status.value, "duration_ms": r.duration_ms, "message": r.message, "fallback_used": r.fallback_used,
                     "findings": per_check.get(r.check_id, 0), "parameters": r.parameters}
                    for r in result.check_runs])
                asm["views"].update(self._module_view(m, ctx))
                self.store.put("assessment", asm_id, asm)
                self._emit(asm_id, {"type": "module_completed", "module": m, "status": result.status.value, "findings": len(findings)})
            asm.update(status="COMPLETED", finished_at=format_ts(finished) if finished else utc_now())
            self.store.put("assessment", asm_id, asm)
            self.audit.append(AuditEvent.ASSESSMENT_COMPLETED, {"assessment_id": asm_id, "findings": len(self.findings_for(asm_id))})
            self._emit(asm_id, {"type": "assessment_completed", "status": "COMPLETED"})
        except InterruptedError:
            asm.update(status="CANCELLED", finished_at=utc_now())
            self.store.put("assessment", asm_id, asm)
            self._emit(asm_id, {"type": "assessment_completed", "status": "CANCELLED"})
        except Exception as exc:  # crash -> FAILED + audit (A10)
            asm.update(status="FAILED", finished_at=utc_now(), error=f"{type(exc).__name__}: {exc}")
            self.store.put("assessment", asm_id, asm)
            self.audit.append(AuditEvent.ASSESSMENT_FAILED, {"assessment_id": asm_id, "error": asm["error"]})
            self._emit(asm_id, {"type": "assessment_completed", "status": "FAILED", "error": asm["error"]})
            if not live:
                raise

    def _module_view(self, m: str, ctx: AssessmentContext) -> dict:
        if m == "M1":
            return {"data": data_view(ctx.inputs["dataset"]["id"])}
        if m == "M2":
            return {"model": model_view(ctx.inputs["model"], ctx.access_level.value)}
        if m == "M4":
            return {"shift": shift_view(ctx.inputs["input_batch"]["id"])}
        return {}

    # ------------------------------------------------------------- findings

    def findings_for(self, asm_id: str) -> list[dict]:
        return [f for f in self.store.list("finding") if f["assessment_id"] == asm_id]

    def decisions_for(self, finding_id: str | None = None) -> list[dict]:
        return [d for d in self.store.list("decision") if finding_id is None or d["finding_id"] == finding_id]

    def _decision_models(self) -> list[Decision]:
        return [Decision.model_validate({k: v for k, v in d.items() if k in Decision.model_fields}) for d in self.store.list("decision")]

    def enrich(self, f: dict, decisions: list[Decision] | None = None) -> dict:
        decisions = decisions if decisions is not None else self._decision_models()
        model = Finding.model_validate(f)
        mine = [d for d in decisions if d.finding_id == model.id]
        name, what, req = CHECK_META.get(model.check_id, (model.check_id, "", ""))
        asm = self.store.get("assessment", model.assessment_id) or {}
        return {
            **f,
            "check_name": name, "check_description": what, "requirement": req,
            "effective_disposition": effective_disposition(model, decisions).value,
            "unresolved": is_unresolved(model, decisions),
            "decision_count": len(mine),
            "latest_decision": mine[-1].model_dump(mode="json") if mine else None,
            "assessment_name": asm.get("name"),
            "asset_label": self._asset_label(model.affected_asset),
        }

    def _asset_label(self, ref: AssetRef) -> str:
        if ref.type is AssetType.CONTRIBUTOR:
            c = CONTRIBUTORS.get(ref.id)
            return f"{c['name']} ({ref.id.replace('contributor_', 'contributor ')})" if c else ref.id
        if ref.type is AssetType.INFERENCE_RECORD:
            return f"Record {ref.id.split('#')[1].split('@')[0]} · {ref.id.split('#')[0]}"
        a = self.store.get("asset", ref.id)
        return a["name"] if a else ref.id

    def finding(self, fid: str) -> dict:
        f = self.store.get("finding", fid)
        if not f:
            raise ApiError(404, "NOT_FOUND", f"Finding {fid} not found.")
        out = self.enrich(f)
        out["decisions"] = sorted(self.decisions_for(fid), key=lambda d: d["decided_at"], reverse=True)
        return out

    def decide(self, fid: str, decision: str, justification: str, user_id: str, at: datetime | None = None) -> dict:
        self.finding(fid)
        if decision not in ("ACCEPT", "REVIEW", "QUARANTINE"):
            raise ApiError(400, "VALIDATION", "Decision must be ACCEPT, REVIEW or QUARANTINE.")
        if not (justification or "").strip():
            raise ApiError(400, "VALIDATION", "A justification is required for every decision.")
        user = self.store.get("user", user_id) or {}
        d = Decision(id=new_id("dec"), finding_id=fid, analyst_id=user_id, decision=Disposition(decision), justification=justification.strip(),
                     decided_at=format_ts(at) if at else utc_now())
        doc = {**d.model_dump(mode="json"), "analyst_name": user.get("display", user_id)}
        self.store.put("decision", d.id, doc)
        self.audit.append(AuditEvent.ANALYST_DECISION, {"finding_id": fid, "decision_id": d.id, "decision": decision, "justification_sha256": sha256_bytes(d.justification.encode())},
                          Actor(type="user", id=user_id))
        return doc

    # -------------------------------------------------------------- summary

    def summary(self, asm_id: str) -> dict:
        asm = self.assessment(asm_id)
        decisions = self._decision_models()
        raw = self.findings_for(asm_id)
        models = [Finding.model_validate(f) for f in raw]
        eff = {f.id: effective_disposition(f, decisions) for f in models}
        tiles = []
        for key, (label, types, module) in TILE_GROUPS.items():
            fs = [f for f in models if f.affected_asset.type.value in types]
            assessed = module in asm["modules"] and (key != "contributors" or bool(asm["inputs"].get("dataset_id")))
            if not assessed:
                tiles.append({"key": key, "label": label, "assessed": False})
                continue
            worst = most_severe(eff[f.id] for f in fs)
            drivers = [f for f in fs if eff[f.id] is worst]
            tile = {
                "key": key, "label": label, "assessed": True, "module": module, "disposition": worst.value,
                "confidence": max((f.confidence for f in drivers), default=None), "findings": len(fs),
                "coverage_gaps": sorted({f.check_id for f in fs if f.status is FindingStatus.UNAVAILABLE}),
                "top_issue": CHECK_META[max(drivers, key=lambda f: (f.severity.rank, f.confidence)).check_id][0] if drivers and worst is not Disposition.ACCEPT else None,
                "top_reason": max(drivers, key=lambda f: (f.severity.rank, f.confidence)).reason if drivers and worst is not Disposition.ACCEPT else None,
            }
            if key == "contributors":
                verdicts = asset_verdicts(fs, decisions)
                if verdicts:
                    w = verdicts[0]
                    tile["worst"] = {"id": w.asset.id, "name": CONTRIBUTORS.get(w.asset.id, {}).get("name", w.asset.id), "disposition": w.disposition.value}
                elif not asm["views"].get("data", {}).get("has_metadata", True):
                    tile["note"] = "No contributor metadata"
            if key in ("dataset", "model", "records", "input_batch"):
                field = {"dataset": "dataset_id", "model": "model_id", "records": "record_stream_id", "input_batch": "input_batch_id"}[key]
                aid = asm["inputs"].get(field)
                tile["asset"] = {"id": aid, "name": self.asset(aid)["name"]} if aid else None
            tiles.append(tile)
        overall = most_severe(Disposition(t["disposition"]) for t in tiles if t.get("assessed"))
        by = lambda key: {k: sum(1 for f in models if key(f) == k) for k in sorted({key(f) for f in models})}
        unresolved = [f.id for f in models if is_unresolved(f, decisions)]
        return {
            "assessment_id": asm_id, "status": asm["status"], "overall_disposition": overall.value if models or tiles else None,
            "tiles": tiles,
            "counts": {
                "total": len(models),
                "by_effective_disposition": {d.value: sum(1 for f in models if eff[f.id] is d) for d in Disposition},
                "by_recommended_disposition": {d.value: sum(1 for f in models if f.recommended_disposition is d) for d in Disposition},
                "by_severity": {s: sum(1 for f in models if f.severity.value == s) for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW")},
                "by_module": by(lambda f: f.module.value),
                "unavailable": sum(1 for f in models if f.status is FindingStatus.UNAVAILABLE),
            },
            "unresolved": len(unresolved),
            "unresolved_ids": unresolved,
        }

    def assessment_full(self, asm_id: str) -> dict:
        asm = copy.deepcopy(self.assessment(asm_id))
        asm["summary"] = self.summary(asm_id) if asm["status"] == "COMPLETED" else None
        asm["inputs_detail"] = [
            {"role": name, "id": asm["inputs"][field], "name": self.asset(asm["inputs"][field])["name"], "type": self.asset(asm["inputs"][field])["type"],
             "digest": self.asset(asm["inputs"][field]).get("digest")}
            for name, field in INPUT_FIELD.items() if asm["inputs"].get(field)
        ]
        creator = self.store.get("user", asm["created_by"]) or {}
        asm["created_by_name"] = creator.get("display", asm["created_by"])
        reps = [r for r in self.store.list("report") if r["assessment_id"] == asm_id]
        asm["report"] = {"id": reps[-1]["id"], "status": reps[-1]["status"]} if reps else None
        asm.pop("views", None)
        return asm

    def list_assessments(self) -> list[dict]:
        out = []
        for a in reversed(self.store.list("assessment")):
            s = self.summary(a["id"]) if a["status"] == "COMPLETED" else None
            reps = [r for r in self.store.list("report") if r["assessment_id"] == a["id"]]
            creator = self.store.get("user", a["created_by"]) or {}
            out.append({
                "id": a["id"], "name": a["name"], "status": a["status"], "created_at": a["created_at"], "finished_at": a["finished_at"],
                "created_by": a["created_by"], "created_by_name": creator.get("display", a["created_by"]), "modules": a["modules"],
                "overall_disposition": s["overall_disposition"] if s else None, "unresolved": s["unresolved"] if s else 0,
                "findings": s["counts"]["total"] if s else 0, "report_status": reps[-1]["status"] if reps else None,
                "access_level_used": a["access_level_used"],
            })
        return out

    def view(self, asm_id: str, key: str) -> dict:
        asm = self.assessment(asm_id)
        v = asm["views"].get(key)
        if v is None:
            raise ApiError(404, "MODULE_NOT_RUN", f"This assessment did not include the {key} module.")
        return v

    def model_detail(self, asm_id: str) -> dict:
        asm = self.assessment(asm_id)
        v = copy.deepcopy(self.view(asm_id, "model"))
        run = next((m for m in asm["module_runs"] if m["module"] == "M2"), {"checks": []})
        v["checks_run"] = [c for c in run["checks"] if c["status"] == "COMPLETED"]
        v["checks_unavailable"] = [c for c in run["checks"] if c["status"] != "COMPLETED"]
        v["model"] = {k: self.asset(asm["inputs"]["model_id"]).get(k) for k in ("id", "name", "format", "supplier", "task")}
        return v

    def provenance(self, asm_id: str) -> dict:
        asm = self.assessment(asm_id)
        rs = asm["inputs"].get("record_stream_id")
        if "M3" not in asm["modules"] or not rs:
            raise ApiError(404, "MODULE_NOT_RUN", "This assessment did not include inference provenance.")
        ver = self.store.get("stream", rs)["verification"]
        counts: dict[str, int] = {}
        for r in ver:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        a = self.asset(rs)
        return {"stream": {"id": rs, "name": a["name"], "stream_id": a["stream_id"], "n_records": a["n_records"], "signer_key_ids": a["signer_key_ids"]},
                "status_counts": counts, "total": len(ver), "verified": counts.get("VERIFIED", 0)}

    def records(self, asm_id: str, status: str | None = None) -> list[dict]:
        rs = self.assessment(asm_id)["inputs"].get("record_stream_id")
        ver = self.store.get("stream", rs)["verification"]
        return [
            {"position": r["position"], "sequence": r["record"].get("sequence"), "timestamp": r["record"].get("timestamp"), "status": r["status"],
             "model_id": r["record"].get("model", {}).get("id"), "input_sha256": r["record"].get("input", {}).get("sha256"),
             "top_class": r["record"].get("output", {}).get("top_k", [{}])[0].get("class"),
             "top_score": r["record"].get("output", {}).get("top_k", [{}])[0].get("score")}
            for r in ver if not status or r["status"] == status
        ]

    def record(self, asm_id: str, position: int) -> dict:
        rs = self.assessment(asm_id)["inputs"].get("record_stream_id")
        ver = self.store.get("stream", rs)["verification"]
        if not 0 <= position < len(ver):
            raise ApiError(404, "NOT_FOUND", "Record not found.")
        return ver[position]

    def verify_edited_record(self, record: dict) -> dict:
        return verify_single(self.keys, record)

    # -------------------------------------------------------------- reports

    def _audit_status(self) -> dict:
        now = time.time()
        if self._verify_cache and now - self._verify_cache[0] < 5:
            return self._verify_cache[1]
        r = self.audit.verify().to_dict()
        r["verified_at"] = utc_now()
        self._verify_cache = (now, r)
        return r

    def generate_report(self, asm_id: str, user_id: str, at: datetime | None = None, report_id: str | None = None) -> dict:
        asm = self.assessment(asm_id)
        if asm["status"] != "COMPLETED":
            raise ApiError(409, "INVALID_STATE", "Reports can only be generated for completed assessments.")
        summary = self.summary(asm_id)
        decisions = self._decision_models()
        findings = [self.enrich(f, decisions) for f in self.findings_for(asm_id)]
        head, count = self.audit.head()
        chain = self._audit_status()
        runs = {m["module"]: m for m in asm["module_runs"]}

        def mod(m: str, extra: dict) -> dict:
            if m not in runs:
                return {"status": "NOT_RUN", "findings": []}
            return {"status": runs[m]["status"], "findings": [f for f in findings if f["module"] == m], **extra}

        views = asm["views"]
        shift = views.get("shift") or {}
        model = views.get("model") or {}
        prov = self.provenance(asm_id) if "M3" in runs else {}
        report_id = report_id or new_id("rep")
        body = {
            "report_id": report_id, "schema_version": "1.0.0", "generated_at": format_ts(at) if at else utc_now(), "status": "DRAFT",
            "demo": True, "demo_notice": DEMO_NOTICE,
            "tool": {"name": TOOL_NAME, "version": __version__, "code_digest": sha256_bytes(f"aura-cv-{__version__}".encode())},
            "assessment": {"id": asm_id, "name": asm["name"], "created_by": asm["created_by"], "started_at": asm["started_at"], "finished_at": asm["finished_at"]},
            "inputs": [{"type": i["type"], "id": i["id"], "name": i["name"], "digest": i["digest"]} for i in self.assessment_full(asm_id)["inputs_detail"]],
            "assessment_context": {
                "offline": True, "model_access_level": asm["access_level_used"],
                "reference_battery_digest": BATTERY["digest"],
                "checks_run": [{"check_id": c["check_id"], "version": c["version"], "parameters": c["parameters"]} for m in asm["module_runs"] for c in m["checks"] if c["status"] == "COMPLETED"],
                "checks_unavailable": [{"check_id": c["check_id"], "reason": c["message"], "fallback_used": c["fallback_used"]} for m in asm["module_runs"] for c in m["checks"] if c["status"] != "COMPLETED"],
                "config_snapshot": asm["config_snapshot"],
            },
            "summary": {"overall_disposition": summary["overall_disposition"], "asset_verdicts": [t for t in summary["tiles"] if t.get("assessed")],
                        "finding_counts": summary["counts"]["by_effective_disposition"], "unresolved": summary["unresolved"]},
            "modules": {
                "data_integrity": mod("M1", {"source_risk": (views.get("data") or {}).get("source_risk", [])}),
                "model_integrity": mod("M2", {"access_level": model.get("access_level"), "confidence": model.get("confidence"), "limitations": model.get("limitations", [])}),
                "inference_provenance": mod("M3", {"records_total": prov.get("total"), "status_counts": prov.get("status_counts")}),
                "distribution_shift": mod("M4", {"shift_detected": shift.get("shift_detected"), "verdict": shift.get("verdict"), "calibrated_risk": shift.get("calibrated_risk"),
                                                 "calibration_quality": shift.get("calibration"), "characterisation": shift.get("characterisation"),
                                                 "rules_fired": [r for r in shift.get("rules", []) if r["fired"]]}),
                "governance": {"analyst_decisions": [d.model_dump(mode="json") for d in decisions if any(f["id"] == d.finding_id for f in findings)]},
            },
            "recommended_actions": self._actions(summary, findings),
            "coverage_statement": COVERAGE,
            "audit": {"log_head_hash": head, "entry_count": count, "chain_verified": chain["valid"]},
        }
        report = self._sign_report(body)
        doc = {"id": report_id, "assessment_id": asm_id, "status": "DRAFT", "created_by": user_id, "created_at": body["generated_at"],
               "report_digest": sha256_canonical(report), "key_id": report["signature"]["key_id"], "audit_head_hash": head, "json": report}
        self.store.put("report", report_id, doc)
        self.audit.append(AuditEvent.REPORT_GENERATED, {"report_id": report_id, "assessment_id": asm_id, "report_digest": doc["report_digest"]}, Actor(type="user", id=user_id))
        return self.report_meta(doc)

    def _actions(self, summary: dict, findings: list[dict]) -> list[str]:
        acts = []
        for f in sorted(findings, key=lambda f: ({"QUARANTINE": 0, "REVIEW": 1, "ACCEPT": 2}[f["effective_disposition"]], -f["confidence"])):
            if f["effective_disposition"] == "QUARANTINE" and len(acts) < 6:
                acts.append(f"Quarantine {f['asset_label']}: {f['check_name'].lower()} ({f['severity'].lower()} severity, confidence {f['confidence']:.2f}).")
        if summary["unresolved"]:
            acts.append(f"Resolve the {summary['unresolved']} findings still awaiting an analyst decision before finalising.")
        if summary["counts"]["unavailable"]:
            acts.append(f"Close {summary['counts']['unavailable']} coverage gap(s): some checks could not run with the inputs or access supplied.")
        if not acts:
            acts.append("No action required: accept the assessed assets for their declared use.")
        return acts

    def _sign_report(self, body: dict) -> dict:
        body = {k: v for k, v in body.items() if k != "signature"}
        key_id, sig = self.keys.sign(KeyPurpose.REPORT, canonicalize(body))
        return {**body, "signature": {"algorithm": "Ed25519", "key_id": key_id, "value": sig}}

    def report_meta(self, doc: dict) -> dict:
        asm = self.store.get("assessment", doc["assessment_id"]) or {}
        creator = self.store.get("user", doc["created_by"]) or {}
        return {k: v for k, v in doc.items() if k != "json"} | {"assessment_name": asm.get("name"), "created_by_name": creator.get("display"),
                                                                 "overall_disposition": doc["json"]["summary"]["overall_disposition"], "unresolved": doc["json"]["summary"]["unresolved"]}

    def report(self, rid: str) -> dict:
        d = self.store.get("report", rid)
        if not d:
            raise ApiError(404, "NOT_FOUND", f"Report {rid} not found.")
        return d

    def reports(self) -> list[dict]:
        return [self.report_meta(r) for r in reversed(self.store.list("report"))]

    def finalise_report(self, rid: str, user_id: str) -> dict:
        doc = self.report(rid)
        if doc["status"] == "FINAL":
            raise ApiError(409, "ALREADY_FINAL", "This report is already FINAL and cannot be changed.")
        decisions = self._decision_models()
        open_ = [self.enrich(f, decisions) for f in self.findings_for(doc["assessment_id"])]
        open_ = [{"id": f["id"], "check_name": f["check_name"], "recommended_disposition": f["recommended_disposition"], "asset_label": f["asset_label"]} for f in open_ if f["unresolved"]]
        if open_:
            raise ApiError(409, "UNRESOLVED_FINDINGS", f"{len(open_)} REVIEW/QUARANTINE findings have no analyst decision yet.", {"unresolved": open_})
        body = {**doc["json"], "status": "FINAL", "finalised_at": utc_now()}
        report = self._sign_report(body)
        doc.update(status="FINAL", json=report, report_digest=sha256_canonical(report), key_id=report["signature"]["key_id"])
        self.store.put("report", rid, doc)
        self.audit.append(AuditEvent.REPORT_FINALISED, {"report_id": rid, "report_digest": doc["report_digest"]}, Actor(type="user", id=user_id))
        return self.report_meta(doc)

    def verify_report(self, report: dict) -> dict:
        sig = report.get("signature") or {}
        body = {k: v for k, v in report.items() if k != "signature"}
        checks = []
        required = ["report_id", "schema_version", "generated_at", "tool", "inputs", "assessment_context", "summary", "modules", "coverage_statement", "audit", "signature"]
        missing = [k for k in required if k not in report]
        checks.append({"step": "Schema (required sections)", "passed": not missing, "detail": "all sections present" if not missing else f"missing: {', '.join(missing)}"})
        try:
            ok = self.keys.verify(sig.get("key_id", ""), canonicalize(body), sig.get("value", ""), purpose=KeyPurpose.REPORT)
            checks.append({"step": "Signing key known", "passed": True, "detail": sig.get("key_id")})
            checks.append({"step": "Signature", "passed": ok, "detail": "Ed25519 signature valid" if ok else "signature does NOT match report contents"})
        except UnknownKeyError:
            checks.append({"step": "Signing key known", "passed": False, "detail": f"{sig.get('key_id')} is not a registered report key"})
            checks.append({"step": "Signature", "passed": None, "detail": "not checkable without a known key"})
        head = (report.get("audit") or {}).get("log_head_hash")
        present = head is not None and verify_log_file(self.audit.path, self.keys, expected_head=head).valid
        checks.append({"step": "Audit head present in current log", "passed": present, "detail": head or "no head hash in report"})
        return {"valid": all(c["passed"] for c in checks), "checks": checks}

    # --------------------------------------------------------------- audit

    def audit_entries(self, event: str | None, q: str | None, page: int, page_size: int) -> dict:
        items = list(self.audit.entries())
        items.reverse()
        rows = [e.model_dump(mode="json") for e in items if (not event or e.event.value == event)]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in str(r["payload"]).lower() or ql in r["actor"]["id"].lower()]
        users = {u["id"]: u["display"] for u in self.store.list("user")}
        for r in rows:
            r["actor_name"] = users.get(r["actor"]["id"], r["actor"]["id"])
        start = (page - 1) * page_size
        return {"items": rows[start:start + page_size], "page": page, "page_size": page_size, "total": len(rows)}

    def audit_verify(self, expected_head: str | None = None) -> dict:
        r = self.audit.verify(expected_head=expected_head).to_dict()
        r["verified_at"] = utc_now()
        self._verify_cache = (time.time(), r)
        return r

    # ------------------------------------------------------------ attack lab

    def _record_attack_run(self, scenario: str, seed: int, outputs: list[str], user_id: str, at: datetime | None = None) -> dict:
        rid = new_id("atk")
        doc = {"id": rid, "scenario_id": scenario, "seed": seed, "output_asset_ids": outputs, "created_at": format_ts(at) if at else utc_now(),
               "created_by": user_id, "status": "COMPLETED", "manifest_digest": sha256_bytes(f"manifest-{scenario}-{seed}".encode()), "demo": True}
        self.store.put("attackrun", rid, doc)
        self.audit.append(AuditEvent.ATTACK_SCENARIO_GENERATED, {"attack_run_id": rid, "scenario_id": scenario, "seed": seed, "outputs": outputs}, Actor(type="user", id=user_id))
        return doc
