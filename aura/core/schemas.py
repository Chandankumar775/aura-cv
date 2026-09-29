"""JSON Schema (draft 2020-12) loading and validation for the exported contracts (R-DEL-3).

Pydantic models guard objects inside the process; these schemas guard what crosses a
boundary (stored findings, exported reports, imported records). A finding that fails
validation is a bug (A3 rule 5), so ``validate_finding`` raises rather than warns.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import BaseModel

from aura.config import get_settings

FINDING = "finding"


class SchemaValidationError(ValueError):
    def __init__(self, schema: str, errors: list[str]):
        self.schema = schema
        self.errors = errors
        super().__init__(f"{schema} schema validation failed: " + "; ".join(errors))


@lru_cache(maxsize=None)
def _validator(schema_path: str) -> Draft202012Validator:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def schema_path(name: str) -> Path:
    return get_settings().schema_dir / f"{name}.schema.json"


def errors_for(name: str, instance: Any) -> list[str]:
    if isinstance(instance, BaseModel):
        instance = instance.model_dump(mode="json")
    validator = _validator(str(schema_path(name)))
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in errors]


def validate(name: str, instance: Any) -> None:
    errors = errors_for(name, instance)
    if errors:
        raise SchemaValidationError(name, errors)


def validate_finding(finding: Any) -> None:
    validate(FINDING, finding)
