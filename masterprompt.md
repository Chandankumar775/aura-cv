# AURA-CV Master Build Prompt (for Claude / Claude Code)

---

## 0. How to Use This File (read this first, this part is for you, not for Claude)

A system this size should **not** be built from one giant message in one go. Claude works best with a stable spec plus small, verifiable milestones. So this file has four parts:

| Part | What it is | How to use it |
|---|---|---|
| **Part A: Master Spec** | The complete, permanent specification | Save it as `CLAUDE.md` in the repository root. Claude Code reads `CLAUDE.md` automatically at the start of every session, so the spec is never forgotten. |
| **Part B: Kickoff Prompt** | The first message you send | Paste it once to start the project. Claude plans and builds Milestone 0 only. |
| **Part C: Milestone Prompts** | One prompt per milestone | After each milestone passes its checks, paste the next one. |
| **Part D: Review Prompts** | Quality and requirement checks | Paste these at the end, or whenever something looks wrong. |

Also copy your solution document (`AURA-CV_Solution_Document.md`) into the repo as `docs/design.md`. Part A refers to it for extra detail.

Recommended workflow:

1. Create an empty folder `aura-cv/`. Copy everything from the **PART A** heading down to (but not including) the **PART B** heading into `aura-cv/CLAUDE.md`. Put the solution document in `aura-cv/docs/design.md`.
2. Open Claude Code in that folder.
3. Paste **Part B**. Review the plan it produces before letting it continue.
4. For each milestone, paste the Part C prompt, let it build, then run the tests yourself and look at the result.
5. Commit to git after every milestone that passes.

---
---

# PART A: MASTER SPEC (save as `CLAUDE.md`)

## A1. Role and Mission

You are a senior engineer building **AURA-CV (Air-Gapped Unified Risk & Assurance for Computer Vision)**, a solution for a Smart India Hackathon problem statement from the Ministry of Defence titled **"Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines."**

AURA-CV is an **offline, model-agnostic, extensible assurance framework** that evaluates a contributed **dataset**, a trained **model**, associated **inference records**, and new **operational input batches**, and produces an **evidence-based assessment of integrity and risk**, without assuming that any contributing source is trusted.

The users are **analysts and administrators** in an air-gapped environment. They are not ML experts. Every result must be understandable, backed by evidence, and actionable.

Extra design detail lives in `docs/design.md`. If this file and `docs/design.md` disagree, **this file wins**. If something is unspecified in both, choose the simplest option that satisfies the requirements, and write the decision in `docs/decisions.md`.

## A2. Problem Statement Requirements (the contract)

Every feature must trace to one of these IDs. Reference the IDs in code comments, tests and docs where relevant.

**General**
- **R-GEN-1** Extensible framework, not hard-coded to a single model architecture or dataset; model-agnostic.
- **R-GEN-2** Assess risks without assuming every contributing source is trusted.
- **R-GEN-3** Produce an evidence-based assessment of integrity and risk.

**Module 1: Training-Data Integrity (PS 2.2.1)**
- **R-DATA-1** Identify samples associated with **trigger injection**.
- **R-DATA-2** Identify **label flipping**.
- **R-DATA-3** Identify **systematic mislabelling**.
- **R-DATA-4** Identify **near-duplicate flooding**.
- **R-DATA-5** Identify **out-of-distribution insertion**.
- **R-DATA-6** When contributor, batch or source metadata exists, aggregate sample-level evidence into **source-level risk** instead of flagging samples in isolation.

**Module 2: Model Integrity (PS 2.2.2)**
- **R-MOD-1** Assess whether a model shows **anomalous, substituted or backdoor-like** behaviour.
- **R-MOD-2** Use methods appropriate to the **level of access**: behavioural fingerprinting, trigger search or reconstruction, parameter or activation statistics, comparison against a defined reference battery.
- **R-MOD-3** State the **access assumptions, confidence and limitations** of every assessment.

**Module 3: Inference Provenance and Output Integrity (PS 2.2.3)**
- **R-INF-1** Verifiable cryptographic binding among **input image, model identifier or weight digest, preprocessing and inference configuration, and output**.
- **R-INF-2** Make post-hoc **alteration, substitution or replay** detectable using **hashes, signatures, and sequence, timestamp or nonce** controls.

**Module 4: Distribution-Shift and Anomaly Assessment (PS 2.2.4)**
- **R-SHIFT-1** Detect material deviation from a **declared reference distribution** (terrain, season, sensor, illumination, acquisition conditions).
- **R-SHIFT-2** **Characterise** the observed shift.
- **R-SHIFT-3** Provide a **calibrated** risk or confidence score.
- **R-SHIFT-4** Distinguish **probable operational drift** from **suspicious manipulation**, but only **where evidence supports it**.

**Module 5: Analyst-Facing Assurance and Governance (PS 2.2.5)**
- **R-GOV-1** Every flag has: **human-readable reason, supporting evidence, confidence or severity, affected asset, recommended disposition (ACCEPT / REVIEW / QUARANTINE)**.
- **R-GOV-2** Maintain a **tamper-evident audit trail**.
- **R-GOV-3** **Explicitly declare** attack classes or conditions that are not supported.

**Constraints (PS 2.2.6)**
- **R-CON-1** The complete evaluation workflow runs **offline and air-gapped**, with no dependency on cloud services or external APIs.
- **R-CON-2** Ingest **COCO and YOLO** dataset formats.
- **R-CON-3** Support **ONNX and PyTorch/TorchScript** models.
- **R-CON-4** Baseline integrity assessment **must not retrain** the contributed model. Optional remediation may retrain.
- **R-CON-5** White-box methods must **fall back gracefully or clearly report unavailability** under black-box access.

**Expected solution and deliverables (PS 2.3)**
- **R-EXP-1** Use publicly available or team-generated datasets and models.
- **R-EXP-2** **Reproducible** methods to introduce poisoning, backdoor, substitution and tampering scenarios.
- **R-EXP-3** Assurance report stating **confidence, limitations and recommended action**.
- **R-DEL-1..5** Deliver: source code; architecture and setup notes; assurance-report schema; reproducible audit log; coverage statement.

## A3. Non-Negotiable Rules

1. **No network at runtime.** No code path may make an outbound network call. No telemetry. No CDN links in the frontend. No calls to any hosted AI or cloud API. Enforce with a test that blocks sockets during the full test suite (except localhost).
2. **Never fabricate results.** Never hard-code detection outcomes, metrics, or "demo" numbers into code, UI or docs. Every number shown must be computed. Placeholder content must be visibly labelled as placeholder.
3. **Never retrain the contributed model during assessment** (R-CON-4). Training exists only in the Attack Lab (to create test models) and in optional remediation, and both must be clearly separated and labelled.
4. **Never silently skip a check.** If a check cannot run, emit a finding with `status: UNAVAILABLE` and a reason (R-CON-5).
5. **Every finding must pass schema validation** with the five mandatory fields (R-GOV-1). A finding that fails validation is a bug.
6. **Every state-changing action writes an audit entry** (R-GOV-2).
7. **Untrusted model files are never unpickled.** Accept ONNX, TorchScript, and PyTorch `state_dict` via `torch.load(..., weights_only=True)` with a registered architecture only.
8. **Ground-truth manifests from the Attack Lab are never read by detectors.** Only the evaluation harness may read them.
9. **Say "tamper-evident", never "tamper-proof" or "impossible to tamper".**
10. **Deterministic by seed.** Every random process takes an explicit seed. Same inputs + same seed = same data artefacts and same findings.

## A4. How You Should Work

- **Plan before coding.** At the start of each milestone, write a short plan: files to create, interfaces, tests. Then implement.
- **Build in milestones** (Part C). Do not start the next milestone until the current one's acceptance checks pass. At the end of each milestone, report: what was built, what tests ran and their results, what is incomplete, and any decisions made.
- **Tests first for core logic.** Crypto, audit chain, schema validation, format adapters and disposition policy must have unit tests.
- **Use tiny synthetic data in tests.** Tests must not depend on downloading datasets. Generate small synthetic images (coloured shapes, textures) with fixed seeds inside the test suite.
- **Check library APIs against installed versions** rather than relying on memory. If an API differs from what you expected, adapt and note it.
- **Keep modules decoupled.** Modules communicate only through the domain types in A7.
- **Type everything.** Python type hints and Pydantic models; TypeScript on the frontend.
- **Small, readable functions.** Prefer clarity over cleverness. Add docstrings explaining the *why* and linking requirement IDs.
- **Update docs as you go**: `docs/architecture.md`, `docs/setup.md`, `docs/coverage_statement.md`, `docs/decisions.md`.
- **Ask before adding scope** that is not in this spec. List it in `docs/future.md` instead.
- **If something is ambiguous**, pick the simplest compliant option, proceed, and record it in `docs/decisions.md`.

## A5. Technology Stack

