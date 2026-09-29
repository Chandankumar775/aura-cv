"""RFC 8785 JSON Canonicalization Scheme (JCS).

Signatures and hash chains are computed over bytes, so the same logical JSON must
always serialise to the same bytes on every machine (R-INF-1, R-INF-2, R-GOV-2).
Serialisation is delegated to the ``rfc8785`` library (Trail of Bits, pure Python,
installable from the offline wheelhouse); tests in ``tests/test_canonical.py`` pin
its behaviour to the RFC's own test vectors.

This wrapper adds two things the library does not do for us:
  * converts Pydantic models, tuples and other containers to plain JSON types;
  * raises one exception type (``CanonicalizationError``) for anything that has no
    canonical form (NaN, Infinity, non-string keys, unsupported types).
"""

from __future__ import annotations

import json
import math
from typing import Any

import rfc8785
from pydantic import BaseModel

# RFC 8785 relies on I-JSON (RFC 7493): integers beyond +/-(2**53 - 1) cannot be
# represented exactly by an IEEE-754 double and are rejected.
MAX_SAFE_INT = 2**53 - 1


class CanonicalizationError(ValueError):
    """The value has no RFC 8785 canonical form."""


def _normalise(obj: Any, path: str = "$") -> Any:
    if isinstance(obj, BaseModel):
        return _normalise(obj.model_dump(mode="json"), path)
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, int):
        if abs(obj) > MAX_SAFE_INT:
            raise CanonicalizationError(f"{path}: integer {obj} outside the I-JSON safe range")
        return obj
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise CanonicalizationError(f"{path}: NaN/Infinity have no JSON representation")
        return obj
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise CanonicalizationError(f"{path}: object keys must be strings, got {type(k).__name__}")
            out[k] = _normalise(v, f"{path}.{k}")
        return out
    if isinstance(obj, (list, tuple)):
        return [_normalise(v, f"{path}[{i}]") for i, v in enumerate(obj)]
    raise CanonicalizationError(f"{path}: unsupported type {type(obj).__name__}")


def canonicalize(obj: Any) -> bytes:
    """Return the RFC 8785 canonical UTF-8 bytes of ``obj``."""
    try:
        return rfc8785.dumps(_normalise(obj))
    except CanonicalizationError:
        raise
    except Exception as exc:  # library-specific domain errors
        raise CanonicalizationError(str(exc)) from exc


def canonicalize_json_text(text: str) -> bytes:
    """Canonicalise a JSON document given as text (used for RFC test vectors and imports)."""
    return canonicalize(json.loads(text))
