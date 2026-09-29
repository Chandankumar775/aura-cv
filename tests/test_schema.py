"""Finding schema: the five R-GOV-1 fields are mandatory, and the Pydantic model agrees."""

import copy

import pytest
from pydantic import ValidationError

from aura.core.schemas import SchemaValidationError, errors_for, validate_finding
from aura.core.types import Finding

VALID = {
    "id": "fnd_0123456789abcdef",
    "assessment_id": "asm_1",
    "module": "M1",
    "check_id": "M1.dup.phash",
    "created_at": "2026-09-29T10:15:02.000Z",
    "status": "FLAGGED",
    "reason": "Twelve images from contributor C are near-copies of one image.",
    "evidence": {
        "metrics": {"cluster_size": 12},
        "thresholds": {"max_hamming": 6},
        "sample_ids": ["s1", "s2"],
        "artefact_ids": [],
    },
    "confidence": 0.9,
    "severity": "MEDIUM",
    "affected_asset": {"type": "contributor", "id": "contributor_C"},
    "recommended_disposition": "REVIEW",
    "limitations": [],
}

MANDATORY = ["reason", "evidence", "confidence", "severity", "affected_asset", "recommended_disposition"]


def _both_reject(doc):
    assert errors_for("finding", doc), "JSON schema accepted an invalid finding"
    with pytest.raises(ValidationError):
        Finding.model_validate(doc)


def test_valid_finding_passes_both():
    validate_finding(VALID)
    f = Finding.model_validate(VALID)
    validate_finding(f)  # round-trip through the model still validates


@pytest.mark.parametrize("field", MANDATORY + ["id", "module", "check_id", "created_at", "status"])
def test_each_required_field_is_enforced(field):
    doc = copy.deepcopy(VALID)
    del doc[field]
    _both_reject(doc)


@pytest.mark.parametrize("reason", ["", "   ", "TODO"])
def test_reason_must_be_readable(reason):
    doc = {**copy.deepcopy(VALID), "reason": reason}
    with pytest.raises(ValidationError):
        Finding.model_validate(doc)
    if not reason.strip():
        assert errors_for("finding", doc)


@pytest.mark.parametrize(
    "patch",
    [
        {"confidence": 1.2},
        {"confidence": -0.1},
        {"severity": "SEVERE"},
        {"recommended_disposition": "IGNORE"},
        {"module": "M9"},
        {"id": "F-M1-0007"},
        {"created_at": "yesterday"},
        {"affected_asset": {"type": "planet", "id": "x"}},
        {"affected_asset": {"type": "model", "id": "m", "digest": "sha256:abc"}},
        {"unexpected_field": 1},
    ],
)
def test_bad_values_rejected(patch):
    _both_reject({**copy.deepcopy(VALID), **patch})


def test_flagged_finding_requires_some_evidence():
    doc = copy.deepcopy(VALID)
    doc["evidence"] = {"metrics": {}, "thresholds": {"t": 1}, "sample_ids": [], "artefact_ids": []}
    _both_reject(doc)


def test_verification_steps_count_as_evidence():
    doc = copy.deepcopy(VALID)
    doc["evidence"] = {
        "metrics": {},
        "thresholds": {},
        "sample_ids": [],
        "artefact_ids": [],
        "verification_steps": [{"step": "signature", "passed": False, "detail": "mismatch"}],
    }
    validate_finding(doc)
    Finding.model_validate(doc)


def test_unavailable_finding_valid_but_never_accept():
    doc = copy.deepcopy(VALID)
    doc.update(
        status="UNAVAILABLE",
        reason="Check M2.trigger_reconstruction could not run: requires WB access.",
        evidence={"metrics": {}, "thresholds": {}, "sample_ids": [], "artefact_ids": [], "fallback_used": "M2.patch_probe"},
        confidence=1.0,
        severity="MEDIUM",
        affected_asset={"type": "model", "id": "mdl_1"},
    )
    validate_finding(doc)
    Finding.model_validate(doc)
    doc["recommended_disposition"] = "ACCEPT"
    _both_reject(doc)


def test_findings_are_immutable():
    f = Finding.model_validate(VALID)
    with pytest.raises(ValidationError):
        f.reason = "changed"  # type: ignore[misc]


def test_validate_finding_raises_with_messages():
    with pytest.raises(SchemaValidationError) as exc:
        validate_finding({**VALID, "confidence": 3})
    assert any("confidence" in e for e in exc.value.errors)
