"""Settings, filesystem layout and policy defaults.

All runtime state lives under one home directory (default: the repository root) so
that an air-gapped install is a single folder. ``AURA_HOME`` overrides it; tests
point it at a temporary directory. Settings are re-read on every call to
``get_settings()`` so an override takes effect immediately.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The API server binds to loopback only (R-CON-1, A11.1). Not configurable on purpose.
BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

MIN_PYTHON = (3, 10)

# Hosted demo (e.g. Vercel serverless). The real product is air-gapped; a hosted build is
# a public demonstration and says so in the UI. Storage is ephemeral (/tmp) there.
_HOST_SIGNALS = ("AURA_HOSTED", "VERCEL", "VERCEL_ENV", "VERCEL_URL", "NOW_REGION", "AWS_LAMBDA_FUNCTION_NAME", "LAMBDA_TASK_ROOT")


def _repo_writable() -> bool:
    try:
        probe = REPO_ROOT / ".aura-write-probe"
        probe.write_text("")
        probe.unlink()
        return True
    except OSError:
        return False


HOSTED = any(os.environ.get(k) for k in _HOST_SIGNALS) or not _repo_writable()


@dataclass(frozen=True)
class Settings:
    home: Path
    schema_dir: Path = REPO_ROOT / "schemas"
    assets_dir: Path = REPO_ROOT / "assets"
    extra_data_roots: tuple[Path, ...] = field(default_factory=tuple)

    @property
    def data_dir(self) -> Path:
        return self.home / "data"

    @property
    def keys_dir(self) -> Path:
        return self.home / "keys"

    @property
    def audit_log_path(self) -> Path:
        return self.data_dir / "audit" / "audit_log.jsonl"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "aura.db"

    @property
    def artefacts_dir(self) -> Path:
        return self.data_dir / "artefacts"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def data_roots(self) -> tuple[Path, ...]:
        """Directories inside which assets may be registered by local path (A10)."""
        return (self.data_dir, *self.extra_data_roots)


def get_settings() -> Settings:
    default_home = Path("/tmp/aura") if HOSTED and "AURA_HOME" not in os.environ else REPO_ROOT
    home = Path(os.environ.get("AURA_HOME", default_home)).resolve()
    roots = tuple(
        Path(p).resolve() for p in os.environ.get("AURA_DATA_ROOTS", "").split(os.pathsep) if p.strip()
    )
    return Settings(home=home, extra_data_roots=roots)


# Check thresholds. Each module milestone (M4-M6) adds its documented defaults here;
# ADMIN changes are versioned and audited (A11.2 /config/thresholds).
DEFAULT_THRESHOLDS: dict[str, dict[str, float | int]] = {}
