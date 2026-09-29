"""Local Ed25519 key management (CLAUDE.md A8.3, design.md §8.6).

* One active key per purpose (inference, audit, report), so compromise of one
  purpose does not let an attacker forge the others.
* Private keys are PKCS#8 PEM files under ``keys/`` with owner-only permissions.
  They never leave that directory and never appear in the registry.
* The public registry (``keys/registry.json``) lists every key ever created,
  including retired ones: rotation retires a key for *signing* but it still
  *verifies* data signed before rotation.

Assumption (design.md §4.2): the keys directory lives in the trusted environment.
Hardware-backed storage (TPM/HSM) is out of scope for the hackathon build (A18).
"""

from __future__ import annotations

import base64
import getpass
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from aura.core.hashing import sha256_bytes, parse_digest
from aura.core.ids import utc_now
from aura.core.types import KeyInfo, KeyPurpose

B64_PREFIX = "b64:"
REGISTRY_NAME = "registry.json"


class KeyStoreError(Exception):
    """Base class for key-store errors."""


class UnknownKeyError(KeyStoreError):
    """A signature names a key_id that is not in the registry: never trust it."""


class NoActiveKeyError(KeyStoreError):
    """No active key exists for the requested purpose (run ``aura keys init``)."""


# ------------------------------------------------------------------ encodings


def b64encode(data: bytes) -> str:
    return B64_PREFIX + base64.b64encode(data).decode("ascii")


def b64decode(text: str) -> bytes:
    if not text.startswith(B64_PREFIX):
        raise ValueError(f"expected '{B64_PREFIX}' prefix")
    return base64.b64decode(text[len(B64_PREFIX):], validate=True)


def _raw_public(pub: Ed25519PublicKey) -> bytes:
    return pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


# --------------------------------------------------------------- permissions


def restrict_permissions(path: Path) -> bool:
    """Make ``path`` readable/writable by the current user only. Returns success.

    POSIX: chmod 600 (files) / 700 (directories). Windows: POSIX modes only toggle
    the read-only flag, so the ACL is reset with ``icacls`` to grant the current
    user full control and remove inherited entries.
    """
    try:
        if sys.platform == "win32":
            user = getpass.getuser()
            result = subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        os.chmod(path, 0o700 if path.is_dir() else 0o600)
        return True
    except OSError:
        return False


def permissions_are_restricted(path: Path) -> tuple[bool, str]:
    """Best-effort check used by ``aura selfcheck``."""
    if sys.platform == "win32":
        try:
            out = subprocess.run(["icacls", str(path)], capture_output=True, text=True, check=False).stdout
        except OSError as exc:
            return False, f"could not run icacls: {exc}"
        user = getpass.getuser().lower()
        aces = [line.strip() for line in out.splitlines() if ":(" in line]
        # First line carries the path prefix; strip it so only the principal remains.
        principals = [ace.replace(str(path), "").strip().split(":(")[0].lower() for ace in aces]
        others = [p for p in principals if not p.endswith("\\" + user) and p != user]
        if not principals:
            return False, "no ACL entries could be read"
        if others:
            return False, f"other principals have access: {', '.join(sorted(set(others)))}"
        return True, "owner-only ACL"
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        return False, f"mode {oct(mode)} grants group/other access"
    return True, f"mode {oct(mode)}"


# ----------------------------------------------------------------- key store


