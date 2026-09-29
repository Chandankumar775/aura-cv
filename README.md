# AURA-CV — Air-Gapped Unified Risk & Assurance for Computer Vision

Smart India Hackathon entry, Ministry of Defence problem statement *"Trustworthy
Computer Vision Integrity Assurance for Data, Models and Inference Outputs in
Multi-Contributor Pipelines"*.

AURA-CV is an offline, model-agnostic assurance framework. It evaluates a contributed
dataset, a trained model, inference records and new operational input batches, and
produces an evidence-based, signed assessment of integrity and risk — without assuming
any contributing source is trusted.

**Status: Milestone M0 (foundations).** Implemented: domain model, RFC 8785 canonical
JSON, SHA-256 digests, Ed25519 key management, the hash-chained signed audit log, the
finding schema, the disposition policy, the check plugin framework with UNAVAILABLE
fallbacks, the outbound network guard and `aura selfcheck`. No detectors yet.

| | |
|---|---|
| Binding spec | [`CLAUDE.md`](CLAUDE.md) |
| Solution design | [`docs/design.md`](docs/design.md) |
| Setup | [`docs/setup.md`](docs/setup.md) |
| Architecture & traceability | [`docs/architecture.md`](docs/architecture.md) |
| Decisions | [`docs/decisions.md`](docs/decisions.md) |
| Coverage statement | [`docs/coverage_statement.md`](docs/coverage_statement.md) |

```bash
aura keys init && aura selfcheck --offline
aura serve                      # local console on 127.0.0.1:8765
```

Hosted demo: deploys to Vercel as-is (`npx vercel --prod`); see [docs/setup.md](docs/setup.md#hosted-demo-on-vercel).
