"""``aura`` command-line interface (CLAUDE.md A11.3). Mirrors the API for scripted runs.

Milestone M0 provides ``selfcheck``, ``keys`` and ``audit verify``; the remaining
commands arrive with the milestones that implement them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from aura.config import BIND_HOST, DEFAULT_PORT, get_settings
from aura.core import netguard
from aura.core.selfcheck import CheckState, passed, run_selfcheck
from aura.core.types import AuditEvent, KeyPurpose

app = typer.Typer(help="AURA-CV: offline assurance for computer-vision data, models and inference.", no_args_is_help=True)
keys_app = typer.Typer(help="Manage local Ed25519 signing keys.", no_args_is_help=True)
audit_app = typer.Typer(help="Inspect and verify the tamper-evident audit log.", no_args_is_help=True)
app.add_typer(keys_app, name="keys")
app.add_typer(audit_app, name="audit")


@app.callback()
def _startup() -> None:
    # Every CLI process runs with the outbound-network guard (R-CON-1).
    netguard.install()


def _stores():
    from aura.m3_provenance.keys import KeyStore
    from aura.m5_governance.audit_log import AuditLog

    s = get_settings()
    store = KeyStore(s.keys_dir)
    return store, AuditLog(s.audit_log_path, store)


_MARK = {CheckState.PASS: "PASS", CheckState.WARN: "WARN", CheckState.FAIL: "FAIL"}


@app.command()
def selfcheck(
    offline: bool = typer.Option(False, "--offline", help="Fail (not warn) if the host has any non-local network route."),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Check the installation: offline guard, crypto, keys, audit chain, schemas."""
    items = run_selfcheck(require_offline=offline)
    if as_json:
        typer.echo(json.dumps({"passed": passed(items), "items": [i.to_dict() for i in items]}, indent=2))
    else:
        for i in items:
            typer.echo(f"[{_MARK[i.state]}] {i.id:<18} {i.detail}")
        typer.echo("selfcheck: " + ("PASSED" if passed(items) else "FAILED"))
    raise typer.Exit(0 if passed(items) else 1)


@keys_app.command("init")
def keys_init() -> None:
    """Create any missing inference, audit and report keys (idempotent)."""
    store, log = _stores()
    created = []
    # The audit key comes first so that its own creation can be logged.
    for purpose in (KeyPurpose.AUDIT, KeyPurpose.INFERENCE, KeyPurpose.REPORT):
        if store.active(purpose) is None:
            created.append(store.generate(purpose))
    for k in created:
        log.append(AuditEvent.KEY_CREATED, {"key_id": k.key_id, "purpose": k.purpose.value, "public_key": k.public_key})
    for purpose in KeyPurpose:
        k = store.require_active(purpose)
        typer.echo(f"{purpose.value:<10} {k.key_id}  {'(created)' if k in created else '(existing)'}")


@keys_app.command("list")
def keys_list() -> None:
    """List public keys, including retired ones (which still verify old data)."""
    store, _ = _stores()
    for k in store.all():
        typer.echo(f"{k.key_id:<32} {k.purpose.value:<10} created {k.created_at}  " + (f"retired {k.retired_at}" if k.retired_at else "active"))


@keys_app.command("rotate")
def keys_rotate(purpose: KeyPurpose = typer.Argument(..., help="inference | audit | report")) -> None:
    """Retire the active key for PURPOSE and create a replacement."""
    store, log = _stores()
    old, new = store.rotate(purpose)
    log.append(
        AuditEvent.KEY_ROTATED,
        {"purpose": purpose.value, "retired_key_id": old.key_id if old else None, "new_key_id": new.key_id, "public_key": new.public_key},
    )
    typer.echo(f"{purpose.value}: {old.key_id if old else '(none)'} -> {new.key_id}")


@audit_app.command("verify")
def audit_verify(
    file: Optional[Path] = typer.Option(None, "--file", help="Verify an exported JSONL file instead of the live log."),
    head: Optional[str] = typer.Option(None, "--head", help="Head hash from an earlier export/report; detects truncation."),
    count: Optional[int] = typer.Option(None, "--count", help="Entry count from an earlier export/report."),
) -> None:
    """Recompute the whole hash chain and signatures; report the first failing entry."""
    from aura.m5_governance.audit_log import verify_log_file

    store, log = _stores()
    result = verify_log_file(file or log.path, store, expected_head=head, expected_count=count)
    typer.echo(json.dumps(result.to_dict(), indent=2))
    raise typer.Exit(0 if result.valid else 1)


@app.command()
def serve(
    port: int = typer.Option(DEFAULT_PORT, "--port", help="Port on 127.0.0.1 (the host is fixed to loopback)."),
    reset: bool = typer.Option(False, "--reset", help="Delete the demo database and audit log and re-seed from scratch."),
) -> None:
    """Run the API + analyst UI on 127.0.0.1 (demo build, seeded with illustrative data)."""
    import uvicorn

    from aura.api.app import create_app

    s = get_settings()
    if reset:
        for p in (s.db_path, s.audit_log_path, s.audit_log_path.with_name(s.audit_log_path.name + ".lock")):
            if p.exists():
                p.unlink()
    typer.echo(f"AURA-CV {BIND_HOST}:{port}  (demo data: illustrative values, not measured results)")
    uvicorn.run(create_app(), host=BIND_HOST, port=port, log_level="warning")


@audit_app.command("head")
def audit_head() -> None:
    """Print the current head hash and entry count."""
    _, log = _stores()
    head_hash, n = log.head()
    typer.echo(json.dumps({"head_hash": head_hash, "entry_count": n}))


if __name__ == "__main__":
    app()
