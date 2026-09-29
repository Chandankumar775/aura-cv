"""Disposition policy (A7.5) and verdict aggregation."""

import pytest

from aura.core.access import AccessLevelError, effective_access
from aura.core.policy import (
    DEFAULT_POLICY,
    DispositionPolicy,
    HardOverride,
    asset_verdicts,
    effective_disposition,
    is_unresolved,
    overall_verdict,
)
from aura.core.types import (
    AccessLevel,
    AssetRef,
    AssetType,
    Decision,
    Disposition,
    Evidence,
    Finding,
    FindingStatus,
    ModuleId,
    Severity,
)

A, R, Q = Disposition.ACCEPT, Disposition.REVIEW, Disposition.QUARANTINE

# The A7.5 table, row by row: (severity, [<0.4, 0.4-0.8, >0.8]).
TABLE = [
    (Severity.LOW, [A, A, R]),
    (Severity.MEDIUM, [A, R, R]),
    (Severity.HIGH, [R, R, Q]),
    (Severity.CRITICAL, [R, Q, Q]),
]


@pytest.mark.parametrize("severity,row", TABLE)
def test_matrix_matches_spec(severity, row):
    for confidence, expected in zip([0.1, 0.6, 0.95], row):
        assert DEFAULT_POLICY.recommend(severity, confidence) is expected


@pytest.mark.parametrize(
    "confidence,band_index",
    [(0.0, 0), (0.3999, 0), (0.4, 1), (0.8, 1), (0.8001, 2), (1.0, 2)],
)
def test_band_boundaries(confidence, band_index):
    for severity, row in TABLE:
        assert DEFAULT_POLICY.recommend(severity, confidence) is row[band_index]


@pytest.mark.parametrize("override", list(HardOverride))
def test_hard_overrides_always_quarantine(override):
    assert DEFAULT_POLICY.recommend(Severity.LOW, 0.0, overrides=[override]) is Q


def test_unavailable_is_review_whatever_the_numbers():
    for severity, _ in TABLE:
        assert DEFAULT_POLICY.recommend(severity, 0.0, FindingStatus.UNAVAILABLE) is R


def test_confidence_out_of_range():
    with pytest.raises(ValueError):
        DEFAULT_POLICY.recommend(Severity.LOW, 1.5)


def test_policy_validation_and_digest():
    with pytest.raises(ValueError):
        DispositionPolicy(unavailable_disposition=A)
    with pytest.raises(ValueError):
        DispositionPolicy(low_below=0.9, high_above=0.5)
    stricter = DispositionPolicy(version=2, matrix={**DEFAULT_POLICY.matrix, Severity.LOW: {b: R for b in DEFAULT_POLICY.matrix[Severity.LOW]}})
    assert stricter.recommend(Severity.LOW, 0.1) is R
    assert stricter.digest() != DEFAULT_POLICY.digest()
    assert DispositionPolicy().digest() == DEFAULT_POLICY.digest()


# ---------------------------------------------------------------- aggregation

def _finding(fid, asset_id, disposition, confidence=0.9, status=FindingStatus.FLAGGED, check="M1.x"):
    return Finding(
        id=fid,
        module=ModuleId.M1,
        check_id=check,
        created_at="2026-09-29T10:00:00.000Z",
        status=status,
        reason="A plain sentence explaining the flag.",
        evidence=Evidence(metrics={"m": 1}),
        confidence=confidence,
        severity=Severity.HIGH,
        affected_asset=AssetRef(type=AssetType.CONTRIBUTOR, id=asset_id),
        recommended_disposition=disposition,
    )


def _decision(did, fid, decision, at):
    return Decision(id=did, finding_id=fid, analyst_id="usr_a", decision=decision, justification="checked", decided_at=at)


def test_latest_decision_wins():
    f = _finding("fnd_1", "c1", Q)
    assert effective_disposition(f) is Q
    decisions = [
        _decision("dec_1", "fnd_1", R, "2026-09-29T10:00:00.000Z"),
        _decision("dec_2", "fnd_1", A, "2026-09-29T11:00:00.000Z"),
        _decision("dec_3", "fnd_other", Q, "2026-09-29T12:00:00.000Z"),
    ]
    assert effective_disposition(f, decisions) is A
    tie = [_decision("dec_4", "fnd_1", R, "2026-09-29T11:00:00.000Z"), _decision("dec_5", "fnd_1", Q, "2026-09-29T11:00:00.000Z")]
    assert effective_disposition(f, tie) is Q  # same timestamp: last appended wins


def test_unresolved_rule():
    assert is_unresolved(_finding("fnd_1", "c1", R))
    assert not is_unresolved(_finding("fnd_1", "c1", A))
    assert not is_unresolved(_finding("fnd_1", "c1", Q), [_decision("dec_1", "fnd_1", Q, "2026-09-29T10:00:00.000Z")])


def test_asset_and_overall_verdicts():
    findings = [
        _finding("fnd_1", "c1", R, 0.5),
        _finding("fnd_2", "c1", Q, 0.85),
        _finding("fnd_3", "c2", A, 0.2),
        _finding("fnd_4", "c3", R, 1.0, FindingStatus.UNAVAILABLE, check="M1.source_risk"),
    ]
    verdicts = {v.asset.id: v for v in asset_verdicts(findings)}
    assert verdicts["c1"].disposition is Q and verdicts["c1"].confidence == 0.85 and verdicts["c1"].finding_count == 2
    assert verdicts["c2"].disposition is A
    assert verdicts["c3"].disposition is R and verdicts["c3"].coverage_gaps == ["M1.source_risk"]
    assert overall_verdict(verdicts.values()) is Q
    ordered = asset_verdicts(findings)
    assert ordered[0].asset.id == "c1"  # most severe first


def test_analyst_can_accept_gap_but_it_stays_visible():
    gap = _finding("fnd_4", "c3", R, 1.0, FindingStatus.UNAVAILABLE, check="M1.source_risk")
    v = asset_verdicts([gap], [_decision("dec_1", "fnd_4", A, "2026-09-29T10:00:00.000Z")])[0]
    assert v.disposition is A and v.coverage_gaps == ["M1.source_risk"]


def test_overall_of_nothing_is_accept():
    assert overall_verdict([]) is A


def test_access_can_only_be_lowered():
    assert effective_access(AccessLevel.WB) is AccessLevel.WB
    assert effective_access(AccessLevel.WB, AccessLevel.BB_S) is AccessLevel.BB_S
    with pytest.raises(AccessLevelError):
        effective_access(AccessLevel.BB_L, AccessLevel.WB)
    assert AccessLevel.WB.satisfies(AccessLevel.BB_S) and not AccessLevel.BB_L.satisfies(AccessLevel.BB_S)
