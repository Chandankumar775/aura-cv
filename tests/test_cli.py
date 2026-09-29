"""CLI: ``aura keys init`` and ``aura selfcheck --offline``."""

import json
import os
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from aura.cli import app
from aura.config import get_settings
from aura.core import netguard, selfcheck
from aura.m3_provenance.keys import KeyStore

runner = CliRunner()


@pytest.fixture
def airgapped(monkeypatch):
    """Simulate an isolated host with the guard active (the suite itself blocks sockets)."""
    monkeypatch.setattr(selfcheck.netguard, "route_exists", lambda: (False, "no route (simulated)"))
    monkeypatch.setattr(selfcheck.netguard, "guard_blocks_outbound", lambda: True)


def test_keys_init_creates_three_keys_and_audits(aura_home):
    result = runner.invoke(app, ["keys", "init"])
    assert result.exit_code == 0, result.output
    assert result.output.count("(created)") == 3
    store = KeyStore(get_settings().keys_dir)
    assert len(store.all()) == 3
    lines = get_settings().audit_log_path.read_text().splitlines()
    assert [json.loads(l)["event"] for l in lines] == ["KEY_CREATED"] * 3

    again = runner.invoke(app, ["keys", "init"])
    assert again.exit_code == 0 and again.output.count("(existing)") == 3
    assert len(get_settings().audit_log_path.read_text().splitlines()) == 3


def test_keys_rotate_and_list(aura_home):
    runner.invoke(app, ["keys", "init"])
    result = runner.invoke(app, ["keys", "rotate", "audit"])
    assert result.exit_code == 0, result.output
    listing = runner.invoke(app, ["keys", "list"]).output
    assert "retired" in listing and listing.count("active") == 3
    verify = runner.invoke(app, ["audit", "verify"])
    assert verify.exit_code == 0 and json.loads(verify.output)["valid"]


def test_selfcheck_fails_before_keys_and_passes_after(aura_home, airgapped):
    before = runner.invoke(app, ["selfcheck", "--offline"])
    assert before.exit_code == 1 and "[FAIL] keys.present" in before.output

    runner.invoke(app, ["keys", "init"])
    after = runner.invoke(app, ["selfcheck", "--offline", "--json"])
    assert after.exit_code == 0, after.output
    report = json.loads(after.output)
    states = {i["id"]: i["state"] for i in report["items"]}
    assert report["passed"] and states["network.isolation"] == "PASS" and states["audit.chain"] == "PASS"
    assert set(states) >= {"python.version", "network.guard", "network.isolation", "crypto.selftest", "keys.present", "audit.chain", "schemas.present"}


def test_selfcheck_offline_flag_turns_route_into_failure(aura_home, monkeypatch):
    monkeypatch.setattr(selfcheck.netguard, "route_exists", lambda: (True, "route via 10.0.0.5"))
    monkeypatch.setattr(selfcheck.netguard, "guard_blocks_outbound", lambda: True)
    runner.invoke(app, ["keys", "init"])
    assert runner.invoke(app, ["selfcheck"]).exit_code == 0  # warning only
    strict = runner.invoke(app, ["selfcheck", "--offline"])
    assert strict.exit_code == 1 and "[FAIL] network.isolation" in strict.output


def test_selfcheck_detects_broken_audit_chain(aura_home, airgapped):
    runner.invoke(app, ["keys", "init"])
    path = get_settings().audit_log_path
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0], lines[2]]) + "\n")
    result = runner.invoke(app, ["selfcheck"])
    assert result.exit_code == 1 and "[FAIL] audit.chain" in result.output


def test_audit_verify_detects_truncation_against_head(aura_home):
    runner.invoke(app, ["keys", "init"])
    head = json.loads(runner.invoke(app, ["audit", "head"]).output)["head_hash"]
    path = get_settings().audit_log_path
    path.write_text(path.read_text().splitlines()[0] + "\n")
    result = runner.invoke(app, ["audit", "verify", "--head", head])
    assert result.exit_code == 1 and "truncated" in json.loads(result.output)["failure_reason"]


def test_guard_blocks_in_a_real_process(tmp_path):
    """Run the guard in a fresh interpreter (pytest-socket owns sockets in this one)."""
    code = (
        "import socket\n"
        "from aura.core import netguard\n"
        "netguard.install()\n"
        "assert netguard.guard_blocks_outbound()\n"
        "for fn in (lambda: socket.create_connection(('192.0.2.1', 80), timeout=1),\n"
        "           lambda: socket.getaddrinfo('example.com', 443),\n"
        "           lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'x', ('192.0.2.1', 9))):\n"
        "    try:\n"
        "        fn()\n"
        "        raise SystemExit('not blocked')\n"
        "    except netguard.OutboundNetworkBlocked:\n"
        "        pass\n"
        "srv = socket.socket(); srv.bind(('127.0.0.1', 0)); srv.listen(1)\n"
        "c = socket.create_connection(srv.getsockname(), timeout=2)\n"  # loopback still works
        "c.close(); srv.close(); print('ok')\n"
    )
    env = {**os.environ, "AURA_HOME": str(tmp_path)}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr


def test_is_local_host():
    for h in ["127.0.0.1", "127.8.9.1", "::1", "[::1]", "localhost", b"localhost", None]:
        assert netguard.is_local_host(h)
    for h in ["192.0.2.1", "10.0.0.1", "example.com", "0.0.0.1", "8.8.8.8"]:
        assert not netguard.is_local_host(h)
