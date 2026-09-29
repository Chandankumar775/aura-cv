# Future Work

Out of scope for the hackathon build (CLAUDE.md A18), or noticed during the build and
parked rather than added without approval (A4).

## From A18
- Trigger reconstruction for detection models
- Clean-label and dynamic-trigger defences
- Video / RTSP streaming ingestion
- SAR / thermal / multispectral plugins
- TPM / HSM key storage
- CI/CD integration
- Automated remediation

## Parked during the build
- **Audit read-only views** (`ANALYST_VIEWED`, design.md §10.4) — not in the A8.5 event list; see decisions D-004.
- **Encrypted private keys at rest** (passphrase-protected PKCS#8) — current protection is file permissions (D-013).
- **PowerShell equivalents of the offline bundle scripts** — pending approval (decisions R5).
- **Head-hash checkpoint file** kept outside the log directory, so truncation is detectable even before the first report is exported.
