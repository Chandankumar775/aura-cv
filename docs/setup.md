# Setup

> Status: Milestone M0. The offline bundle scripts (`scripts/prepare_offline_bundle.sh`,
> `scripts/install_offline.sh`) arrive in M10; until then this is a development setup.

## Development machine (connected)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt      # Windows
# .venv/bin/python -m pip install -r requirements-dev.txt        # Linux/macOS
.venv/Scripts/python -m pip install --no-build-isolation --no-deps -e .
```

Requires Python ≥ 3.10 (developed on 3.12.10).

## First run

```bash
aura keys init              # creates inference, audit and report Ed25519 keys (idempotent)
aura selfcheck              # PASS/WARN/FAIL per item
aura selfcheck --offline    # as above, but a live network route is a FAIL
aura audit verify           # recompute the audit hash chain and signatures
```

On a connected machine `selfcheck --offline` fails `network.isolation` by design; it
passes only when the host has no non-loopback route. AURA-CV itself never opens an
outbound connection: every CLI process installs an in-process guard that refuses them.

## Runtime state

All state lives under `AURA_HOME` (default: the repository root):

| Path | Content |
|---|---|
| `keys/` | private keys (owner-only), `registry.json` of public keys |
| `data/audit/audit_log.jsonl` | the tamper-evident audit log |
| `data/` | database, artefacts and uploads (from M2) |

Both `keys/` and `data/` are git-ignored.

## Tests

```bash
.venv/Scripts/python -m pytest
```

The suite runs with non-loopback sockets blocked (`pytest-socket`, configured in
`pyproject.toml`) and needs no downloads.

## Hosted demo on Vercel

The repository deploys to Vercel as-is: `vercel.json` builds the UI to `ui/dist` (served from the CDN) and exposes the FastAPI app through `api/index.py` (a Python serverless function; `requirements.txt` is installed automatically).

```bash
npx vercel          # preview deployment (first run links the project)
npx vercel --prod   # production deployment
```

Or push the repository to GitHub and import it at vercel.com/new. No framework preset or build settings are needed; `vercel.json` carries them.

Optional environment variable: `AURA_SESSION_SECRET` (any long random string) signs login sessions. Without it, a per-deployment secret is derived; the demo credentials are public on the login page anyway.

What changes in hosted mode (detected from Vercel's `VERCEL` variable, or forced locally with `AURA_HOSTED=1`):

| Aspect | Hosted behaviour |
|---|---|
| Labelling | Status bar and login page say "Hosted demo, not air-gapped". The production build is installed offline. |
| Storage | `/tmp/aura`, per serverless instance. It resets when an instance recycles; every instance seeds the identical demo world (deterministic ids). |
| Sessions | HMAC-signed tokens, valid on any instance. |
| Live runs | Executed inside the streaming `/events` request (serverless hosts freeze background threads). The run page also polls status as a fallback. |
| Network guard | Not installed (the provider's runtime needs sockets). |

Known limits of the hosted demo: decisions, reports and new assessments live only on the instance that handled them. They can disappear after a cold start or when traffic spreads across instances. The seeded scenario is always present.
