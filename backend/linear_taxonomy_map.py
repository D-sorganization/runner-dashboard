"""Linear-to-dashboard taxonomy mapping helpers.

This module converts raw Linear issue payloads into the same taxonomy fields
used by GitHub issue inventory. It is intentionally limited to pure mapping
logic: callers pass a Linear issue payload and a mapping policy, and the module
returns synthesized GitHub-style labels plus parsed taxonomy fields. The only
I/O helper is ``load_mapping_config(path)``, which reads an explicit path and
validates the operator-provided JSON file.

Config schema, in plain language:

* Top-level ``workspaces`` is a list of workspace records. Each workspace has
  an ``id``, ``auth`` block, team selector list, mapping name, trigger label,
  webhook secret environment variable name, default repository, and
  ``prefer_source`` merge hint.
* ``auth.kind`` is a tagged union. Version 1 accepts only ``"api_key"`` with
  an ``env`` field naming the environment variable read by later auth code.
  This module does not read environment variables.
* Top-level ``mappings`` is an object keyed by mapping name. A workspace's
  ``mapping`` value must reference one of these keys.
* Each mapping policy maps Linear ``priority``, ``estimate``, and
  ``state.type`` values to lists of GitHub-style labels. ``estimate`` values
  use an exact match when present, otherwise the closest lower numeric bucket
  is used. For example, estimate ``4`` maps through bucket ``3`` if ``3`` is
  the highest configured bucket at or below ``4``.
* ``label_aliases`` maps exact Linear label names to GitHub-style labels.
  Aliases are applied before passthrough prefixes.
* ``label_passthrough_prefixes`` lets matching Linear labels pass through
  unchanged, such as ``type:bug`` or ``domain:backend``.
* If no ``judgement:*`` label is produced, ``judgement:<default_judgement>`` is
  appended. The default judgement defaults to ``objective`` when omitted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict, cast

from issue_inventory import parse_taxonomy


class MappingResult(TypedDict):
    """Return shape of apply_mapping, compatible with issue_inventory taxonomy."""

    type: str | None
    complexity: str | None
    effort: str | None
    judgement: str | None
    quick_win: bool
    panel_review: bool
    domains: list[str]
    wave: int | str | None
    derived_labels: list[str]
    source_signals: dict[str, Any]


def load_mapping_config(path: Path) -> dict[str, Any]:
    """Read and validate a Linear mapping config file.

    Raises
    ------
    ValueError
        If the JSON is malformed or required config fields are missing.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid Linear config JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("Linear config must be a JSON object")

    workspaces = raw.get("workspaces")
    if not isinstance(workspaces, list):
        raise ValueError("Linear config requires 'workspaces' as a list")

    mappings = raw.get("mappings")
    if not isinstance(mappings, dict):
        raise ValueError("Linear config requires 'mappings' as an object")

    for mapping_name, mapping in mappings.items():
        if not isinstance(mapping_name, str) or not mapping_name:
            raise ValueError("Linear config mapping names must be non-empty strings")
        _validate_mapping(mapping_name, mapping)

    for index, workspace in enumerate(workspaces):
        if not isinstance(workspace, dict):
            raise ValueError(f"workspaces[{index}] must be an object")
        _validate_workspace(index, workspace, mappings)

    return raw


def derived_labels(linear_issue: dict[str, Any], mapping: dict[str, Any]) -> list[str]:
    """Return synthesized GitHub-style labels, deduplicated in stable order."""
    labels, _ = _derive_labels_and_signals(linear_issue, mapping)
    return labels


