"""Audit chain: append, verify, and detection of edit / delete / reorder / truncate (R-GOV-2)."""

import json
import threading

import pytest

from aura.core.canonical import canonicalize
from aura.core.hashing import ZERO_DIGEST, sha256_bytes, sha256_canonical
from aura.core.types import Actor, AuditEvent, KeyPurpose
from aura.m5_governance.audit_log import AuditLog, AuditLogError, entry_body, verify_log_file


def _fill(log: AuditLog, n: int = 6) -> None:
    for i in range(n):
        log.append(AuditEvent.CHECK_STARTED, {"check_id": f"M1.dummy.{i}", "i": i})


def _lines(log: AuditLog) -> list[dict]:
    return [json.loads(line) for line in log.path.read_text(encoding="utf-8").splitlines()]


def _write(log: AuditLog, entries: list[dict]) -> None:
    log.path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")


def test_append_links_and_verifies(audit_log):
    _fill(audit_log)
    entries = _lines(audit_log)
    assert [e["index"] for e in entries] == list(range(6))
    assert entries[0]["prev_entry_hash"] == ZERO_DIGEST
    for prev, cur in zip(entries, entries[1:]):
        assert cur["prev_entry_hash"] == prev["entry_hash"]
    result = audit_log.verify()
    assert result.valid and result.entries_checked == 6
    assert audit_log.head() == (entries[-1]["entry_hash"], 6)


def test_entry_hash_is_canonical_body_digest(audit_log):
    e = audit_log.append(AuditEvent.SESSION_START, {"note": "héllo"}, Actor(type="user", id="usr_1"))
    raw = _lines(audit_log)[0]
    assert e.entry_hash == sha256_bytes(canonicalize(entry_body(raw)))
    assert e.payload_sha256 == sha256_canonical({"note": "héllo"})
    assert raw["actor"] == {"type": "user", "id": "usr_1"}


def test_empty_log_is_valid(audit_log):
    result = audit_log.verify()
    assert result.valid and result.entries_checked == 0 and result.head_hash == ZERO_DIGEST


def test_unknown_event_rejected(audit_log):
    with pytest.raises(ValueError):
        audit_log.append("DELETE_EVERYTHING", {})


def test_edit_payload_detected(audit_log):
    _fill(audit_log)
    entries = _lines(audit_log)
    entries[3]["payload"]["i"] = 999
    _write(audit_log, entries)
    r = audit_log.verify()
    assert not r.valid and r.first_failure_index == 3 and "payload" in r.failure_reason


def test_edit_with_recomputed_hashes_caught_by_signature(audit_log):
    """An attacker without the audit key re-hashes the edited entry and the rest of the chain."""
    _fill(audit_log)
    entries = _lines(audit_log)
    entries[2]["payload"]["i"] = 999
    entries[2]["payload_sha256"] = sha256_canonical(entries[2]["payload"])
    prev = entries[1]["entry_hash"]
    for e in entries[2:]:
        e["prev_entry_hash"] = prev
        e["entry_hash"] = sha256_bytes(canonicalize(entry_body(e)))
        prev = e["entry_hash"]
    _write(audit_log, entries)
    r = audit_log.verify()
    assert not r.valid and r.first_failure_index == 2 and "signature" in r.failure_reason


def test_edit_timestamp_detected(audit_log):
    _fill(audit_log)
    entries = _lines(audit_log)
    entries[4]["timestamp"] = "2000-01-01T00:00:00.000Z"
    _write(audit_log, entries)
    r = audit_log.verify()
    assert not r.valid and r.first_failure_index == 4


def test_delete_middle_entry_detected(audit_log):
    _fill(audit_log)
    entries = _lines(audit_log)
    del entries[2]
    _write(audit_log, entries)
    r = audit_log.verify()
    assert not r.valid and r.first_failure_index == 2 and "deleted" in r.failure_reason


def test_reorder_detected(audit_log):
    _fill(audit_log)
    entries = _lines(audit_log)
    entries[1], entries[2] = entries[2], entries[1]
    _write(audit_log, entries)
    r = audit_log.verify()
    assert not r.valid and r.first_failure_index == 1


def test_truncation_needs_and_uses_exported_head(audit_log):
    _fill(audit_log, 8)
    head, count = audit_log.head()
    _write(audit_log, _lines(audit_log)[:5])
    # The chain alone still verifies: this is exactly why heads are exported in reports.
    assert audit_log.verify().valid
    r = audit_log.verify(expected_head=head)
    assert not r.valid and r.first_failure_index == 5 and "truncated" in r.failure_reason
    r = audit_log.verify(expected_count=count)
    assert not r.valid and r.first_failure_index == 5


def test_older_head_still_matches_after_growth(audit_log):
    _fill(audit_log, 3)
    head, count = audit_log.head()
    _fill(audit_log, 3)
    assert audit_log.verify(expected_head=head, expected_count=count).valid


def test_entry_signed_with_non_audit_key_rejected(keystore, audit_log):
    _fill(audit_log, 2)
    entries = _lines(audit_log)
    body = entry_body(entries[1])
    report_key = keystore.require_active(KeyPurpose.REPORT)
    body["key_id"] = report_key.key_id
    data = canonicalize(body)
    entries[1] = {**body, "entry_hash": sha256_bytes(data), "signature": keystore.sign_with(report_key.key_id, data)}
    _write(audit_log, entries)
    r = audit_log.verify()
    assert not r.valid and r.first_failure_index == 1 and "audit key" in r.failure_reason


def test_unknown_signing_key_rejected(audit_log):
    _fill(audit_log, 2)
    entries = _lines(audit_log)
    entries[0]["key_id"] = "audit-20990101-00000000"
    _write(audit_log, entries)
    r = audit_log.verify()
    assert not r.valid and r.first_failure_index == 0


def test_verification_survives_audit_key_rotation(keystore, audit_log):
    _fill(audit_log, 3)
    keystore.rotate(KeyPurpose.AUDIT)
    _fill(audit_log, 3)
    key_ids = {e["key_id"] for e in _lines(audit_log)}
    assert len(key_ids) == 2 and audit_log.verify().valid


def test_refuses_to_extend_corrupt_tail(audit_log):
    _fill(audit_log, 2)
    with open(audit_log.path, "a", encoding="utf-8") as fh:
        fh.write('{"index": 2, "trunc')
    with pytest.raises(AuditLogError):
        audit_log.append(AuditEvent.SESSION_END, {})


def test_non_canonical_payload_rejected(audit_log):
    with pytest.raises(AuditLogError):
        audit_log.append(AuditEvent.SESSION_START, {"x": float("nan")})


def test_concurrent_appends_keep_one_chain(audit_log):
    def worker(t: int) -> None:
        for i in range(25):
            audit_log.append(AuditEvent.CHECK_COMPLETED, {"t": t, "i": i})

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    r = audit_log.verify()
    assert r.valid and r.entries_checked == 100


def test_second_instance_on_same_file_continues_chain(keystore, audit_log):
    _fill(audit_log, 2)
    AuditLog(audit_log.path, keystore).append(AuditEvent.SESSION_END, {})
    r = audit_log.verify()
    assert r.valid and r.entries_checked == 3


def test_verify_exported_copy(tmp_path, keystore, audit_log):
    _fill(audit_log, 4)
    head, count = audit_log.head()
    copy = tmp_path / "export.jsonl"
    copy.write_bytes(audit_log.path.read_bytes())
    assert verify_log_file(copy, keystore, expected_head=head, expected_count=count).valid
