"""Shared fixtures.

Sockets: pyproject's ``addopts`` runs the whole suite under pytest-socket with only
loopback hosts allowed (A3 rule 1). ``test_offline.py`` asserts that this is in force.
State: every test that touches keys or the audit log gets its own AURA_HOME.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aura.config import get_settings
from aura.m3_provenance.keys import KeyStore
from aura.m5_governance.audit_log import AuditLog
from aura.core.types import KeyPurpose


@pytest.fixture
def aura_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "aura_home"
    home.mkdir()
    monkeypatch.setenv("AURA_HOME", str(home))
    return home


@pytest.fixture
def keystore(aura_home: Path) -> KeyStore:
    store = KeyStore(get_settings().keys_dir)
    for purpose in KeyPurpose:
        store.generate(purpose)
    return store


@pytest.fixture
def audit_log(keystore: KeyStore) -> AuditLog:
    return AuditLog(get_settings().audit_log_path, keystore)
