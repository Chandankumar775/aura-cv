"""Model access levels (R-MOD-2, R-CON-5).

Detection of the level a given model file offers needs the model adapters and lands
in Milestone M2. What lives here now is the rule that matters for honesty: a user may
*declare a lower* level than detected, to simulate black-box conditions, but can never
claim more access than the file actually gives.
"""

from __future__ import annotations

from aura.core.types import AccessLevel


class AccessLevelError(ValueError):
    pass


def effective_access(detected: AccessLevel, declared: AccessLevel | None = None) -> AccessLevel:
    if declared is None:
        return detected
    if declared.rank > detected.rank:
        raise AccessLevelError(
            f"declared access {declared.value} exceeds the detected {detected.value}; "
            "access can only be lowered, never raised"
        )
    return declared
