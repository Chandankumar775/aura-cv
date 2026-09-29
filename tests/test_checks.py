"""Scheduler behaviour with dummy checks: gating, UNAVAILABLE findings, fallbacks, audit (R-CON-5)."""

from __future__ import annotations

import json

import pytest

from aura.core.checks import AssessmentContext, BaseCheck, CheckRegistry, Scheduler
from aura.core.schemas import validate_finding
from aura.core.types import (
    AccessLevel,
    AssetRef,
    AssetType,
    CheckRunStatus,
    Disposition,
    FindingStatus,
    ModuleId,
    ModuleStatus,
    Severity,
)

MODEL = AssetRef(type=AssetType.MODEL, id="mdl_test", digest="sha256:" + "a" * 64)
DATASET = AssetRef(type=AssetType.DATASET, id="ds_test")


class Flagging(BaseCheck):
    """Emits one HIGH finding per run."""

    def __init__(self, cid, module=ModuleId.M2, access=AccessLevel.NONE, inputs=("model",), fallback=None):
        self.id, self.module, self.requires_access = cid, module, access
        self.requires_inputs, self.fallback_check_id = set(inputs), fallback
        self.calls = 0

    def parameters(self, ctx):
        return {"threshold": 0.5}

    def run(self, ctx, progress):
        self.calls += 1
        progress(1.0, "done")
        return [
            ctx.make_finding(
                module=self.module,
                check_id=self.id,
                reason=f"{self.id} saw something suspicious.",
                severity=Severity.HIGH,
                confidence=0.9,
                affected_asset=ctx.assets.get("model", DATASET),
                evidence={"metrics": {"score": 0.9}},
            )
        ]


class NotApplicable(Flagging):
    def is_applicable(self, ctx):
        return False, "not supported for detection models in this version"


class Crashing(Flagging):
    def run(self, ctx, progress):
        raise RuntimeError("boom")


class Mislabelled(Flagging):
    def run(self, ctx, progress):
        f = super().run(ctx, progress)[0]
        return [f.model_copy(update={"check_id": "M2.other"})]


def _ctx(access=AccessLevel.WB, **inputs):
    inputs = inputs or {"model": object()}
    assets = {"model": MODEL} if "model" in inputs else {}
    return AssessmentContext(assessment_id="asm_test", access_level=access, inputs=inputs, assets=assets, seed=7)


class RecordingAudit:
    def __init__(self):
        self.events = []

    def append(self, event, payload=None, actor=None):
        self.events.append((event.value, payload))


def _run(checks, ctx, audit=None):
    reg = CheckRegistry()
    for c in checks:
        reg.register(c)
    return Scheduler(reg, audit).run_module(ModuleId.M2, ctx)


def test_all_checks_run_when_access_suffices():
    audit = RecordingAudit()
    res = _run([Flagging("M2.a", access=AccessLevel.WB), Flagging("M2.b", access=AccessLevel.BB_L)], _ctx(), audit)
    assert res.status is ModuleStatus.COMPLETED
    assert [f.check_id for f in res.findings] == ["M2.a", "M2.b"]
    assert [e for e, _ in audit.events] == ["CHECK_STARTED", "CHECK_COMPLETED"] * 2
    assert audit.events[0][1]["parameters"] == {"threshold": 0.5}
    assert audit.events[1][1]["finding_ids"] == [res.findings[0].id]
    assert all(f.recommended_disposition is Disposition.QUARANTINE for f in res.findings)  # HIGH x 0.9


def test_insufficient_access_yields_unavailable_and_runs_fallback():
    wb = Flagging("M2.trigger_reconstruction", access=AccessLevel.WB, fallback="M2.patch_probe")
    probe = Flagging("M2.patch_probe", access=AccessLevel.BB_L)
    audit = RecordingAudit()
    res = _run([wb, probe], _ctx(AccessLevel.BB_S), audit)

    assert res.status is ModuleStatus.PARTIAL
    assert wb.calls == 0 and probe.calls == 1  # fallback ran exactly once
    gap = next(f for f in res.findings if f.status is FindingStatus.UNAVAILABLE)
    assert gap.check_id == "M2.trigger_reconstruction"
    assert "requires WB model access" in gap.reason and "M2.patch_probe" in gap.reason
    assert gap.recommended_disposition is Disposition.REVIEW
    assert gap.severity is Severity.MEDIUM and gap.confidence == 1.0
    assert gap.affected_asset == MODEL
    assert gap.evidence.model_extra["fallback_used"] == "M2.patch_probe"
    validate_finding(gap)
    assert res.checks_unavailable == [
        {"check_id": "M2.trigger_reconstruction", "reason": gap.evidence.model_extra["unavailable_reason"], "fallback_used": "M2.patch_probe"}
    ]
    assert [c["check_id"] for c in res.checks_run] == ["M2.patch_probe"]
    events = [e for e, _ in audit.events]
    assert events == ["CHECK_STARTED", "CHECK_COMPLETED", "CHECK_UNAVAILABLE"]


