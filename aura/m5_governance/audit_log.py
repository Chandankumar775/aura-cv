"""Append-only, hash-chained, signed audit log (R-GOV-2, R-DEL-4; design.md §10.5, §14.3).

Each line of the JSONL file is one ``AuditEntry``:

    body       = entry without ``entry_hash`` and ``signature``
    entry_hash = SHA-256(RFC8785(body))
    signature  = Ed25519(audit_key, RFC8785(body))
    body.prev_entry_hash = entry_hash of the previous line (ZERO_DIGEST for index 0)

What this detects (tamper-*evident*, not tamper-proof):
  * editing any field of any entry           -> hash / signature mismatch at that index
  * deleting or reordering entries           -> index gap / broken prev_entry_hash link
  * rewriting entries and re-hashing them    -> signature failure (needs the audit key)
  * truncating the tail                      -> only against a previously exported head
                                                hash (a chain alone cannot see it), so
                                                ``verify(expected_head=...)`` is provided
What it does not detect: an attacker holding the audit private key rewriting the log
from scratch (a stated assumption, design.md §4.2).

Appends are serialised with an in-process lock *and* a cross-process lock file, and the
tail is re-read under the lock, so the CLI and the API server can share one log without
forking the chain. The DB mirror required by A8.5 is added with storage in Milestone M2.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aura import TOOL_NAME, __version__
from aura.core.canonical import CanonicalizationError, canonicalize
from aura.core.hashing import ZERO_DIGEST, sha256_bytes, sha256_canonical
from aura.core.ids import parse_ts, utc_now
from aura.core.types import Actor, AuditEntry, AuditEvent, KeyPurpose
from aura.m3_provenance.keys import KeyStore, UnknownKeyError

SYSTEM_ACTOR = Actor(type="system", id=f"{TOOL_NAME.lower()}/{__version__}")


class AuditLogError(Exception):
    pass


@dataclass
class AuditVerification:
    """Result of a full chain verification (shape used by ``POST /audit/verify``)."""

    valid: bool
    entries_checked: int
    head_hash: str
    first_failure_index: int | None = None
    failure_reason: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "entries_checked": self.entries_checked,
            "head_hash": self.head_hash,
            "first_failure_index": self.first_failure_index,
            "failure_reason": self.failure_reason,
            "warnings": list(self.warnings),
        }


def entry_body(entry: dict[str, Any]) -> dict[str, Any]:
    """The hashed/signed part of an entry: everything except entry_hash and signature."""
    return {k: v for k, v in entry.items() if k not in ("entry_hash", "signature")}


# ------------------------------------------------------------ cross-process lock


@contextmanager
def _file_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as fh:
        if sys.platform == "win32":
            import msvcrt

            fh.seek(0)
            while True:
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:  # LK_LOCK gives up after ~10 s; keep waiting
                    continue
            try:
                yield
            finally:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _read_last_line(path: Path) -> str | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        pos = fh.tell()
        buf = b""
        while pos > 0:
            step = min(4096, pos)
            pos -= step
            fh.seek(pos)
            buf = fh.read(step) + buf
            stripped = buf.rstrip(b"\n")
            if b"\n" in stripped:
                return stripped.rsplit(b"\n", 1)[1].decode("utf-8")
        return buf.rstrip(b"\n").decode("utf-8") or None


# --------------------------------------------------------------------- the log


class AuditLog:
    def __init__(self, path: str | Path, keystore: KeyStore, fsync: bool = True):
        self.path = Path(path)
        self.keystore = keystore
        self.fsync = fsync
        self._lock = threading.Lock()
        # (file size, next index, head hash) after our own last write. Re-read the tail only
        # when the size changed, i.e. another process appended in the meantime.
        self._tail_cache: tuple[int, int, str] | None = None

    @property
    def _lock_path(self) -> Path:
        return self.path.with_name(self.path.name + ".lock")

    def _tail(self) -> tuple[int, str]:
        """(next index, prev hash) from the last line; refuses to extend a corrupt tail."""
        size = self.path.stat().st_size if self.path.exists() else 0
        if self._tail_cache and self._tail_cache[0] == size:
            return self._tail_cache[1], self._tail_cache[2]
        line = _read_last_line(self.path)
        if line is None:
            return 0, ZERO_DIGEST
        try:
            last = json.loads(line)
            return int(last["index"]) + 1, str(last["entry_hash"])
        except (ValueError, KeyError, TypeError) as exc:
            raise AuditLogError(
                "the last audit entry is unreadable; refusing to extend a damaged log "
                "(run 'aura audit verify')"
            ) from exc

    def append(self, event: AuditEvent | str, payload: dict[str, Any] | None = None, actor: Actor | None = None) -> AuditEntry:
        """Append one signed entry. Every state-changing action calls this (A3 rule 6)."""
        event = AuditEvent(event)  # rejects events outside the A8.5 vocabulary
        payload = dict(payload or {})
        try:
            payload_digest = sha256_canonical(payload)
        except CanonicalizationError as exc:
            raise AuditLogError(f"audit payload is not canonical JSON: {exc}") from exc
        actor = actor or SYSTEM_ACTOR
        key = self.keystore.require_active(KeyPurpose.AUDIT)

        with self._lock, _file_lock(self._lock_path):
            index, prev_hash = self._tail()
            body = {
                "index": index,
                "timestamp": utc_now(),
                "actor": actor.model_dump(mode="json"),
                "event": event.value,
                "payload": payload,
                "payload_sha256": payload_digest,
                "prev_entry_hash": prev_hash,
                "key_id": key.key_id,
            }
            data = canonicalize(body)
            signature = self.keystore.sign_with(key.key_id, data)
            entry = AuditEntry.model_validate({**body, "entry_hash": sha256_bytes(data), "signature": signature})
            line = json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(line + "\n")
                fh.flush()
                if self.fsync:
                    os.fsync(fh.fileno())
            self._tail_cache = (self.path.stat().st_size, entry.index + 1, entry.entry_hash)
        return entry

    def head(self) -> tuple[str, int]:
        """(head hash, entry count). The head hash is embedded in every exported report."""
        index, prev = self._tail()
        return prev, index

    def entries(self) -> Iterator[AuditEntry]:
        if not self.path.exists():
            return
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield AuditEntry.model_validate_json(line)

    def verify(self, expected_head: str | None = None, expected_count: int | None = None) -> AuditVerification:
        return verify_log_file(self.path, self.keystore, expected_head, expected_count)


def verify_log_file(
    path: str | Path,
    keystore: KeyStore,
    expected_head: str | None = None,
    expected_count: int | None = None,
) -> AuditVerification:
    """Recompute the whole chain and stop at the first failing entry.

    ``expected_head``/``expected_count`` come from a previously exported report or
    audit export; they are the only way to detect truncation of the tail.
    """
    path = Path(path)
    prev_hash = ZERO_DIGEST
    prev_ts = None
    seen_hashes: set[str] = set()
    warnings: list[str] = []
    checked = 0

    def fail(index: int, reason: str) -> AuditVerification:
        return AuditVerification(False, checked, prev_hash, index, reason, warnings)

    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for i, line in enumerate(lines):
        if not line.strip():
            return fail(i, f"line {i + 1} is blank; the log has been edited")
        try:
            raw = json.loads(line)
            entry = AuditEntry.model_validate(raw)
        except (ValueError, ValidationError) as exc:
            return fail(i, f"entry is not a valid audit entry: {str(exc).splitlines()[0]}")
        if entry.index != i:
            return fail(i, f"expected index {i} but found {entry.index}: entries were deleted, inserted or reordered")
        if entry.prev_entry_hash != prev_hash:
            return fail(i, "prev_entry_hash does not match the previous entry: the chain is broken")
        if sha256_canonical(raw["payload"]) != entry.payload_sha256:
            return fail(i, "payload does not match payload_sha256: the payload was altered")
        body_bytes = canonicalize(entry_body(raw))
        if sha256_bytes(body_bytes) != entry.entry_hash:
            return fail(i, "entry_hash does not match the entry contents: the entry was altered")
        try:
            sig_ok = keystore.verify(entry.key_id, body_bytes, entry.signature, purpose=KeyPurpose.AUDIT)
        except UnknownKeyError:
            return fail(i, f"entry is signed with unknown key {entry.key_id!r}")
        if not sig_ok:
            return fail(i, "signature is not valid for this entry under an audit key")
        ts = parse_ts(entry.timestamp)
        if prev_ts is not None and ts < prev_ts:
            warnings.append(f"entry {i} has a timestamp earlier than entry {i - 1} (clock change?)")
        prev_ts = ts
        prev_hash = entry.entry_hash
        seen_hashes.add(entry.entry_hash)
        checked += 1

    if expected_count is not None and checked < expected_count:
        return fail(checked, f"log has {checked} entries but {expected_count} were exported earlier: the tail was truncated")
    if expected_head is not None and expected_head != ZERO_DIGEST and expected_head not in seen_hashes:
        return fail(checked, "the expected head hash is not in the log: the log was truncated or rewritten")
    return AuditVerification(True, checked, prev_hash, None, None, warnings)
