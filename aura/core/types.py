"""Core domain model (CLAUDE.md A7). Modules communicate only through these types.

The ``Finding`` is the central object: every module emits findings, and every finding
carries the five fields the problem statement demands of a flag (R-GOV-1): reason,
evidence, confidence/severity, affected asset and recommended disposition. The JSON
Schema in ``schemas/finding.schema.json`` is the exported contract for the same shape;
``tests/test_schema.py`` keeps the two in agreement.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from aura.core.ids import TIMESTAMP_PATTERN

# --------------------------------------------------------------------------- enums


class AssetType(str, Enum):
    SAMPLE = "sample"
    CONTRIBUTOR = "contributor"
    BATCH = "batch"
    SOURCE = "source"
    DATASET = "dataset"
    MODEL = "model"
    INFERENCE_RECORD = "inference_record"
    RECORD_STREAM = "record_stream"
    INPUT_BATCH = "input_batch"
    REFERENCE = "reference"
    AUDIT_LOG = "audit_log"
    REPORT = "report"


class AccessLevel(str, Enum):
    """Model access available to Module 2 (R-MOD-2, R-CON-5).

    BB-L: black-box, labels/boxes only. BB-S: black-box with scores/logits.
    WB: weights + activations (+ gradients for TorchScript).
    """

    NONE = "NONE"
    BB_L = "BB-L"
    BB_S = "BB-S"
    WB = "WB"

    @property
    def rank(self) -> int:
        return _ACCESS_RANK[self]

    def satisfies(self, required: "AccessLevel") -> bool:
        return self.rank >= required.rank


_ACCESS_RANK = {AccessLevel.NONE: 0, AccessLevel.BB_L: 1, AccessLevel.BB_S: 2, AccessLevel.WB: 3}


class Task(str, Enum):
    CLASSIFICATION = "classification"
    DETECTION = "detection"


class Disposition(str, Enum):
    ACCEPT = "ACCEPT"
    REVIEW = "REVIEW"
    QUARANTINE = "QUARANTINE"

    @property
    def rank(self) -> int:
        return {"ACCEPT": 0, "REVIEW": 1, "QUARANTINE": 2}[self.value]


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}[self.value]


class FindingStatus(str, Enum):
    FLAGGED = "FLAGGED"
    UNAVAILABLE = "UNAVAILABLE"


class ModuleId(str, Enum):
    M1 = "M1"
    M2 = "M2"
    M3 = "M3"
    M4 = "M4"
    M5 = "M5"


class ModuleStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


class CheckRunStatus(str, Enum):
    """Outcome of one check execution (the ``status`` of a CheckRun, A7.2)."""

    COMPLETED = "COMPLETED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class AssessmentStatus(str, Enum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ReportStatus(str, Enum):
    DRAFT = "DRAFT"
    FINAL = "FINAL"


class RecordStatus(str, Enum):
    VERIFIED = "VERIFIED"
    ALTERED = "ALTERED"
    FORGED = "FORGED"
    SUBSTITUTED = "SUBSTITUTED"
    REPLAYED = "REPLAYED"
    CHAIN_BROKEN = "CHAIN_BROKEN"
    MODEL_MISMATCH = "MODEL_MISMATCH"
    CONFIG_MISMATCH = "CONFIG_MISMATCH"
    INPUT_MISMATCH = "INPUT_MISMATCH"
    UNVERIFIABLE = "UNVERIFIABLE"


class ShiftVerdict(str, Enum):
    NO_MATERIAL_SHIFT = "NO_MATERIAL_SHIFT"
    PROBABLE_OPERATIONAL_DRIFT = "PROBABLE_OPERATIONAL_DRIFT"
    SUSPICIOUS_MANIPULATION = "SUSPICIOUS_MANIPULATION"
    INCONCLUSIVE = "INCONCLUSIVE"


class Role(str, Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"


class KeyPurpose(str, Enum):
    """Separate keys per purpose (A8.3): a leaked report key cannot forge records."""

    INFERENCE = "inference"
    AUDIT = "audit"
    REPORT = "report"


class ArtefactKind(str, Enum):
    THUMBNAIL = "thumbnail"
    OVERLAY = "overlay"
    HEATMAP = "heatmap"
    CHART = "chart"
    TRIGGER_IMAGE = "trigger_image"
    TABLE = "table"
    VERIFICATION_STEPS = "verification_steps"


class AuditEvent(str, Enum):
    """Audit event vocabulary (A8.5). Anything else is rejected by the audit log."""

    SESSION_START = "SESSION_START"
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    KEY_CREATED = "KEY_CREATED"
    KEY_ROTATED = "KEY_ROTATED"
    REFERENCE_REGISTERED = "REFERENCE_REGISTERED"
    BATTERY_BUILT = "BATTERY_BUILT"
    ASSET_REGISTERED = "ASSET_REGISTERED"
    POLICY_CHANGED = "POLICY_CHANGED"
    ASSESSMENT_CREATED = "ASSESSMENT_CREATED"
    ASSESSMENT_STARTED = "ASSESSMENT_STARTED"
    ACCESS_LEVEL_SET = "ACCESS_LEVEL_SET"
    CHECK_STARTED = "CHECK_STARTED"
    CHECK_COMPLETED = "CHECK_COMPLETED"
    CHECK_UNAVAILABLE = "CHECK_UNAVAILABLE"
    FINDING_CREATED = "FINDING_CREATED"
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"
    ASSESSMENT_FAILED = "ASSESSMENT_FAILED"
    ANALYST_DECISION = "ANALYST_DECISION"
    REPORT_GENERATED = "REPORT_GENERATED"
    REPORT_FINALISED = "REPORT_FINALISED"
    REPORT_EXPORTED = "REPORT_EXPORTED"
    ATTACK_SCENARIO_GENERATED = "ATTACK_SCENARIO_GENERATED"
    EVAL_RUN = "EVAL_RUN"
    SESSION_END = "SESSION_END"


# ------------------------------------------------------------------ shared scalars

Digest = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
Timestamp = Annotated[str, StringConstraints(pattern=TIMESTAMP_PATTERN)]
Unit = Annotated[float, Field(ge=0.0, le=1.0)]
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _prefixed(prefix: str) -> Any:
    return Annotated[str, StringConstraints(pattern=rf"^{prefix}_[0-9A-Za-z_-]+$")]


class _Model(BaseModel):
    model_config = ConfigDict(use_enum_values=False, extra="forbid")


# ----------------------------------------------------------------- finding (A7.3)


class Actor(_Model):
    type: Literal["system", "user"]
    id: NonEmptyStr


class AssetRef(_Model):
    type: AssetType
    id: NonEmptyStr
    digest: Digest | None = None


class VerificationStep(_Model):
    """One step of a verification procedure. ``passed=None`` means not performed."""

    step: NonEmptyStr
    passed: bool | None
    detail: str = ""


class Evidence(BaseModel):
    """Structured evidence behind a finding (R-GOV-1, R-GEN-3).

    Extra keys are allowed (e.g. ``rules_fired`` for Module 4, ``fallback_used`` for
    UNAVAILABLE findings) so checks can attach module-specific evidence.
    """

    model_config = ConfigDict(extra="allow")

    metrics: dict[str, Any] = Field(default_factory=dict)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    sample_ids: list[str] = Field(default_factory=list)
    artefact_ids: list[str] = Field(default_factory=list)
    verification_steps: list[VerificationStep] | None = None


class Finding(_Model):
    """A single flag raised by a check. Immutable once created (A7.2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: _prefixed("fnd")  # type: ignore[valid-type]
    assessment_id: str | None = None
    module: ModuleId
    check_id: NonEmptyStr
    created_at: Timestamp
    status: FindingStatus
    reason: NonEmptyStr
    evidence: Evidence
    confidence: Unit
    severity: Severity
    affected_asset: AssetRef
    recommended_disposition: Disposition
    limitations: list[str] = Field(default_factory=list)

    @field_validator("reason")
    @classmethod
    def _reason_is_prose(cls, v: str) -> str:
        # R-GOV-1 asks for a *human-readable* reason: guard against placeholder text.
        if v.lower() in {"todo", "tbd", "n/a", "none", "-"}:
            raise ValueError("reason must be a human-readable explanation, not a placeholder")
        return v

    @model_validator(mode="after")
    def _status_rules(self) -> "Finding":
        # Same two rules as the allOf block in schemas/finding.schema.json.
        if self.status is FindingStatus.FLAGGED:
            ev = self.evidence
            if not (ev.metrics or ev.sample_ids or ev.artefact_ids or ev.verification_steps):
                raise ValueError("a FLAGGED finding needs supporting evidence (metrics, samples, artefacts or steps)")
        elif self.recommended_disposition is Disposition.ACCEPT:
            raise ValueError("an UNAVAILABLE finding can never recommend ACCEPT (coverage gap)")
        return self


# --------------------------------------------------------------- entities (A7.2)


class User(_Model):
    id: _prefixed("usr")  # type: ignore[valid-type]
    username: NonEmptyStr
    password_hash: NonEmptyStr
    role: Role
    created_at: Timestamp
    disabled: bool = False


class Asset(_Model):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyStr
    type: AssetType
    name: NonEmptyStr
    path: str
    format: str | None = None
    digest: Digest
    metadata: dict[str, Any] = Field(default_factory=dict)
    registered_by: str
    registered_at: Timestamp


class DatasetAsset(Asset):
    task: Task
    class_names: list[str]
    n_images: int = Field(ge=0)
    n_annotations: int = Field(ge=0)
    has_contributor_metadata: bool = False
    validation_summary: dict[str, Any] = Field(default_factory=dict)


class ModelAsset(Asset):
    task: Task
    class_names: list[str]
    input_spec: dict[str, Any] = Field(default_factory=dict)
    preprocessing_config: dict[str, Any] = Field(default_factory=dict)
    weight_digest: Digest
    structure_digest: Digest | None = None
    detected_access_level: AccessLevel
    declared_access_level: AccessLevel | None = None
    registered_fingerprint_id: str | None = None


class RecordStreamAsset(Asset):
    stream_id: NonEmptyStr
    n_records: int = Field(ge=0)
    signer_key_ids: list[str] = Field(default_factory=list)


class InputBatchAsset(Asset):
    n_images: int = Field(ge=0)
    acquisition_metadata: dict[str, Any] = Field(default_factory=dict)


class ReferenceAsset(Asset):
    n_images: int = Field(ge=0)
    embedding_digest: Digest | None = None
    descriptor_digest: Digest | None = None
    calibration_set_digest: Digest | None = None
    is_default: bool = False


class Assessment(_Model):
    id: _prefixed("asm")  # type: ignore[valid-type]
    name: NonEmptyStr
    created_by: str
    status: AssessmentStatus = AssessmentStatus.DRAFT
    dataset_id: str | None = None
    model_id: str | None = None
    record_stream_id: str | None = None
    input_batch_id: str | None = None
    reference_id: str | None = None
    modules_selected: list[ModuleId]
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    access_level_used: AccessLevel | None = None
    started_at: Timestamp | None = None
    finished_at: Timestamp | None = None
    error: str | None = None


class ModuleRun(_Model):
    assessment_id: str
    module: ModuleId
    status: ModuleStatus = ModuleStatus.PENDING
    progress: Unit = 0.0
    started_at: Timestamp | None = None
    finished_at: Timestamp | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class CheckRun(_Model):
    module_run_id: str | None = None
    check_id: NonEmptyStr
    version: NonEmptyStr
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: CheckRunStatus
    duration_ms: int = Field(ge=0)
    message: str = ""
    fallback_used: str | None = None


class Decision(_Model):
    """Analyst confirmation or override. Append-only; the latest one is effective."""

    id: _prefixed("dec")  # type: ignore[valid-type]
    finding_id: _prefixed("fnd")  # type: ignore[valid-type]
    analyst_id: NonEmptyStr
    decision: Disposition
    justification: NonEmptyStr
    decided_at: Timestamp


class Artefact(_Model):
    id: _prefixed("art")  # type: ignore[valid-type]
    kind: ArtefactKind
    path: str
    digest: Digest
    finding_id: str | None = None


class Report(_Model):
    id: _prefixed("rep")  # type: ignore[valid-type]
    assessment_id: str
    status: ReportStatus = ReportStatus.DRAFT
    json_path: str
    html_path: str | None = None
    pdf_path: str | None = None
    report_digest: Digest
    signature: str
    key_id: str
    audit_head_hash: Digest
    created_by: str
    created_at: Timestamp


class AuditEntry(_Model):
    """One line of the tamper-evident audit log (R-GOV-2, design.md §14.3)."""

    index: int = Field(ge=0)
    timestamp: Timestamp
    actor: Actor
    event: AuditEvent
    payload: dict[str, Any]
    payload_sha256: Digest
    prev_entry_hash: Digest
    entry_hash: Digest
    key_id: NonEmptyStr
    signature: NonEmptyStr


class KeyInfo(_Model):
    """Public half of a signing key; safe to store in the DB and print in reports."""

    key_id: NonEmptyStr
    purpose: KeyPurpose
    algorithm: Literal["Ed25519"] = "Ed25519"
    public_key: NonEmptyStr  # "b64:" + raw 32-byte Ed25519 public key
    created_at: Timestamp
    retired_at: Timestamp | None = None

    @property
    def active(self) -> bool:
        return self.retired_at is None


class AttackRun(_Model):
    id: _prefixed("atk")  # type: ignore[valid-type]
    scenario_id: NonEmptyStr
    seed: int
    config: dict[str, Any] = Field(default_factory=dict)
    output_asset_ids: list[str] = Field(default_factory=list)
    manifest_path: str  # restricted: only aura.eval may read it (A3 rule 8)
    created_at: Timestamp


class EvalRun(_Model):
    id: _prefixed("evl")  # type: ignore[valid-type]
    attack_run_ids: list[str]
    assessment_ids: list[str]
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_at: Timestamp
