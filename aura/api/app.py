"""FastAPI application (CLAUDE.md A11), demo build. Binds to 127.0.0.1 only.

Serves the JSON API under /api/v1 and the built UI (ui/dist) at "/".
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from aura import __version__
from aura.config import HOSTED, REPO_ROOT, get_settings
from aura.core import netguard
from aura.core.policy import DEFAULT_POLICY
from aura.core.selfcheck import run_selfcheck
from aura.demo import DEMO_NOTICE
from aura.demo.catalog import BATTERY, CHECK_META, CONTRIBUTORS
from aura.demo.images import png_bytes, trigger_png
from aura.m5_governance.coverage import COVERAGE
from aura.api.engine import ApiError, Engine

COOKIE = "aura_session"

SCENARIOS = [
    {"id": "D1", "group": "Data", "name": "Patch trigger", "description": "Stamp a visible patch on a fraction of one contributor's images and relabel them to a target class.",
     "params": {"patch_size_px": 14, "position": "bottom-right", "target_class": "civilian_car", "poison_rate": 0.04, "contributor": "contributor_C"}},
    {"id": "D2", "group": "Data", "name": "Blended trigger", "description": "Alpha-blend a faint pattern into a subset of images.", "params": {"alpha": 0.08, "poison_rate": 0.03}},
    {"id": "D3", "group": "Data", "name": "Random label flip", "description": "Flip labels uniformly at random for one contributor.", "params": {"flip_rate": 0.025, "contributor": "contributor_E"}},
    {"id": "D4", "group": "Data", "name": "Systematic relabel", "description": "One contributor maps class X to class Y.", "params": {"source_class": "truck", "target_class": "civilian_car", "rate": 0.18}},
    {"id": "D5", "group": "Data", "name": "Near-duplicate flood", "description": "Insert augmented copies (crop, brightness, flip, JPEG).", "params": {"copies": 64, "contributor": "contributor_D"}},
    {"id": "D6", "group": "Data", "name": "OOD insertion", "description": "Insert images from an unrelated domain.", "params": {"count": 12, "contributor": "contributor_B"}},
    {"id": "D7", "group": "Data", "name": "Mixed contributor", "description": "Combine several data attacks in one contributor.", "params": {"attacks": ["D1", "D4"]}},
    {"id": "M1", "group": "Model", "name": "Backdoored model", "description": "Fine-tune a clean model on D1 data (test-model creation only).", "params": {"epochs": 3, "base_model": "VehNet-R18 v2.0 (clean)"}},
    {"id": "M2", "group": "Model", "name": "Substituted model", "description": "Swap in a different checkpoint with the same interface.", "params": {"replacement": "VehNet-R18 v2.2"}},
    {"id": "M3", "group": "Model", "name": "Modified weights", "description": "Perturb a subset of weights in one layer.", "params": {"layer": "layer4.1", "fraction": 0.02}},
    {"id": "M4", "group": "Model", "name": "Clean control", "description": "Unmodified model for false-positive measurement.", "params": {}},
    {"id": "I1", "group": "Records", "name": "Alter field", "description": "Edit an output field after signing.", "params": {"records": 2}},
    {"id": "I2", "group": "Records", "name": "Substitute record", "description": "Swap in a valid record from another image/stream.", "params": {"records": 1}},
    {"id": "I3", "group": "Records", "name": "Replay", "description": "Re-insert earlier records.", "params": {"records": 2}},
    {"id": "I4", "group": "Records", "name": "Delete / reorder", "description": "Remove records from the stream.", "params": {"records": 1}},
    {"id": "I5", "group": "Records", "name": "Forge with unknown key", "description": "Sign a record with a key that is not registered.", "params": {"records": 1}},
    {"id": "I6", "group": "Records", "name": "Model / config swap", "description": "Genuine records produced by an unregistered model or config.", "params": {"records": 2}},
    {"id": "S1", "group": "Shift", "name": "Natural-style shift", "description": "Brightness, blur, haze, noise, colour cast, JPEG, resolution.", "params": {"haze": 0.28, "gamma": 0.62}},
    {"id": "S2", "group": "Shift", "name": "Different source", "description": "Images from a different source dataset.", "params": {}},
    {"id": "S3", "group": "Shift", "name": "Adversarial perturbation", "description": "Offline FGSM / PGD perturbation.", "params": {"epsilon": 0.03, "steps": 10}},
    {"id": "S4", "group": "Shift", "name": "Localised patch on subset", "description": "Structured perturbation on a subset of images.", "params": {"fraction": 0.14}},
    {"id": "S5", "group": "Shift", "name": "Clean control", "description": "Held-out images from the reference distribution.", "params": {}},
    {"id": "L1", "group": "Audit log", "name": "Edit entry", "description": "Edit one entry in a copy of the log.", "params": {}},
    {"id": "L2", "group": "Audit log", "name": "Delete middle entry", "description": "Delete an entry from a copy of the log.", "params": {}},
    {"id": "L3", "group": "Audit log", "name": "Truncate tail", "description": "Truncate a copy of the log.", "params": {}},
]
SCENARIO_OUTPUTS = {"D": ["ds_vehicles_v3"], "M": ["mdl_vehnet_v21"], "I": ["rs_uav07_front"], "S": ["ib_sector7_dawn"], "L": []}


def _interleave(items: list[dict]) -> list[dict]:
    """Within each severity level, alternate modules so one module cannot fill the queue."""
    out: list[dict] = []
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        by_mod: dict[str, list[dict]] = {}
        for f in items:
            if f["severity"] == sev:
                by_mod.setdefault(f["module"], []).append(f)
        while any(by_mod.values()):
            for m in sorted(by_mod):
                if by_mod[m]:
                    out.append(by_mod[m].pop(0))
    return out


def create_app() -> FastAPI:
    if not HOSTED:
        # R-CON-1: this process never talks to the network. A hosted demo runs inside the
        # provider's runtime, which needs its own sockets; it is labelled "not air-gapped".
        netguard.install()
    engine = Engine(get_settings())
    app = FastAPI(title="AURA-CV", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.engine = engine

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}})

    def user(request: Request) -> dict:
        u = engine.session_user(request.cookies.get(COOKIE))
        if not u:
            raise ApiError(401, "UNAUTHENTICATED", "Please sign in.")
        return u

    def admin(u: dict = Depends(user)) -> dict:
        if u["role"] != "ADMIN":
            raise ApiError(403, "FORBIDDEN", "This action needs the ADMIN role.")
        return u

    api = "/api/v1"

    # --------------------------------------------------------------- system
    @app.get(f"{api}/health")
    def health():
        return {"status": "ok", "version": __version__, "demo": True, "hosted": HOSTED}

    @app.get(f"{api}/system/status")
    def status(u: dict = Depends(user)):
        has_route, route_detail = netguard.route_exists()
        audit = engine._audit_status()
        ref = next((a for a in engine.assets("reference") if a.get("is_default")), None)
        return {
            "demo": True, "demo_notice": DEMO_NOTICE, "version": __version__, "hosted": HOSTED,
            "network": {"guard_active": netguard.guard_blocks_outbound(), "air_gapped": not has_route, "detail": route_detail},
            "keys": {"active": sum(1 for k in engine.keys.all() if k.active), "total": len(engine.keys.all())},
            "reference": {"id": ref["id"], "name": ref["name"]} if ref else None,
            "audit": {"valid": audit["valid"], "entries": audit["entries_checked"], "verified_at": audit["verified_at"], "head_hash": audit["head_hash"]},
            "battery": {"version": BATTERY["version"], "digest": BATTERY["digest"]},
        }

    @app.get(f"{api}/system/selfcheck")
    def selfcheck(u: dict = Depends(user)):
        items = run_selfcheck()
        return {"items": [i.to_dict() for i in items]}

    @app.get(f"{api}/system/info")
    def info(u: dict = Depends(user)):
        return {"version": __version__, "python": sys.version.split()[0], "demo": True}

    # ----------------------------------------------------------------- auth
    @app.post(f"{api}/auth/login")
    async def login(request: Request, response: Response):
        body = await request.json()
        token, u = engine.login(body.get("username", ""), body.get("password", ""))
        secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
        response.set_cookie(COOKIE, token, httponly=True, samesite="strict", secure=secure, max_age=12 * 3600)
        return u

    @app.post(f"{api}/auth/logout")
    def logout(request: Request, response: Response):
        engine.logout(request.cookies.get(COOKIE, ""))
        response.delete_cookie(COOKIE)
        return {"ok": True}

    @app.get(f"{api}/auth/me")
    def me(u: dict = Depends(user)):
        return engine.public_user(u)

    @app.get(f"{api}/users")
    def users(u: dict = Depends(admin)):
        return {"items": [engine.public_user(x) for x in engine.store.list("user")]}

    @app.get(f"{api}/keys")
    def keys(u: dict = Depends(user)):
        return {"items": [k.model_dump(mode="json") for k in engine.keys.all()]}

    # ------------------------------------------------------------ dashboard
    @app.get(f"{api}/dashboard")
    def dashboard(u: dict = Depends(user)):
        items = engine.list_assessments()
        completed = [a for a in items if a["status"] == "COMPLETED"]
        full = [a for a in completed if len(a["modules"]) >= 3]
        latest = (full or completed or [None])[0]
        out: dict[str, Any] = {"recent": items[:8], "latest": None}
        if latest:
            asm = engine.assessment_full(latest["id"])
            fs = [engine.enrich(f) for f in engine.findings_for(latest["id"])]
            attention = _interleave(sorted([f for f in fs if f["unresolved"]], key=lambda f: ({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[f["severity"]], -f["confidence"])))
            views = engine.assessment(latest["id"])["views"]
            health: dict[str, Any] = {}
            if "data" in views:
                sr = views["data"]["source_risk"]
                health["data"] = {"worst": sr[0] if sr else None, "counts": views["data"]["counts_by_attack"], "flagged": views["data"]["totals"]["flagged"], "images": views["data"]["totals"]["images"]}
            if "model" in views:
                md = engine.model_detail(latest["id"])
                health["model"] = {"access_level": md["access_level"], "digest_match": md["identity"]["digest_match"], "fingerprint": md["identity"]["fingerprint_agreement"],
                                   "backdoor": next((t for t in (md["triggers"] or []) if t["anomalous"]), None), "unavailable": len(md["checks_unavailable"])}
            if "M3" in asm["modules"]:
                p = engine.provenance(latest["id"])
                failures = {k: v for k, v in p["status_counts"].items() if k != "VERIFIED"}
                health["provenance"] = {"verified": p["verified"], "total": p["total"], "failed": p["total"] - p["verified"],
                                        "top_failure": max(failures, key=failures.get) if failures else None, "status_counts": p["status_counts"]}
            if "shift" in views:
                s = views["shift"]
                health["shift"] = {"verdict": s["verdict"], "calibrated_risk": s["calibrated_risk"], "characterisation": s["characterisation"].split(". ")[0] + "."}
            out["latest"] = {"assessment": asm, "attention": attention[:12], "attention_total": len(attention), "health": health}
        return out

    # ---------------------------------------------------------- assessments
    @app.get(f"{api}/assessments")
    def assessments(u: dict = Depends(user)):
        items = engine.list_assessments()
        return {"items": items, "page": 1, "page_size": len(items), "total": len(items)}

    @app.post(f"{api}/assessments/preview")
    async def preview(request: Request, u: dict = Depends(user)):
        return engine.preview(await request.json())

    @app.post(f"{api}/assessments", status_code=201)
    async def create(request: Request, u: dict = Depends(user)):
        return engine.create_assessment(await request.json(), u["id"])

    @app.post(f"{api}/assessments/{{asm_id}}/start", status_code=202)
    def start(asm_id: str, u: dict = Depends(user)):
        return engine.start(asm_id, u["id"])

    @app.post(f"{api}/assessments/{{asm_id}}/cancel")
    def cancel(asm_id: str, u: dict = Depends(user)):
        return engine.cancel(asm_id)

    @app.get(f"{api}/assessments/{{asm_id}}")
    def assessment(asm_id: str, u: dict = Depends(user)):
        return engine.assessment_full(asm_id)

    @app.get(f"{api}/assessments/{{asm_id}}/summary")
    def summary(asm_id: str, u: dict = Depends(user)):
        return engine.summary(asm_id)

    @app.get(f"{api}/assessments/{{asm_id}}/events")
    async def events(asm_id: str, request: Request, u: dict = Depends(user)):
        engine.assessment(asm_id)
        engine.claim_run(asm_id)  # no-op unless QUEUED and unclaimed (hosted mode)

        async def gen():
            idx = 0
            while True:
                if await request.is_disconnected():
                    return
                batch = await asyncio.to_thread(engine.events_since, asm_id, idx, 10.0)
                if not batch:
                    status = engine.assessment(asm_id)["status"]
                    if status in ("COMPLETED", "FAILED", "CANCELLED"):
                        yield f"data: {json.dumps({'type': 'assessment_completed', 'status': status})}\n\n"
                        return
                    yield ": keep-alive\n\n"
                    continue
                for ev in batch:
                    yield f"data: {json.dumps(ev)}\n\n"
                    idx += 1
                    if ev["type"] == "assessment_completed":
                        return

        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})

    @app.get(f"{api}/assessments/{{asm_id}}/findings")
    def asm_findings(asm_id: str, u: dict = Depends(user)):
        return {"items": _sort([engine.enrich(f) for f in engine.findings_for(asm_id)])}

    @app.get(f"{api}/assessments/{{asm_id}}/data")
    def data(asm_id: str, u: dict = Depends(user)):
        return engine.view(asm_id, "data")

    @app.get(f"{api}/assessments/{{asm_id}}/model")
    def model(asm_id: str, u: dict = Depends(user)):
        return engine.model_detail(asm_id)

    @app.get(f"{api}/assessments/{{asm_id}}/shift")
    def shift(asm_id: str, u: dict = Depends(user)):
        return engine.view(asm_id, "shift")

    @app.get(f"{api}/assessments/{{asm_id}}/provenance")
    def provenance(asm_id: str, u: dict = Depends(user)):
        return engine.provenance(asm_id)

    @app.get(f"{api}/assessments/{{asm_id}}/provenance/records")
    def records(asm_id: str, status: str | None = None, u: dict = Depends(user)):
        items = engine.records(asm_id, status)
        return {"items": items, "total": len(items)}

    @app.get(f"{api}/assessments/{{asm_id}}/provenance/records/{{position}}")
    def record(asm_id: str, position: int, u: dict = Depends(user)):
        return engine.record(asm_id, position)

    @app.post(f"{api}/provenance/verify-record")
    async def verify_record(request: Request, u: dict = Depends(user)):
        return engine.verify_edited_record((await request.json())["record"])

    # ------------------------------------------------------------- findings
    def _sort(items):
        return sorted(items, key=lambda f: (not f["unresolved"], {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[f["severity"]], -f["confidence"]))

    @app.get(f"{api}/findings")
    def findings(u: dict = Depends(user), module: str | None = None, disposition: str | None = None, unresolved: bool = False, status: str | None = None, q: str | None = None):
        items = [engine.enrich(f) for f in engine.store.list("finding")]
        if module:
            items = [f for f in items if f["module"] == module]
        if disposition:
            items = [f for f in items if f["effective_disposition"] == disposition]
        if status:
            items = [f for f in items if f["status"] == status]
        if unresolved:
            items = [f for f in items if f["unresolved"]]
        if q:
            ql = q.lower()
            items = [f for f in items if ql in f["reason"].lower() or ql in f["check_id"].lower() or ql in f["asset_label"].lower()]
        return {"items": _sort(items), "total": len(items)}

    @app.get(f"{api}/findings/{{fid}}")
    def finding(fid: str, u: dict = Depends(user)):
        return engine.finding(fid)

    @app.post(f"{api}/findings/{{fid}}/decisions", status_code=201)
    async def decide(fid: str, request: Request, u: dict = Depends(user)):
        body = await request.json()
        engine.decide(fid, body.get("decision", ""), body.get("justification", ""), u["id"])
        return engine.finding(fid)

    # --------------------------------------------------------------- assets
    @app.get(f"{api}/assets")
    def assets(type: str | None = None, u: dict = Depends(user)):
        return {"items": engine.assets(type)}

    @app.get(f"{api}/assets/{{asset_id}}")
    def asset(asset_id: str, u: dict = Depends(user)):
        return engine.asset(asset_id)

    @app.get(f"{api}/contributors")
    def contributors(u: dict = Depends(user)):
        return {"items": [{"id": k, **v} for k, v in CONTRIBUTORS.items()]}

    @app.get(f"{api}/images/{{sample_id}}.png")
    def image(sample_id: str, size: int = Query(224, ge=32, le=448)):
        if not all(ch.isalnum() or ch == "-" for ch in sample_id) or len(sample_id) > 40:
            raise ApiError(400, "VALIDATION", "Invalid sample id.")
        return Response(png_bytes(sample_id, size), media_type="image/png", headers={"Cache-Control": "max-age=86400"})

    @app.get(f"{api}/images/trigger/{{cls}}.png")
    def trigger(cls: int, anomalous: bool = False):
        return Response(trigger_png(cls % 5, anomalous), media_type="image/png", headers={"Cache-Control": "max-age=86400"})

    # -------------------------------------------------------------- reports
    @app.get(f"{api}/reports")
    def reports(u: dict = Depends(user)):
        return {"items": engine.reports()}

    @app.post(f"{api}/assessments/{{asm_id}}/reports", status_code=201)
    def gen_report(asm_id: str, u: dict = Depends(user)):
        return engine.generate_report(asm_id, u["id"])

    @app.get(f"{api}/reports/{{rid}}")
    def report(rid: str, u: dict = Depends(user)):
        d = engine.report(rid)
        return engine.report_meta(d) | {"json": d["json"]}

    @app.get(f"{api}/reports/{{rid}}/json")
    def report_json(rid: str, u: dict = Depends(user)):
        d = engine.report(rid)
        from aura.core.types import AuditEvent, Actor
        engine.audit.append(AuditEvent.REPORT_EXPORTED, {"report_id": rid, "format": "json"}, Actor(type="user", id=u["id"]))
        return Response(json.dumps(d["json"], indent=2, ensure_ascii=False), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{rid}.json"'})

    @app.get(f"{api}/reports/{{rid}}/pdf")
    def report_pdf(rid: str, u: dict = Depends(user)):
        raise ApiError(501, "PDF_UNAVAILABLE", "No PDF renderer is installed on this host. Use the HTML view and print, or the signed JSON.")

    @app.post(f"{api}/reports/{{rid}}/finalise")
    def finalise(rid: str, u: dict = Depends(user)):
        return engine.finalise_report(rid, u["id"])

    @app.post(f"{api}/reports/verify")
    async def verify_report(request: Request, u: dict = Depends(user)):
        return engine.verify_report(await request.json())

    # ---------------------------------------------------------------- audit
    @app.get(f"{api}/audit")
    def audit(u: dict = Depends(user), event: str | None = None, q: str | None = None, page: int = 1, page_size: int = 50):
        return engine.audit_entries(event, q, max(page, 1), min(max(page_size, 1), 200))

    @app.get(f"{api}/audit/head")
    def audit_head(u: dict = Depends(user)):
        h, n = engine.audit.head()
        return {"head_hash": h, "entry_count": n}

    @app.post(f"{api}/audit/verify")
    async def audit_verify(request: Request, u: dict = Depends(user)):
        try:
            body = await request.json()
        except Exception:
            body = {}
        return engine.audit_verify(body.get("expected_head") or None)

    @app.get(f"{api}/audit/export")
    def audit_export(u: dict = Depends(user)):
        h, n = engine.audit.head()
        text = engine.audit.path.read_text(encoding="utf-8") if engine.audit.path.exists() else ""
        return Response(text, media_type="application/x-ndjson", headers={"Content-Disposition": f'attachment; filename="audit_log_{n}_{h[7:19]}.jsonl"', "X-Audit-Head": h})

    # --------------------------------------------------------------- config
    @app.get(f"{api}/config/policy")
    def policy(u: dict = Depends(user)):
        return DEFAULT_POLICY.model_dump(mode="json") | {"digest": DEFAULT_POLICY.digest()}

    @app.get(f"{api}/config/thresholds")
    def thresholds(u: dict = Depends(user)):
        return {"items": [{"check_id": c.id, "name": CHECK_META[c.id][0], "module": c.module.value, "requires_access": c.requires_access.value,
                           "requirement": CHECK_META[c.id][2], "parameters": c.parameters(None)} for c in engine.registry.all()]}

    @app.get(f"{api}/coverage")
    def coverage():
        return COVERAGE

    @app.get(f"{api}/checks")
    def checks(u: dict = Depends(user)):
        return {"items": [{"check_id": k, "name": v[0], "description": v[1], "requirement": v[2]} for k, v in CHECK_META.items()]}

    # ----------------------------------------------------------- attack lab
    @app.get(f"{api}/attack-lab/scenarios")
    def scenarios(u: dict = Depends(admin)):
        return {"items": SCENARIOS}

    @app.get(f"{api}/attack-lab/runs")
    def attack_runs(u: dict = Depends(admin)):
        return {"items": list(reversed(engine.store.list("attackrun")))}

    @app.post(f"{api}/attack-lab/runs", status_code=201)
    async def attack_run(request: Request, u: dict = Depends(admin)):
        body = await request.json()
        sc = next((s for s in SCENARIOS if s["id"] == body.get("scenario_id")), None)
        if not sc:
            raise ApiError(404, "NOT_FOUND", "Unknown scenario.")
        await asyncio.sleep(1.2)
        return engine._record_attack_run(sc["id"], int(body.get("seed", 1337)), SCENARIO_OUTPUTS[sc["id"][0]], u["id"])

    # ------------------------------------------------------------ static UI
    dist = REPO_ROOT / "ui" / "dist"
    if (dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="ui-assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            candidate = (dist / path).resolve()
            if path and candidate.is_file() and dist.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app