| Layer | Choice |
|---|---|
| Language | Python 3.10+ |
| API | FastAPI + Uvicorn, bound to `127.0.0.1` only |
| Validation | Pydantic v2, `jsonschema` (draft 2020-12) |
| Storage | SQLite (via SQLAlchemy 2.x or SQLModel) + a local `data/` directory for artefacts |
| Jobs | In-process background job runner (thread or process pool). **No Redis, no Celery, no external brokers.** |
| CV / ML | PyTorch (CPU), TorchScript, ONNX Runtime (CPU), `onnx`, OpenCV, NumPy, SciPy, scikit-learn, Pillow |
| Hashing | `hashlib` (SHA-256), `imagehash` (pHash) |
| Crypto | `cryptography` (Ed25519); RFC 8785 JSON canonicalisation (use a maintained library if available offline, otherwise implement per RFC 8785 with tests) |
| Reports | Jinja2 HTML templates; PDF via a locally installed renderer (for example WeasyPrint); if PDF rendering is unavailable, report that clearly and still provide HTML |
| CLI | Typer |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS + Lucide icons + Recharts; HTML5 Canvas for overlays. Built to static files and served by FastAPI. |
| Tests | pytest, pytest-socket (or an equivalent socket blocker), Vitest for frontend units, Playwright optional for E2E |
| Packaging | Pinned `requirements.txt`, offline wheelhouse, prebuilt frontend bundle, bundled model weights |

Pin versions. Keep dependencies minimal. Every dependency must be installable offline from a wheelhouse.

## A6. Repository Layout

```
aura-cv/
├── CLAUDE.md                      # this spec
├── README.md
├── docs/
│   ├── design.md                  # solution document
│   ├── architecture.md
│   ├── setup.md
│   ├── coverage_statement.md
│   ├── threat_model.md
│   ├── decisions.md
│   ├── future.md
│   └── demo_script.md
├── schemas/
│   ├── finding.schema.json
│   ├── assurance_report.schema.json
│   ├── inference_record.schema.json
│   └── audit_entry.schema.json
├── aura/
│   ├── __init__.py
│   ├── config.py                  # settings, paths, policy defaults
│   ├── core/
│   │   ├── types.py               # enums, domain models (A7)
│   │   ├── checks.py              # Check protocol, registry, scheduler
│   │   ├── access.py              # access level detection
│   │   ├── policy.py              # disposition policy
│   │   ├── hashing.py             # sha256 helpers, digest format
│   │   └── canonical.py           # RFC 8785 canonical JSON
│   ├── storage/                   # db models, repositories, artefact store
│   ├── jobs/                      # background runner, progress events
│   ├── adapters/
│   │   ├── datasets/              # coco.py, yolo.py, imagefolder.py, metadata.py
│   │   └── models/                # base.py, onnx_model.py, torchscript_model.py, statedict_model.py
│   ├── features/                  # frozen extractor, embedding index
│   ├── m1_data/                   # annot_sanity, triggers, flips, systematic, duplicates, ood, source_risk
│   ├── m2_model/                  # digest, structure, fingerprint, battery, reconstruction, activations, params, strip, probing
│   ├── m3_provenance/             # keys, signer, verifier, attested_inference
│   ├── m4_shift/                  # reference, descriptors, tests, calibration, verdict
│   ├── m5_governance/             # audit_log, findings_service, decisions, report_builder, exporters
│   ├── attack_lab/                # scenario registry, generators, manifests
│   ├── eval/                      # harness, metrics
│   ├── api/                       # FastAPI app, routers, schemas, auth
│   └── cli.py
├── ui/                            # React app
├── assets/
│   ├── weights/                   # bundled frozen feature extractor
│   ├── battery/                   # reference battery bundle
│   └── fonts/
├── attack_lab_configs/            # YAML scenarios
├── data/                          # runtime: db, artefacts, uploads (gitignored)
├── keys/                          # runtime: generated keys (gitignored)
├── scripts/
│   ├── prepare_offline_bundle.sh  # run on a CONNECTED machine: wheels, weights, npm build
│   └── install_offline.sh         # run on the AIR-GAPPED machine
├── tests/
└── wheelhouse/                    # gitignored, produced by prepare script
```

## A7. Core Domain Model

### A7.1 Enums

```
AssetType      = sample | contributor | batch | source | dataset | model | inference_record
                 | record_stream | input_batch | reference | audit_log | report
AccessLevel    = NONE | BB-L | BB-S | WB
                 # BB-L: black-box labels/boxes only; BB-S: black-box with scores/logits;
                 # WB: weights + activations (+ gradients for TorchScript)
Task           = classification | detection
Disposition    = ACCEPT | REVIEW | QUARANTINE
Severity       = LOW | MEDIUM | HIGH | CRITICAL
FindingStatus  = FLAGGED | UNAVAILABLE
ModuleId       = M1 | M2 | M3 | M4 | M5
ModuleStatus   = PENDING | RUNNING | COMPLETED | PARTIAL | UNAVAILABLE | ERROR | CANCELLED
AssessmentStatus = DRAFT | QUEUED | RUNNING | COMPLETED | FAILED | CANCELLED
ReportStatus   = DRAFT | FINAL
RecordStatus   = VERIFIED | ALTERED | FORGED | SUBSTITUTED | REPLAYED | CHAIN_BROKEN
                 | MODEL_MISMATCH | CONFIG_MISMATCH | INPUT_MISMATCH | UNVERIFIABLE
ShiftVerdict   = NO_MATERIAL_SHIFT | PROBABLE_OPERATIONAL_DRIFT | SUSPICIOUS_MANIPULATION | INCONCLUSIVE
Role           = ADMIN | ANALYST
```

### A7.2 Entities

| Entity | Key fields |
|---|---|
| **User** | id, username, password_hash (argon2 or bcrypt), role, created_at, disabled |
| **Asset** | id (prefixed: `ds_`, `mdl_`, `rs_`, `ib_`, `ref_`), type, name, path, format, digest (`sha256:<hex>`), metadata JSON, registered_by, registered_at |
| **Dataset** (Asset) | task, class_names, n_images, n_annotations, has_contributor_metadata, validation_summary |
| **Model** (Asset) | format, task, class_names, input_spec, preprocessing_config, weight_digest, structure_digest, detected_access_level, declared_access_level, registered_fingerprint_id |
| **RecordStream** (Asset) | stream_id, n_records, signer_key_ids |
| **InputBatch** (Asset) | n_images, acquisition_metadata |
| **Reference** (Asset) | n_images, embedding_digest, descriptor_digest, calibration_set_digest, is_default |
| **Assessment** | id (`asm_`), name, created_by, status, asset ids, modules_selected, config_snapshot (thresholds, policy, seeds), access_level_used, started_at, finished_at, error |
| **ModuleRun** | assessment_id, module, status, progress (0..1), started_at, finished_at, summary JSON |
| **CheckRun** | module_run_id, check_id, version, parameters, status, duration_ms, message |
| **Finding** | see A7.3; **immutable** after creation |
| **Decision** | id, finding_id, analyst_id, decision (Disposition), justification (non-empty), decided_at; **append-only**, latest wins |
| **Artefact** | id, kind (thumbnail, overlay, heatmap, chart, trigger_image, table, verification_steps), path, digest, finding_id |
| **Report** | id (`rep_`), assessment_id, status (DRAFT/FINAL), json_path, html_path, pdf_path, report_digest, signature, key_id, audit_head_hash, created_by, created_at |
| **AuditEntry** | index, timestamp, actor {type: system/user, id}, event, payload, payload_sha256, prev_entry_hash, entry_hash, signature, key_id |
| **Key** | key_id, purpose (inference / audit / report), public_key, created_at, retired_at |
| **AttackRun** | id, scenario_id, seed, config, output_asset_ids, manifest_path (restricted), created_at |
| **EvalRun** | id, attack_run_ids, assessment_ids, metrics JSON, created_at |

### A7.3 Finding (the central object)

```
Finding {
  id: "fnd_..."
  assessment_id
  module: M1..M5
  check_id: e.g. "M1.dup.phash"
  created_at
  status: FLAGGED | UNAVAILABLE
  reason: str (1-3 plain sentences, non-empty)                 # R-GOV-1
  evidence: {                                                   # R-GOV-1
    metrics: {...}, thresholds: {...},
    sample_ids: [...], artefact_ids: [...],
    verification_steps?: [{step, passed, detail}]
  }
  confidence: float 0..1                                        # R-GOV-1
  severity: LOW|MEDIUM|HIGH|CRITICAL                            # R-GOV-1
  affected_asset: {type, id, digest?}                           # R-GOV-1
  recommended_disposition: ACCEPT|REVIEW|QUARANTINE             # R-GOV-1
  limitations: [str]
}
```

For `UNAVAILABLE` findings: `reason` explains why the check could not run, `confidence` is the confidence in the unavailability itself (normally 1.0), `severity` reflects the risk of the coverage gap (normally MEDIUM), and `recommended_disposition` is REVIEW for the affected asset.

### A7.4 Check plugin interface (R-GEN-1)

```python
class Check(Protocol):
    id: str
    module: ModuleId
    version: str
    requires_access: AccessLevel     # minimum model access (NONE for data-only checks)
    requires_inputs: set[str]        # e.g. {"dataset"}, {"model", "battery"}
    fallback_check_id: str | None
    def is_applicable(self, ctx: AssessmentContext) -> tuple[bool, str]: ...
    def run(self, ctx: AssessmentContext, progress: ProgressFn) -> list[Finding]: ...
```

A registry holds all checks. The scheduler, per module: filters by required inputs, compares `requires_access` to the context's access level, runs applicable checks, runs the fallback if the primary is not applicable, otherwise emits an `UNAVAILABLE` finding. Every check run writes `CHECK_STARTED` and `CHECK_COMPLETED` or `CHECK_UNAVAILABLE` to the audit log.

### A7.5 Disposition policy (configurable, stored in config, changes audited)

