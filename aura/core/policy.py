"""Disposition policy (CLAUDE.md A7.5, design.md §10.3) and verdict aggregation.

Severity x confidence -> recommended disposition, with hard overrides that always
QUARANTINE. The matrix is data, not code, so an ADMIN can change it; every change
bumps ``version`` and is audited (POLICY_CHANGED, wired up with the API in M8).

Confidence bands (decisions.md D-008): ``< 0.4`` low, ``0.4 .. 0.8`` inclusive medium,
``> 0.8`` high - exactly as the A7.5 column headers read.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aura.core.hashing import sha256_canonical
from aura.core.types import AssetRef, AssetType, Decision, Disposition, Finding, FindingStatus, Severity


class ConfidenceBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class HardOverride(str, Enum):
    """Conditions that bypass the matrix (A7.5)."""

    SIGNATURE_FAILURE = "SIGNATURE_FAILURE"
    MODEL_DIGEST_MISMATCH = "MODEL_DIGEST_MISMATCH"
    AUDIT_CHAIN_BREAK = "AUDIT_CHAIN_BREAK"


_A, _R, _Q = Disposition.ACCEPT, Disposition.REVIEW, Disposition.QUARANTINE

DEFAULT_MATRIX: dict[Severity, dict[ConfidenceBand, Disposition]] = {
    Severity.LOW: {ConfidenceBand.LOW: _A, ConfidenceBand.MEDIUM: _A, ConfidenceBand.HIGH: _R},
    Severity.MEDIUM: {ConfidenceBand.LOW: _A, ConfidenceBand.MEDIUM: _R, ConfidenceBand.HIGH: _R},
    Severity.HIGH: {ConfidenceBand.LOW: _R, ConfidenceBand.MEDIUM: _R, ConfidenceBand.HIGH: _Q},
    Severity.CRITICAL: {ConfidenceBand.LOW: _R, ConfidenceBand.MEDIUM: _Q, ConfidenceBand.HIGH: _Q},
}


class DispositionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int = Field(default=1, ge=1)
    low_below: float = Field(default=0.4, ge=0.0, le=1.0)
    high_above: float = Field(default=0.8, ge=0.0, le=1.0)
    matrix: dict[Severity, dict[ConfidenceBand, Disposition]] = Field(default_factory=lambda: DEFAULT_MATRIX)
    hard_overrides: dict[HardOverride, Disposition] = Field(
        default_factory=lambda: {o: Disposition.QUARANTINE for o in HardOverride}
    )
    unavailable_disposition: Disposition = Disposition.REVIEW

    @model_validator(mode="after")
    def _complete(self) -> "DispositionPolicy":
        if self.low_below > self.high_above:
            raise ValueError("low_below must not exceed high_above")
        for sev in Severity:
            if sev not in self.matrix or set(self.matrix[sev]) != set(ConfidenceBand):
                raise ValueError(f"matrix row {sev.value} must define LOW, MEDIUM and HIGH bands")
        if self.unavailable_disposition is Disposition.ACCEPT:
            raise ValueError("UNAVAILABLE checks may never map to ACCEPT (A7.5)")
        return self

    def band(self, confidence: float) -> ConfidenceBand:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence {confidence} outside [0, 1]")
        if confidence < self.low_below:
            return ConfidenceBand.LOW
        if confidence > self.high_above:
            return ConfidenceBand.HIGH
        return ConfidenceBand.MEDIUM

    def recommend(
        self,
        severity: Severity,
        confidence: float,
        status: FindingStatus = FindingStatus.FLAGGED,
        overrides: Iterable[HardOverride] = (),
    ) -> Disposition:
        forced = [self.hard_overrides[o] for o in overrides]
        if status is FindingStatus.UNAVAILABLE:
            forced.append(self.unavailable_disposition)
            return most_severe(forced)
        return most_severe([self.matrix[severity][self.band(confidence)], *forced])

    def digest(self) -> str:
        """Pinned into each assessment's config snapshot for reproducibility (A10)."""
        return sha256_canonical(self.model_dump(mode="json"))


DEFAULT_POLICY = DispositionPolicy()


# ------------------------------------------------------------ verdict aggregation


def most_severe(dispositions: Iterable[Disposition]) -> Disposition:
    return max(dispositions, key=lambda d: d.rank, default=Disposition.ACCEPT)


def effective_disposition(finding: Finding, decisions: Sequence[Decision] = ()) -> Disposition:
    """Latest analyst decision for this finding if any, otherwise the recommendation."""
    mine = [d for d in decisions if d.finding_id == finding.id]
    if not mine:
        return finding.recommended_disposition
    # Stable sort: equal timestamps keep append order, so the last appended wins.
    return sorted(mine, key=lambda d: d.decided_at)[-1].decision


def is_unresolved(finding: Finding, decisions: Sequence[Decision] = ()) -> bool:
    """REVIEW/QUARANTINE findings without a decision block report finalisation (A8.5)."""
    needs_decision = finding.recommended_disposition in (Disposition.REVIEW, Disposition.QUARANTINE)
    return needs_decision and not any(d.finding_id == finding.id for d in decisions)


class AssetVerdict(BaseModel):
    asset: AssetRef
    disposition: Disposition
    confidence: float
    finding_count: int
    coverage_gaps: list[str] = Field(default_factory=list)


def asset_verdicts(findings: Sequence[Finding], decisions: Sequence[Decision] = ()) -> list[AssetVerdict]:
    """Most severe effective disposition per affected asset (A7.5).

    ``confidence`` is the highest confidence among the findings that set the verdict.
    ``coverage_gaps`` lists the check ids that were UNAVAILABLE for the asset; they stay
    visible even if an analyst later accepts the gap.
    """
    groups: dict[tuple[AssetType, str], list[Finding]] = {}
    for f in findings:
        groups.setdefault((f.affected_asset.type, f.affected_asset.id), []).append(f)

    verdicts = []
    for fs in groups.values():
        effective = {f.id: effective_disposition(f, decisions) for f in fs}
        worst = most_severe(effective.values())
        drivers = [f for f in fs if effective[f.id] is worst]
        verdicts.append(
            AssetVerdict(
                asset=fs[0].affected_asset,
                disposition=worst,
                confidence=max(f.confidence for f in drivers),
                finding_count=len(fs),
                coverage_gaps=sorted({f.check_id for f in fs if f.status is FindingStatus.UNAVAILABLE}),
            )
        )
    verdicts.sort(key=lambda v: (-v.disposition.rank, -v.confidence, v.asset.type.value, v.asset.id))
    return verdicts


def overall_verdict(verdicts: Iterable[AssetVerdict]) -> Disposition:
    return most_severe(v.disposition for v in verdicts)


def policy_from_mapping(data: Mapping[str, object]) -> DispositionPolicy:
    return DispositionPolicy.model_validate(data)
