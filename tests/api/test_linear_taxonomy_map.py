from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from issue_inventory import parse_taxonomy
from linear_taxonomy_map import apply_mapping, derived_labels, load_mapping_config


def base_mapping() -> dict[str, Any]:
    return {
        "priority": {
            "0": [],
            "1": ["complexity:trivial", "quick-win"],
            "2": ["complexity:routine"],
            "3": ["complexity:routine"],
            "4": ["complexity:complex"],
        },
        "estimate": {
            "1": ["effort:xs"],
            "2": ["effort:s"],
            "3": ["effort:m"],
            "5": ["effort:l"],
            "8": ["effort:xl"],
        },
        "state_type": {
            "triage": ["judgement:design"],
            "backlog": [],
            "unstarted": [],
            "started": [],
            "completed": [],
            "canceled": [],
        },
        "label_aliases": {
            "Bug": ["type:bug"],
            "Feature": ["type:task"],
            "Improvement": ["type:task"],
            "Documentation": ["type:docs"],
            "Chore": ["type:chore"],
            "Security": ["type:security"],
        },
        "label_passthrough_prefixes": [
            "type:",
            "domain:",
            "wave:",
            "complexity:",
            "effort:",
            "judgement:",
        ],
        "default_judgement": "objective",
    }


def linear_issue(**overrides: Any) -> dict[str, Any]:
    issue: dict[str, Any] = {
        "id": "issue-id",
        "identifier": "ENG-123",
        "title": "Example",
        "description": "Example description",
        "priority": 0,
        "estimate": None,
        "state": {"name": "Started", "type": "started"},
        "labels": {"nodes": []},
    }
    issue.update(overrides)
    return issue


def with_labels(*names: str) -> dict[str, list[dict[str, str]]]:
    return {"nodes": [{"name": name} for name in names]}


def test_priority_urgent_maps_to_trivial_quick_win() -> None:
    result = apply_mapping(linear_issue(priority=1), base_mapping())

    assert result["complexity"] == "trivial"
    assert result["quick_win"] is True
    assert result["derived_labels"][:2] == ["complexity:trivial", "quick-win"]


def test_priority_no_priority_zero_no_labels() -> None:
    labels = derived_labels(linear_issue(priority=0), base_mapping())

    assert "complexity:trivial" not in labels
    assert "quick-win" not in labels


def test_priority_low_maps_to_complex() -> None:
    result = apply_mapping(linear_issue(priority=4), base_mapping())

    assert result["complexity"] == "complex"


def test_estimate_exact_match() -> None:
    result = apply_mapping(linear_issue(estimate=3), base_mapping())

    assert result["effort"] == "m"
    assert "effort:m" in result["derived_labels"]


def test_estimate_unknown_falls_back_to_closest_lower() -> None:
    assert apply_mapping(linear_issue(estimate=4), base_mapping())["effort"] == "m"
    assert apply_mapping(linear_issue(estimate=13), base_mapping())["effort"] == "xl"


def test_state_triage_maps_to_judgement_design() -> None:
    result = apply_mapping(linear_issue(state={"name": "Triage", "type": "triage"}), base_mapping())

    assert result["judgement"] == "design"


def test_state_started_no_judgement_label_uses_default_objective() -> None:
    result = apply_mapping(linear_issue(state={"name": "Started", "type": "started"}), base_mapping())

    assert result["judgement"] == "objective"
    assert "judgement:objective" in result["derived_labels"]


def test_label_alias_bug_maps_to_type_bug() -> None:
    result = apply_mapping(linear_issue(labels=with_labels("Bug")), base_mapping())

    assert result["type"] == "bug"


def test_label_passthrough_type_prefix() -> None:
    result = apply_mapping(linear_issue(labels=with_labels("type:docs")), base_mapping())

    assert result["type"] == "docs"


def test_label_alias_takes_precedence_over_passthrough() -> None:
    mapping = base_mapping()
    mapping["label_passthrough_prefixes"] = ["B", *mapping["label_passthrough_prefixes"]]

    labels = derived_labels(linear_issue(labels=with_labels("Bug")), mapping)

    assert "type:bug" in labels
    assert "Bug" not in labels


def test_unknown_label_ignored() -> None:
    labels = derived_labels(linear_issue(labels=with_labels("wibble")), base_mapping())

    assert "wibble" not in labels