class KeyStore:
    """File-backed Ed25519 key store. Thread-safe within one process."""

    def __init__(self, keys_dir: str | Path):
        self.dir = Path(keys_dir)
        self._lock = threading.RLock()

    # -- registry -------------------------------------------------------------

    @property
    def registry_path(self) -> Path:
        return self.dir / REGISTRY_NAME

    def _load_registry(self) -> list[KeyInfo]:
        if not self.registry_path.exists():
            return []
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return [KeyInfo.model_validate(k) for k in data.get("keys", [])]

    def _save_registry(self, keys: list[KeyInfo]) -> None:
        tmp = self.registry_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps({"keys": [k.model_dump(mode="json") for k in keys]}, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self.registry_path)

    def _ensure_dir(self) -> None:
        if not self.dir.exists():
            self.dir.mkdir(parents=True)
            restrict_permissions(self.dir)

    def all(self) -> list[KeyInfo]:
        with self._lock:
            return self._load_registry()

    def get(self, key_id: str) -> KeyInfo:
        for k in self.all():
            if k.key_id == key_id:
                return k
        raise UnknownKeyError(f"unknown key_id {key_id!r}")

    def active(self, purpose: KeyPurpose) -> KeyInfo | None:
        for k in self.all():
            if k.purpose == purpose and k.active:
                return k
        return None

    def require_active(self, purpose: KeyPurpose) -> KeyInfo:
        key = self.active(purpose)
        if key is None:
            raise NoActiveKeyError(f"no active {purpose.value} key; run 'aura keys init'")
        return key

    # -- lifecycle ------------------------------------------------------------

    def private_key_path(self, key_id: str) -> Path:
        return self.dir / f"{key_id}.pem"

    def generate(self, purpose: KeyPurpose) -> KeyInfo:
        """Create a new key. Refuses if an active key for ``purpose`` already exists."""
        with self._lock:
            self._ensure_dir()
            keys = self._load_registry()
            if any(k.purpose == purpose and k.active for k in keys):
                raise KeyStoreError(f"an active {purpose.value} key already exists; rotate it instead")
            return self._create(purpose, keys)

    def _create(self, purpose: KeyPurpose, keys: list[KeyInfo]) -> KeyInfo:
        private = Ed25519PrivateKey.generate()
        raw_pub = _raw_public(private.public_key())
        fingerprint = parse_digest(sha256_bytes(raw_pub))[:8]
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        key_id = f"{purpose.value}-{date}-{fingerprint}"
        pem = private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        path = self.private_key_path(key_id)
        # O_EXCL: never overwrite an existing private key file.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(pem)
        restrict_permissions(path)
        info = KeyInfo(key_id=key_id, purpose=purpose, public_key=b64encode(raw_pub), created_at=utc_now())
        keys.append(info)
        self._save_registry(keys)
        return info

    def rotate(self, purpose: KeyPurpose) -> tuple[KeyInfo | None, KeyInfo]:
        """Retire the active key for ``purpose`` (if any) and create its replacement."""
        with self._lock:
            self._ensure_dir()
            keys = self._load_registry()
            old: KeyInfo | None = None
            now = utc_now()
            for i, k in enumerate(keys):
                if k.purpose == purpose and k.active:
                    old = k.model_copy(update={"retired_at": now})
                    keys[i] = old
            new = self._create(purpose, keys)
            return old, new

    # -- signing / verification ----------------------------------------------

    def _load_private(self, key_id: str) -> Ed25519PrivateKey:
        pem = self.private_key_path(key_id).read_bytes()
        key = serialization.load_pem_private_key(pem, password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise KeyStoreError(f"{key_id} is not an Ed25519 private key")
        return key

    def sign(self, purpose: KeyPurpose, data: bytes) -> tuple[str, str]:
        """Sign with the active key for ``purpose``. Returns ``(key_id, "b64:<sig>")``."""
        info = self.require_active(purpose)
        return info.key_id, self.sign_with(info.key_id, data)

    def sign_with(self, key_id: str, data: bytes) -> str:
        """Sign with a specific key. Retired keys are refused: they only verify."""
        if not self.get(key_id).active:
            raise KeyStoreError(f"{key_id} is retired and may no longer sign")
        return b64encode(self._load_private(key_id).sign(data))

    def public_key(self, key_id: str) -> Ed25519PublicKey:
        return Ed25519PublicKey.from_public_bytes(b64decode(self.get(key_id).public_key))

    def verify(self, key_id: str, data: bytes, signature: str, purpose: KeyPurpose | None = None) -> bool:
        """True iff ``signature`` is valid for ``data`` under ``key_id``.

        Raises ``UnknownKeyError`` for keys not in the registry, so callers can map
        that case to UNVERIFIABLE rather than to a plain failure (A8.3). If
        ``purpose`` is given, a key registered for a different purpose never
        verifies (a report key must not be able to sign audit entries).
        """
        info = self.get(key_id)
        if purpose is not None and info.purpose != purpose:
            return False
        try:
            sig = b64decode(signature)
            self.public_key(key_id).verify(sig, data)
            return True
        except (InvalidSignature, ValueError):
            return False

    def export_public_pem(self, key_id: str) -> str:
        return (
            self.public_key(key_id)
            .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
            .decode("ascii")
        )
