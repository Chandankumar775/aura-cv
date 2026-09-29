# AURA-CV Architecture

> Living document, updated each milestone. Design rationale: `docs/design.md` (§5).
> Binding spec: `CLAUDE.md`. Decisions: `docs/decisions.md`.

## 1. Layers

```
            CLI (Typer)        API (FastAPI, 127.0.0.1)        UI (React, static)
                 \                    |                           /
                  +------ orchestration: assessments, jobs (M7/M2) ------+
                                      |
        Scheduler + Check registry  (aura/core/checks.py)  — one plugin protocol for every detector
          |          |           |           |
         M1         M2          M3          M4        -> Findings (aura/core/types.py)
        data       model    provenance     shift            |
          \          |           |          /           M5 governance: policy, decisions,
           adapters (datasets/models) + frozen features     audit log, reports, coverage
                                      |
                      core: hashing · RFC 8785 canonical JSON · Ed25519 keys · netguard
```

Modules talk only through the domain types in `aura/core/types.py` (A4).

## 2. Built so far (Milestone M0)

| Component | File | Notes |
|---|---|---|
| Domain model: all A7.1 enums, A7.2 entities, A7.3 Finding | `aura/core/types.py` | Pydantic v2; `Finding` frozen; mirrors `schemas/finding.schema.json` |
| Prefixed ids, deterministic finding ids, timestamps | `aura/core/ids.py` | D-007, D-020 |
| SHA-256 + `sha256:` digest format | `aura/core/hashing.py` | streaming file hash |
| RFC 8785 canonical JSON | `aura/core/canonical.py` | D-006 |
| Ed25519 key store (generate, rotate, sign, verify, purposes) | `aura/m3_provenance/keys.py` | D-013 |
| Hash-chained signed audit log + verifier | `aura/m5_governance/audit_log.py` | D-010, D-011, D-014 |
| Finding JSON Schema + validator | `schemas/finding.schema.json`, `aura/core/schemas.py` | R-GOV-1 |
| Disposition policy, effective/asset/overall verdicts | `aura/core/policy.py` | A7.5, D-008, D-016..018 |
| Access-level lowering rule | `aura/core/access.py` | detection in M2 |
| Check protocol, registry, scheduler, UNAVAILABLE + fallback | `aura/core/checks.py` | A7.4, D-012, D-019 |
| Outbound network guard | `aura/core/netguard.py` | D-022 |
| Selfcheck | `aura/core/selfcheck.py` | D-023 |
| CLI: `selfcheck`, `keys init/list/rotate`, `audit verify/head` | `aura/cli.py` | |

## 3. Requirement traceability

Status: **M0** = foundation in place; **plan** = milestone that implements it. Tests are
listed once they exist.

| Req | Milestone(s) | Code (so far) | Tests (so far) |
|---|---|---|---|
| R-GEN-1 extensible, model-agnostic | M0 (plugin framework), M2 (adapters) | `core/checks.py` | `tests/test_checks.py` |
| R-GEN-2 untrusted sources | M4 (source risk), all | — | — |
| R-GEN-3 evidence-based | M0 (evidence required by schema), M4–M7 | `core/types.py`, `schemas/finding.schema.json` | `tests/test_schema.py` |
| R-DATA-1 trigger injection | M4 | — | — |
| R-DATA-2 label flipping | M4 | — | — |
| R-DATA-3 systematic mislabelling | M4 | — | — |
| R-DATA-4 near-duplicate flooding | M4 | — | — |
| R-DATA-5 OOD insertion | M4 | — | — |
| R-DATA-6 source-level risk | M4 | — | — |
| R-MOD-1 anomalous/substituted/backdoor | M5 | — | — |
| R-MOD-2 access-appropriate methods | M0 (access gating), M5 | `core/checks.py`, `core/access.py` | `tests/test_checks.py`, `tests/test_policy.py` |
| R-MOD-3 state access, confidence, limitations | M5 | — | — |
| R-INF-1 cryptographic binding | M0 (keys, canonical JSON), M1 | `m3_provenance/keys.py`, `core/canonical.py` | `tests/test_keys.py`, `tests/test_canonical.py` |
| R-INF-2 alteration/substitution/replay detectable | M1 | — | — |
| R-SHIFT-1 material deviation | M6 | — | — |
| R-SHIFT-2 characterise shift | M6 | — | — |
| R-SHIFT-3 calibrated score | M6 | — | — |
| R-SHIFT-4 drift vs manipulation | M6 | — | — |
| R-GOV-1 five mandatory fields | M0 | `core/types.py`, `schemas/finding.schema.json`, `core/checks.py` | `tests/test_schema.py`, `tests/test_checks.py` |
| R-GOV-2 tamper-evident audit trail | M0 (log), M2 (DB mirror), M7 | `m5_governance/audit_log.py` | `tests/test_audit_log.py`, `tests/test_cli.py` |
| R-GOV-3 declare unsupported | M7 (coverage.py), M9 (UI) | `docs/coverage_statement.md` (draft) | — |
| R-CON-1 offline / air-gapped | M0 (guard, selfcheck, socket-blocked suite), M10 (bundle) | `core/netguard.py`, `core/selfcheck.py` | `tests/test_offline.py`, `tests/test_cli.py` |
| R-CON-2 COCO and YOLO | M2 | — | — |
| R-CON-3 ONNX and PyTorch/TorchScript | M2 | — | — |
| R-CON-4 no retraining | M5 (digest-unchanged test) | — | — |
| R-CON-5 graceful fallback / report unavailability | M0 (scheduler), M5 | `core/checks.py` | `tests/test_checks.py` |
| R-EXP-1 public/team-generated data and models | M2 (synthetic generator), M3 | — | — |
| R-EXP-2 reproducible attack scenarios | M1 (I1–I6), M3, M5, M6 | — | — |
| R-EXP-3 report with confidence, limitations, action | M7 | — | — |
| R-DEL-1 source code | all | repository | — |
| R-DEL-2 architecture and setup notes | M0 (started), M10 | `docs/architecture.md`, `docs/setup.md` | — |
| R-DEL-3 assurance-report schema | M0 (finding), M1 (record), M7 (report, audit entry) | `schemas/finding.schema.json` | `tests/test_schema.py` |
| R-DEL-4 reproducible audit log | M0 (log), M10 (demo log) | `m5_governance/audit_log.py` | `tests/test_audit_log.py` |
| R-DEL-5 coverage statement | M7, M10 | `docs/coverage_statement.md` (draft) | — |
