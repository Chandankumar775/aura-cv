# Design Decisions Log

Decisions taken where `CLAUDE.md` (binding) and `docs/design.md` disagree, or where
both are silent. Rule applied throughout: *if they disagree, CLAUDE.md wins; if both
are silent, take the simplest compliant option and record it here* (A1, A4).

Each entry: **context → decision → consequence**. Status is `Adopted` unless noted.

---

## Spec conflicts (CLAUDE.md vs design.md)

**D-001 Repository root.** The prompt suggests a fresh `aura-cv/` folder; the working
folder `auracv/` already holds the spec sources. → The repository root **is** `auracv/`.
`masterprompt.md` and `supermd.md` stay at the root as source material; `supermd.md`
is copied verbatim to `docs/design.md`; Part A of the prompt is `CLAUDE.md`.

**D-002 Finding id format.** design.md §13.3 uses `F-M1-0007`; CLAUDE.md A11.1 uses
prefixed ids. → `fnd_<16 hex>`. The schema rejects the old form.

**D-003 Evidence artefacts.** design.md §13.3 inlines `artefacts: [{kind, path, digest}]`;
CLAUDE.md A7.3 uses `artefact_ids`. → `artefact_ids` in findings; path and digest live on
the `Artefact` entity. The report builder (M7) may inline artefact metadata for
readability, but the finding contract stays id-based.

**D-004 Audit event vocabulary.** design.md §14.3 lists `INGEST` and `ANALYST_VIEWED`;
CLAUDE.md A8.5 lists `ASSET_REGISTERED` and no view event. → The A8.5 list exactly
(`AuditEvent` enum); unknown events are rejected at append. Consequence: read-only views
are **not** audited in the MVP (design.md §10.4 said they would be). Recorded in
`future.md`.

**D-005 Asset types.** design.md §10.2 lists 8 asset types; CLAUDE.md A7.1 lists 12. → A7.1.

## Cryptography and formats

**D-006 Canonical JSON.** Use the `rfc8785` package (Trail of Bits, pure Python, pinned,
offline-installable) behind `aura/core/canonical.py`. Tests pin it to the RFC 8785
Appendix B number vectors and the §3.2.2 / §3.2.3 examples. The wrapper additionally
rejects NaN/Infinity, non-string keys and integers outside ±(2^53−1) with one error type.

**D-007 Encodings.** Digests `sha256:<64 lowercase hex>`; signatures, nonces and public
keys `b64:<standard base64>` (design.md §14.1). Timestamps UTC ISO-8601 with
**millisecond** precision and `Z` suffix (`2026-09-29T17:42:03.261Z`), fixed width so
canonical bytes are stable.

**D-009 Hash-chain genesis.** The first audit entry (and, in M1, the first record of a
stream) uses `prev_*_hash = sha256:000…000` (64 zeros).

**D-010 What an audit entry signs.** `entry_hash` and `signature` are both computed over
the RFC 8785 bytes of the entry minus `entry_hash` and `signature` — so `index`,
`timestamp`, `actor`, `event`, `payload`, `payload_sha256`, `prev_entry_hash` and `key_id`
are all covered. Same construction as inference records (A8.3), one code path to reason
about. Signing uses the exact `key_id` written in the body (`sign_with`), so a rotation
racing an append cannot produce a mismatched entry.

**D-011 Audit verification rules.** Verification stops at the first failure and reports
its index and a plain reason. Checks, in order: JSON/schema → `index == line number`
(deletion/insertion/reorder) → `prev_entry_hash` link → `payload_sha256` → `entry_hash` →
signature under a key registered with purpose `audit` (a report or inference key never
verifies an audit entry; an unknown `key_id` fails). Truncation is detected only against a
supplied `expected_head` / `expected_count` (from a report or export); an older head that
is still present in a longer log is valid (the log grew). Timestamps going backwards are a
**warning**, not a failure (clock changes on an isolated host are plausible and the chain
already catches reordering). Append refuses to extend a log whose last line is unreadable.

**D-013 Key storage.** Unencrypted PKCS#8 PEM per key in `keys/`, created with `O_EXCL`
(never overwrites) and owner-only permissions: `chmod 600` on POSIX; on Windows the ACL is
reset with `icacls /inheritance:r /grant:r <user>:F` because POSIX modes do not apply.
Public keys (including retired ones) live in `keys/registry.json` until the DB exists (M2),
then are mirrored into it. `key_id = <purpose>-<YYYYMMDD>-<first 8 hex of SHA-256(raw
public key)>`. Retired keys verify but refuse to sign. TPM/HSM storage is out of scope (A18).

**D-014 Cross-process audit appends.** The CLI and the API server may append to the same
log. Appends take an in-process lock plus an OS file lock (`msvcrt`/`fcntl`) on
`audit_log.jsonl.lock` and re-read the tail under the lock, so the chain never forks.

## Policy and verdicts

**D-008 Confidence bands.** Exactly as the A7.5 headers read: `< 0.4` LOW,
`0.4 ≤ c ≤ 0.8` MEDIUM (both ends inclusive), `> 0.8` HIGH.