| Severity \ Confidence | < 0.4 | 0.4 – 0.8 | > 0.8 |
|---|---|---|---|
| LOW | ACCEPT | ACCEPT | REVIEW |
| MEDIUM | ACCEPT | REVIEW | REVIEW |
| HIGH | REVIEW | REVIEW | QUARANTINE |
| CRITICAL | REVIEW | QUARANTINE | QUARANTINE |

Hard overrides: signature failure, model digest mismatch, or audit chain break → always QUARANTINE. An UNAVAILABLE check never lets the affected asset be ACCEPT on that aspect; the asset shows a coverage gap.

**Asset verdict** = most severe effective disposition among its findings (effective = latest analyst decision if present, otherwise recommended). **Overall verdict** = most severe asset verdict.

## A8. Module Specifications

### A8.0 Shared components

- **Dataset adapters** (R-CON-2): `coco` (instances JSON), `yolo` (per-image `.txt` with `class cx cy w h` normalised + `data.yaml` or `classes.txt`), `imagefolder` (`root/<class>/<img>`). Auto-detect format. Produce a unified `DatasetView` of samples: `{sample_id, image_path, image_digest, labels: [{class_id, bbox?}], contributor_id?, batch_id?, source_id?}`. Detection datasets also expose an **object-level view** (cropped boxes as labelled samples).
- **Contributor metadata** loader: CSV or JSON mapping `image → contributor_id, batch_id, source_id`.
- **Model adapters** (R-CON-3): common interface `predict(images) -> outputs`, `scores(images)`, `features(images, layer)` (WB only), `gradients(...)` (TorchScript WB only), `describe_structure()`. ONNX via onnxruntime; TorchScript via `torch.jit.load`; state_dict via `weights_only=True` plus a registered architecture from a small built-in zoo (for example ResNet-18). Access level detection: WB if weights/activations are readable; BB-S if only outputs with scores; BB-L if labels only. The user may **declare a lower access level** to simulate black-box conditions (important for the demo).
- **Feature extractor**: bundled frozen backbone (ResNet-18 or MobileNetV3, ImageNet weights) in `assets/weights/`, loaded locally, CPU. Produces L2-normalised embeddings. Cache embeddings per image digest.

### A8.1 Module 1: Training-Data Integrity

| check_id | Req | Access | Method | Evidence |
|---|---|---|---|---|
| `M1.annot.sanity` | R-CON-2 | NONE | Out-of-bounds or zero-area boxes, invalid class IDs, missing images, unreadable files | list of problems per sample |
| `M1.trigger.patch_repeat` | R-DATA-1 | NONE | Hash small regions (corners + grid tiles) and find near-identical patches recurring across many images of one label | patch location overlay, count, label concentration, contributors |
| `M1.trigger.hf_residual` | R-DATA-1 | NONE | Image minus blurred image; localised, consistent high-frequency residue across samples | residual heatmaps |
| `M1.trigger.activation_cluster` | R-DATA-1 | NONE (backbone) / better with WB model | Per class: 2-cluster k-means on embeddings (reduced with PCA); small, well-separated cluster flagged | cluster sizes, silhouette, members |
| `M1.trigger.spectral` | R-DATA-1 | same as above | Per class: projection on top singular vector of centred embeddings; high-score outliers | score distribution, top samples |
| `M1.flip.knn` | R-DATA-2 | NONE | k-NN consensus label vs given label | given vs consensus, agreement ratio, neighbours |
| `M1.flip.confident` | R-DATA-2 | NONE | Cross-validated logistic regression on embeddings; flag high-confidence disagreements | out-of-sample probabilities |
| `M1.systematic.confusion` | R-DATA-3 | NONE | Per-contributor confusion matrix (consensus vs given) vs pooled others; per-cell test with multiple-comparison correction | contributor, source→target class, rates |
| `M1.dup.phash` | R-DATA-4 | NONE | pHash, Hamming ≤ configurable threshold; union-find clusters | cluster members, distances |
| `M1.dup.embed` | R-DATA-4 | NONE | Cosine similarity ≥ configurable threshold; merge with pHash clusters | cluster, similarities |
| `M1.ood.knn` | R-DATA-5 | NONE | k-NN distance to reference/bulk; threshold at configurable percentile of trusted reference scores | score, threshold, percentile |
| `M1.ood.mahalanobis` | R-DATA-5 | NONE | Per-class Gaussian on embeddings | score, threshold |
| `M1.source_risk` | R-DATA-6 | NONE | Beta-Binomial per contributor/batch/source: prior Beta(α,β), posterior Beta(α+k, β+n−k) with k = confidence-weighted flags; risk = P(θ > p₀) × 100; per-type breakdown | table row per source |

If no contributor metadata: `M1.source_risk` → UNAVAILABLE with reason "no contributor/batch/source metadata supplied".

Module 1 outputs: findings; `source_risk` table; duplicate clusters; per-contributor confusion matrices.

### A8.2 Module 2: Model Integrity

| check_id | Req | Min access | Method |
|---|---|---|---|
| `M2.digest` | R-MOD-1 | NONE (file) | SHA-256 of weight file vs registered/declared digest. First-time model → register and report "baseline registered; substitution detectable from now on". |
| `M2.structure` | R-MOD-1 | WB | Canonical graph/layer description digest vs registered |
| `M2.fingerprint` | R-MOD-1, R-MOD-2 | BB-L | Run reference battery; top-1 agreement vs registered fingerprint; with BB-S also output-distribution divergence |
| `M2.reference_accuracy` | R-MOD-1 | BB-L | Accuracy on battery clean set vs supplier claim (if claim provided) |
| `M2.trigger_reconstruction` | R-MOD-1, R-MOD-2 | WB (gradients; TorchScript classification) | Neural-Cleanse-style mask+pattern optimisation per target class; MAD anomaly index; output trigger image. Bounded iterations and time budget. Fallback: `M2.patch_probe`. |
| `M2.activation_stats` | R-MOD-2 | WB | Neurons dormant on clean battery but strongly activated by candidate triggers |
| `M2.param_stats` | R-MOD-2 | WB | Per-layer kurtosis/skew vs reference; **supporting evidence only**, max severity MEDIUM |
| `M2.strip` | R-MOD-1 | BB-S | Superimpose clean images; low-entropy persistence indicates trigger |
| `M2.patch_probe` | R-MOD-1 | BB-L | Paste probe patches (plus M1 trigger candidates) on battery images; flip rate towards one class (classification) or box disappearance/class change (detection) |

Detection models: trigger reconstruction → UNAVAILABLE ("not supported for detection models in this version"), fallback to `M2.patch_probe`.

Module 2 must output an **assessment_context** block: access level used, checks run, checks unavailable with reasons, battery digest, overall confidence, limitations list (R-MOD-3).

**Reference battery** (`assets/battery/`): versioned, hashed bundle of clean samples per class, controlled variants (brightness, blur, noise, JPEG), and probe patches. Built by an admin command from a trusted reference set; its digest goes into every report.

### A8.3 Module 3: Inference Provenance

**Record fields** (R-INF-1): `record_version, stream_id, sequence, timestamp, nonce (128-bit random, base64), input {sha256, width, height, encoding}, model {id, format, weight_digest}, config {preprocessing, inference (includes output rounding precision), sha256}, output (canonicalised, rounded), prev_record_hash, signer {key_id, algorithm: Ed25519}, signature`.

**Signing:** canonical JSON (RFC 8785) of the record without `signature` → `record_hash = SHA-256(bytes)`; `signature = Ed25519(private_key, bytes)`; next record's `prev_record_hash = record_hash`. Sequence is per stream, strictly +1.

**Attested inference service:** runs the model on an image with a registered config and returns a signed record (used to create genuine records for the demo and for real use).

**Verifier** (R-INF-2): for each record, run and report every step separately:
1. schema, 2. signature, 3. chain (`prev_record_hash`), 4. sequence (+1, gaps, repeats), 5. nonce uniqueness, 6. timestamp freshness and monotonicity, 7. model digest vs registered, 8. config digest vs registered, 9. input hash vs supplied image (if supplied), 10. optional re-execution within tolerance (if image + model supplied).
Map results to `RecordStatus`. Every non-VERIFIED record creates a finding (severity CRITICAL for signature/chain/model failures). Unknown `key_id` → UNVERIFIABLE, never accepted.

**Keys:** Ed25519 keys generated locally; separate keys for inference, audit, and report signing; private keys in `keys/` with restricted file permissions; public keys stored in DB; rotation supported; retired keys still verify old data.

### A8.4 Module 4: Distribution Shift

