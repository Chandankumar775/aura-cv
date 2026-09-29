"""SHA-256 helpers and the ``sha256:<64 lowercase hex>`` digest format.

Every digest AURA-CV stores or prints uses this one format (CLAUDE.md A11.1), so
digests from datasets, models, records, audit entries and reports can be compared
as plain strings. Supports R-INF-1 (binding), R-GOV-2 (audit chain) and R-DEL-4.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, BinaryIO

from aura.core.canonical import canonicalize

DIGEST_PREFIX = "sha256:"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
# Genesis value for hash chains (audit log, record streams): an all-zero digest.
ZERO_DIGEST = DIGEST_PREFIX + "0" * 64

_CHUNK = 1024 * 1024


def format_digest(hex_digest: str) -> str:
    """Wrap a raw hex digest in the canonical ``sha256:`` format."""
    hex_digest = hex_digest.lower()
    digest = DIGEST_PREFIX + hex_digest
    if not DIGEST_RE.match(digest):
        raise ValueError(f"not a SHA-256 hex digest: {hex_digest!r}")
    return digest


def is_digest(value: object) -> bool:
    return isinstance(value, str) and DIGEST_RE.match(value) is not None


def parse_digest(digest: str) -> str:
    """Return the 64-char hex part of a ``sha256:`` digest, rejecting anything else."""
    if not is_digest(digest):
        raise ValueError(f"malformed digest (expected sha256:<64 lowercase hex>): {digest!r}")
    return digest[len(DIGEST_PREFIX):]


def sha256_bytes(data: bytes) -> str:
    return format_digest(hashlib.sha256(data).hexdigest())


def sha256_stream(stream: BinaryIO) -> str:
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(_CHUNK), b""):
        h.update(chunk)
    return format_digest(h.hexdigest())


def sha256_file(path: str | Path) -> str:
    """Stream a file from disk so large weight files are never loaded whole."""
    with open(path, "rb") as fh:
        return sha256_stream(fh)


def sha256_canonical(obj: Any) -> str:
    """Digest of the RFC 8785 canonical JSON form of ``obj``."""
    return sha256_bytes(canonicalize(obj))


def short_digest(digest: str, n: int = 12) -> str:
    """Human-readable abbreviation for logs and UI; never use for comparison."""
    return parse_digest(digest)[:n]
