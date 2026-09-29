"""Prefixed identifiers and UTC timestamps (CLAUDE.md A11.1).

Two kinds of id exist:
  * ``new_id`` - random, for things that are created once (users, assessments, jobs);
  * ``derived_id`` - a digest of stable parts, for things that must come out identical
    when the same inputs are assessed with the same seed (findings, A3 rule 10).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

ID_PREFIXES = frozenset(
    {"usr", "ds", "mdl", "rs", "ib", "ref", "asm", "fnd", "dec", "art", "rep", "atk", "evl", "job"}
)

TIMESTAMP_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$"


def _check_prefix(prefix: str) -> None:
    if prefix not in ID_PREFIXES:
        raise ValueError(f"unknown id prefix {prefix!r}; expected one of {sorted(ID_PREFIXES)}")


def new_id(prefix: str) -> str:
    _check_prefix(prefix)
    return f"{prefix}_{secrets.token_hex(8)}"


def derived_id(prefix: str, *parts: object) -> str:
    """Deterministic id from ``parts``; parts are joined unambiguously before hashing."""
    _check_prefix(prefix)
    h = hashlib.sha256()
    for part in parts:
        encoded = str(part).encode("utf-8")
        h.update(len(encoded).to_bytes(8, "big"))
        h.update(encoded)
    return f"{prefix}_{h.hexdigest()[:16]}"


def format_ts(dt: datetime) -> str:
    """UTC ISO-8601 with millisecond precision and a ``Z`` suffix."""
    if dt.tzinfo is None:
        raise ValueError("naive datetimes are ambiguous; pass a timezone-aware datetime")
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def utc_now() -> str:
    return format_ts(datetime.now(timezone.utc))


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))