**D-016 Analyst decisions vs hard rules.** A7.2 says the latest analyst decision is
effective. → That holds even for hard-override QUARANTINE findings and for UNAVAILABLE
findings: an analyst may accept, with mandatory justification, and the decision is
audited. Coverage gaps remain listed on the asset verdict regardless (A7.5 "the asset
shows a coverage gap"). *Open for review:* whether hard-rule findings should require
ADMIN to downgrade — propose deciding in M7.

**D-017 Asset-verdict confidence.** The report schema needs a confidence per asset
verdict. → The highest confidence among the findings whose effective disposition set the
verdict. Assets with no findings at all get their verdict in M7 (needs the list of
assessed assets and their check coverage).

**D-018 Equal decision timestamps.** "Latest wins" uses a stable sort on `decided_at`, so
with identical millisecond timestamps the later-appended decision wins.

## Check framework

**D-012 Additions to the A7.4 protocol.** Two optional attributes, read with `getattr`:
`asset_input` (which input a check's findings concern — needed to address its UNAVAILABLE
finding) and `parameters(ctx)` (thresholds recorded in `CHECK_STARTED` and in
`checks_run`). The protocol itself is unchanged.

**D-019 Scheduler semantics.** Gate order: missing inputs → insufficient access →
`is_applicable`. A check that fails the gate *or raises* produces exactly one UNAVAILABLE
finding (MEDIUM, confidence 1.0, REVIEW; A7.3) and a `CHECK_UNAVAILABLE` audit entry
(`status: UNAVAILABLE | ERROR`); its fallback then runs once (a check already run —
standalone or as someone's fallback — is never run twice). Findings a check returns are
re-validated against the JSON schema and must carry the check's own module and id;
otherwise the check is treated as crashed. Module status: all ran → COMPLETED; some →
PARTIAL; none, with an error → ERROR; none → UNAVAILABLE; cancel → CANCELLED. Registration
order is execution order.

**D-020 Deterministic finding ids.** `fnd_` + SHA-256 of (assessment id, check id, asset
type, asset id, per-(check, asset) ordinal). Same inputs + seed → same ids (A3 rule 10).
`created_at` is excluded from determinism comparisons.

**D-021 Where dispositions come from.** Checks never choose a disposition; they give
severity, confidence and optional hard-override flags, and `AssessmentContext.make_finding`
applies the policy. The schema and the Pydantic model both forbid an UNAVAILABLE finding
recommending ACCEPT and a FLAGGED finding with no evidence at all.

## Offline enforcement

**D-022 Two layers of network enforcement.** (1) `aura/core/netguard.py` patches the socket
layer in every CLI/API process so any non-loopback `connect`/`sendto`/DNS lookup raises
`OutboundNetworkBlocked` before a packet leaves. (2) The test suite runs under
`pytest-socket --allow-hosts=127.0.0.1,::1`. pytest-socket restores the socket functions
between tests, so the guard itself is tested in a subprocess.

**D-023 What `selfcheck --offline` means.** `network.isolation` asks the OS routing table
for a route to TEST-NET-1 (192.0.2.1) with a UDP `connect()`, which transmits nothing. A
route to any non-loopback address → **FAIL** with `--offline`, **WARN** without. On the
connected development machine this item fails with `--offline` by design.

## Environment and packaging

**D-015 Incremental dependency pins.** `requirements.txt` pins only what is installed and
exercised so far (M0: pydantic, cryptography, jsonschema, rfc8785, typer, PyYAML).
PyTorch (CPU), torchvision, onnx, onnxruntime, NumPy, SciPy, scikit-learn, OpenCV,
Pillow, imagehash, SQLAlchemy, FastAPI, Jinja2 etc. are added — and pinned to the versions
actually verified — in the milestone that first uses them (M2 onwards). Typer ≥ 0.2x no
longer depends on `click`.

**D-024 Schemas location.** Schemas live in top-level `schemas/` (A6) and are located via
`aura.config` (`REPO_ROOT/schemas`). An editable/in-place install is assumed; if the
package is ever built as a wheel, schemas must be added as package data.

**D-025 SQL layer.** SQLAlchemy 2.x (not SQLModel) for M2, with the Pydantic models in
`aura/core/types.py` kept as the domain contract.

---

## Risks and ambiguities flagged for later milestones

| # | Risk / ambiguity | Proposed handling | Milestone |
|---|---|---|---|
| R1 | PDF rendering: WeasyPrint needs GTK/Pango native libraries, usually missing on Windows | Probe at runtime; HTML always produced; `/reports/{id}/pdf` → 501 with reason; selfcheck item | M7 |
| R2 | Bundled backbone weights need torchvision's ImageNet ResNet-18 (≈45 MB), fetched only on the connected build machine | `scripts/fetch_weights.py` + digest pin in `BUNDLE_MANIFEST.json`; runtime loads by path only, auto-download disabled | M2 |
| R3 | M4 calibration labels ("operationally harmful") need a model; an assessment without a model cannot calibrate | Calibrated risk → UNAVAILABLE finding with reason; uncalibrated shift statistics still reported | M6 |
| R4 | Gradient-based checks (trigger reconstruction) need TorchScript; ONNX has no gradients | ONNX WB = activations/params only; reconstruction UNAVAILABLE → `M2.patch_probe` (already "Partial" in A16) | M5 |
| R5 | `scripts/*.sh` assume a POSIX shell; the target air-gapped host OS is not stated and the dev machine is Windows | Deliver the `.sh` scripts as specified; propose `.ps1` equivalents — **needs your OK** (scope) | M10 |
| R6 | Neural-Cleanse-style reconstruction on CPU can be slow | Hard iteration and wall-clock budgets per class; report budget exhaustion as a limitation | M5 |
| R7 | "Reproducible audit log" cannot be byte-identical (timestamps) | Reproducibility = same events, same order, same payload digests (design.md §14.3); a comparison tool in M10 | M10 |
| R8 | Hard-rule QUARANTINE downgrade by an ANALYST (D-016) | Decide in M7 whether ADMIN role is required | M7 |
| R9 | Model-scenario M1 (backdoored model) needs training on CPU | Tiny classifier on the synthetic dataset, few epochs, seeded; clearly labelled test-model creation | M5 |
