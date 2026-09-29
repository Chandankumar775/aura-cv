import json

import pytest

from aura.core.types import KeyPurpose
from aura.m3_provenance import keys as keys_mod
from aura.m3_provenance.keys import (
    KeyStore,
    KeyStoreError,
    NoActiveKeyError,
    UnknownKeyError,
    b64decode,
    b64encode,
    permissions_are_restricted,
)


def test_generate_one_active_key_per_purpose(tmp_path):
    store = KeyStore(tmp_path / "keys")
    infos = {p: store.generate(p) for p in KeyPurpose}
    assert len({i.key_id for i in infos.values()}) == 3
    for purpose, info in infos.items():
        assert info.key_id.startswith(purpose.value + "-")
        assert store.active(purpose) == info
        assert len(b64decode(info.public_key)) == 32
    with pytest.raises(KeyStoreError):
        store.generate(KeyPurpose.AUDIT)


def test_sign_verify_roundtrip_and_tamper(tmp_path):
    store = KeyStore(tmp_path / "keys")
    store.generate(KeyPurpose.INFERENCE)
    key_id, sig = store.sign(KeyPurpose.INFERENCE, b"payload")
    assert sig.startswith("b64:")
    assert store.verify(key_id, b"payload", sig)
    assert not store.verify(key_id, b"payloaD", sig)
    assert not store.verify(key_id, b"payload", b64encode(b"\x00" * 64))
    assert not store.verify(key_id, b"payload", "b64:not-base64!!")


def test_purpose_binding(tmp_path):
    store = KeyStore(tmp_path / "keys")
    store.generate(KeyPurpose.REPORT)
    key_id, sig = store.sign(KeyPurpose.REPORT, b"x")
    assert store.verify(key_id, b"x", sig, purpose=KeyPurpose.REPORT)
    assert not store.verify(key_id, b"x", sig, purpose=KeyPurpose.AUDIT)


def test_unknown_key_raises(tmp_path):
    store = KeyStore(tmp_path / "keys")
    with pytest.raises(UnknownKeyError):
        store.verify("audit-20990101-deadbeef", b"x", "b64:AAAA")
    with pytest.raises(NoActiveKeyError):
        store.sign(KeyPurpose.AUDIT, b"x")


def test_rotation_retires_but_old_key_still_verifies(tmp_path):
    store = KeyStore(tmp_path / "keys")
    first = store.generate(KeyPurpose.AUDIT)
    _, old_sig = store.sign(KeyPurpose.AUDIT, b"old data")
    old, new = store.rotate(KeyPurpose.AUDIT)
    assert old is not None and old.key_id == first.key_id and old.retired_at is not None
    assert store.active(KeyPurpose.AUDIT) == new
    assert new.key_id != first.key_id
    assert store.verify(first.key_id, b"old data", old_sig)
    with pytest.raises(KeyStoreError):
        store.sign_with(first.key_id, b"new data")  # retired keys only verify
    assert [k.key_id for k in store.all()] == [first.key_id, new.key_id]


def test_registry_holds_no_private_material(tmp_path):
    store = KeyStore(tmp_path / "keys")
    info = store.generate(KeyPurpose.AUDIT)
    text = store.registry_path.read_text()
    assert "PRIVATE" not in text
    assert set(json.loads(text)["keys"][0]) == {"key_id", "purpose", "algorithm", "public_key", "created_at", "retired_at"}
    assert b"PRIVATE KEY" in store.private_key_path(info.key_id).read_bytes()
    assert "BEGIN PUBLIC KEY" in store.export_public_pem(info.key_id)


def test_private_key_permissions_restricted(tmp_path):
    store = KeyStore(tmp_path / "keys")
    info = store.generate(KeyPurpose.AUDIT)
    ok, detail = permissions_are_restricted(store.private_key_path(info.key_id))
    assert ok, detail


def test_never_overwrites_existing_private_key(tmp_path, monkeypatch):
    store = KeyStore(tmp_path / "keys")
    info = store.generate(KeyPurpose.AUDIT)
    before = store.private_key_path(info.key_id).read_bytes()
    # Force a key-id collision: the O_EXCL open must refuse to clobber the file.
    fingerprint = info.key_id.rsplit("-", 1)[1]
    monkeypatch.setattr(keys_mod, "parse_digest", lambda d: fingerprint + "0" * 56)
    with pytest.raises(FileExistsError):
        store.rotate(KeyPurpose.AUDIT)
    assert store.private_key_path(info.key_id).read_bytes() == before
