"""Start-up self-check (CLAUDE.md A11.2 ``/system/selfcheck``, A14.2 criterion 1).

Each item returns PASS / WARN / FAIL with a plain explanation. Items are added as the
milestones that own them land (bundled weights and battery in M2/M5, DB in M2, PDF
renderer in M7). Shared by ``aura selfcheck`` and, later, the API.
"""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from enum import Enum

from aura.config import MIN_PYTHON, Settings, get_settings
from aura.core import netguard
from aura.core.canonical import canonicalize
from aura.core.types import KeyPurpose


class CheckState(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class SelfCheckItem:
    id: str
    state: CheckState
    detail: str

    def to_dict(self) -> dict[str, str]:
        d = asdict(self)
        d["state"] = self.state.value
        return d


def _python() -> SelfCheckItem:
    v = sys.version_info
    ok = (v.major, v.minor) >= MIN_PYTHON
    return SelfCheckItem(
        "python.version",
        CheckState.PASS if ok else CheckState.FAIL,
        f"Python {v.major}.{v.minor}.{v.micro} (need >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})",
    )


def _guard() -> SelfCheckItem:
    if netguard.guard_blocks_outbound():
        return SelfCheckItem("network.guard", CheckState.PASS, "in-process guard refuses non-loopback connections and DNS lookups")
    return SelfCheckItem("network.guard", CheckState.FAIL, "outbound network guard is not installed in this process")


def _isolation(require_offline: bool) -> SelfCheckItem:
    has_route, detail = netguard.route_exists()
    if not has_route:
        return SelfCheckItem("network.isolation", CheckState.PASS, f"air-gapped: {detail}")
    state = CheckState.FAIL if require_offline else CheckState.WARN
    return SelfCheckItem(
        "network.isolation",
        state,
        f"{detail}; disable networking for air-gapped operation (AURA-CV itself makes no outbound calls)",
    )


def _crypto() -> SelfCheckItem:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    try:
        # RFC 8785 §3.2.2 numbers example, plus an Ed25519 round-trip on a throwaway key.
        vector = canonicalize({"n": [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27]})
        assert vector == b'{"n":[333333333.3333333,1e+30,4.5,0.002,1e-27]}', vector
        key = Ed25519PrivateKey.generate()
        key.public_key().verify(key.sign(vector), vector)
    except Exception as exc:
        return SelfCheckItem("crypto.selftest", CheckState.FAIL, f"canonical JSON / Ed25519 self-test failed: {exc}")
    return SelfCheckItem("crypto.selftest", CheckState.PASS, "RFC 8785 vector and Ed25519 sign/verify OK")


def _keys(settings: Settings) -> list[SelfCheckItem]:
    from aura.m3_provenance.keys import KeyStore, permissions_are_restricted

    store = KeyStore(settings.keys_dir)
    missing = [p.value for p in KeyPurpose if store.active(p) is None]
    items = [
        SelfCheckItem(
            "keys.present",
            CheckState.FAIL if missing else CheckState.PASS,
            f"no active key for: {', '.join(missing)} (run 'aura keys init')" if missing else "inference, audit and report keys active",
        )
    ]
    bad = []
    for k in store.all():
        path = store.private_key_path(k.key_id)
        if path.exists():
            ok, why = permissions_are_restricted(path)
            if not ok:
                bad.append(f"{k.key_id}: {why}")
    if store.all():
        items.append(
            SelfCheckItem(
                "keys.permissions",
                CheckState.WARN if bad else CheckState.PASS,
                "; ".join(bad) if bad else "private key files are owner-only",
            )
        )
    return items


def _audit(settings: Settings) -> SelfCheckItem:
    from aura.m3_provenance.keys import KeyStore
    from aura.m5_governance.audit_log import verify_log_file

    path = settings.audit_log_path
    if not path.exists():
        return SelfCheckItem("audit.chain", CheckState.PASS, "audit log is empty (no entries yet)")
    result = verify_log_file(path, KeyStore(settings.keys_dir))
    if result.valid:
        return SelfCheckItem("audit.chain", CheckState.PASS, f"{result.entries_checked} entries verified; head {result.head_hash}")
    return SelfCheckItem(
        "audit.chain",
        CheckState.FAIL,
        f"verification failed at entry {result.first_failure_index}: {result.failure_reason}",
    )


def _schemas(settings: Settings) -> SelfCheckItem:
    from aura.core.schemas import _validator, schema_path

    try:
        _validator(str(schema_path("finding")))
    except Exception as exc:
        return SelfCheckItem("schemas.present", CheckState.FAIL, f"finding schema unusable: {exc}")
    return SelfCheckItem("schemas.present", CheckState.PASS, f"finding schema loaded from {settings.schema_dir}")


def run_selfcheck(require_offline: bool = False, settings: Settings | None = None) -> list[SelfCheckItem]:
    settings = settings or get_settings()
    return [
        _python(),
        _guard(),
        _isolation(require_offline),
        _crypto(),
        *_keys(settings),
        _audit(settings),
        _schemas(settings),
    ]


def passed(items: list[SelfCheckItem]) -> bool:
    return all(i.state is not CheckState.FAIL for i in items)