def test_derived_labels_deduplicated_and_stable_order() -> None:
    mapping = base_mapping()
    mapping["priority"]["1"] = ["complexity:trivial", "quick-win", "type:task"]
    issue = linear_issue(priority=1, labels=with_labels("Feature", "type:task", "domain:backend"))

    assert derived_labels(issue, mapping) == [
        "complexity:trivial",
        "quick-win",
        "type:task",
        "domain:backend",
        "judgement:objective",
    ]


def test_default_judgement_objective_added_when_state_does_not_set_one() -> None:
    assert apply_mapping(linear_issue(), base_mapping())["judgement"] == "objective"


def test_state_triage_keeps_design_judgement_does_not_get_overridden() -> None:
    result = apply_mapping(linear_issue(state={"name": "Triage", "type": "triage"}), base_mapping())

    assert result["judgement"] == "design"
    assert "judgement:objective" not in result["derived_labels"]


def test_apply_mapping_returns_taxonomy_compatible_with_parse_taxonomy() -> None:
    result = apply_mapping(
        linear_issue(priority=1, estimate=3, labels=with_labels("Bug", "domain:backend", "wave:1")),
        base_mapping(),
    )

    taxonomy = parse_taxonomy(result["derived_labels"])
    for field in ("type", "complexity", "effort", "judgement", "quick_win", "panel_review", "domains", "wave"):
        assert result[field] == taxonomy[field]


def write_config(path: Path, config: dict[str, Any]) -> None:
    path.write_text(json.dumps(config), encoding="utf-8")


def valid_config() -> dict[str, Any]:
    return {
        "$schema": "./linear.schema.json",
        "workspaces": [
            {
                "id": "personal",
                "auth": {"kind": "api_key", "env": "LINEAR_API_KEY"},
                "teams": ["*"],
                "mapping": "default",
                "trigger_label": "dispatch",
                "webhook_secret_env": "LINEAR_WEBHOOK_SECRET",
                "default_repository": "D-sorganization/runner-dashboard",
                "prefer_source": "linear",
            }
        ],
        "mappings": {"default": base_mapping()},
    }


def test_load_mapping_config_validates_required_fields(tmp_path: Path) -> None:
    path = tmp_path / "linear.json"
    write_config(path, {"mappings": {"default": base_mapping()}})

    with pytest.raises(ValueError, match="workspaces"):
        load_mapping_config(path)

    write_config(path, {"workspaces": []})
    with pytest.raises(ValueError, match="mappings"):
        load_mapping_config(path)


def test_load_mapping_config_validates_auth_kind(tmp_path: Path) -> None:
    config = valid_config()
    config["workspaces"][0]["auth"]["kind"] = "wat"
    path = tmp_path / "linear.json"
    write_config(path, config)

    with pytest.raises(ValueError, match="auth.kind"):
        load_mapping_config(path)


def test_load_mapping_config_validates_named_mapping_exists(tmp_path: Path) -> None:
    config = valid_config()
    config["workspaces"][0]["mapping"] = "missing"
    path = tmp_path / "linear.json"
    write_config(path, config)

    with pytest.raises(ValueError, match="missing"):
        load_mapping_config(path)


def test_apply_mapping_pure_no_mutation() -> None:
    issue = linear_issue(priority=1, estimate=3, labels=with_labels("Bug"))
    mapping = base_mapping()
    original_issue = copy.deepcopy(issue)
    original_mapping = copy.deepcopy(mapping)

    apply_mapping(issue, mapping)

    assert issue == original_issue
    assert mapping == original_mapping


def test_source_signals_records_all_inputs() -> None:
    result = apply_mapping(
        linear_issue(
            priority=1,
            estimate=3,
            state={"name": "Triage", "type": "triage"},
            labels=with_labels("Bug", "domain:backend"),
        ),
        base_mapping(),
    )

    assert result["source_signals"] == {
        "priority": 1,
        "priority_labels": ["complexity:trivial", "quick-win"],
        "estimate": 3,
        "estimate_labels": ["effort:m"],
        "state_type": "triage",
        "state_labels": ["judgement:design"],
        "linear_labels": ["Bug", "domain:backend"],
        "label_aliases_applied": {"Bug": ["type:bug"]},
        "passthrough_labels": ["domain:backend"],
        "ignored_labels": [],
        "default_judgement": None,
    }
