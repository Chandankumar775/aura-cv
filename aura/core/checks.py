"""Check plugin protocol, registry and scheduler (CLAUDE.md A7.4; R-GEN-1, R-CON-5).

Every detector in every module is a ``Check``. The scheduler decides, per module and
per check, whether the check can run with the inputs and model access available, runs
it, and - this is the point - never silently skips anything:

    missing inputs / insufficient access / not applicable / crashed
        -> an UNAVAILABLE finding with the reason, plus the fallback check (if any)

Each decision is written to the audit log (CHECK_STARTED, CHECK_COMPLETED,
CHECK_UNAVAILABLE) so the report can list checks run and checks unavailable.

Extension beyond the A7.4 protocol (decisions.md D-012): a check may define
``asset_input`` (which input its findings are about, used to address UNAVAILABLE
findings) and ``parameters(ctx)`` (thresholds recorded in the audit log). Both are
optional and read with ``getattr``.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import ValidationError

from aura.core.ids import derived_id, utc_now
from aura.core.policy import DEFAULT_POLICY, DispositionPolicy, HardOverride
from aura.core.schemas import SchemaValidationError, validate_finding
from aura.core.types import (
    AccessLevel,
    AssetRef,
    AssetType,
    AuditEvent,
    CheckRun,
    CheckRunStatus,
    Evidence,
    Finding,
    FindingStatus,
    ModuleId,
    ModuleStatus,
    Severity,
)

ProgressFn = Callable[[float, str], None]

# Input name -> asset type, used to address findings about an input.
INPUT_ASSET_TYPES: dict[str, AssetType] = {
    "dataset": AssetType.DATASET,
    "model": AssetType.MODEL,
    "records": AssetType.RECORD_STREAM,
    "input_batch": AssetType.INPUT_BATCH,
    "reference": AssetType.REFERENCE,
    "battery": AssetType.REFERENCE,
    "audit_log": AssetType.AUDIT_LOG,
}

# Where a module's UNAVAILABLE findings land when a check names no asset_input.
MODULE_PRIMARY_INPUT: dict[ModuleId, str] = {
    ModuleId.M1: "dataset",
    ModuleId.M2: "model",
    ModuleId.M3: "records",
    ModuleId.M4: "input_batch",
    ModuleId.M5: "audit_log",
}


class AuditSink(Protocol):
    def append(self, event: AuditEvent, payload: dict[str, Any] | None = None, actor: Any = None) -> Any: ...


class AssessmentCancelled(Exception):
    pass


@dataclass
class AssessmentContext:
    """Everything a check may read. Checks must not reach outside it.

    ``inputs`` maps input names (``dataset``, ``model``, ``battery``, ...) to loaded
    objects; ``assets`` maps the same names to the registered ``AssetRef`` so findings
    can name the asset they affect. Ground-truth manifests are never placed here
    (A3 rule 8).
    """

    assessment_id: str
    access_level: AccessLevel = AccessLevel.NONE
    inputs: dict[str, Any] = field(default_factory=dict)
    assets: dict[str, AssetRef] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    policy: DispositionPolicy = DEFAULT_POLICY
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _ordinals: dict[tuple[str, str, str], int] = field(default_factory=dict, repr=False)

    def has_input(self, name: str) -> bool:
        return self.inputs.get(name) is not None

    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def asset_for(self, input_name: str) -> AssetRef:
        if input_name in self.assets:
            return self.assets[input_name]
        # The input was not supplied: still address the finding, and say so plainly.
        return AssetRef(type=INPUT_ASSET_TYPES.get(input_name, AssetType.DATASET), id=f"{input_name}:not-supplied")

    def make_finding(
        self,
        *,
        module: ModuleId,
        check_id: str,
        reason: str,
        severity: Severity,
        confidence: float,
        affected_asset: AssetRef,
        evidence: Evidence | dict[str, Any] | None = None,
        status: FindingStatus = FindingStatus.FLAGGED,
        limitations: Iterable[str] = (),
        overrides: Iterable[HardOverride] = (),
    ) -> Finding:
        """Build a finding whose disposition comes from the policy, never from the check.

        The id is derived from (assessment, check, asset, ordinal) so re-running the
        same inputs with the same seed yields the same finding ids (A3 rule 10).
        """
        key = (check_id, affected_asset.type.value, affected_asset.id)
        ordinal = self._ordinals.get(key, 0)
        self._ordinals[key] = ordinal + 1
        if not isinstance(evidence, Evidence):
            evidence = Evidence.model_validate(evidence or {})
        return Finding(
            id=derived_id("fnd", self.assessment_id, *key, ordinal),
            assessment_id=self.assessment_id,
            module=module,
            check_id=check_id,
            created_at=utc_now(),
            status=status,
            reason=reason,
            evidence=evidence,
            confidence=confidence,
            severity=severity,
            affected_asset=affected_asset,
            recommended_disposition=self.policy.recommend(severity, confidence, status, overrides),
            limitations=list(limitations),
        )


@runtime_checkable
class Check(Protocol):
    id: str
    module: ModuleId
    version: str
    requires_access: AccessLevel  # minimum model access (NONE for data-only checks)
    requires_inputs: set[str]
    fallback_check_id: str | None

    def is_applicable(self, ctx: AssessmentContext) -> tuple[bool, str]: ...

    def run(self, ctx: AssessmentContext, progress: ProgressFn) -> list[Finding]: ...


class BaseCheck:
    """Optional convenience base with the defaults most checks want."""

    id: str = ""
    module: ModuleId = ModuleId.M1
    version: str = "1.0.0"
    requires_access: AccessLevel = AccessLevel.NONE
    requires_inputs: set[str] = set()
    fallback_check_id: str | None = None
    asset_input: str | None = None
    limitations: tuple[str, ...] = ()

    def is_applicable(self, ctx: AssessmentContext) -> tuple[bool, str]:
        return True, ""

    def parameters(self, ctx: AssessmentContext) -> dict[str, Any]:
        return {}

    def run(self, ctx: AssessmentContext, progress: ProgressFn) -> list[Finding]:
        raise NotImplementedError


# -------------------------------------------------------------------- registry


class CheckRegistry:
    def __init__(self) -> None:
        self._checks: dict[str, Check] = {}

    def register(self, check: Check) -> Check:
        if not isinstance(check, Check):
            raise TypeError(f"{check!r} does not implement the Check protocol")
        if check.id in self._checks:
            raise ValueError(f"check {check.id!r} is already registered")
        self._checks[check.id] = check
        return check

    def get(self, check_id: str) -> Check:
        return self._checks[check_id]

    def __contains__(self, check_id: str) -> bool:
        return check_id in self._checks

    def all(self) -> list[Check]:
        return list(self._checks.values())

    def for_module(self, module: ModuleId) -> list[Check]:
        """Registration order is execution order, which keeps runs deterministic."""
        return [c for c in self._checks.values() if c.module == module]


REGISTRY = CheckRegistry()


def register_check(cls: type) -> type:
    """Class decorator: instantiate and add to the global registry."""
    REGISTRY.register(cls())
    return cls


# ------------------------------------------------------------------- scheduler


@dataclass
class CheckPlan:
    check_id: str
    will_run: bool
    reason: str = ""
    fallback_check_id: str | None = None


@dataclass
class ModuleResult:
    module: ModuleId
    status: ModuleStatus
    findings: list[Finding] = field(default_factory=list)
    check_runs: list[CheckRun] = field(default_factory=list)

    @property
    def checks_run(self) -> list[dict[str, Any]]:
        return [
            {"check_id": r.check_id, "version": r.version, "parameters": r.parameters}
            for r in self.check_runs
            if r.status is CheckRunStatus.COMPLETED
        ]

    @property
    def checks_unavailable(self) -> list[dict[str, Any]]:
        return [
            {"check_id": r.check_id, "reason": r.message, "fallback_used": r.fallback_used}
            for r in self.check_runs
            if r.status is not CheckRunStatus.COMPLETED
        ]


def _gate(check: Check, ctx: AssessmentContext) -> tuple[bool, str]:
    """Can ``check`` run in ``ctx``? Returns (ok, human-readable reason if not)."""
    missing = sorted(i for i in check.requires_inputs if not ctx.has_input(i))
    if missing:
        return False, f"required input(s) not supplied: {', '.join(missing)}"
    if not ctx.access_level.satisfies(check.requires_access):
        return False, (
            f"requires {check.requires_access.value} model access but the assessment has "
            f"{ctx.access_level.value} access"
        )
    ok, why = check.is_applicable(ctx)
    return (True, "") if ok else (False, why or "check is not applicable to these inputs")


class Scheduler:
    def __init__(self, registry: CheckRegistry = REGISTRY, audit: AuditSink | None = None):
        self.registry = registry
        self.audit = audit

    def _log(self, event: AuditEvent, payload: dict[str, Any]) -> None:
        if self.audit is not None:
            self.audit.append(event, payload)

    def preview(self, module: ModuleId, ctx: AssessmentContext) -> list[CheckPlan]:
        """What would run and what would be UNAVAILABLE (New Assessment review step, S3)."""
        return [
            CheckPlan(c.id, *_gate(c, ctx), fallback_check_id=c.fallback_check_id)
            for c in self.registry.for_module(module)
        ]

    def run_module(self, module: ModuleId, ctx: AssessmentContext, progress: ProgressFn | None = None) -> ModuleResult:
        checks = self.registry.for_module(module)
        result = ModuleResult(module=module, status=ModuleStatus.RUNNING)
        done: set[str] = set()  # checks already executed (incl. as a fallback)
        report = progress or (lambda frac, msg: None)

        for n, check in enumerate(checks):
            if ctx.is_cancelled():
                result.status = ModuleStatus.CANCELLED
                return result
            if check.id not in done:
                self._run_one(check, ctx, result, done, report)
            report((n + 1) / len(checks), f"{check.id} done")

        result.status = _module_status(result)
        return result

    def _run_one(
        self,
        check: Check,
        ctx: AssessmentContext,
        result: ModuleResult,
        done: set[str],
        progress: ProgressFn,
    ) -> None:
        done.add(check.id)
        params = _parameters(check, ctx)
        base = {"assessment_id": ctx.assessment_id, "module": check.module.value, "check_id": check.id, "version": check.version}
        ok, reason = _gate(check, ctx)
        if not ok:
            self._unavailable(check, ctx, result, done, progress, reason, CheckRunStatus.UNAVAILABLE, params)
            return

        self._log(AuditEvent.CHECK_STARTED, {**base, "parameters": params})
        started = time.perf_counter()
        try:
            findings = list(check.run(ctx, progress))
            for f in findings:
                _validate_emitted(check, f)
        except AssessmentCancelled:
            raise
        except Exception as exc:  # a crashed check is a coverage gap, never a silent skip
            reason = f"the check stopped with an internal error ({type(exc).__name__}: {exc})"
            self._unavailable(check, ctx, result, done, progress, reason, CheckRunStatus.ERROR, params, started)
            return

        duration = _ms_since(started)
        result.findings.extend(findings)
        result.check_runs.append(
            CheckRun(check_id=check.id, version=check.version, parameters=params, status=CheckRunStatus.COMPLETED, duration_ms=duration)
        )
        self._log(
            AuditEvent.CHECK_COMPLETED,
            {**base, "duration_ms": duration, "finding_ids": [f.id for f in findings]},
        )

    def _unavailable(
        self,
        check: Check,
        ctx: AssessmentContext,
        result: ModuleResult,
        done: set[str],
        progress: ProgressFn,
        reason: str,
        status: CheckRunStatus,
        params: dict[str, Any],
        started: float | None = None,
    ) -> None:
        fallback_id = check.fallback_check_id if check.fallback_check_id in self.registry else None
        if fallback_id and fallback_id not in done:
            self._run_one(self.registry.get(fallback_id), ctx, result, done, progress)
        fallback_ran = fallback_id is not None and any(
            r.check_id == fallback_id and r.status is CheckRunStatus.COMPLETED for r in result.check_runs
        )
        fallback_used = fallback_id if fallback_ran else None

        asset_input = getattr(check, "asset_input", None) or MODULE_PRIMARY_INPUT[check.module]
        sentence = f"Check {check.id} could not run: {reason}."
        if fallback_used:
            sentence += f" The fallback check {fallback_used} was run instead, with weaker guarantees."
        else:
            sentence += " This aspect of the asset has not been assessed."
        finding = ctx.make_finding(
            module=check.module,
            check_id=check.id,
            status=FindingStatus.UNAVAILABLE,
            reason=sentence,
            severity=Severity.MEDIUM,
            confidence=1.0,
            affected_asset=ctx.asset_for(asset_input),
            evidence=Evidence(
                metrics={},
                thresholds=params,
                unavailable_reason=reason,
                required_access=check.requires_access.value,
                access_level_used=ctx.access_level.value,
                fallback_used=fallback_used,
            ),
            limitations=[f"No coverage from {check.id} for this asset: {reason}."],
        )
        validate_finding(finding)
        result.findings.append(finding)
        result.check_runs.append(
            CheckRun(
                check_id=check.id,
                version=check.version,
                parameters=params,
                status=status,
                duration_ms=_ms_since(started) if started is not None else 0,
                message=reason,
                fallback_used=fallback_used,
            )
        )
        self._log(
            AuditEvent.CHECK_UNAVAILABLE,
            {
                "assessment_id": ctx.assessment_id,
                "module": check.module.value,
                "check_id": check.id,
                "version": check.version,
                "status": status.value,
                "reason": reason,
                "fallback_used": fallback_used,
                "finding_id": finding.id,
            },
        )


def _parameters(check: Check, ctx: AssessmentContext) -> dict[str, Any]:
    fn = getattr(check, "parameters", None)
    return dict(fn(ctx)) if callable(fn) else {}


def _validate_emitted(check: Check, finding: Finding) -> None:
    if not isinstance(finding, Finding):
        raise TypeError(f"{check.id} returned {type(finding).__name__}, not a Finding")
    if finding.module != check.module or finding.check_id != check.id:
        raise ValueError(f"{check.id} emitted a finding labelled {finding.module.value}/{finding.check_id}")
    try:
        validate_finding(finding)
    except (SchemaValidationError, ValidationError) as exc:
        raise ValueError(f"{check.id} emitted a schema-invalid finding: {exc}") from exc


def _module_status(result: ModuleResult) -> ModuleStatus:
    statuses = [r.status for r in result.check_runs]
    if not statuses:
        return ModuleStatus.UNAVAILABLE
    completed = statuses.count(CheckRunStatus.COMPLETED)
    if completed == len(statuses):
        return ModuleStatus.COMPLETED
    if completed == 0:
        return ModuleStatus.ERROR if CheckRunStatus.ERROR in statuses else ModuleStatus.UNAVAILABLE
    return ModuleStatus.PARTIAL


def _ms_since(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