- **Reference registration:** compute and store embeddings, descriptors, model output statistics (if a model is given), metadata summary, and digests.
- **Detection** (R-SHIFT-1): MMD with permutation test (seeded) on embeddings; per-sample k-NN novelty; per-descriptor KS tests; model output shift (class frequency, confidence distribution). Material = significant AND effect size ≥ configurable threshold.
- **Descriptors** (R-SHIFT-2): mean luminance, dynamic range, contrast, per-channel colour histogram + colour temperature estimate, sharpness (variance of Laplacian), noise estimate, 2D-FFT radial spectrum band energies, texture/edge density, resolution/aspect/JPEG quality, supplied metadata. Each maps to a factor: terrain, season, sensor, illumination, acquisition, other. Report standardised effect sizes and a generated plain-language summary built from the top descriptors (template-based, not free text generation).
- **Calibration** (R-SHIFT-3): calibration set built from Attack Lab S-scenarios on the trusted reference (no shift, natural shifts at several strengths, manipulations). Label = "operationally harmful" if the model's accuracy drop or prediction-change rate exceeds a configurable threshold. Fit isotonic regression (fallback Platt) from shift features to probability. Report ECE on held-out split and a reliability diagram. If the observed shift is outside the calibration range, mark `extrapolated: true` and lower confidence.
- **Verdict** (R-SHIFT-4): rules engine with explicit evidence rules; output PROBABLE_OPERATIONAL_DRIFT, SUSPICIOUS_MANIPULATION, or **INCONCLUSIVE** when rules conflict or evidence is weak. Rules for drift: broad/coherent shift, physically plausible descriptor pattern (global luminance change, high-frequency loss under haze/blur, colour cast), consistent with metadata, gradual model degradation. Rules for manipulation: localised/subset-concentrated shift, structured high-frequency energy inconsistent with the reference noise profile, localised patches, sharp prediction flips towards one class, small pixel change with large embedding/output change. Known ambiguity (low-light noise; low-frequency adversarial perturbation) → INCONCLUSIVE. List which rules fired in the evidence.

### A8.5 Module 5: Governance

- **Findings service:** validates every finding against `schemas/finding.schema.json` before storing; findings are immutable.
- **Decisions:** analysts confirm or override with non-empty justification; append-only; latest decision is effective.
- **Audit log** (R-GOV-2): append-only JSONL file **and** DB mirror; each entry hashed (canonical JSON excluding `entry_hash` and `signature`), linked to previous, signed with the audit key. Head hash exposed. Verification recomputes everything and returns the first failing index. Truncation is detected by comparing with head hashes stored in exported reports.
- **Audit events:** `SESSION_START, USER_LOGIN, USER_LOGOUT, KEY_CREATED, KEY_ROTATED, REFERENCE_REGISTERED, BATTERY_BUILT, ASSET_REGISTERED, POLICY_CHANGED, ASSESSMENT_CREATED, ASSESSMENT_STARTED, ACCESS_LEVEL_SET, CHECK_STARTED, CHECK_COMPLETED, CHECK_UNAVAILABLE, FINDING_CREATED, ASSESSMENT_COMPLETED, ASSESSMENT_FAILED, ANALYST_DECISION, REPORT_GENERATED, REPORT_FINALISED, REPORT_EXPORTED, ATTACK_SCENARIO_GENERATED, EVAL_RUN, SESSION_END`.
- **Report builder** (R-EXP-3): builds the assurance report JSON (schema in A13), validates it, signs it, renders HTML (and PDF if available). Report states confidence, limitations, recommended actions, coverage statement, audit head hash.
- **Report finalisation rule:** a report can be generated as **DRAFT** at any time. It can be marked **FINAL** only when every finding with recommended disposition REVIEW or QUARANTINE has at least one analyst decision. FINAL reports are immutable.
- **Coverage statement** (R-GOV-3): single source of truth in `aura/m5_governance/coverage.py` (content in A16), exported to `docs/coverage_statement.md`, embedded in every report, shown in UI.

## A9. Attack Lab (R-EXP-1, R-EXP-2)

- Scenario configs in `attack_lab_configs/*.yaml`, each with `scenario_id`, `seed`, base asset, parameters.
- Generators produce new registered assets plus a **manifest** (digests, config, seed, tool version, ground truth). Manifests are stored under a restricted path readable only by `aura/eval/`.
- Byte-identical data artefacts for the same config and seed.
- Scenario catalogue:
  - **Data:** D1 patch trigger (size, colour, position, target class, poison rate, contributor), D2 blended trigger, D3 random label flip, D4 systematic class→class relabel by one contributor, D5 near-duplicate flood (crop, brightness, flip, JPEG), D6 OOD insertion, D7 mixed contributor.
  - **Model:** M1 backdoored model (fine-tune a clean model on D1/D2 data; this is test-model creation only), M2 substituted model (different checkpoint/architecture with same interface), M3 modified weights (perturb subset / alter layer), M4 clean control.
  - **Records:** I1 alter field, I2 swap with a valid record from another image, I3 replay, I4 delete/reorder, I5 forge with unknown key, I6 substituted model or altered config.
  - **Shift:** S1 natural-style (brightness/gamma, blur, synthetic haze/dust, sensor noise, colour cast, JPEG, resolution), S2 different source dataset, S3 adversarial perturbation (FGSM/PGD, offline), S4 localised patch on subset, S5 clean control.
  - **Audit log:** L1 edit entry, L2 delete middle entry, L3 truncate tail (operates on a **copy** of the log, never the live log).
- A **built-in synthetic dataset generator** (coloured shapes on textured backgrounds, multiple classes, fixed seed) must exist so the whole system can be demonstrated without any download.

## A10. Storage and Job Execution

- SQLite database at `data/aura.db`; artefacts under `data/artefacts/<assessment_id>/`; uploads under `data/uploads/`.
- Registration by **local path** is allowed only inside configured data roots (prevent path traversal). Uploads have size limits.
- Long-running work (assessment, battery build, attack generation, eval) runs as background jobs. Progress is published per module and per check and streamed via Server-Sent Events.
- Jobs are cancellable. A crash marks the assessment FAILED with an error message and writes `ASSESSMENT_FAILED` to the audit log.
- Each assessment stores a **config snapshot** (thresholds, policy, seeds, tool version, code digest) so it is reproducible.

## A11. REST API Specification

### A11.1 Conventions

- Base path: `/api/v1`. Server binds to `127.0.0.1` only. CORS allows only the local UI origin.
- JSON everywhere. Timestamps in UTC ISO-8601. Digests formatted `sha256:<64 lowercase hex>`.
- IDs are prefixed strings: `usr_`, `ds_`, `mdl_`, `rs_`, `ib_`, `ref_`, `asm_`, `fnd_`, `dec_`, `art_`, `rep_`, `atk_`, `evl_`, `job_`.
- Pagination: `?page=1&page_size=50`; responses include `{items, page, page_size, total}`.
- Error format: `{"error": {"code": "STRING_CODE", "message": "human text", "details": {...}}}` with proper HTTP status (400 validation, 401 unauthenticated, 403 forbidden, 404 not found, 409 conflict/state, 422 schema, 500 internal).
- Auth: local session cookie (HTTP-only, SameSite=Strict) after login. Roles: **ADMIN**, **ANALYST**. ADMIN can do everything; ANALYST cannot manage users, keys, references, battery, policy, or run the Attack Lab.
- **Every mutating endpoint writes an audit entry** with the acting user.
- Long operations return `202 Accepted` with a `job_id`; progress via `GET /jobs/{id}` or SSE.

### A11.2 Endpoints

**System**

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/health` | none | Liveness |
| GET | `/system/info` | any | Version, code digest, python/runtime versions, build time |
| GET | `/system/selfcheck` | any | Offline check (no outbound network attempted/possible), bundled weights present and digest-verified, battery present, keys present, DB writable, audit chain status, PDF renderer availability. Returns per-item pass/fail. |
| GET | `/system/setup-status` | any | First-run checklist: keys created, reference registered, battery built, admin user exists |

**Auth and users**

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/auth/login` | none | `{username, password}` → session |
| POST | `/auth/logout` | any | End session |
| GET | `/auth/me` | any | Current user and role |
| GET | `/users` | ADMIN | List users |
| POST | `/users` | ADMIN | Create user `{username, password, role}` |
| PATCH | `/users/{id}` | ADMIN | Change role, disable, reset password |

The first admin is created by CLI (`aura users create-admin`), not by the API.

**Keys**

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/keys` | any | Public keys: key_id, purpose, created_at, retired_at |
| POST | `/keys` | ADMIN | Generate key `{purpose: inference|audit|report}` |
| POST | `/keys/{key_id}/rotate` | ADMIN | Retire and create replacement |

**References and battery**

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/references` | ADMIN | Register reference distribution `{name, path, metadata_path?, set_default?}` → job |
| GET | `/references` | any | List |
| GET | `/references/{id}` | any | Details, digests, descriptor summary |
| POST | `/battery/build` | ADMIN | Build reference battery from a reference `{reference_id, per_class, seed}` → job |
| GET | `/battery` | any | Current battery version, digest, contents summary |

**Assets**

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/datasets` | any | Register `{name, path, format: auto|coco|yolo|imagefolder, metadata_path?, task?}` → validation summary (images, annotations, classes, contributors, sanity issues) |
| POST | `/datasets/upload` | any | Multipart upload of a zipped dataset (size-limited) |
| GET | `/datasets` | any | List |
| GET | `/datasets/{id}` | any | Details |
| GET | `/datasets/{id}/samples` | any | Paginated samples, filter by `class`, `contributor`, `flagged` |
| GET | `/datasets/{id}/samples/{sample_id}/image` | any | Image or `?thumb=1` thumbnail |
| POST | `/models` | any | Register `{name, path, format: auto|onnx|torchscript|state_dict, task, class_names, input_spec, preprocessing_config, architecture?, declared_access_level?, claimed_accuracy?}` → digest, detected access level, structure summary |
| POST | `/models/upload` | any | Multipart upload |
| GET | `/models` | any | List |
| GET | `/models/{id}` | any | Details incl. registered fingerprint status |
| POST | `/record-streams` | any | Import records `{name, path}` (JSONL) |
| GET | `/record-streams/{id}` | any | Details |
| POST | `/input-batches` | any | Register new operational images `{name, path, metadata_path?}` |
| GET | `/input-batches/{id}` | any | Details |

**Assessments**

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/assessments` | any | Create `{name, dataset_id?, model_id?, record_stream_id?, input_batch_id?, reference_id?, modules: [M1..M4], access_level_override?, config_overrides?, seed}`. Validates which modules can run with given inputs and returns warnings. Status DRAFT. |
| POST | `/assessments/{id}/start` | any | Queue → job |
| POST | `/assessments/{id}/cancel` | any | Cancel |
| GET | `/assessments` | any | List with status, overall verdict, created_by |
| GET | `/assessments/{id}` | any | Status, module runs, check runs, config snapshot |
| GET | `/assessments/{id}/events` | any | **SSE** stream: module/check progress, findings count, completion |
| GET | `/assessments/{id}/summary` | any | Overall verdict, asset verdicts (disposition, confidence, coverage gaps), finding counts by disposition/severity/module, unresolved review count |
| GET | `/assessments/{id}/findings` | any | Filter: `module, check_id, severity, disposition, effective_disposition, asset_type, asset_id, status, unresolved, q` |

