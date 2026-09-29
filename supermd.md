# AURA-CV: Air-Gapped Unified Risk & Assurance for Computer Vision

**Solution Design Document for Smart India Hackathon (SIH)**
**Organisation:** Ministry of Defence (MoD)
**Problem Statement Title:** Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines

---

## Table of Contents

1. [Purpose of this Document](#1-purpose-of-this-document)
2. [Problem Statement (Faithful Restatement)](#2-problem-statement-faithful-restatement)
3. [Requirements Traceability Matrix](#3-requirements-traceability-matrix)
4. [Threat Model and Trust Assumptions](#4-threat-model-and-trust-assumptions)
5. [Solution Overview and Architecture](#5-solution-overview-and-architecture)
6. [Module 1: Training-Data Integrity](#6-module-1-training-data-integrity)
7. [Module 2: Model Integrity](#7-module-2-model-integrity)
8. [Module 3: Inference Provenance and Output Integrity](#8-module-3-inference-provenance-and-output-integrity)
9. [Module 4: Distribution-Shift and Anomaly Assessment](#9-module-4-distribution-shift-and-anomaly-assessment)
10. [Module 5: Analyst-Facing Assurance and Governance](#10-module-5-analyst-facing-assurance-and-governance)
11. [Reproducible Attack Generation (Attack Lab)](#11-reproducible-attack-generation-attack-lab)
12. [Constraints Compliance](#12-constraints-compliance)
13. [Assurance Report Schema](#13-assurance-report-schema)
14. [Inference Record and Audit Log Formats](#14-inference-record-and-audit-log-formats)
15. [Evaluation Plan and Metrics](#15-evaluation-plan-and-metrics)
16. [Coverage Statement](#16-coverage-statement)
17. [Analyst User Interface](#17-analyst-user-interface)
18. [Technology Stack](#18-technology-stack)
19. [Repository Structure and Setup Notes](#19-repository-structure-and-setup-notes)
20. [MVP Scope versus Phase 2](#20-mvp-scope-versus-phase-2)
21. [Demonstration Script](#21-demonstration-script)
22. [Deliverables Checklist](#22-deliverables-checklist)
23. [Suggested Team Work Split](#23-suggested-team-work-split)
24. [References](#24-references)

---

## 1. Purpose of this Document

This document describes the design of **AURA-CV**, a proposed solution to the SIH problem statement above. It is written so that every design decision can be traced back to a specific clause of the problem statement.

Three conventions are used throughout:

- **"Required"** marks something the problem statement explicitly asks for. The exact clause is referenced by section number (for example, *PS 2.2.3*).
- **"Design choice"** marks a technique or decision made by the team. The problem statement specifies *what* must be achieved, not *how*, so these choices are ours and can be changed.
- **"Target"** marks a goal that has not yet been measured. No performance figure in this document should be read as a measured result until the evaluation in Section 15 has been run.

---

## 2. Problem Statement (Faithful Restatement)

### 2.1 Background (PS 2.1)

Operational computer vision pipelines may combine:

1. training data from multiple contributors,
2. pretrained or vendor-supplied models, and
3. inference outputs consumed by downstream systems.

This creates distinct integrity and assurance risks across the **data, model and inference lifecycle**:

| Lifecycle stage | Risks named in the problem statement |
|---|---|
| **Data** | Deliberately or inadvertently mislabelled samples, duplicated content, out-of-distribution material, trigger-based backdoors |
| **Model** | Substitution, modification, or hidden behaviour that is not apparent during routine validation |
| **Inference records** | Replay, replacement or alteration after generation, unless cryptographically linked to the exact input, model and processing chain that produced them |

Existing controls often address only individual parts of this lifecycle. The challenge is to create a **unified, evidence-based assurance layer** that can assess these risks **without assuming that every contributing source is trusted**.

### 2.2 What must be built (PS 2.2)

An **extensible computer-vision assurance framework** that evaluates:

- a contributed **dataset**,
- a trained **model**, and
- associated **inference records**,

and produces an **evidence-based assessment of integrity and risk**. The solution **should not be hard-coded to a single model architecture or dataset**.

Five core capabilities are required:

| # | Capability | PS clause |
|---|---|---|
| 1 | Training-Data Integrity | 2.2.1 |
| 2 | Model Integrity | 2.2.2 |
| 3 | Inference Provenance and Output Integrity | 2.2.3 |
| 4 | Distribution-Shift and Anomaly Assessment | 2.2.4 |
| 5 | Analyst-Facing Assurance and Governance | 2.2.5 |

Plus mandatory constraints (PS 2.2.6) and an expected solution with deliverables (PS 2.3).

### 2.3 Expected solution (PS 2.3)

- A **model-agnostic** assurance system for training data, trained CV models and inference outputs.
- Uses **publicly available or team-generated** datasets and models.
- Teams develop **reproducible methods** to introduce representative **poisoning, backdoor, substitution and tampering** scenarios for testing.
- The system identifies suspicious data or contributor behaviour, assesses model integrity, detects tampering of inference records, provides supporting evidence for each finding, and generates a clear **assurance report** stating **confidence, limitations and recommended action**.

**Deliverables (PS 2.3):** source code; architecture and setup notes; the assurance-report schema; a reproducible audit log; a coverage statement identifying supported attack classes, assumptions and known limitations.

---

## 3. Requirements Traceability Matrix

Every requirement is given an ID. Later sections refer to these IDs.

| ID | Requirement (from problem statement) | PS clause | Where addressed |
|---|---|---|---|
| **R-GEN-1** | Extensible framework, not hard-coded to a single architecture or dataset; model-agnostic | 2.2, 2.3 | §5.3, §7.2, §19 |
| **R-GEN-2** | Assess risks without assuming every contributing source is trusted | 2.1 | §4 |
| **R-GEN-3** | Evidence-based assessment of integrity and risk | 2.2 | §10, §13 |
| **R-DATA-1** | Identify samples associated with **trigger injection** | 2.2.1 | §6.4.1 |
| **R-DATA-2** | Identify samples associated with **label flipping** | 2.2.1 | §6.4.2 |
| **R-DATA-3** | Identify **systematic mislabelling** | 2.2.1 | §6.4.3 |
| **R-DATA-4** | Identify **near-duplicate flooding** | 2.2.1 | §6.4.4 |
| **R-DATA-5** | Identify **out-of-distribution insertion** | 2.2.1 | §6.4.5 |
| **R-DATA-6** | Aggregate sample-level evidence into **source-level risk** when contributor/batch/source metadata is available | 2.2.1 | §6.5 |
| **R-MOD-1** | Assess whether a model shows **anomalous, substituted or backdoor-like** behaviour | 2.2.2 | §7.4 |
| **R-MOD-2** | Use methods **appropriate to the level of access** (fingerprinting, trigger search/reconstruction, parameter/activation statistics, reference battery comparison) | 2.2.2 | §7.3, §7.4 |
| **R-MOD-3** | State **access assumptions, confidence and limitations** of the assessment | 2.2.2 | §7.6 |
| **R-INF-1** | Verifiable cryptographic binding among **input image, model identifier or weight digest, preprocessing and inference configuration, and output** | 2.2.3 | §8.3 |
| **R-INF-2** | Make **post-hoc alteration, substitution or replay** detectable via **hashes, signatures, and sequence, timestamp or nonce** controls | 2.2.3 | §8.4, §8.5 |
| **R-SHIFT-1** | Detect material deviation from a **declared reference distribution** (terrain, season, sensor, illumination, acquisition conditions) | 2.2.4 | §9.3 |
| **R-SHIFT-2** | **Characterise** the observed shift | 2.2.4 | §9.4 |
| **R-SHIFT-3** | Provide a **calibrated** risk or confidence score | 2.2.4 | §9.5 |
| **R-SHIFT-4** | Distinguish **probable operational drift** from **suspicious manipulation** where the evidence supports it | 2.2.4 | §9.6 |
| **R-GOV-1** | Every flag includes: **human-readable reason, supporting evidence, confidence or severity, affected asset, recommended disposition (accept / review / quarantine)** | 2.2.5 | §10.2 |
| **R-GOV-2** | Maintain a **tamper-evident audit trail** | 2.2.5 | §10.5, §14.3 |
| **R-GOV-3** | **Explicitly declare** attack classes or conditions not supported | 2.2.5 | §16 |
| **R-CON-1** | Complete evaluation workflow operates **offline, air-gapped**, no cloud services or external APIs | 2.2.6 | §12 |
| **R-CON-2** | Ingest common dataset formats including **COCO and YOLO** | 2.2.6 | §6.2 |
| **R-CON-3** | Support organiser-defined model formats including **ONNX and PyTorch/TorchScript** | 2.2.6 | §7.2 |
| **R-CON-4** | Baseline integrity assessment **must not require retraining** the contributed model (optional remediation may retrain) | 2.2.6 | §7.7, §12 |
| **R-CON-5** | White-box methods **fall back gracefully** or **clearly report unavailability** under black-box access | 2.2.6 | §7.3 |
| **R-EXP-1** | Use publicly available or team-generated datasets and models | 2.3 | §11.2 |
| **R-EXP-2** | **Reproducible** methods to introduce poisoning, backdoor, substitution and tampering scenarios | 2.3 | §11 |
| **R-EXP-3** | Generate a clear assurance report stating **confidence, limitations and recommended action** | 2.3 | §13 |
| **R-DEL-1** | Submit source code | 2.3 | §22 |
| **R-DEL-2** | Submit architecture and setup notes | 2.3 | §5, §19 |
| **R-DEL-3** | Submit the assurance-report schema | 2.3 | §13 |
| **R-DEL-4** | Submit a reproducible audit log | 2.3 | §14.3, §22 |
| **R-DEL-5** | Submit a coverage statement (supported attack classes, assumptions, known limitations) | 2.3 | §16 |

---

## 4. Threat Model and Trust Assumptions

The problem statement requires that the system does **not assume every contributing source is trusted** (R-GEN-2). This section makes explicit who is and is not trusted.

### 4.1 Untrusted parties

| Party | What they may do |
|---|---|
| **Data contributors** (vendors, units, allied sources) | Submit mislabelled, duplicated, out-of-distribution or trigger-poisoned samples, deliberately or by accident. A single contributor may be malicious while others are honest. |
| **Model suppliers** | Supply a model that is substituted, modified, or contains a hidden backdoor that passes routine validation. |
| **Anyone handling inference records after generation** | Alter, replace, delete, reorder or replay records. |
| **Operating environment** | Produce inputs that drift from the reference distribution (terrain, season, sensor, illumination, acquisition), or be used to inject manipulated inputs. |

### 4.2 Trusted computing base (assumptions)

These are **assumptions**, and they are repeated in the coverage statement (§16):

1. **The AURA-CV tool itself** (code, bundled feature extractor weights, reference battery) is obtained through a trusted channel and has not been modified.
2. **The declared reference distribution** supplied to Module 4 is representative of intended operating conditions and is not itself poisoned.
3. **The signing private keys** used by Module 3 and the audit log are generated and stored in the trusted environment and have not been compromised.
4. **The inference host** that runs the model and signs records is trusted *at the moment of signing*. Integrity is guaranteed **from the point of signing onward**; a record cannot prove that the input image was genuine before it reached the signer.
5. **A small trusted reference set** (clean, correctly labelled samples) is available for calibration and for the reference battery.

### 4.3 Attacker capability assumed for evaluation

- The attacker can control **one or more contributors** but not all of them.
- The attacker may control the **model supplier**.
- The attacker **does not know** the internal thresholds of AURA-CV. Adaptive attackers who optimise specifically against our detectors are **out of scope** for the baseline (see §16).

---

## 5. Solution Overview and Architecture

### 5.1 One-line summary

AURA-CV is an offline, model-agnostic assurance layer that checks **data**, **models**, **inference records** and **incoming distribution** without trusting any contributing source, and turns every finding into an evidence-backed, analyst-readable decision recorded in a tamper-evident audit trail.

### 5.2 High-level architecture

```
                 ┌──────────────────────────────────────────────┐
                 │               INPUTS (untrusted)             │
                 │  Dataset (COCO / YOLO) + contributor metadata│
                 │  Model (ONNX / TorchScript / PyTorch)        │
                 │  Inference records                           │
                 │  New operational images                      │
                 └──────────────────────┬───────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                     AURA-CV  (fully offline, air-gapped)                │
 │                                                                         │
 │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
 │  │ M1 DATA GUARD    │  │ M2 MODEL TRUST   │  │ M3 INFERENCE ATTESTOR│   │
 │  │ trigger, flip,   │  │ digest, finger-  │  │ SHA-256 binding,     │   │
 │  │ systematic,      │  │ print, trigger   │  │ Ed25519 signature,   │   │
 │  │ duplicates, OOD, │  │ search, act/param│  │ sequence, timestamp, │   │
 │  │ contributor risk │  │ stats, fallback  │  │ nonce, hash chain    │   │
 │  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘   │
 │           │                     │                       │               │
 │  ┌────────┴─────────────────────┴───────────────────────┴───────────┐   │
 │  │ M4 SHIFT PROFILER: detect, characterise, calibrated score,       │   │
 │  │    drift vs suspicious vs inconclusive                           │   │
 │  └────────────────────────────────┬─────────────────────────────────┘   │
 │                                   ▼                                     │
 │  ┌──────────────────────────────────────────────────────────────────┐   │
 │  │ M5 GOVERNANCE: findings (reason, evidence, confidence/severity,  │   │
 │  │    asset, disposition), analyst review, hash-chained audit log,  │   │
 │  │    signed assurance report, coverage statement                   │   │
 │  └──────────────────────────────────────────────────────────────────┘   │
 │                                                                         │
 │  Shared services: format adapters · frozen feature extractor ·          │
 │  key store · reference battery · Attack Lab (test scenarios)            │
 └─────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
              Signed assurance report (JSON + HTML/PDF) + audit log
```

### 5.3 Extensibility (R-GEN-1)

**Design choice:** every check is a plugin implementing a common interface, so new detectors, formats and model types can be added without changing the core.

```python
class Check(Protocol):
    id: str                       # e.g. "M1.duplicates.phash"
    module: str                   # "M1" .. "M5"
    requires_access: AccessLevel  # NONE, BLACK_BOX_LABELS, BLACK_BOX_SCORES, WHITE_BOX
    def is_applicable(self, ctx: AssessmentContext) -> Applicability: ...
    def run(self, ctx: AssessmentContext) -> list[Finding]: ...
```

- **Format adapters** convert COCO, YOLO and plain image folders into one internal representation, so detectors never depend on a particular dataset format.
- **Model adapters** wrap ONNX Runtime and TorchScript behind one `predict()` / `features()` / `gradients()` interface. A check that needs gradients simply declares `WHITE_BOX`, and the scheduler decides whether it can run (see §7.3).
- **Task adapters** support image classification and object detection; detection datasets can additionally be assessed at object level via cropped annotations.

### 5.4 End-to-end workflow

1. **Ingest:** load dataset, metadata, model, inference records and reference distribution through adapters. Hash every input and write an `INGEST` entry to the audit log.
2. **Determine access level** for the model (§7.3) and record it.
3. **Run M1** on the dataset, then aggregate to contributor risk.
4. **Run M2** on the model with every check that the access level permits; mark the rest `UNAVAILABLE`.
5. **Run M3** verification over the supplied inference records.
6. **Run M4** comparing new operational images to the declared reference distribution.
7. **M5** collects all findings, applies the disposition policy, presents them for analyst review, logs every analyst action, and exports the signed report.

---
## 6. Module 1: Training-Data Integrity

### 6.1 What the problem statement requires (PS 2.2.1)

> Identify suspicious or anomalous samples associated with trigger injection, label flipping, systematic mislabelling, near-duplicate flooding and out-of-distribution insertion. Where contributor, batch or source metadata is available, the system should aggregate sample-level evidence into a source-level risk assessment rather than flagging samples in isolation.

Requirements covered: **R-DATA-1 to R-DATA-6**, **R-CON-2**.

### 6.2 Inputs and format adapters (R-CON-2)

| Input | Supported forms |
|---|---|
| **Images** | Folder of PNG / JPEG / TIFF |
| **COCO annotations** | `instances_*.json` with `images`, `annotations`, `categories` |
| **YOLO annotations** | One `.txt` per image, lines of `class_id cx cy w h` (normalised), plus class-name list (`data.yaml` or `classes.txt`) |
| **Classification layout** | `root/<class_name>/<image>` |
| **Contributor metadata (optional)** | CSV or JSON mapping `image_id → contributor_id, batch_id, source_id` |

**Annotation sanity checks** (design choice, cheap and always-on): boxes outside image bounds, zero or negative area boxes, invalid class IDs, missing images for annotations, images without annotations, and malformed files. These produce findings of their own and also protect later checks from crashing on bad input.

**Object-level view for detection datasets:** each annotated box can be cropped and treated as a labelled sample, so label-consistency checks (§6.4.2, §6.4.3) work for detection as well as classification.

### 6.3 Shared representation

**Design choice:** most checks operate on **embeddings**, numeric feature vectors that summarise image content.

- A **frozen, bundled feature extractor** (for example a ResNet-18 or MobileNetV3 with ImageNet weights, shipped locally with the tool) produces an embedding for every image or object crop. No internet access and no training are required.
- If the **contributed model is available with white-box access**, its own penultimate-layer activations are also extracted. This matters for trigger detection (§6.4.1), because a model trained on poisoned data separates poisoned samples in its own representation much more clearly than a generic backbone does.
- Embeddings are L2-normalised and indexed for nearest-neighbour search.

### 6.4 Detection of the five named data risks

#### 6.4.1 Trigger injection (R-DATA-1)

**What it is:** a small pattern (patch, sticker, watermark or blended signal) is added to a subset of samples, usually relabelled to an attacker-chosen target class, so that a model trained on the data learns "pattern → target class".

**What it looks like in data:** many samples sharing a small, consistent visual element, concentrated in one label, often from one contributor.

**Methods (design choice):**

| Method | Access needed | Idea |
|---|---|---|
| **Activation clustering** | Contributed model activations (best) or frozen backbone | Within each class, cluster embeddings into two groups; a small, well-separated cluster is suspicious. |
| **Spectral signature** | Same as above | Within each class, compute the top singular vector of centred representations; samples with large projections are outliers. |
| **Repeated local-patch search** | None (pixels only) | Hash small image regions (for example corners and a grid of tiles) and look for identical or near-identical patches recurring across many images of the same label. |
| **High-frequency residual analysis** | None | Subtract a smoothed copy of the image and look for localised, structured high-frequency residue that is consistent across samples. |

**Evidence produced:** the cluster or patch statistics, example thumbnails, the location of a recurring patch (drawn as an overlay), the class concentration, and the contributors involved.

**Honest limitation:** without the contributed model's own activations, generic-backbone clustering is weaker for subtle triggers. This is reported in the finding's `limitations` field.

#### 6.4.2 Label flipping (R-DATA-2)

**What it is:** a correctly depicted sample carries a deliberately or accidentally wrong label.

**Methods (design choice):**

- **k-NN label consensus:** for each sample, look at its *k* nearest neighbours in embedding space. If most neighbours carry a different label, the sample's label is suspicious.
- **Confident-learning style check:** fit a lightweight linear classifier on the embeddings with cross-validation (seconds on CPU, no deep training), estimate out-of-sample predicted probabilities, and flag samples where the classifier is confident that the given label is wrong.

**Evidence produced:** given label, consensus label, neighbour agreement ratio, predicted probability of the given label, and the nearest neighbours as thumbnails.

#### 6.4.3 Systematic mislabelling (R-DATA-3)

**What it is:** a **consistent pattern** of wrong labels, for example one contributor labelling every "bus" as "truck". Label flipping concerns individual samples; systematic mislabelling concerns **which class maps to which, and who does it**.

**Method (design choice):**

- For each contributor, build a **confusion matrix** of *consensus label* (from §6.4.2) against *given label*.
- Compare each contributor's matrix against the pooled matrix of all other contributors, using a per-cell test (for example a chi-square or Fisher's exact test with multiple-comparison correction).
- Flag cells where one contributor has a significantly higher rate of a specific class-to-class substitution.

**Evidence produced:** the contributor, the source class and target class, counts, rate versus other contributors, and example samples.

#### 6.4.4 Near-duplicate flooding (R-DATA-4)

**What it is:** many slightly altered copies of the same content (crops, brightness changes, flips, recompression) inserted to over-weight a pattern.

**Methods (design choice):**

- **Perceptual hash (pHash):** a hash that stays similar when images look similar. Pairs with Hamming distance at or below a **configurable threshold** are candidate duplicates.
- **Embedding cosine similarity** above a configurable threshold, to catch duplicates that pHash misses (for example larger crops).
- Candidates are merged into **duplicate clusters**. A cluster is flagged when its size is unusually large relative to the dataset, or when it is dominated by one contributor or one label.

**Evidence produced:** cluster size, members as thumbnails, contributors and labels in the cluster, and similarity values.

#### 6.4.5 Out-of-distribution insertion (R-DATA-5)

**What it is:** samples that do not belong to the task domain, for example indoor photographs in an aerial dataset.

**Methods (design choice):**

- **k-NN distance** of each sample to the trusted reference set (or to the bulk of the dataset) in embedding space.
- **Mahalanobis distance** to per-class Gaussian models of the embeddings.
- Thresholds are set from the distribution of scores on the trusted reference set (for example a high percentile), and are configurable.

**Evidence produced:** OOD score, the threshold used, the percentile, nearest in-distribution examples for contrast.

### 6.5 Source-level risk aggregation (R-DATA-6)

The problem statement explicitly asks that sample-level evidence be aggregated into **source-level risk** rather than flagging samples in isolation.

**Design choice: Beta-Binomial contributor risk.**

For contributor *c* with *n* samples, of which *k* are flagged by any M1 check (weighted by finding confidence):

1. Choose a prior **Beta(α, β)** reflecting the expected base rate of anomalies in honest data, estimated from the trusted reference set or set conservatively.
2. The posterior anomaly rate is **Beta(α + k, β + n − k)**.
3. **Contributor risk** = posterior probability that the contributor's anomaly rate exceeds an acceptable rate *p₀*: `risk = P(θ > p₀ | data)`, reported on a 0 to 100 scale.

Why this choice:

- A contributor with 2 flags out of 3 samples is **not** automatically judged worse than one with 200 flags out of 1,000; the posterior accounts for sample size, so small contributors are not over-penalised on thin evidence.
- The score is interpretable: "there is a 97% probability that this contributor's anomaly rate is above 5%."

Each contributor also receives a **breakdown by risk type** (trigger, flip, systematic, duplicate, OOD), so the analyst sees *why* the contributor is risky. Batch and source IDs are aggregated the same way when present.

**If no metadata is available**, source-level aggregation is reported as `UNAVAILABLE: no contributor/batch/source metadata supplied`, and findings remain sample-level.

### 6.6 Module 1 outputs

- Sample-level findings for each of the five risk types.
- Contributor, batch and source risk table with per-type breakdown.
- Duplicate clusters and trigger candidates as visual evidence.
- All findings in the common format of §10.2.

---

## 7. Module 2: Model Integrity

### 7.1 What the problem statement requires (PS 2.2.2)

> Assess whether a supplied model exhibits anomalous, substituted or backdoor-like behaviour using methods appropriate to the level of access available. Approaches may include behavioural fingerprinting, trigger search or reconstruction, parameter or activation statistics, and comparison against a defined reference battery. The system must state the access assumptions, confidence and limitations of its assessment.

Requirements covered: **R-MOD-1, R-MOD-2, R-MOD-3, R-CON-3, R-CON-4, R-CON-5**.

### 7.2 Model loading (R-CON-3)

| Format | How it is loaded | Notes |
|---|---|---|
| **ONNX** | ONNX Runtime (CPU) | Graph structure and initialiser tensors are readable, so white-box statistics are possible; gradients are available only if the graph is exported to a framework, so gradient-based checks treat ONNX as partially white-box. |
| **TorchScript** | `torch.jit.load` | Full forward pass, parameters and gradients available. |
| **PyTorch weights (`state_dict`)** | `torch.load(..., weights_only=True)` plus a registered architecture definition | **Security note:** full pickled PyTorch models can execute arbitrary code when loaded. Because the model is untrusted (§4.1), AURA-CV never unpickles arbitrary objects; it accepts TorchScript, ONNX, or weights-only state dictionaries. |

**Model identity:** on ingestion the tool computes a **SHA-256 digest of the weight file** and, for ONNX, a canonical description of the graph (operator types, tensor shapes, input/output signature). This digest is the **model identifier** that Module 3 binds into every inference record.

### 7.3 Access levels and graceful fallback (R-MOD-2, R-CON-5)

AURA-CV determines the access level at ingestion and records it in the report.

| Level | What is available | Example |
|---|---|---|
| **BB-L** (black-box, labels) | Only predicted labels / boxes | A sealed inference service |
| **BB-S** (black-box, scores) | Predicted labels plus confidence scores or logits | Most exported inference APIs |
| **WB** (white-box) | Weights, intermediate activations, and (for TorchScript) gradients | TorchScript or ONNX file |

Every check declares the minimum level it needs. The scheduler:

- **runs** checks the access level permits,
- **substitutes a weaker fallback** where one exists (for example, trigger reconstruction falls back to black-box patch probing), and
- otherwise emits an explicit finding: `status: UNAVAILABLE`, with the reason, for example *"Neural-Cleanse-style trigger reconstruction requires gradient (white-box) access; only black-box scores were provided."*

It never silently skips a check.

### 7.4 Checks

#### 7.4.1 Substitution and modification checks

| Check | Access | Method (design choice) |
|---|---|---|
| **Digest verification** | Any file | Compare the supplied weight digest with the digest registered at intake or declared by the supplier. A mismatch means the file is not the registered model. |
| **Structure verification** | WB | Compare graph/layer structure with the registered description. |
| **Behavioural fingerprinting** | BB-L / BB-S | Run the **reference battery** (§7.5) and record outputs. Compare against the registered fingerprint using top-1 agreement rate and, if scores are available, a divergence measure between output distributions. Substitution or modification changes the fingerprint even when the file name and interface are unchanged. |

**Important nuance:** if a model is seen for the first time, there is no registered digest or fingerprint to compare against. In that case AURA-CV **registers** the digest and fingerprint at intake, and substitution is detectable from that point onward, both here and in every inference record bound by Module 3. The report states which case applies.

#### 7.4.2 Backdoor checks

| Check | Access | Method (design choice) |
|---|---|---|
| **Trigger reconstruction** | WB (gradients) | Neural-Cleanse-style optimisation: for each candidate target class, find the smallest mask and pattern that sends clean inputs to that class. A class whose required trigger is abnormally small compared with the others (measured with a median-absolute-deviation anomaly index) indicates a likely backdoor. The reconstructed trigger is shown as an image. |
| **Activation statistics** | WB | On the reference battery, look for neurons that are nearly dormant on clean data but strongly activated by candidate triggers, and for abnormal activation distributions. |
| **Parameter statistics** | WB | Weight distribution statistics (for example kurtosis and skew per layer) compared with reference models. **Supporting heuristic only**, never a sole basis for quarantine. |
| **Perturbation-entropy test** | BB-S | STRIP-style test: superimpose clean images on the input and measure prediction entropy. Inputs carrying a backdoor trigger tend to keep a low-entropy, fixed prediction. |
| **Black-box patch probing** | BB-L / BB-S | Paste a library of candidate patches (and any trigger candidates found by Module 1) onto reference images and measure the **flip rate** towards a single class. |

**Detection models:** trigger reconstruction was designed for classifiers and is considerably harder for object detectors. In the MVP, detection models are assessed with **digest, fingerprint and black-box patch probing** (measuring whether objects disappear or change class when patches are applied). Full trigger reconstruction for detectors is **Phase 2** and is listed as *partial* in the coverage statement.

#### 7.4.3 Anomalous behaviour checks

- **Reference-battery accuracy** on the trusted reference set compared with the supplier's claimed performance.
- **Calibration and confidence profile** on the reference battery (a model that is unusually over-confident on specific classes is flagged for review).
- **Per-class disparity** between the reference battery and the registered fingerprint.

### 7.5 Reference battery (R-MOD-2)

The problem statement mentions "comparison against a defined reference battery". **Design choice:** the reference battery is a versioned, hashed bundle shipped with the tool containing:

1. **Clean reference samples** per class from the trusted reference set.
2. **Controlled variants** of those samples (brightness, blur, noise, JPEG compression) to profile robustness.
3. **Probe patches** used for black-box trigger probing.

The battery's own digest is recorded in every report, so assessments are reproducible and comparable.

### 7.6 Stating access assumptions, confidence and limitations (R-MOD-3)

Every Module 2 result carries a mandatory block:

```json
"assessment_context": {
  "access_level": "BB-S",
  "checks_run": ["M2.digest", "M2.fingerprint", "M2.strip", "M2.patch_probe"],
  "checks_unavailable": [
    {"check": "M2.trigger_reconstruction", "reason": "requires white-box gradients"}
  ],
  "reference_battery_digest": "sha256:…",
  "confidence": 0.72,
  "limitations": [
    "Black-box tests cannot rule out backdoors with triggers absent from the probe library.",
    "No registered fingerprint existed before intake; substitution is detectable only from intake onward."
  ]
}
```

### 7.7 No retraining (R-CON-4)

All baseline checks above run on the model **as supplied**. None retrains or fine-tunes it. **Optional remediation** (for example, fine-tuning on data that Module 1 has cleaned, or pruning neurons implicated by activation statistics) is a separate, clearly labelled action that produces a *new* model with a *new* digest, which is then re-assessed.

---
## 8. Module 3: Inference Provenance and Output Integrity

### 8.1 What the problem statement requires (PS 2.2.3)

> Create a verifiable cryptographic binding among the input image, model identifier or weight digest, preprocessing and inference configuration, and resulting output. The design should make post-hoc alteration, substitution or replay of protected inference records detectable through hashes, signatures and appropriate sequence, timestamp or nonce controls.

Requirements covered: **R-INF-1, R-INF-2**.

### 8.2 Basic concepts

| Term | Meaning |
|---|---|
| **Hash (SHA-256)** | A fixed-length fingerprint of data. Changing a single byte of the input produces a completely different hash. |
| **Digital signature (Ed25519)** | A value computed with a private key over some data. Anyone holding the matching public key can verify that the data was signed by that key and has not changed since. |
| **Canonical serialisation** | A single, deterministic way to turn a record into bytes (fixed key order, number formatting, encoding), so the same record always hashes to the same value. **Design choice:** JSON Canonicalization Scheme (RFC 8785). |
| **Sequence number** | A counter that increases by exactly one for each record in a stream. |
| **Timestamp** | When the inference was performed, according to the signer's clock. |
| **Nonce** | A random, single-use value included in each record so that no two records are ever identical. |
| **Hash chain** | Each record contains the hash of the previous record, so removing, inserting or reordering records breaks the chain. |

### 8.3 What is bound into every record (R-INF-1)

| Field | Content | Why |
|---|---|---|
| `input.sha256` | Hash of the **exact input image bytes** as received | Binds the output to one specific image |
| `model.weight_digest` | SHA-256 of the model weight file (from §7.2) | Binds the output to one exact model; detects model substitution |
| `model.id`, `model.format` | Registered identifier and format | Human-readable identity |
| `config.preprocessing` | Resize, crop, normalisation mean/std, colour order, letterboxing | The same image can give different outputs under different preprocessing |
| `config.inference` | Confidence threshold, NMS IoU threshold, batch settings, runtime and version | Same reason as above |
| `config.sha256` | Hash of the canonical config block | Compact binding of the full configuration |
| `output` | Labels, scores, bounding boxes (canonical form) | The result being protected |
| `stream_id`, `sequence` | Stream identifier and monotonic counter | Replay, deletion and reordering detection |
| `timestamp` | UTC time of inference | Freshness checks |
| `nonce` | 128-bit random value | Uniqueness of every record |
| `prev_record_hash` | Hash of the previous record in the stream | Hash chain |
| `signer.key_id` | Identifier of the signing key | Key selection during verification |
| `signature` | Ed25519 signature over the canonical bytes of all fields above | Authenticity and integrity |

The **record hash** is SHA-256 of the canonical bytes of all fields except `signature`. The signature is computed over those same bytes.

### 8.4 Attacks and how each is detected (R-INF-2)

| Attack | What the attacker does | How it is detected |
|---|---|---|
| **Alteration** | Edits a field, for example changes a box, label or score | Recomputed record hash no longer matches the signed bytes, so **signature verification fails**. |
| **Forgery** | Creates a new record without the private key | **Signature verification fails** under the pinned public key. |
| **Substitution (record swap)** | Replaces a record with another *validly signed* record (for example from a different image or time) | A valid signature alone does **not** catch this. It is caught by: `sequence` and `prev_record_hash` not matching the chain position; and, when the verifier has the original image, `input.sha256` not matching that image. |
| **Model substitution at inference** | Runs a different model but claims the original | `model.weight_digest` does not match the registered digest from Module 2. |
| **Configuration substitution** | Runs with a different threshold or preprocessing | `config.sha256` does not match the declared, registered configuration. |
| **Replay** | Resubmits an old valid record as if new | **Duplicate nonce** already seen; **sequence** not greater than the last accepted value; **timestamp** outside the accepted freshness window. |
| **Deletion or reordering** | Removes or reorders records in a stored log | **Sequence gaps** and **broken hash chain**. |

### 8.5 Verification procedure

For each record, the verifier performs these checks in order and reports each result individually, so the analyst sees exactly which check failed:

1. **Schema check:** all required fields present and well-formed.
2. **Signature check:** Ed25519 verification with the public key identified by `signer.key_id`.
3. **Chain check:** `prev_record_hash` equals the hash of the preceding record in the same stream.
4. **Sequence check:** `sequence` equals previous sequence + 1 (gaps and repeats are reported).
5. **Nonce check:** nonce not previously seen for this stream.
6. **Freshness check:** timestamp within the configured window and not earlier than the previous record.
7. **Model binding check:** `model.weight_digest` matches the registered model.
8. **Config binding check:** `config.sha256` matches the registered configuration.
9. **Input binding check (if image available):** `input.sha256` matches the SHA-256 of the provided image.
10. **Optional re-execution check (if image and model available):** rerun inference with the bound configuration and compare outputs within a stated numerical tolerance.

**Record status values:** `VERIFIED`, `ALTERED`, `FORGED`, `SUBSTITUTED`, `REPLAYED`, `CHAIN_BROKEN`, `MODEL_MISMATCH`, `CONFIG_MISMATCH`, `INPUT_MISMATCH`, `UNVERIFIABLE` (for example, unknown key).

### 8.6 Key management

- Ed25519 key pairs are generated **offline** inside the trusted environment during setup.
- The private key is stored in a file readable only by the signing service (MVP). **Phase 2:** hardware-backed storage such as a TPM 2.0 or HSM.
- Public keys are **pinned** in the verifier configuration by `key_id`. Records signed by an unknown key are reported as `UNVERIFIABLE`, never silently accepted.
- Key rotation is supported by adding a new `key_id`; old records remain verifiable with retired public keys.

### 8.7 What this module guarantees and what it does not

- **Guarantees:** any change to a signed record after signing is **detectable**, and removal, reordering and replay within a stream are **detectable**.
- **Does not guarantee:** that the image was genuine before it reached the signer, or integrity if the private signing key is compromised. Both are stated in the coverage statement (§16). The system is **tamper-evident**, not tamper-proof.

---

## 9. Module 4: Distribution-Shift and Anomaly Assessment

### 9.1 What the problem statement requires (PS 2.2.4)

> Detect material deviation from a declared reference distribution, including changes caused by terrain, season, sensor, illumination or acquisition conditions. The system should characterise the observed shift, provide a calibrated risk or confidence score, and distinguish probable operational drift from suspicious manipulation where the available evidence supports such a distinction.

Requirements covered: **R-SHIFT-1 to R-SHIFT-4**.

### 9.2 The declared reference distribution

The **reference distribution** is a set of images, supplied and declared by the operator, that represents the conditions the model is intended for. At setup AURA-CV computes and stores, with a digest:

- embeddings from the frozen feature extractor,
- per-image descriptors (listed in §9.4),
- optionally, the model's own output statistics on the reference set (class frequencies, confidence distribution),
- available acquisition metadata (for example sensor ID, resolution, capture time) when present.

### 9.3 Detecting material deviation (R-SHIFT-1)

**Design choice:** a combination of distribution-level and sample-level tests.

| Test | Level | Idea |
|---|---|---|
| **Maximum Mean Discrepancy (MMD)** with a permutation test | Batch | Measures how different the new batch's embedding distribution is from the reference; the permutation test gives a p-value. |
| **Per-sample novelty score** | Sample | k-NN distance of each new image to the reference embeddings. |
| **Per-descriptor two-sample tests** | Batch | For example Kolmogorov-Smirnov on each descriptor in §9.4. |
| **Model output shift** | Batch | Change in predicted class frequencies and confidence distribution relative to the reference. |

A shift is **material** when the batch-level test is significant *and* the effect size exceeds a configurable threshold, so that tiny, operationally irrelevant differences in large batches are not flagged.

### 9.4 Characterising the shift (R-SHIFT-2)

The problem statement asks the system to **characterise** the shift, not just detect it. **Design choice:** interpretable descriptors, each mapped to the factors named in the problem statement.

| Descriptor | Computed as | Most related factor |
|---|---|---|
| Mean luminance, dynamic range | Pixel intensity statistics | Illumination |
| Contrast | Standard deviation of luminance | Illumination, weather |
| Colour distribution | Per-channel histograms, colour temperature estimate | Season, terrain, sensor |
| Sharpness | Variance of the Laplacian | Acquisition (focus, motion), weather (haze, dust) |
| Noise level | Robust noise estimate from high-frequency residuals | Sensor, low light |
| Radial frequency spectrum | 2D FFT, energy per radial frequency band | Blur and haze (loss of high frequency) versus added high-frequency structure |
| Texture statistics | Local binary pattern or edge-density histograms | Terrain |
| Resolution, aspect ratio, compression | Image metadata and JPEG quantisation tables where available | Sensor, acquisition pipeline |
| Metadata | Sensor ID, capture time, altitude or other fields if supplied | Sensor, season, acquisition |

For each descriptor, the report gives a **standardised effect size** against the reference, and the finding summarises the largest ones in plain language, for example:

> *"Mean luminance is 3.1 standard deviations below reference and sharpness is reduced; the pattern is consistent with low-light or haze conditions."*

(The numbers in this example are illustrative, not results.)

### 9.5 Calibrated risk and confidence score (R-SHIFT-3)

A raw distance or test statistic is not a calibrated probability. **Design choice:**

1. **Build a calibration set** from the trusted reference data with controlled, labelled transformations produced by the Attack Lab (§11): no shift, natural-style shifts of varying strength (brightness, blur, haze, noise, colour cast, JPEG), and manipulations (adversarial perturbations, localised patches).
2. **Measure the actual consequence** of each case on the model (for example accuracy drop or rate of changed predictions), so "risk" is tied to operational impact rather than to distance alone.
3. **Fit a calibration map** (isotonic regression or Platt scaling) from the raw shift features to the probability that the shift is operationally harmful.
4. **Report calibration quality** on a held-out split: Expected Calibration Error (ECE) and a reliability diagram. A score of 0.8 should correspond to harmful shifts in roughly 80% of such cases on held-out data.

The report states the calibration set's digest and the ECE achieved, so the analyst knows how far the score can be trusted. If the observed shift type lies outside anything seen during calibration, the score is marked **"extrapolated, low confidence"**.

### 9.6 Drift versus suspicious manipulation (R-SHIFT-4)

The problem statement requires this distinction only **"where the available evidence supports such a distinction"**. AURA-CV therefore produces **three** verdicts, not two:

| Verdict | Meaning |
|---|---|
| **PROBABLE_OPERATIONAL_DRIFT** | Evidence is consistent with natural change in terrain, season, sensor, illumination or acquisition. |
| **SUSPICIOUS_MANIPULATION** | Evidence is inconsistent with natural causes and consistent with deliberate interference. |
| **INCONCLUSIVE** | Evidence is insufficient or mixed. This is a valid, honest outcome. |

**Evidence rules (design choice):**

| Evidence pointing to natural drift | Evidence pointing to manipulation |
|---|---|
| Shift is **broad and coherent** across the batch | Shift is **concentrated** in a subset, a contributor, or specific classes |
| Descriptor changes match a **plausible physical cause** (for example global luminance drop, loss of high-frequency energy under haze or dust, colour cast by season) | **Structured high-frequency energy** that does not match the sensor's noise profile, or a **localised** anomaly (patch) |
| Consistent with **declared metadata** (for example a new sensor ID) | Contradicts metadata (for example same sensor ID but different noise signature) |
| Model degradation is **gradual** and spread across classes | Model predictions **flip sharply** for small input changes, or flip towards one class |
| Embedding shift is **smooth** | Perturbation is small in pixel space but causes a large embedding or output change |

**Known failure cases, stated in the coverage statement:**

- Low-light and high-ISO sensor noise also **increase high-frequency energy**, which can mimic manipulation.
- Some adversarial perturbations are deliberately **low-frequency** or semantically natural, which can mimic drift.

When these cases apply, the verdict defaults to **INCONCLUSIVE** rather than guessing.

### 9.7 Module 4 outputs

- Shift detected or not, with test statistics and effect sizes.
- Characterisation in plain language plus a descriptor table.
- Calibrated risk score with its calibration quality.
- Verdict (drift / suspicious / inconclusive) with the supporting evidence rules that fired.

---
## 10. Module 5: Analyst-Facing Assurance and Governance

### 10.1 What the problem statement requires (PS 2.2.5)

> Every flag must include a human-readable reason, supporting evidence, confidence or severity, the affected asset, and a recommended disposition such as accept, review or quarantine. The solution must maintain a tamper-evident audit trail and explicitly declare attack classes or conditions that it does not support.

Requirements covered: **R-GOV-1, R-GOV-2, R-GOV-3, R-GEN-3, R-EXP-3**.

### 10.2 The Finding object (R-GOV-1)

Every check in every module emits findings in one common structure. The five fields required by the problem statement are **mandatory**; a finding without them fails schema validation and cannot be exported.

| Field | Required by PS | Content |
|---|---|---|
| `reason` | Yes | One or two plain-language sentences, for example *"Contributor_C supplied 41 images sharing an identical 8×8 patch in the lower-right corner; 39 of them are labelled 'civilian_vehicle'."* |
| `evidence` | Yes | Structured evidence: metrics, thresholds, sample IDs, thumbnails, overlays, charts, verification step results |
| `confidence` | Yes (confidence **or** severity) | 0 to 1, how certain the system is that the finding is real |
| `severity` | Yes (confidence **or** severity) | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, how harmful it would be if real |
| `affected_asset` | Yes | Type (`sample`, `contributor`, `batch`, `source`, `dataset`, `model`, `inference_record`, `input_batch`) and identifier, plus its digest |
| `recommended_disposition` | Yes | `ACCEPT`, `REVIEW` or `QUARANTINE` |
| `id`, `module`, `check_id`, `created_at` | Design choice | Traceability |
| `limitations` | Design choice | Anything that weakens this particular finding |
| `analyst_decision` | Design choice | Filled when an analyst confirms or overrides |

AURA-CV reports **both** confidence and severity, since the problem statement accepts either and analysts need both to prioritise.

### 10.3 Disposition policy

**Design choice:** a default, configurable policy mapping severity and confidence to a recommended disposition.

| Severity \ Confidence | Low (< 0.4) | Medium (0.4 to 0.8) | High (> 0.8) |
|---|---|---|---|
| **LOW** | ACCEPT | ACCEPT | REVIEW |
| **MEDIUM** | ACCEPT | REVIEW | REVIEW |
| **HIGH** | REVIEW | REVIEW | QUARANTINE |
| **CRITICAL** | REVIEW | QUARANTINE | QUARANTINE |

Hard rules override the table: a **failed signature**, **model digest mismatch**, or **broken audit chain** is always `QUARANTINE`. A check that returned `UNAVAILABLE` never produces `ACCEPT` for the asset it would have covered; the asset-level summary shows the gap.

**Asset-level verdict:** each asset (dataset, contributor, model, record stream, input batch) receives the most severe disposition among its findings, with the counts shown.

### 10.4 Analyst review

- The analyst sees every finding with its evidence and can **confirm** or **override** the recommended disposition.
- An override requires a short written justification.
- Every view, confirmation, override and export is written to the audit log with the analyst identity.

### 10.5 Tamper-evident audit trail (R-GOV-2)

**Design choice:** an append-only, hash-chained, signed log (format in §14.3).

- Every event (ingestion with input digests, access-level decision, each check run with its version and parameters, each finding, each analyst action, each export) becomes one entry.
- Each entry contains the hash of the previous entry and is signed with the audit key.
- The **head hash** (hash of the latest entry) is printed in every exported report. Because a hash chain alone cannot detect removal of the most recent entries, comparing the log against a previously exported head hash reveals **truncation**.
- A **verify** command and a UI button recompute the whole chain and report the first entry at which verification fails.

The audit log is **tamper-evident**: changes are detectable, not impossible.

### 10.6 Declaring unsupported attack classes (R-GOV-3)

The coverage statement (§16) is embedded in every exported report and shown in the UI, so no report can be read without its limitations.

---

## 11. Reproducible Attack Generation (Attack Lab)

### 11.1 What the problem statement requires (PS 2.3)

> The solution shall use publicly available or team-generated datasets and models, with teams developing reproducible methods to introduce representative poisoning, backdoor, substitution and tampering scenarios for testing.

Requirements covered: **R-EXP-1, R-EXP-2**.

### 11.2 Datasets and models (R-EXP-1)

**Design choice:** use small, public datasets and models so every experiment runs on a CPU laptop.

- **Classification:** a small public image-classification dataset (for example CIFAR-10 or GTSRB) with a lightweight CNN (for example ResNet-18). This is the primary setting for backdoor experiments because the methods are most mature there.
- **Aerial object detection:** a public aerial or drone dataset (for example VisDrone or DOTA) with a small detector (for example the smallest YOLO variant), exported to ONNX.
- **Team-generated data:** synthetic variants produced by the Attack Lab.

The team must check and respect the **licence terms** of each dataset and model before use.

### 11.3 Reproducibility rules

- Every scenario is defined by a **YAML config** and a **random seed**.
- Every generated artefact is written with a **manifest** listing its SHA-256 digest, the config, the seed, the tool version, and the **ground truth** (which samples were poisoned, which records were tampered).
- Running the same config with the same seed produces **byte-identical** data artefacts. Model training is made as deterministic as the framework allows, and the manifest records the resulting model digest.
- Ground-truth manifests are used only by the evaluation harness (§15); they are **never** read by the detectors.

Example scenario config:

```yaml
scenario: A1_patch_trigger_contributor_C
seed: 1337
base_dataset: datasets/cifar10_train
contributors:
  - {id: contributor_A, share: 0.35, attacks: []}
  - {id: contributor_B, share: 0.35, attacks: []}
  - {id: contributor_C, share: 0.30, attacks:
      [{type: patch_trigger, patch: yellow_square_4x4, position: bottom_right,
        target_class: truck, poison_rate: 0.10}]}
outputs:
  dataset: out/A1/dataset
  manifest: out/A1/manifest.json
```

### 11.4 Scenario catalogue

**Data poisoning (Module 1)**

| ID | Scenario | Parameters |
|---|---|---|
| D1 | Patch trigger (BadNets-style) | patch size, colour, position, target class, poison rate, contributor |
| D2 | Blended trigger | blend pattern, opacity, target class, poison rate |
| D3 | Random label flipping | flip rate, classes affected, contributor |
| D4 | Systematic mislabelling | source class → target class, rate, contributor |
| D5 | Near-duplicate flooding | seed images, number of copies, augmentations (crop, brightness, flip, JPEG) |
| D6 | Out-of-distribution insertion | source of foreign images, count, labels assigned |
| D7 | Mixed contributor | several of the above within one contributor, at low rates |

**Model attacks (Module 2)**

| ID | Scenario | How produced |
|---|---|---|
| M1 | Backdoored model | Fine-tune a clean pretrained model on D1 or D2 data (fine-tuning is used only to *create* the test model, not to assess it) |
| M2 | Substituted model | Replace with a different checkpoint or architecture exposing the same interface |
| M3 | Modified model | Perturb a subset of weights, or prune/alter a layer |
| M4 | Clean control | Unmodified model, used to measure false positives |

**Inference record tampering (Module 3)**

| ID | Scenario |
|---|---|
| I1 | Alter a label, score or bounding box in a signed record |
| I2 | Swap a record with a validly signed record from another image |
| I3 | Replay an old record |
| I4 | Delete or reorder records |
| I5 | Forge a record with an unknown key |
| I6 | Produce records with a substituted model or altered config |

**Distribution shift and manipulation (Module 4)**

| ID | Scenario |
|---|---|
| S1 | Natural-style shifts: brightness and gamma, blur, synthetic haze or dust, sensor noise, colour cast, JPEG compression, resolution change |
| S2 | Different real acquisition source (a different dataset or sensor as "new domain") |
| S3 | Adversarial perturbation against the model (for example FGSM or PGD, generated offline) |
| S4 | Localised adversarial or trigger patch on a subset of inputs |
| S5 | Clean control (held-out reference images) |

**Audit log tampering (Module 5)**

| ID | Scenario |
|---|---|
| L1 | Edit an entry |
| L2 | Delete a middle entry |
| L3 | Truncate recent entries |

---

## 12. Constraints Compliance

| Constraint (PS 2.2.6) | How AURA-CV complies |
|---|---|
| **Offline and air-gapped; no cloud services or external APIs** (R-CON-1) | All dependencies are installed from a bundled local wheelhouse; feature-extractor weights, reference battery and UI assets (fonts, icons, scripts) are bundled locally; no code path performs network calls; the demo is run with networking disabled. A startup self-check reports any attempted outbound connection as an error. |
| **Ingest COCO and YOLO** (R-CON-2) | Format adapters in §6.2; image-folder layout also supported. |
| **Support ONNX and PyTorch/TorchScript** (R-CON-3) | Model adapters in §7.2; safe loading only (no arbitrary unpickling). |
| **Baseline assessment without retraining** (R-CON-4) | All Module 2 checks use the model as supplied (§7.7). Retraining exists only as optional remediation producing a new, re-assessed model. The only training in the project is used by the **Attack Lab to create test models**, not by the assessment. |
| **White-box methods fall back or report unavailability** (R-CON-5) | Access-level scheduler in §7.3; `UNAVAILABLE` findings with reasons. |
| **Not hard-coded to one architecture or dataset** (R-GEN-1) | Plugin checks, format adapters, model adapters (§5.3). |

---
## 13. Assurance Report Schema

The assurance-report schema is a required deliverable (R-DEL-3). The report is produced as **JSON** (machine-readable, validated against the schema below) and rendered to **HTML/PDF** for analysts. The HTML/PDF is a view of the JSON; the JSON is authoritative.

### 13.1 Report structure at a glance

```
AssuranceReport
├── report_id, schema_version, generated_at, tool
├── inputs            (every assessed asset with its SHA-256 digest)
├── assessment_context (access level, reference distribution, battery, calibration, offline flag)
├── summary           (overall and per-asset dispositions, counts)
├── modules
│   ├── data_integrity          (findings + contributor risk table)
│   ├── model_integrity         (findings + checks run/unavailable)
│   ├── inference_provenance    (findings + per-record status counts)
│   ├── distribution_shift      (findings + verdict + calibration)
│   └── governance              (analyst decisions)
├── coverage_statement (supported / partial / unsupported / assumptions / limitations)
├── audit              (audit log head hash, entry count, chain status)
└── signature          (Ed25519 over canonical report bytes)
```

### 13.2 JSON Schema (draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "aura-cv/assurance-report/1.0.0",
  "title": "AURA-CV Assurance Report",
  "type": "object",
  "required": [
    "report_id", "schema_version", "generated_at", "tool", "inputs",
    "assessment_context", "summary", "modules", "coverage_statement",
    "audit", "signature"
  ],
  "properties": {
    "report_id": { "type": "string" },
    "schema_version": { "const": "1.0.0" },
    "generated_at": { "type": "string", "format": "date-time" },
    "tool": {
      "type": "object",
      "required": ["name", "version", "code_digest"],
      "properties": {
        "name": { "const": "AURA-CV" },
        "version": { "type": "string" },
        "code_digest": { "$ref": "#/$defs/digest" }
      }
    },
    "inputs": {
      "type": "array",
      "items": { "$ref": "#/$defs/asset" }
    },
    "assessment_context": {
      "type": "object",
      "required": ["offline", "model_access_level", "checks_run", "checks_unavailable"],
      "properties": {
        "offline": { "const": true },
        "model_access_level": { "enum": ["NONE", "BB-L", "BB-S", "WB"] },
        "reference_distribution_digest": { "$ref": "#/$defs/digest" },
        "reference_battery_digest": { "$ref": "#/$defs/digest" },
        "calibration_set_digest": { "$ref": "#/$defs/digest" },
        "checks_run": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["check_id", "version"],
            "properties": {
              "check_id": { "type": "string" },
              "version": { "type": "string" },
              "parameters": { "type": "object" }
            }
          }
        },
        "checks_unavailable": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["check_id", "reason"],
            "properties": {
              "check_id": { "type": "string" },
              "reason": { "type": "string" },
              "fallback_used": { "type": ["string", "null"] }
            }
          }
        }
      }
    },
    "summary": {
      "type": "object",
      "required": ["overall_disposition", "asset_verdicts", "finding_counts"],
      "properties": {
        "overall_disposition": { "$ref": "#/$defs/disposition" },
        "asset_verdicts": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["asset", "disposition", "confidence"],
            "properties": {
              "asset": { "$ref": "#/$defs/asset_ref" },
              "disposition": { "$ref": "#/$defs/disposition" },
              "confidence": { "$ref": "#/$defs/unit" },
              "coverage_gaps": { "type": "array", "items": { "type": "string" } }
            }
          }
        },
        "finding_counts": {
          "type": "object",
          "required": ["ACCEPT", "REVIEW", "QUARANTINE"],
          "properties": {
            "ACCEPT": { "type": "integer", "minimum": 0 },
            "REVIEW": { "type": "integer", "minimum": 0 },
            "QUARANTINE": { "type": "integer", "minimum": 0 }
          }
        }
      }
    },
    "modules": {
      "type": "object",
      "required": [
        "data_integrity", "model_integrity", "inference_provenance",
        "distribution_shift", "governance"
      ],
      "properties": {
        "data_integrity": {
          "type": "object",
          "required": ["status", "findings", "source_risk"],
          "properties": {
            "status": { "$ref": "#/$defs/module_status" },
            "findings": { "type": "array", "items": { "$ref": "#/$defs/finding" } },
            "source_risk": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["source_type", "source_id", "n_samples", "n_flagged", "risk_score", "breakdown"],
                "properties": {
                  "source_type": { "enum": ["contributor", "batch", "source"] },
                  "source_id": { "type": "string" },
                  "n_samples": { "type": "integer", "minimum": 0 },
                  "n_flagged": { "type": "integer", "minimum": 0 },
                  "risk_score": { "type": "number", "minimum": 0, "maximum": 100 },
                  "breakdown": {
                    "type": "object",
                    "properties": {
                      "trigger_injection": { "type": "integer", "minimum": 0 },
                      "label_flipping": { "type": "integer", "minimum": 0 },
                      "systematic_mislabelling": { "type": "integer", "minimum": 0 },
                      "near_duplicate_flooding": { "type": "integer", "minimum": 0 },
                      "out_of_distribution": { "type": "integer", "minimum": 0 }
                    }
                  }
                }
              }
            }
          }
        },
        "model_integrity": {
          "type": "object",
          "required": ["status", "access_level", "confidence", "limitations", "findings"],
          "properties": {
            "status": { "$ref": "#/$defs/module_status" },
            "access_level": { "enum": ["NONE", "BB-L", "BB-S", "WB"] },
            "registered_digest_existed": { "type": "boolean" },
            "confidence": { "$ref": "#/$defs/unit" },
            "limitations": { "type": "array", "items": { "type": "string" } },
            "findings": { "type": "array", "items": { "$ref": "#/$defs/finding" } }
          }
        },
        "inference_provenance": {
          "type": "object",
          "required": ["status", "records_total", "status_counts", "findings"],
          "properties": {
            "status": { "$ref": "#/$defs/module_status" },
            "records_total": { "type": "integer", "minimum": 0 },
            "status_counts": {
              "type": "object",
              "additionalProperties": { "type": "integer", "minimum": 0 }
            },
            "findings": { "type": "array", "items": { "$ref": "#/$defs/finding" } }
          }
        },
        "distribution_shift": {
          "type": "object",
          "required": ["status", "shift_detected", "verdict", "calibrated_risk", "characterisation", "findings"],
          "properties": {
            "status": { "$ref": "#/$defs/module_status" },
            "shift_detected": { "type": "boolean" },
            "verdict": {
              "enum": ["NO_MATERIAL_SHIFT", "PROBABLE_OPERATIONAL_DRIFT", "SUSPICIOUS_MANIPULATION", "INCONCLUSIVE"]
            },
            "calibrated_risk": { "$ref": "#/$defs/unit" },
            "calibration_quality": {
              "type": "object",
              "properties": {
                "ece": { "type": "number", "minimum": 0 },
                "extrapolated": { "type": "boolean" }
              }
            },
            "characterisation": {
              "type": "object",
              "required": ["summary", "descriptors"],
              "properties": {
                "summary": { "type": "string" },
                "descriptors": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["name", "effect_size"],
                    "properties": {
                      "name": { "type": "string" },
                      "effect_size": { "type": "number" },
                      "related_factor": {
                        "enum": ["terrain", "season", "sensor", "illumination", "acquisition", "other"]
                      }
                    }
                  }
                }
              }
            },
            "findings": { "type": "array", "items": { "$ref": "#/$defs/finding" } }
          }
        },
        "governance": {
          "type": "object",
          "required": ["analyst_decisions"],
          "properties": {
            "analyst_decisions": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["finding_id", "analyst_id", "decision", "justification", "decided_at"],
                "properties": {
                  "finding_id": { "type": "string" },
                  "analyst_id": { "type": "string" },
                  "decision": { "$ref": "#/$defs/disposition" },
                  "justification": { "type": "string", "minLength": 1 },
                  "decided_at": { "type": "string", "format": "date-time" }
                }
              }
            }
          }
        }
      }
    },
    "coverage_statement": {
      "type": "object",
      "required": ["supported", "partial", "unsupported", "assumptions", "known_limitations"],
      "properties": {
        "supported": { "type": "array", "items": { "type": "string" } },
        "partial": { "type": "array", "items": { "type": "string" } },
        "unsupported": { "type": "array", "items": { "type": "string" } },
        "assumptions": { "type": "array", "items": { "type": "string" } },
        "known_limitations": { "type": "array", "items": { "type": "string" } }
      }
    },
    "audit": {
      "type": "object",
      "required": ["log_head_hash", "entry_count", "chain_verified"],
      "properties": {
        "log_head_hash": { "$ref": "#/$defs/digest" },
        "entry_count": { "type": "integer", "minimum": 0 },
        "chain_verified": { "type": "boolean" }
      }
    },
    "signature": {
      "type": "object",
      "required": ["algorithm", "key_id", "value"],
      "properties": {
        "algorithm": { "const": "Ed25519" },
        "key_id": { "type": "string" },
        "value": { "type": "string" }
      }
    }
  },
  "$defs": {
    "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
    "unit": { "type": "number", "minimum": 0, "maximum": 1 },
    "disposition": { "enum": ["ACCEPT", "REVIEW", "QUARANTINE"] },
    "severity": { "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
    "module_status": { "enum": ["COMPLETED", "PARTIAL", "UNAVAILABLE", "ERROR"] },
    "asset_type": {
      "enum": ["sample", "contributor", "batch", "source", "dataset", "model", "inference_record", "record_stream", "input_batch", "audit_log"]
    },
    "asset_ref": {
      "type": "object",
      "required": ["type", "id"],
      "properties": {
        "type": { "$ref": "#/$defs/asset_type" },
        "id": { "type": "string" },
        "digest": { "$ref": "#/$defs/digest" }
      }
    },
    "asset": {
      "type": "object",
      "required": ["type", "id", "digest"],
      "properties": {
        "type": { "$ref": "#/$defs/asset_type" },
        "id": { "type": "string" },
        "digest": { "$ref": "#/$defs/digest" },
        "format": { "type": "string" },
        "metadata": { "type": "object" }
      }
    },
    "finding": {
      "type": "object",
      "required": [
        "id", "module", "check_id", "created_at",
        "reason", "evidence", "confidence", "severity",
        "affected_asset", "recommended_disposition"
      ],
      "properties": {
        "id": { "type": "string" },
        "module": { "enum": ["M1", "M2", "M3", "M4", "M5"] },
        "check_id": { "type": "string" },
        "created_at": { "type": "string", "format": "date-time" },
        "status": { "enum": ["FLAGGED", "UNAVAILABLE"], "default": "FLAGGED" },
        "reason": { "type": "string", "minLength": 1 },
        "evidence": {
          "type": "object",
          "properties": {
            "metrics": { "type": "object" },
            "thresholds": { "type": "object" },
            "sample_ids": { "type": "array", "items": { "type": "string" } },
            "artefacts": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["kind", "path", "digest"],
                "properties": {
                  "kind": { "enum": ["thumbnail", "overlay", "heatmap", "chart", "trigger_image", "table", "verification_steps"] },
                  "path": { "type": "string" },
                  "digest": { "$ref": "#/$defs/digest" }
                }
              }
            }
          }
        },
        "confidence": { "$ref": "#/$defs/unit" },
        "severity": { "$ref": "#/$defs/severity" },
        "affected_asset": { "$ref": "#/$defs/asset_ref" },
        "recommended_disposition": { "$ref": "#/$defs/disposition" },
        "limitations": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

### 13.3 Example finding

```json
{
  "id": "F-M1-0007",
  "module": "M1",
  "check_id": "M1.trigger.patch_repeat",
  "created_at": "2026-10-01T10:15:02Z",
  "status": "FLAGGED",
  "reason": "Contributor_C supplied 41 images sharing an identical 4x4 patch in the bottom-right corner; 39 of them are labelled 'truck', far above the contributor's normal share of that class.",
  "evidence": {
    "metrics": { "images_with_patch": 41, "fraction_in_target_class": 0.95, "contributor_share_of_class": 0.31 },
    "thresholds": { "min_repeat_count": 10 },
    "sample_ids": ["img_10441", "img_10458", "img_10502"],
    "artefacts": [
      { "kind": "overlay", "path": "evidence/F-M1-0007/overlay.png", "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000" }
    ]
  },
  "confidence": 0.91,
  "severity": "CRITICAL",
  "affected_asset": { "type": "contributor", "id": "contributor_C" },
  "recommended_disposition": "QUARANTINE",
  "limitations": ["Detected with pixel-level patch search; blended or invisible triggers would not be found by this check."]
}
```

*(All numbers and the zero digest above are placeholders for illustration.)*

---

## 14. Inference Record and Audit Log Formats

### 14.1 Inference record (Module 3)

```json
{
  "record_version": "1.0",
  "stream_id": "uav-07-cam-front",
  "sequence": 1043,
  "timestamp": "2026-10-01T10:20:31.512Z",
  "nonce": "b64:3q2+7w==",
  "input": { "sha256": "sha256:<64 hex>", "width": 1920, "height": 1080, "encoding": "jpeg" },
  "model": { "id": "detector-v3", "format": "onnx", "weight_digest": "sha256:<64 hex>" },
  "config": {
    "preprocessing": { "resize": [640, 640], "letterbox": true, "mean": [0, 0, 0], "std": [255, 255, 255], "channel_order": "RGB" },
    "inference": { "conf_threshold": 0.25, "nms_iou": 0.45, "runtime": "onnxruntime-cpu", "runtime_version": "<version>" },
    "sha256": "sha256:<64 hex>"
  },
  "output": {
    "detections": [
      { "class": "vehicle", "score": 0.87, "bbox_xyxy": [412.0, 220.5, 498.0, 281.0] }
    ]
  },
  "prev_record_hash": "sha256:<64 hex>",
  "signer": { "key_id": "infer-key-2026-01", "algorithm": "Ed25519" },
  "signature": "b64:<signature>"
}
```

Signing procedure:

1. Build the record without `signature`.
2. Serialise canonically (RFC 8785).
3. `record_hash = SHA-256(canonical_bytes)`.
4. `signature = Ed25519_sign(private_key, canonical_bytes)`.
5. The next record's `prev_record_hash` is this `record_hash`.

### 14.2 Numerical canonicalisation of outputs

Floating-point outputs are rounded to a fixed, declared precision (for example 4 decimal places for scores, 1 for pixel coordinates) **before** signing, and the precision is part of `config.inference`. This keeps canonical serialisation deterministic across machines.

### 14.3 Audit log (Module 5, R-GOV-2, R-DEL-4)

Stored as **JSON Lines**, one entry per line, append-only.

```json
{
  "index": 57,
  "timestamp": "2026-10-01T10:15:02Z",
  "actor": { "type": "system", "id": "aura-cv/1.0.0" },
  "event": "FINDING_CREATED",
  "payload": { "finding_id": "F-M1-0007", "check_id": "M1.trigger.patch_repeat" },
  "payload_sha256": "sha256:<64 hex>",
  "prev_entry_hash": "sha256:<64 hex>",
  "entry_hash": "sha256:<64 hex>",
  "signature": "b64:<signature>"
}
```

**Event types (design choice):** `SESSION_START`, `INGEST`, `ACCESS_LEVEL_SET`, `CHECK_STARTED`, `CHECK_COMPLETED`, `CHECK_UNAVAILABLE`, `FINDING_CREATED`, `ANALYST_VIEWED`, `ANALYST_DECISION`, `REPORT_EXPORTED`, `KEY_ROTATED`, `SESSION_END`.

**Verification:** recompute each `entry_hash` from the canonical entry (excluding `entry_hash` and `signature`), confirm it matches, confirm `prev_entry_hash` links to the previous entry, verify each signature, and compare the final `entry_hash` with the head hash recorded in the last exported report.

**Reproducibility (R-DEL-4):** the submission includes an audit log generated by running the full demo scenario set with fixed seeds, together with the command that regenerates it and the command that verifies it. Timestamps differ between runs (and therefore entry hashes and signatures, even though Ed25519 signing itself is deterministic), so reproducibility is defined as: **the same events, in the same order, with the same payload digests** for the same inputs and seeds.

---
## 15. Evaluation Plan and Metrics

Every scenario in §11 has a ground-truth manifest, so detection quality can be measured rather than claimed. **No results are reported in this document; the tables below define what will be measured.**

### 15.1 Metrics per module

| Module | What is measured | Metrics |
|---|---|---|
| **M1 Data** | Sample-level detection per attack type (D1 to D6) | Precision, recall, F1, AUROC, false positive rate on clean contributors |
| **M1 Data** | Source-level detection (D7 and mixed cases) | Rank of the malicious contributor, AUROC over contributors, false alarms on honest contributors |
| **M2 Model** | Backdoor detection (M1 vs M4) | True positive rate on backdoored models, false positive rate on clean models, trigger reconstruction quality (overlap with true trigger) |
| **M2 Model** | Substitution and modification (M2, M3) | Detection rate, and the smallest weight perturbation that is detected |
| **M2 Model** | Fallback behaviour | Every white-box check reports `UNAVAILABLE` under black-box access (pass/fail) |
| **M3 Provenance** | Tampering (I1 to I6) | Detection rate per tamper type (expected 100% for cryptographic checks), false rejection rate on untampered records, verification time per record |
| **M4 Shift** | Shift detection (S1 to S5) | Detection rate by shift strength, false positive rate on S5 |
| **M4 Shift** | Calibration | Expected Calibration Error, reliability diagram |
| **M4 Shift** | Drift vs manipulation (S1/S2 vs S3/S4) | Accuracy on cases with a decisive verdict, and the fraction labelled INCONCLUSIVE |
| **M5 Governance** | Audit log tampering (L1 to L3) | Detection rate (expected 100%) |
| **M5 Governance** | Report completeness | Every finding validates against the schema (pass/fail) |
| **System** | Offline operation | Full run with networking disabled completes (pass/fail) |
| **System** | Performance | Wall-clock time and peak memory on the stated reference laptop |

### 15.2 Evaluation protocol

1. Generate all scenarios from configs with fixed seeds.
2. Run AURA-CV on each scenario **without** access to ground truth.
3. The evaluation harness compares findings with manifests and computes metrics.
4. Repeat with several seeds and report mean and spread.
5. Publish the configs, seeds, manifests and metric outputs with the submission.

---

## 16. Coverage Statement

This is a required deliverable (R-DEL-5, R-GOV-3). It is embedded in every report.

### 16.1 Supported attack classes and conditions

| Area | Supported |
|---|---|
| Data | Visible patch triggers and blended triggers present in a subset of samples; random label flipping; systematic class-to-class mislabelling by a contributor; near-duplicate flooding via common augmentations; out-of-distribution insertion; annotation format errors |
| Data (source level) | Contributor, batch and source risk when metadata is supplied |
| Model | Weight-file substitution against a registered digest; behavioural change against a registered fingerprint; backdoors in **classification** models with patch-like triggers (white-box reconstruction and black-box probing) |
| Inference records | Alteration, forgery, record substitution, replay, deletion, reordering, model and configuration substitution, input mismatch (when the image is available) |
| Distribution | Global shifts in illumination, contrast, colour, sharpness, noise, resolution and compression; domain change between sources |
| Audit | Edits, deletions and truncation (truncation relative to an exported head hash) |

### 16.2 Partially supported

| Area | Why partial |
|---|---|
| Backdoors in **object detection** models | Digest, fingerprint and black-box patch probing are supported; full trigger reconstruction for detectors is Phase 2 |
| Trigger detection **without** the contributed model's activations | Uses a generic backbone and pixel-level search; subtle triggers may be missed |
| Drift vs manipulation | Decisive only when evidence rules agree; otherwise INCONCLUSIVE |
| ONNX gradient-based checks | ONNX graphs expose weights and activations, but gradient-based reconstruction may be unavailable depending on the exported graph |
| Terrain and season characterisation | Inferred indirectly from colour and texture statistics unless metadata is supplied |

### 16.3 Not supported

- **Clean-label poisoning**, where poisoned samples keep correct labels.
- **Sample-specific or input-aware triggers** (for example warping-based or invisible dynamic triggers).
- **Physical-world triggers** and adversarial patches applied to real objects in the scene at inference time.
- **Adaptive attackers** who know and optimise against AURA-CV's detectors and thresholds.
- **Poisoning that is spread evenly across all contributors**, since source-level comparison relies on at least some honest contributors.
- **Compromise of signing keys** or of the signing host.
- **Forgery of the input before signing** (the system proves integrity from the point of signing onward).
- **Privacy attacks** (membership inference, model inversion) and **model extraction**.
- **Non-RGB modalities** (SAR, thermal, multispectral) and **video-level temporal attacks** in the MVP.

### 16.4 Assumptions

1. The AURA-CV code, bundled weights and reference battery are trusted and unmodified.
2. The declared reference distribution and trusted reference set are clean and representative.
3. Signing keys are generated and held in the trusted environment and are not compromised.
4. At least some contributors are honest when source-level comparison is used.
5. The model's declared input/output interface is correct enough to run it.

### 16.5 Known limitations

- Detection thresholds are tuned on the team's generated scenarios and may need recalibration for new domains.
- FFT-based evidence can confuse low-light sensor noise with manipulation, and low-frequency adversarial perturbations with drift.
- Weight-statistics checks are weak signals and are used only as supporting evidence.
- Very small contributors produce wide risk intervals; the Beta-Binomial score reflects this as lower confidence rather than as low risk.
- Performance figures are measured only on the stated reference hardware.

---

## 17. Analyst User Interface

The problem statement does not mandate a specific UI, but PS 2.2.5 is explicitly **analyst-facing**. Every screen below maps to a requirement.

| Screen | Contents | Requirement |
|---|---|---|
| **Dashboard** | Overall and per-asset disposition, finding counts, status of each module, model access level badge, offline indicator | R-GOV-1, R-MOD-3, R-CON-1 |
| **New Assessment** | Load dataset (COCO/YOLO), metadata, model (ONNX/TorchScript), records, reference distribution; choose access level; progress per module | R-CON-2, R-CON-3 |
| **Data Integrity** | Contributor risk table with breakdown, duplicate clusters, flagged image gallery with overlays, per-contributor confusion matrix | R-DATA-1 to 6 |
| **Model Integrity** | Access assumptions, digest and fingerprint result, reconstructed trigger image, probing results, `UNAVAILABLE` cards with reasons, confidence and limitations | R-MOD-1 to 3, R-CON-5 |
| **Inference Provenance** | Record table with status, record detail showing each bound field and each verification step result | R-INF-1, R-INF-2 |
| **Distribution Shift** | Shift score with calibration quality, descriptor chart, reference vs new embedding plot, verdict including INCONCLUSIVE | R-SHIFT-1 to 4 |
| **Findings / Review Queue** | Every finding with its five mandatory fields; filters; confirm or override with justification | R-GOV-1 |
| **Audit Log** | Hash-chained entries; "Verify chain" button showing the first failing entry | R-GOV-2 |
| **Report & Export** | Preview; export signed JSON and HTML/PDF; export audit log | R-EXP-3, R-DEL-3, R-DEL-4 |
| **Coverage & Limitations** | Supported, partial, unsupported, assumptions, known limitations | R-GOV-3, R-DEL-5 |
| **Attack Lab** (demo) | Run a seeded scenario with one click and re-assess | R-EXP-2 |

**UI rules:** all fonts, icons and scripts bundled locally (no CDN); every score shown next to its reason; dispositions shown as text labels, not colour alone; unavailable checks always visible.

---

## 18. Technology Stack

All components are open source and installable offline.

| Layer | Choice | Role |
|---|---|---|
| Language | Python 3.10+ | Core engine |
| CV and ML | PyTorch (TorchScript, frozen backbone), ONNX Runtime (CPU), OpenCV, NumPy, SciPy, scikit-learn | Model execution, embeddings, statistics, lightweight classifiers, calibration |
| Hashing | `imagehash` (pHash), `hashlib` (SHA-256) | Duplicates and digests |
| Cryptography | `cryptography` library (Ed25519), RFC 8785 canonical JSON implementation | Signatures and canonical serialisation |
| Schema | `jsonschema` | Report validation |
| Backend API | FastAPI with Uvicorn, bound to localhost | UI backend |
| Frontend | React with Vite and Tailwind CSS, built to static files and served locally | Analyst UI |
| Reports | HTML templates, with PDF rendering via a locally installed engine | Human-readable report |
| CLI | Typer or argparse | Scripted, reproducible runs |
| Packaging | Local wheelhouse and prebuilt frontend bundle; optional offline container image | Air-gapped installation |

---

## 19. Repository Structure and Setup Notes

### 19.1 Repository layout (proposed)

```
aura-cv/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── setup.md
│   ├── coverage_statement.md
│   └── threat_model.md
├── schemas/
│   ├── assurance_report.schema.json
│   ├── inference_record.schema.json
│   └── audit_entry.schema.json
├── aura/
│   ├── core/            # context, scheduler, access levels, finding model, disposition policy
│   ├── adapters/        # coco.py, yolo.py, imagefolder.py, onnx_model.py, torchscript_model.py
│   ├── features/        # frozen extractor, embedding index
│   ├── m1_data/         # triggers, flips, systematic, duplicates, ood, source_risk
│   ├── m2_model/        # digest, structure, fingerprint, reconstruction, activations, strip, probing
│   ├── m3_provenance/   # signer, verifier, keys, canonical json
│   ├── m4_shift/        # descriptors, mmd, calibration, verdict
│   ├── m5_governance/   # audit log, report builder, exporters
│   └── api/             # FastAPI app
├── ui/                  # React frontend
├── attack_lab/
│   ├── configs/         # YAML scenarios with seeds
│   ├── generators/      # data, model, record, shift, log tampering
│   └── manifests/       # generated ground truth
├── eval/                # harness and metric scripts
├── assets/              # bundled weights, reference battery, fonts, icons
├── keys/                # generated at setup, never committed
├── tests/
└── wheelhouse/          # offline Python packages
```

### 19.2 Setup notes (offline)

1. Copy the repository, `wheelhouse/` and `assets/` to the air-gapped machine through the approved transfer process.
2. Create a virtual environment and install only from the local wheelhouse (for example `pip install --no-index --find-links wheelhouse -r requirements.txt`).
3. Generate signing keys locally with the CLI (for example `aura keys init`); keys are written to `keys/` with restricted permissions.
4. Register the reference distribution and reference battery (for example `aura reference register <path>`); their digests are logged.
5. Start the backend on localhost and open the bundled UI.
6. Run the offline self-check (for example `aura selfcheck --offline`) before any assessment.

*Command names above are the planned CLI design and will be finalised in the codebase.*

---

## 20. MVP Scope versus Phase 2

### 20.1 MVP (hackathon)

Principle: **every module works end to end at a basic level**, since the problem statement asks for a unified layer.

| Module | MVP scope |
|---|---|
| M1 | All five data risks on embeddings plus pixel-level patch search; COCO and YOLO adapters; contributor Beta-Binomial risk with breakdown |
| M2 | Digest and structure check; behavioural fingerprint on reference battery; white-box trigger reconstruction for classifiers; STRIP-style and patch probing for black-box; explicit `UNAVAILABLE` reporting |
| M3 | Complete: binding, signing, chain, sequence, nonce, timestamp, full verifier with per-step results |
| M4 | MMD and per-sample novelty; descriptor characterisation; isotonic calibration with ECE; three-way verdict |
| M5 | Finding schema with mandatory fields; disposition policy; analyst override; signed hash-chained audit log with verify; signed JSON and HTML report; coverage statement |
| Attack Lab | Seeded generators for D1 to D7, M1 to M4, I1 to I6, S1 to S5, L1 to L3 |
| UI | Screens in §17, local only |

### 20.2 Phase 2

- Trigger reconstruction for object detection models.
- Support for sample-specific and clean-label attacks where research methods allow.
- Streaming ingestion for large COCO/YOLO datasets and video feeds.
- Plugins for SAR, thermal and multispectral imagery.
- Hardware-backed keys (TPM 2.0 or HSM) on edge devices.
- Offline CI integration that blocks unverified models from deployment.
- Optional remediation workflows (retraining on cleaned data, neuron pruning) with automatic re-assessment.

---

## 21. Demonstration Script

Run with networking disabled to demonstrate air-gapped operation (R-CON-1).

1. **Clean baseline.** Load a clean dataset from three contributors, a clean model and clean records. Show that the report is ACCEPT, with the coverage statement visible.
2. **Data poisoning.** Generate D7 for Contributor_C (patch trigger, flips, duplicates). Show Contributor_C at the top of the risk table with its breakdown, the overlay of the recurring patch, and a QUARANTINE disposition.
3. **Backdoored model.** Load the M1 model with white-box access. Show the reconstructed trigger. Reload the same model as black-box and show trigger reconstruction as `UNAVAILABLE` with the fallback probing result.
4. **Model substitution.** Load the M2 model under the same name. Show the digest and fingerprint mismatch.
5. **Record tampering.** Edit a bounding box (I1) and show the signature failure. Replay an old record (I3) and show the nonce and sequence failure. Swap two valid records (I2) and show the chain failure.
6. **Distribution shift.** Feed S1 low-light and haze images and show PROBABLE_OPERATIONAL_DRIFT with its characterisation. Feed S3 adversarial images and show SUSPICIOUS_MANIPULATION or INCONCLUSIVE with the evidence rules.
7. **Audit log.** Edit one audit entry (L1) and press "Verify chain" to show the failing entry.
8. **Export.** Export the signed JSON and HTML report, show the schema validation passing, and show the audit head hash in the report.

---

## 22. Deliverables Checklist

| Deliverable (PS 2.3) | What is submitted | Status |
|---|---|---|
| **Source code** | `aura/`, `ui/`, `attack_lab/`, `eval/`, `tests/` | ☐ |
| **Architecture and setup notes** | `docs/architecture.md`, `docs/setup.md`, this document | ☐ |
| **Assurance-report schema** | `schemas/assurance_report.schema.json` (§13.2), plus record and audit schemas | ☐ |
| **Reproducible audit log** | Log from the full demo run, with regenerate and verify commands (§14.3) | ☐ |
| **Coverage statement** | `docs/coverage_statement.md` (§16), also embedded in every report | ☐ |
| Supporting: attack scenarios | Configs, seeds and manifests (§11) | ☐ |
| Supporting: evaluation results | Metric outputs from §15 | ☐ |

---

## 23. Suggested Team Work Split

A suggested split for a six-person team; adjust to actual team size and skills.

| Member | Ownership |
|---|---|
| 1 | Module 1 (data checks, contributor risk) and format adapters |
| 2 | Module 2 (model adapters, fingerprinting, trigger reconstruction, probing) |
| 3 | Module 3 (signing, verification, keys) and Module 5 audit log |
| 4 | Module 4 (descriptors, MMD, calibration, verdict) |
| 5 | Attack Lab and evaluation harness |
| 6 | UI, report rendering, schema validation, integration and demo |

Integration rule: every module outputs findings in the §10.2 format from the first day, so the UI and report can be built in parallel with the detectors.

---

## 24. References"

1. B. Wang et al., "Neural Cleanse: Identifying and Mitigating Backdoor Attacks in Neural Networks," *IEEE Symposium on Security and Privacy*, 2019.
2. T. Gu, B. Dolan-Gavitt, S. Garg, "BadNets: Identifying Vulnerabilities in the Machine Learning Model Supply Chain," arXiv:1708.06733, 2017.
3. B. Chen et al., "Detecting Backdoor Attacks on Deep Neural Networks by Activation Clustering," arXiv:1811.03728, 2018.
4. B. Tran, J. Li, A. Madry, "Spectral Signatures in Backdoor Attacks," *NeurIPS*, 2018.
5. Y. Gao et al., "STRIP: A Defence Against Trojan Attacks on Deep Neural Networks," *ACSAC*, 2019.
6. B. Wu et al., "BackdoorBench: A Comprehensive Benchmark of Backdoor Learning," *NeurIPS Datasets and Benchmarks Track*, 2022.
7. C. Northcutt, L. Jiang, I. Chuang, "Confident Learning: Estimating Uncertainty in Dataset Labels," *Journal of Artificial Intelligence Research*, 2021.
8. K. Lee et al., "A Simple Unified Framework for Detecting Out-of-Distribution Samples and Adversarial Attacks," *NeurIPS*, 2018 (Mahalanobis OOD).
9. W. Liu et al., "Energy-based Out-of-distribution Detection," *NeurIPS*, 2020.
10. A. Gretton et al., "A Kernel Two-Sample Test," *Journal of Machine Learning Research*, 2012 (MMD).
11. C. Guo et al., "On Calibration of Modern Neural Networks," *ICML*, 2017.
12. R. Selvaraju et al., "Grad-CAM: Visual Explanations from Deep Networks via Gradient-based Localization," *ICCV*, 2017.
13. IETF RFC 8032, "Edwards-Curve Digital Signature Algorithm (EdDSA)," 2017.
14. NIST FIPS 186-5, "Digital Signature Standard (DSS)," 2023 (includes EdDSA).
15. NIST FIPS 180-4, "Secure Hash Standard (SHS)" (SHA-256).
16. IETF RFC 8785, "JSON Canonicalization Scheme (JCS)," 2020.
17. IARPA / NIST **TrojAI** program (Trojan detection in AI models).
18. G.-S. Xia et al., "DOTA: A Large-scale Dataset for Object Detection in Aerial Images," *CVPR*, 2018.
19. P. Zhu et al., VisDrone: drone-captured benchmark datasets for detection and tracking.

*Verify each citation against the original source before final submission.*