def test_missing_input_is_unavailable_not_skipped():
    res = _run([Flagging("M2.fingerprint", inputs=("model", "battery"))], _ctx())
    assert res.status is ModuleStatus.UNAVAILABLE
    (gap,) = res.findings
    assert gap.status is FindingStatus.UNAVAILABLE and "battery" in gap.reason


def test_not_applicable_reason_is_passed_through():
    res = _run([NotApplicable("M2.trigger_reconstruction")], _ctx())
    assert "not supported for detection models" in res.findings[0].reason
    assert "has not been assessed" in res.findings[0].reason


def test_crashing_check_is_error_with_unavailable_finding():
    audit = RecordingAudit()
    res = _run([Crashing("M2.strip"), Flagging("M2.ok")], _ctx(), audit)
    assert res.status is ModuleStatus.PARTIAL
    run = next(r for r in res.check_runs if r.check_id == "M2.strip")
    assert run.status is CheckRunStatus.ERROR and "boom" in run.message
    gap = next(f for f in res.findings if f.check_id == "M2.strip")
    assert gap.status is FindingStatus.UNAVAILABLE and "internal error" in gap.reason
    unavailable = [p for e, p in audit.events if e == "CHECK_UNAVAILABLE"]
    assert unavailable[0]["status"] == "ERROR"


def test_all_errors_gives_module_error():
    assert _run([Crashing("M2.a"), Crashing("M2.b")], _ctx()).status is ModuleStatus.ERROR


def test_findings_with_wrong_labels_are_rejected():
    res = _run([Mislabelled("M2.a")], _ctx())
    assert res.check_runs[0].status is CheckRunStatus.ERROR
    assert res.findings[0].status is FindingStatus.UNAVAILABLE


def test_finding_ids_are_deterministic():
    def ids():
        res = _run([Flagging("M2.a"), Flagging("M2.b", access=AccessLevel.WB, fallback=None)], _ctx(AccessLevel.BB_L))
        return [(f.id, f.check_id, f.status.value, f.reason) for f in res.findings]

    assert ids() == ids()


def test_preview_matches_run():
    reg = CheckRegistry()
    reg.register(Flagging("M2.a", access=AccessLevel.WB, fallback="M2.b"))
    reg.register(Flagging("M2.b", access=AccessLevel.BB_L))
    plan = Scheduler(reg).preview(ModuleId.M2, _ctx(AccessLevel.BB_L))
    assert [(p.check_id, p.will_run) for p in plan] == [("M2.a", False), ("M2.b", True)]
    assert plan[0].fallback_check_id == "M2.b" and "WB" in plan[0].reason


def test_cancellation_stops_module():
    ctx = _ctx()
    ctx.cancel_event.set()
    assert _run([Flagging("M2.a")], ctx).status is ModuleStatus.CANCELLED


def test_registry_rejects_duplicates_and_non_checks():
    reg = CheckRegistry()
    reg.register(Flagging("M2.a"))
    with pytest.raises(ValueError):
        reg.register(Flagging("M2.a"))
    with pytest.raises(TypeError):
        reg.register(object())  # type: ignore[arg-type]


def test_scheduler_writes_real_signed_audit_entries(audit_log):
    wb = Flagging("M2.trigger_reconstruction", access=AccessLevel.WB, fallback="M2.patch_probe")
    _run([wb, Flagging("M2.patch_probe")], _ctx(AccessLevel.BB_S), audit_log)
    assert audit_log.verify().valid
    events = [json.loads(l)["event"] for l in audit_log.path.read_text().splitlines()]
    assert events == ["CHECK_STARTED", "CHECK_COMPLETED", "CHECK_UNAVAILABLE"]