**Module views**

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/assessments/{id}/data/source-risk` | any | Contributor/batch/source table with breakdown |
| GET | `/assessments/{id}/data/duplicate-clusters` | any | Clusters with members |
| GET | `/assessments/{id}/data/confusion` | any | `?contributor=` per-contributor confusion matrix |
| GET | `/assessments/{id}/model` | any | assessment_context (access, checks run/unavailable, confidence, limitations), digest/fingerprint results |
| GET | `/assessments/{id}/model/triggers` | any | Reconstructed triggers per class with anomaly index, artefact ids |
| GET | `/assessments/{id}/provenance` | any | Record status counts |
| GET | `/assessments/{id}/provenance/records` | any | Paginated records with status, filter by status |
| GET | `/assessments/{id}/provenance/records/{seq}` | any | Record fields + every verification step result |
| GET | `/assessments/{id}/shift` | any | Detected, verdict, calibrated risk, calibration quality, characterisation, descriptors, rules fired, embedding projection points for plotting |

**Findings and decisions**

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/findings/{id}` | any | Full finding with artefacts and decision history |
| POST | `/findings/{id}/decisions` | any | `{decision, justification}` (justification required, non-empty) |
| GET | `/findings/{id}/decisions` | any | History |
| GET | `/artefacts/{id}` | any | Serve artefact file after digest verification (reject if digest mismatch) |

**Provenance services**

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/inference/attest` | any | `{model_id, stream_id, config_id, image (multipart)}` → run model, return signed record, append to stream |
| POST | `/provenance/verify` | any | Verify an uploaded records file or a `record_stream_id`, with optional images folder → per-record results (ad-hoc, outside an assessment) |

**Reports**

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/assessments/{id}/reports` | any | Generate DRAFT report → report id |
| POST | `/reports/{id}/finalise` | any | Mark FINAL (409 if unresolved REVIEW/QUARANTINE findings; response lists them) |
| GET | `/reports/{id}` | any | Metadata |
| GET | `/reports/{id}/json` | any | Signed JSON |
| GET | `/reports/{id}/html` | any | Rendered HTML |
| GET | `/reports/{id}/pdf` | any | PDF, or 501 with reason if renderer unavailable |
| POST | `/reports/verify` | any | Upload a report JSON → schema valid?, signature valid?, key known?, audit head hash present in current log? |

**Audit**

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/audit` | any | Paginated entries, filter `event, actor, from, to, assessment_id` |
| GET | `/audit/head` | any | Current head hash and entry count |
| POST | `/audit/verify` | any | Full chain verification → `{valid, entries_checked, first_failure_index?, failure_reason?}` |
| GET | `/audit/export` | any | Download JSONL + head hash |
| POST | `/audit/verify-file` | any | Verify an uploaded exported log against a supplied head hash |

**Policy and configuration**

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/config/policy` | any | Disposition matrix, hard overrides |
| PUT | `/config/policy` | ADMIN | Update (audited, versioned) |
| GET | `/config/thresholds` | any | All check thresholds |
| PUT | `/config/thresholds` | ADMIN | Update (audited, versioned) |
| GET | `/coverage` | any | Coverage statement (A16) |

**Attack Lab and evaluation**

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/attack-lab/scenarios` | ADMIN | Catalogue with parameters and defaults |
| POST | `/attack-lab/runs` | ADMIN | `{scenario_id, seed, params?, base_asset_id?}` → job → generated asset ids |
| GET | `/attack-lab/runs` | ADMIN | List |
| GET | `/attack-lab/runs/{id}` | ADMIN | Details (never exposes ground truth to detectors; ground truth visible only in eval results) |
| POST | `/attack-lab/runs/{id}/assess` | ADMIN | Convenience: create a pre-filled assessment from the generated assets |
| POST | `/eval/runs` | ADMIN | `{attack_run_ids, assessment_ids}` → metrics |
| GET | `/eval/runs/{id}` | ADMIN | Metrics per module (precision, recall, F1, AUROC, FPR, detection rates, ECE) |

**Jobs**

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/jobs/{id}` | any | Status, progress, result ids, error |
| GET | `/jobs/{id}/events` | any | SSE |

### A11.3 CLI (mirrors the API for scripted, reproducible runs)

```
aura selfcheck --offline
aura users create-admin
aura keys init
aura reference register <path> [--metadata <file>] [--default]
aura battery build --reference <id> --seed 42
aura dataset register <path> [--format auto] [--metadata <file>]
aura model register <path> [--format auto] [--task classification] [--access BB-S]
aura assess --dataset <id> --model <id> --records <id> --input-batch <id> --seed 42
aura report generate <assessment_id> [--final]
aura audit verify [--file <jsonl> --head <hash>]
aura attack generate <scenario_id> --seed 1337
aura demo run --seed 1337          # full demo pipeline end to end
aura eval run --attack-runs ... --assessments ...
```

## A12. Frontend: Information Architecture, Screens and Flows

### A12.1 Design principles

- **Answer "what needs my attention?" first.** The main screen is a triage view, not a menu.
- **Evidence next to every score.** No number without a reason.
- **Dispositions are text labels plus colour**, never colour alone: `ACCEPT` (green), `REVIEW` (amber), `QUARANTINE` (red), `UNAVAILABLE` (grey, dashed border).
- **Gaps are visible.** Unavailable checks always appear, never hidden.
- **Dark, calm, professional theme** (slate background, emerald/amber/red accents). High contrast, keyboard accessible, readable at a distance for demo.
- **Fully local**: fonts in `assets/fonts` or system font stack, icons from the npm package, no remote images.
- Every page has clear **empty**, **loading**, and **error** states.

### A12.2 Global layout

- **Left sidebar navigation:** Dashboard · New Assessment · Assessments · Assets · Findings · Reports · Audit Log · Attack Lab (ADMIN) · Settings (ADMIN) · Coverage.
- **Top status strip (always visible):** `OFFLINE ✓` indicator from selfcheck · keys status · default reference name · audit chain status (last verified time, valid/invalid) · current user and role · logout.
- **Global job tray:** running jobs with progress, click to open.

### A12.3 Screens

**S0. Login**
Username, password, role shown after login. No "forgot password" (air-gapped); admin resets passwords.

**S1. First-Run Setup Wizard (ADMIN, shown until setup-status is complete)**
Step 1 Selfcheck (show each item pass/fail; block if network access is possible or bundled weights missing) → Step 2 Generate keys (inference, audit, report) → Step 3 Register reference distribution → Step 4 Build reference battery → Step 5 Review default policy and thresholds → Done → Dashboard.
Analysts who log in before setup is complete see a message "Setup pending, contact admin".

**S2. Dashboard (MAIN SCREEN)**
Top to bottom:

1. **Status strip** (global, above).
2. **Latest assessment verdict card**: assessment name, time, run by; big **overall disposition** label; five **asset verdict tiles**: Dataset · Contributors (worst contributor named) · Model · Inference Records · Input Batch. Each tile shows disposition, confidence, and a "coverage gap" badge if any check was UNAVAILABLE. Click a tile → corresponding module tab.
3. **Needs Attention queue**: unresolved findings with recommended REVIEW or QUARANTINE, sorted by severity then confidence. Each row: severity, disposition, one-line reason, affected asset, module, "Open" button. Shows "N unresolved; report cannot be finalised until resolved".
4. **Module health row**: four compact cards:
   - Data: worst contributor and risk score, counts by attack type.
   - Model: access level used, digest/fingerprint result, backdoor result, number of unavailable checks.
   - Provenance: records verified vs failed, top failure type.
   - Shift: verdict, calibrated risk, one-line characterisation.
5. **Recent assessments table**: name, date, overall verdict, unresolved count, report status (none/draft/final).
6. **Quick actions**: New Assessment · Verify Audit Chain · Verify a Report · (ADMIN) Attack Lab.
7. **Empty state (no assessments yet):** checklist with links: register a dataset, register a model, import records, register an input batch, run your first assessment; plus (ADMIN) "Run demo scenario".

**S3. New Assessment Wizard**
- Step 1 **Select inputs**: pick or register dataset (with contributor metadata), model, record stream, input batch, reference. Registering inline shows validation summary (format detected, counts, sanity issues) before continuing.
- Step 2 **Scope and access**: modules to run (auto-disabled with reason if inputs missing, e.g. "M4 needs an input batch and a reference"), detected model access level with option to **declare a lower level** (for black-box simulation), seed, optional threshold overrides (ADMIN only).
- Step 3 **Review**: summary of inputs with digests, which checks will run, which will be UNAVAILABLE and why (preview from scheduler). "Start assessment".
→ goes to S4.