def apply_mapping(
    linear_issue: dict[str, Any], mapping: dict[str, Any]
) -> MappingResult:
    """Apply a mapping policy to a raw Linear issue payload."""
    labels, source_signals = _derive_labels_and_signals(linear_issue, mapping)
    taxonomy = parse_taxonomy(labels)

    return {
        "type": cast(str | None, taxonomy["type"]),
        "complexity": cast(str | None, taxonomy["complexity"]),
        "effort": cast(str | None, taxonomy["effort"]),
        "judgement": cast(str | None, taxonomy["judgement"]),
        "quick_win": bool(taxonomy["quick_win"]),
        "panel_review": bool(taxonomy["panel_review"]),
        "domains": cast(list[str], taxonomy["domains"]),
        "wave": cast(int | str | None, taxonomy["wave"]),
        "derived_labels": labels,
        "source_signals": source_signals,
    }


def _derive_labels_and_signals(
    linear_issue: dict[str, Any],
    mapping: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    labels: list[str] = []

    priority = linear_issue.get("priority")
    priority_labels = _labels_for_exact_key(mapping.get("priority", {}), priority)
    labels.extend(priority_labels)

    estimate = linear_issue.get("estimate")
    estimate_labels = _labels_for_estimate(mapping.get("estimate", {}), estimate)
    labels.extend(estimate_labels)

    state = (
        linear_issue.get("state") if isinstance(linear_issue.get("state"), dict) else {}
    )
    state_type = state.get("type") if isinstance(state, dict) else None
    state_labels = _labels_for_exact_key(mapping.get("state_type", {}), state_type)
    labels.extend(state_labels)

    label_names = _linear_label_names(linear_issue)
    aliases = mapping.get("label_aliases", {})
    passthrough_prefixes = mapping.get("label_passthrough_prefixes", [])
    aliases_applied: dict[str, list[str]] = {}
    passthrough_labels: list[str] = []
    ignored_labels: list[str] = []

    for label_name in label_names:
        if isinstance(aliases, dict) and label_name in aliases:
            alias_labels = _string_list(aliases[label_name])
            labels.extend(alias_labels)
            aliases_applied[label_name] = alias_labels
        elif _matches_passthrough(label_name, passthrough_prefixes):
            labels.append(label_name)
            passthrough_labels.append(label_name)
        else:
            ignored_labels.append(label_name)

    labels = _dedupe_stable(labels)
    default_judgement = None
    if not any(label.startswith("judgement:") for label in labels):
        default_judgement = str(mapping.get("default_judgement") or "objective")
        labels.append(f"judgement:{default_judgement}")

    source_signals: dict[str, Any] = {
        "priority": priority,
        "priority_labels": priority_labels,
        "estimate": estimate,
        "estimate_labels": estimate_labels,
        "state_type": state_type,
        "state_labels": state_labels,
        "linear_labels": label_names,
        "label_aliases_applied": aliases_applied,
        "passthrough_labels": passthrough_labels,
        "ignored_labels": ignored_labels,
        "default_judgement": default_judgement,
    }
    return labels, source_signals


def _validate_workspace(
    index: int, workspace: dict[str, Any], mappings: dict[str, Any]
) -> None:
    for field in (
        "id",
        "auth",
        "teams",
        "mapping",
        "trigger_label",
        "webhook_secret_env",
        "default_repository",
        "prefer_source",
    ):
        if field not in workspace:
            raise ValueError(f"workspaces[{index}] missing required field '{field}'")

    if not isinstance(workspace["id"], str) or not workspace["id"]:
        raise ValueError(f"workspaces[{index}].id must be a non-empty string")

    auth = workspace["auth"]
    if not isinstance(auth, dict):
        raise ValueError(f"workspaces[{index}].auth must be an object")
    if auth.get("kind") != "api_key":
        raise ValueError(f"workspaces[{index}].auth.kind must be 'api_key'")
    if not isinstance(auth.get("env"), str) or not auth["env"]:
        raise ValueError(f"workspaces[{index}].auth.env must be a non-empty string")

    if not isinstance(workspace["teams"], list) or not all(
        isinstance(team, str) for team in workspace["teams"]
    ):
        raise ValueError(f"workspaces[{index}].teams must be a list of strings")

    mapping_name = workspace["mapping"]
    if not isinstance(mapping_name, str) or not mapping_name:
        raise ValueError(f"workspaces[{index}].mapping must be a non-empty string")
    if mapping_name not in mappings:
        raise ValueError(
            f"workspaces[{index}] references missing mapping '{mapping_name}'"
        )

    for field in (
        "trigger_label",
        "webhook_secret_env",
        "default_repository",
        "prefer_source",
    ):
        if not isinstance(workspace[field], str) or not workspace[field]:
            raise ValueError(f"workspaces[{index}].{field} must be a non-empty string")


def _validate_mapping(mapping_name: str, mapping: Any) -> None:
    if not isinstance(mapping, dict):
        raise ValueError(f"mappings.{mapping_name} must be an object")

    for field in (
        "priority",
        "estimate",
        "state_type",
        "label_aliases",
        "label_passthrough_prefixes",
    ):
        if field not in mapping:
            raise ValueError(
                f"mappings.{mapping_name} missing required field '{field}'"
            )

    for field in ("priority", "estimate", "state_type", "label_aliases"):
        if not isinstance(mapping[field], dict):
            raise ValueError(f"mappings.{mapping_name}.{field} must be an object")

    for field in ("priority", "estimate", "state_type", "label_aliases"):
        for key, value in mapping[field].items():
            if not isinstance(key, str):
                raise ValueError(
                    f"mappings.{mapping_name}.{field} keys must be strings"
                )
            if not _is_string_list(value):
                raise ValueError(
                    f"mappings.{mapping_name}.{field}.{key} must be a list of strings"
                )

    prefixes = mapping["label_passthrough_prefixes"]
    if not _is_string_list(prefixes):
        raise ValueError(
            f"mappings.{mapping_name}.label_passthrough_prefixes must be a list of strings"
        )

    default_judgement = mapping.get("default_judgement", "objective")
    if not isinstance(default_judgement, str) or not default_judgement:
        raise ValueError(
            f"mappings.{mapping_name}.default_judgement must be a non-empty string"
        )


def _labels_for_exact_key(source: Any, value: Any) -> list[str]:
    if not isinstance(source, dict) or value is None:
        return []
    return _string_list(source.get(str(value), []))


def _labels_for_estimate(source: Any, estimate: Any) -> list[str]:
    if not isinstance(source, dict) or estimate is None:
        return []
    try:
        estimate_value = int(estimate)
    except (TypeError, ValueError):
        return []

    if str(estimate_value) in source:
        return _string_list(source[str(estimate_value)])

    numeric_buckets = sorted(int(key) for key in source if _is_int_string(key))
    lower_buckets = [bucket for bucket in numeric_buckets if bucket <= estimate_value]
    if not lower_buckets:
        return []
    return _string_list(source[str(lower_buckets[-1])])


def _linear_label_names(linear_issue: dict[str, Any]) -> list[str]:
    labels = linear_issue.get("labels")
    if isinstance(labels, dict):
        nodes = labels.get("nodes")
    else:
        nodes = labels
    if not isinstance(nodes, list):
        return []

    names: list[str] = []
    for node in nodes:
        if isinstance(node, dict) and isinstance(node.get("name"), str):
            names.append(node["name"])
        elif isinstance(node, str):
            names.append(node)
    return names


def _matches_passthrough(label_name: str, prefixes: Any) -> bool:
    if not isinstance(prefixes, list):
        return False
    return any(
        isinstance(prefix, str) and label_name.startswith(prefix) for prefix in prefixes
    )


def _dedupe_stable(labels: list[str]) -> list[str]:
    seen: set[str] = set()
    stable: list[str] = []
    for label in labels:
        if label not in seen:
            stable.append(label)
            seen.add(label)
    return stable


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _string_list(value: Any) -> list[str]:
    if not _is_string_list(value):
        return []
    return list(value)


def _is_int_string(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        int(value)
    except ValueError:
        return False
    return True
