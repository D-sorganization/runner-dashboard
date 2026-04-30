"""Input validation helpers for workflow_dispatch handlers.

GitHub's `workflow_dispatch` API accepts an ``inputs`` mapping where every
value is a string. Without a per-key length cap and a per-dict key-count cap,
a malicious or buggy client can ship a multi-megabyte payload that is
serialized to a temp file and forwarded to ``gh`` before GitHub itself
rejects it with a 422. This module centralizes the size and type checks so
both ``/api/workflows/dispatch`` and ``/api/feature-requests/dispatch``
share a single contract (DRY) and reject abuse cases before any I/O.

Constants are deliberately conservative — GitHub's own per-input-value cap
sits well above ``MAX_INPUT_VALUE_LENGTH``; the dashboard's tighter limit
exists to protect the dashboard itself, not GitHub.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException

# ─── Module constants ─────────────────────────────────────────────────────────

MAX_INPUT_VALUE_LENGTH: int = 1000
"""Maximum number of characters permitted per input value."""

MAX_INPUT_KEYS: int = 20
"""Maximum number of keys permitted in an inputs mapping."""


def validate_workflow_inputs(inputs: Any) -> dict[str, str]:
    """Validate a ``workflow_dispatch`` inputs payload.

    Pre-conditions
    --------------
    * ``inputs`` is ``None``, an empty mapping, or a mapping of string keys
      to string values.
    * The mapping has at most ``MAX_INPUT_KEYS`` entries.
    * Every value has at most ``MAX_INPUT_VALUE_LENGTH`` characters.

    Post-conditions
    ---------------
    * Returns a fresh ``dict[str, str]`` containing the validated inputs.
    * Raises ``HTTPException`` with status 400 if any pre-condition fails.

    The function is intentionally side-effect-free so callers can apply it
    before any temp-file or subprocess work.
    """
    if inputs is None:
        return {}
    if not isinstance(inputs, Mapping):
        raise HTTPException(
            status_code=400,
            detail="inputs must be an object (mapping of string keys to string values)",
        )
    if len(inputs) > MAX_INPUT_KEYS:
        raise HTTPException(
            status_code=400,
            detail=(f"inputs has too many keys: {len(inputs)} > {MAX_INPUT_KEYS}. Reduce the number of input keys."),
        )

    validated: dict[str, str] = {}
    for key, value in inputs.items():
        if not isinstance(key, str):
            raise HTTPException(
                status_code=400,
                detail="inputs keys must be strings",
            )
        if not isinstance(value, str):
            raise HTTPException(
                status_code=400,
                detail=(f"inputs[{key!r}] must be a string; GitHub workflow_dispatch inputs are always strings"),
            )
        if len(value) > MAX_INPUT_VALUE_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=(f"inputs[{key!r}] exceeds maximum length ({len(value)} > {MAX_INPUT_VALUE_LENGTH} chars)"),
            )
        validated[key] = value

    assert len(validated) <= MAX_INPUT_KEYS  # invariant
    return validated