**S4. Assessment Run (live)**
Per-module progress bars and per-check list (queued, running, completed, unavailable, error) via SSE; running count of findings by severity; cancel button; on completion auto-navigate to S5.

**S5. Assessment Overview** (tabs across the top: Overview · Data · Model · Provenance · Shift · Findings · Report)
- **Overview tab:** same verdict card and needs-attention queue as the dashboard but scoped to this assessment; config snapshot (seed, thresholds version, tool version); inputs with digests.

**S6. Data tab (Module 1)**
- **Contributor risk table** (sortable): contributor, samples, flagged, risk score (0–100 with bar), breakdown chips (trigger, flip, systematic, duplicate, OOD), disposition. Click a row → contributor drill-down drawer: breakdown chart, confusion matrix heatmap (systematic mislabelling), gallery of that contributor's flagged samples.
- **Attack-type sections**: triggers (patch overlay gallery, residual heatmaps), label issues (given vs consensus with neighbours), duplicate clusters (grouped thumbnails), OOD (sample next to nearest in-distribution examples).
- **Sample detail drawer**: full image with canvas overlay (boxes, trigger location), labels, all findings for this sample.
- If metadata missing: banner "Source-level risk unavailable: no contributor metadata supplied".

**S7. Model tab (Module 2)**
- **Access assumption banner** at top (for example "Assessed with BLACK-BOX (scores) access").
- Identity card: weight digest, registered digest, match/mismatch; structure match (WB); fingerprint agreement.
- Backdoor section: reconstructed trigger images per class with anomaly index chart (WB), or STRIP entropy histogram and patch-probe flip-rate table (BB).
- **Unavailable checks** as grey cards with reason and fallback used.
- Confidence and **limitations list** (always shown).

**S8. Provenance tab (Module 3)**
- Status count chips (VERIFIED, ALTERED, REPLAYED, …).
- Records table: sequence, timestamp, status, model id, input hash (short), click to open.
- **Record detail**: all bound fields in a readable layout; a **verification checklist** of the ten steps with pass/fail and detail; for failures, a plain explanation (for example "Signature does not match the record contents: the record was modified after signing").
- **Tamper demo panel** (only for records generated in this session or by the Attack Lab, clearly labelled DEMO): edit a box or label in a local copy and re-verify to show the signature flip from VERIFIED to ALTERED. Never modifies stored records.

**S9. Shift tab (Module 4)**
- Verdict badge (Drift / Suspicious / Inconclusive / No material shift) and calibrated risk with ECE and "extrapolated" warning if applicable.
- Plain-language characterisation.
- Descriptor effect-size bar chart grouped by factor (terrain, season, sensor, illumination, acquisition).
- Radial FFT spectrum chart: reference vs input batch.
- 2D embedding projection scatter (reference vs new).
- Evidence rules fired (for and against each verdict).
- Most novel samples gallery.

**S10. Findings tab / global Findings page**
- Filterable table: severity, disposition (recommended and effective), module, check, asset, status (FLAGGED/UNAVAILABLE), unresolved only.
- **Finding detail drawer** (the core analyst interaction): the five mandatory fields displayed prominently (Reason, Evidence, Confidence and Severity, Affected Asset, Recommended Disposition), artefacts (images, charts), limitations, decision history, and a **decision form**: Accept / Review / Quarantine + required justification → submit (writes audit entry). Keyboard shortcuts for fast triage (next/previous, A/R/Q).

**S11. Report tab / Reports page**
- Generate DRAFT → preview HTML inline.
- **Finalise** button, disabled with the list of unresolved findings until all REVIEW/QUARANTINE findings have decisions.
- Downloads: signed JSON, HTML, PDF (or a clear message if PDF unavailable).
- Shows report digest, signature key id, embedded audit head hash, schema validation result.
- **Verify a report** tool: upload a JSON report → schema, signature and head-hash checks.

**S12. Audit Log**
- Paginated, filterable entries (time, actor, event, short payload, entry hash).
- **Verify chain** button → result banner (valid, entries checked, or first failing index with reason, and the entry highlighted).
- Export JSONL with head hash. Verify an exported file against a head hash.

**S13. Assets**
Tabs: Datasets · Models · Record Streams · Input Batches · References. Register new, view details (digests, validation summaries, detected access level, registered fingerprint).

**S14. Attack Lab (ADMIN)**
- Scenario catalogue grouped by D / M / I / S / L with parameter forms and defaults, seed field.
- Generate → job progress → generated assets listed → **"Assess these assets"** button (pre-fills S3) → after assessment, **"Evaluate against ground truth"** → metrics view (per-module precision/recall/F1/AUROC/FPR/detection rate/ECE).
- **One-click "Full Demo"**: runs the demo pipeline (clean baseline, poisoned contributor, backdoored model, substituted model, tampered/replayed records, natural vs adversarial shift) and links each resulting assessment.

**S15. Settings (ADMIN)**
Users · Keys (create, rotate) · References (default) · Battery (build, version) · Policy matrix editor · Thresholds editor. Every save shows "This change is recorded in the audit log".

**S16. Coverage & Limitations**
Supported · Partial · Not supported · Assumptions · Known limitations (from `/coverage`). Linked from every report and from each module tab footer.

### A12.4 User flows

**Admin first-run flow**
Login → Setup Wizard (selfcheck → keys → reference → battery → policy) → Dashboard (empty state) → Attack Lab → Full Demo or individual scenarios → review results → Settings as needed.

**Analyst assessment flow (primary flow)**
Login → Dashboard → New Assessment (select/register inputs → scope/access → review) → Run (live progress) → Assessment Overview → work through **Needs Attention** queue: open finding → inspect evidence in module tab if needed → decide with justification → next → when queue is empty → Report tab → Generate draft → preview → Finalise → download JSON/HTML/PDF → Audit Log → Verify chain.

**Provenance check flow**
Assets → Record Streams → import records → New Assessment with only M3 (or `/provenance/verify` ad-hoc) → Provenance tab → open failed record → verification checklist explains which step failed → decision → report.

**Black-box vs white-box flow (demonstrates R-CON-5)**
New Assessment with a TorchScript model at WB → Model tab shows trigger reconstruction → New Assessment with the same model declared BB-S → Model tab shows reconstruction UNAVAILABLE with reason and fallback results.

**Evaluation flow (ADMIN)**
Attack Lab → generate scenario → assess → evaluate → metrics → export metrics JSON for the submission.

### A12.5 Frontend implementation notes

- Routes: `/login`, `/setup`, `/`, `/assessments/new`, `/assessments/:id/run`, `/assessments/:id/:tab`, `/findings`, `/reports`, `/audit`, `/assets/:type`, `/attack-lab`, `/settings/:section`, `/coverage`.
- Typed API client generated from the FastAPI OpenAPI schema (or hand-written types kept in sync).
- SSE hook for job and assessment progress with reconnect.
- Reusable components: `DispositionBadge`, `SeverityBadge`, `ConfidenceMeter`, `AssetChip`, `DigestText` (shortened with copy), `EvidenceGallery`, `CanvasOverlay`, `FindingDrawer`, `DecisionForm`, `UnavailableCard`, `VerificationChecklist`, `EmptyState`, `ErrorState`.
- Build output served by FastAPI from `ui/dist` at `/`.

## A13. Data Formats (schemas are deliverables, R-DEL-3)

Create these JSON Schemas (draft 2020-12) in `schemas/`, and validate against them in code and tests. Full field lists are in `docs/design.md` §13 and §14; the essentials:

- **`finding.schema.json`**: A7.3. Required: `id, module, check_id, created_at, status, reason (minLength 1), evidence, confidence (0..1), severity, affected_asset {type, id}, recommended_disposition`.
- **`assurance_report.schema.json`**: top-level required keys `report_id, schema_version, generated_at, status (DRAFT|FINAL), tool {name, version, code_digest}, inputs [assets with digests], assessment_context {offline: true, model_access_level, reference/battery/calibration digests, checks_run, checks_unavailable}, summary {overall_disposition, asset_verdicts[], finding_counts}, modules {data_integrity {status, findings, source_risk}, model_integrity {status, access_level, confidence, limitations, findings}, inference_provenance {status, records_total, status_counts, findings}, distribution_shift {status, shift_detected, verdict, calibrated_risk, calibration_quality, characterisation, rules_fired, findings}, governance {analyst_decisions}}, coverage_statement {supported, partial, unsupported, assumptions, known_limitations}, audit {log_head_hash, entry_count, chain_verified}, signature {algorithm: Ed25519, key_id, value}`.
- **`inference_record.schema.json`**: A8.3 fields.
- **`audit_entry.schema.json`**: `index, timestamp, actor {type, id}, event, payload, payload_sha256, prev_entry_hash, entry_hash, key_id, signature`.

Report signing: canonical JSON of the report without `signature` → Ed25519 with the report key.

## A14. Testing and Acceptance

### A14.1 Test layers

- **Unit:** hashing, canonical JSON (including RFC 8785 test vectors), Ed25519 sign/verify, audit chain (append, verify, edit, delete, truncate), record verifier (each RecordStatus), dataset adapters (COCO, YOLO, imagefolder, malformed inputs), model adapters (tiny ONNX and TorchScript models created in the test), disposition policy, Beta-Binomial risk, schema validation.
- **Detector tests on synthetic data:** each M1 check detects its matching seeded attack on a synthetic dataset and stays quiet on the clean control within a stated tolerance; M2 digest/fingerprint detect substitution; M2 fallback emits UNAVAILABLE under BB access; M3 detects I1–I6; M4 separates S1 vs S5 and reports INCONCLUSIVE when rules conflict; M5 detects L1–L3.
- **API tests:** every endpoint happy path + auth/role checks + error format; mutating endpoints produce audit entries.
- **Offline test:** the full test suite runs with sockets blocked except localhost.
- **Determinism test:** same config + seed twice → identical artefact digests and identical finding sets.
- **E2E (optional):** Playwright flow: login → new assessment → run → decide → finalise report → verify audit.

### A14.2 Acceptance criteria (system level)

1. `aura selfcheck --offline` passes on a machine with networking disabled.
2. `aura demo run --seed 1337` completes end to end offline and produces assessments, a FINAL report after scripted decisions, and a valid audit log.
3. Every finding in every report validates against the schema; every report validates and its signature verifies.
4. Seeded attacks are detected: the malicious contributor ranks first in source risk; backdoored classifier flagged under WB; substituted model flagged; every tampered record type detected; audit edit/delete/truncate detected. (Report measured metrics; do not assert numbers you have not measured.)
5. Under declared black-box access, every white-box check appears as UNAVAILABLE with a reason, and fallbacks run.
6. The UI main screen shows the latest verdict, asset tiles, and needs-attention queue; the analyst flow in A12.4 works without errors.
7. `docs/` contains architecture, setup (offline), coverage statement, threat model, decisions, demo script; `schemas/` contains all four schemas.

## A15. Offline Packaging (R-CON-1)

- `scripts/prepare_offline_bundle.sh` (run on a **connected** build machine): download pinned wheels into `wheelhouse/`, download and digest-pin feature extractor weights into `assets/weights/`, run `npm ci && npm run build` for `ui/dist`, bundle fonts, optionally fetch small public datasets for evaluation, and write `BUNDLE_MANIFEST.json` with digests of everything.
- `scripts/install_offline.sh` (run on the **air-gapped** machine): verify `BUNDLE_MANIFEST.json` digests, create venv, `pip install --no-index --find-links wheelhouse -r requirements.txt`, run `aura selfcheck --offline`.
- The runtime must never attempt downloads (for example, disable any library auto-download of pretrained weights; load from `assets/weights/` by path only).

## A16. Coverage Statement Content (R-GOV-3, R-DEL-5)

**Supported:** visible patch and blended triggers in a subset of samples; random label flipping; systematic class-to-class mislabelling by a contributor; near-duplicate flooding via common augmentations; OOD insertion; annotation errors; contributor/batch/source risk when metadata supplied; weight-file substitution vs registered digest; behavioural change vs registered fingerprint; patch-like backdoors in classification models (WB reconstruction, BB probing); record alteration, forgery, substitution, replay, deletion, reordering, model/config substitution, input mismatch; global illumination, contrast, colour, sharpness, noise, resolution and compression shifts and domain change; audit log edit, deletion, and truncation (relative to an exported head hash).

**Partial:** backdoors in detection models (digest, fingerprint and probing only); trigger detection without the contributed model's activations; drift vs manipulation (decisive only when evidence rules agree); gradient-based checks on ONNX; terrain/season characterisation without metadata.

**Not supported:** clean-label poisoning; sample-specific/input-aware/invisible dynamic triggers; physical-world triggers and adversarial patches on real objects; adaptive attackers targeting AURA-CV; poisoning spread evenly across all contributors; compromised signing keys or signing host; input forgery before signing; privacy attacks and model extraction; non-RGB modalities (SAR, thermal, multispectral) and video temporal attacks.

**Assumptions:** AURA-CV code, bundled weights and battery are trusted; declared reference and trusted reference set are clean and representative; keys are generated and held in the trusted environment; at least some contributors are honest for source comparison; the model's declared interface is correct.

**Known limitations:** thresholds tuned on generated scenarios may need recalibration for new domains; FFT evidence can confuse low-light noise with manipulation and low-frequency adversarial perturbations with drift; weight statistics are weak signals; small contributors get wide uncertainty; performance measured only on stated hardware.

## A17. Definition of Done

- All requirement IDs in A2 map to implemented code, tests, and a section in `docs/architecture.md` (include a traceability table).
- Acceptance criteria A14.2 pass, with test output saved to `docs/test_results.md`.
- Demo script in `docs/demo_script.md` rehearsed end to end offline.
- Deliverables present: source code, architecture and setup notes, schemas, a reproducible audit log from `aura demo run --seed 1337` with regenerate and verify commands, coverage statement.
- No hard-coded results, no network calls, no "tamper-proof" wording, no unpickling of untrusted files.

## A18. Out of Scope for the Hackathon Build

Trigger reconstruction for detection models, clean-label and dynamic-trigger defences, video/RTSP streaming ingestion, SAR/thermal plugins, TPM/HSM key storage, CI/CD integration, and automated remediation. Record any of these as future work in `docs/future.md`; do not implement unless asked.

---
---

# PART B: KICKOFF PROMPT (paste this first)

```
Read CLAUDE.md completely, then read docs/design.md. CLAUDE.md is the binding spec.

Before writing any code:
1. Restate, in a table, every requirement ID from CLAUDE.md §A2 and the milestone (from the list below) in which you will implement it.
2. List any contradictions, ambiguities or risks you see in the spec, and the decision you propose for each. Write them to docs/decisions.md.
3. Check the environment: Python version, whether PyTorch, onnxruntime, Node/npm are available, OS. Report what is missing.
4. Propose the exact directory skeleton you will create.

Milestones:
M0 Foundations · M1 Provenance core · M2 Storage, jobs, adapters, features, synthetic data · M3 Attack Lab (data, records, logs, image shifts) · M4 Module 1 · M5 Module 2 + battery + model scenarios · M6 Module 4 + calibration · M7 Governance, orchestration, reports · M8 Full API + auth + SSE · M9 Frontend · M10 Evaluation, demo, packaging, docs

Then implement ONLY Milestone M0 (details below). Do not start M1.

M0 Foundations:
- Repository skeleton per §A6, pyproject/requirements with pinned versions, README stub.
- aura/core/types.py with all enums and domain models from §A7 (Pydantic v2).
- aura/core/hashing.py (sha256 helpers, "sha256:<hex>" format) and aura/core/canonical.py (RFC 8785) with tests including RFC test vectors.
- aura/m3_provenance/keys.py: Ed25519 key generation, storage in keys/ with restricted permissions, load, public key export, rotation.
- aura/m5_governance/audit_log.py: append-only JSONL + verify (edit, delete, truncate-vs-head detection), signed entries.
- schemas/finding.schema.json and a validator; aura/core/policy.py disposition policy with hard overrides.
- aura/core/checks.py: Check protocol, registry, scheduler skeleton that emits UNAVAILABLE findings when access is insufficient (test with dummy checks).
- aura/cli.py with `aura selfcheck --offline` (initial items: python version, keys dir, audit log verify, no-network test) and `aura keys init`.
- tests/ with a socket-blocking fixture applied to the whole suite.

When done: run the full test suite, paste the summary, list what was built, what is incomplete, and any decisions made. Then stop and wait.
```

---

# PART C: MILESTONE PROMPTS (paste one at a time after the previous passes)

### M1: Provenance core

```
Implement Milestone M1 per CLAUDE.md §A8.3.
- aura/m3_provenance/signer.py: build canonical record (RFC 8785), rounding of outputs per declared precision, record_hash, Ed25519 signature, per-stream sequence and prev_record_hash, 128-bit nonce, UTC timestamp.
- aura/m3_provenance/verifier.py: all ten verification steps reported individually; map to RecordStatus; unknown key_id → UNVERIFIABLE.
- schemas/inference_record.schema.json.
- Record tampering generators I1–I6 in aura/attack_lab/generators/records.py (operate on copies).
- Tests: a genuine stream of synthetic records verifies; each of I1–I6 is detected with the correct status; deterministic with seed.
Do not implement attested inference yet (needs model adapters, done in M2). Run tests, report, stop.
```

### M2: Storage, jobs, adapters, features, synthetic data

```
Implement Milestone M2 per CLAUDE.md §A8.0 and §A10.
- aura/storage: SQLite models for all entities in §A7.2, repositories, artefact store with digest verification on read, allowed data roots.
- aura/jobs: background runner with progress events, cancellation, failure handling, audit entries.
- Dataset adapters: coco, yolo, imagefolder, auto-detect, contributor metadata loader, object-level crop view, annotation sanity check (M1.annot.sanity).
- Model adapters: onnx, torchscript, state_dict (weights_only=True + small built-in architecture zoo), access level detection, declared lower access level, weight_digest and structure_digest.
- aura/features: frozen backbone loaded ONLY from assets/weights by path, embeddings cache keyed by image digest. Add a scripts/fetch_weights.py for the connected build machine only.
- aura/attack_lab/synthetic.py: seeded synthetic multi-class dataset generator (shapes on textures), exportable as imagefolder, COCO and YOLO.
- Attested inference service in aura/m3_provenance/attested_inference.py using model adapters.
- Tests: adapters parse synthetic COCO/YOLO/imagefolder identically; malformed inputs produce sanity findings, not crashes; tiny ONNX and TorchScript models load and report correct access levels; no unpickling path exists.
Run tests, report, stop.
```

### M3: Attack Lab generators

```
Implement Milestone M3 per CLAUDE.md §A9 (data, records, audit log and image-shift scenarios; model scenarios come in M5).
- Scenario registry reading attack_lab_configs/*.yaml; D1–D7, L1–L3, S1, S4, S5 generators (S2 and S3 in M6).
- Each run registers output assets and writes a manifest (digests, config, seed, tool version, ground truth) in a restricted path readable only by aura/eval.
- Provide example YAML configs for every scenario with default parameters and seeds.
- Tests: byte-identical outputs for the same config and seed; manifests list correct ground truth; detectors cannot import the manifest path (enforce with a test that greps imports).
Run tests, report, stop.
```

### M4: Module 1 (Training-Data Integrity)

```
Implement Milestone M4: every check in CLAUDE.md §A8.1 as Check plugins, plus source-level risk.
- Each check emits schema-valid findings with a plain-language reason, evidence (metrics, thresholds, sample ids, artefacts such as overlays and thumbnails), confidence, severity, affected asset, recommended disposition (via policy), limitations.
- Source risk: Beta-Binomial with configurable prior and p0, per-type breakdown; UNAVAILABLE finding when metadata is absent.
- Aggregated outputs: source_risk table, duplicate clusters, per-contributor confusion matrices.
- All thresholds configurable in aura/config.py with documented defaults.
- Tests on synthetic data from M3: each of D1–D7 is detected by the intended check; the malicious contributor ranks first; clean control produces few/no high-severity findings (report the measured counts, do not hard-code expectations beyond a tolerance you justify).
Run tests, report measured detection numbers, stop.
```

### M5: Module 2 (Model Integrity) and reference battery

```
Implement Milestone M5 per CLAUDE.md §A8.2.
- Reference battery builder (clean per class, controlled variants, probe patches), versioned and digested.
- Model scenarios M1–M4 in the Attack Lab (M1 fine-tunes a clean model on D1/D2 data purely to create a test model; label this clearly as test-model creation).
- Checks: M2.digest (register on first sight), M2.structure, M2.fingerprint, M2.reference_accuracy, M2.trigger_reconstruction (TorchScript classification, bounded time, MAD anomaly index, trigger image artefact), M2.activation_stats, M2.param_stats (max severity MEDIUM), M2.strip, M2.patch_probe (classification and detection).
- Scheduler fallbacks: under BB access, WB checks emit UNAVAILABLE with reasons and fallbacks run. Detection models: reconstruction UNAVAILABLE with reason.
- Module output includes the assessment_context block (access, checks run/unavailable, battery digest, confidence, limitations).
- Confirm no check retrains or modifies the supplied model (add a test that the model digest is unchanged after assessment).
- Tests: backdoored vs clean classifier under WB; same models declared BB-S; substituted and modified models detected.
Run tests, report measured results, stop.
```

### M6: Module 4 (Distribution Shift) and calibration

```
Implement Milestone M6 per CLAUDE.md §A8.4.
- Reference registration (embeddings, descriptors, output stats, metadata summary, digests).
- Detection: seeded MMD permutation test, per-sample novelty, per-descriptor KS tests, model output shift, materiality rule.
- Descriptors mapped to factors, standardised effect sizes, template-based plain-language characterisation.
- Attack Lab S2 (different source) and S3 (FGSM/PGD offline) generators.
- Calibration: build calibration set from S-scenarios, harm labels from model impact, isotonic (fallback Platt), ECE and reliability diagram artefact, extrapolation flag.
- Verdict rules engine producing DRIFT / SUSPICIOUS / INCONCLUSIVE / NO_MATERIAL_SHIFT with rules_fired in evidence; ambiguous cases → INCONCLUSIVE.
- Tests: S5 → no material shift; S1 → drift; S3/S4 → suspicious or inconclusive (never drift with high confidence); ECE reported.
Run tests, report measured results, stop.
```

### M7: Governance, orchestration and reports

```
Implement Milestone M7 per CLAUDE.md §A8.5 and §A13.
- Assessment orchestration: create (with input validation and module/check preview), start, run modules via scheduler as a job, config snapshot, cancel, failure handling, audit events.
- Findings service with schema validation; decisions (append-only, justification required); effective disposition; asset and overall verdicts.
- Report builder: JSON per assurance_report.schema.json, sign with report key, HTML via Jinja2 (clear, printable, includes coverage statement and audit head hash), PDF if renderer available else explicit message; DRAFT vs FINAL rule.
- Coverage statement single source in aura/m5_governance/coverage.py, exported to docs/coverage_statement.md.
- Report verifier (schema, signature, known key, head hash present in log).
- CLI: aura assess, aura report generate, aura audit verify, aura demo run (scripted end-to-end with fixed seed and scripted analyst decisions).
- Tests: finalise blocked while unresolved findings exist; report signature verifies; tampered report fails; demo run completes offline.
Run tests, report, stop.
```

### M8: Full API

```
Implement Milestone M8: every endpoint in CLAUDE.md §A11 with the stated roles, error format, pagination, SSE progress, and audit entries for every mutating call. Local session auth with argon2/bcrypt password hashes; first admin via CLI only. Bind to 127.0.0.1; CORS limited to the local UI origin. Serve ui/dist at "/" when present.
Tests: happy path and role checks for every endpoint, error format, audit entry per mutation, SSE emits progress for a synthetic assessment.
Export the OpenAPI schema to docs/openapi.json. Run tests, report, stop.
```

### M9: Frontend

```
Implement Milestone M9: the React + TypeScript + Vite + Tailwind UI per CLAUDE.md §A12, exactly the screens S0–S16, the global layout, and the flows in §A12.4.
Priorities, in order: (1) Dashboard main screen, (2) New Assessment wizard and live run page, (3) Findings drawer with decision form, (4) Module tabs Data, Model, Provenance, Shift, (5) Reports and Audit Log, (6) Setup wizard, Assets, Attack Lab, Settings, Coverage.
Rules: no CDN or remote assets; typed API client; SSE hook; empty/loading/error states on every page; dispositions as text + colour; unavailable checks always visible; canvas overlays for boxes and trigger locations; keyboard triage shortcuts in the findings drawer.
Do not show any number that is not returned by the API.
After building: run the UI against the backend with the demo data and walk through the analyst flow in §A12.4, listing any broken step. Report, stop.
```

### M10: Evaluation, demo, packaging and docs

```
Implement Milestone M10.
- aura/eval: harness reading manifests, metrics per CLAUDE.md §A14 and docs/design.md §15 (precision, recall, F1, AUROC, FPR, detection rates, ECE), multi-seed runs with mean and spread, metrics JSON and markdown export.
- Attack Lab "Full Demo" in API/UI and `aura demo run`.
- scripts/prepare_offline_bundle.sh and scripts/install_offline.sh with BUNDLE_MANIFEST.json digest verification.
- Docs: architecture.md with requirement traceability table (every A2 ID → code → tests), setup.md (offline install), threat_model.md, coverage_statement.md, demo_script.md, test_results.md with real measured outputs.
- Generate the reproducible audit log deliverable from `aura demo run --seed 1337`, with regenerate and verify commands documented. Explain that timestamps differ between runs, so reproducibility means same events, same order, same payload digests.
Run everything offline, report final metrics honestly (including weaknesses), stop.
```

---

# PART D: REVIEW PROMPTS (use at the end or whenever needed)

### D1: Requirement traceability audit

```
Audit the codebase against every requirement ID in CLAUDE.md §A2. For each ID give: implemented (yes/partial/no), file paths, test names, and any gap. Be strict: "partial" if any sub-clause is missing (for example R-GOV-1 needs all five fields on every finding, including UNAVAILABLE findings). Fix gaps that are small; list larger ones.
```

### D2: Offline and security audit

```
Search the entire repo (Python and UI) for any possible network access: http/https URLs, CDN links, library auto-downloads of weights, telemetry, DNS lookups, remote fonts. Also check: untrusted unpickling, path traversal in path registration, upload size limits, server bound to 127.0.0.1, key file permissions, secrets committed to git, SQL injection, XSS in rendered reasons/labels in HTML reports and UI. Report each issue with file and line, fix them, and rerun the socket-blocked test suite.
```

### D3: Honesty audit

```
Search for any hard-coded detection results, metrics, sample numbers, or demo values presented as real in code, UI, reports or docs. Search for the words "tamper-proof", "impossible", "guarantee", "100%" and check each use is accurate (cryptographic detection of tampering may be stated as detectable; nothing is tamper-proof). Confirm every UI number comes from the API. Confirm the coverage statement is embedded in every report and shown in the UI. Fix and report.
```

### D4: UX walkthrough

```
Act as a non-ML analyst. Walk through the flows in CLAUDE.md §A12.4 on the running app with the demo data. For each screen, note: is it clear what needs attention, is every score next to a reason, are unavailable checks visible, can the analyst decide and justify quickly, are empty/error states helpful. Propose and implement the top ten improvements that do not change the spec.
```

### D5: Demo rehearsal

```
Run docs/demo_script.md end to end with networking disabled. Time each step. Identify any step that is slow, fragile or confusing for judges and fix it. Make sure the whole demo runs within 7 minutes and that every step shows a requirement from the problem statement (name the requirement ID on screen or in the narration notes).
```