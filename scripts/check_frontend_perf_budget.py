"""Validate the frontend performance budget contract.

The dashboard is still a no-build single-file SPA, so this check enforces the
checked-in mobile budget values and a gzip guardrail for the current artifact.
When route chunks land, the same budget file can be extended to inspect built
assets without weakening the target values.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUDGET_PATH = ROOT / "frontend" / "perf-budget.json"
INDEX_PATH = ROOT / "frontend" / "index.html"

REQUIRED_TARGETS: dict[tuple[str, str], int] = {
    ("mobile_shell", "js_gzip_bytes"): 204800,
    ("mobile_shell", "css_gzip_bytes"): 51200,
    ("tab_chunk", "js_gzip_bytes"): 102400,
    ("mobile_lighthouse", "performance_min"): 90,
    ("field_timing", "inp_p75_ms"): 200,
    ("field_timing", "fcp_ms"): 1800,
}


def _gzip_size(text: str) -> int:
    return len(gzip.compress(text.encode("utf-8"), compresslevel=9, mtime=0))


def _inline_blocks(html: str, tag: str) -> str:
    if tag == "script":
        pattern = r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>"
    else:
        pattern = rf"<{tag}[^>]*>(.*?)</{tag}>"
    return "\n".join(re.findall(pattern, html, flags=re.IGNORECASE | re.DOTALL))


def load_budget(path: Path = BUDGET_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_budget_contract(budget: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if budget.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if budget.get("issue") != 200:
        errors.append("issue must be 200")

    budgets = budget.get("budgets")
    if not isinstance(budgets, dict):
        return errors + ["budgets must be an object"]

    for (section, key), expected in REQUIRED_TARGETS.items():
        actual = budgets.get(section, {}).get(key)
        if actual != expected:
            errors.append(f"budgets.{section}.{key} must remain {expected}, got {actual!r}")

    routes = budgets.get("mobile_lighthouse", {}).get("routes")
    expected_routes = ["Fleet", "Workflows", "Remediation", "Maxwell", "Reports"]
    if routes != expected_routes:
        errors.append(f"mobile_lighthouse.routes must be {expected_routes!r}")

    change_control = budget.get("change_control", {})
    if change_control.get("budget_increases_require_justification") is not True:
        errors.append("change_control.budget_increases_require_justification must be true")

    return errors


def measure_frontend(index_path: Path = INDEX_PATH) -> dict[str, int]:
    html = index_path.read_text(encoding="utf-8")
    return {
        "index_html_gzip_bytes": _gzip_size(html),
        "inline_js_gzip_bytes": _gzip_size(_inline_blocks(html, "script")),
        "inline_css_gzip_bytes": _gzip_size(_inline_blocks(html, "style")),
    }


def validate_interim_sizes(budget: dict[str, Any], sizes: dict[str, int]) -> list[str]:
    interim = budget.get("budgets", {}).get("interim_single_file", {})
    errors: list[str] = []
    for key, actual in sizes.items():
        limit = interim.get(key)
        if not isinstance(limit, int):
            errors.append(f"budgets.interim_single_file.{key} must be an integer")
            continue
        if actual > limit:
            errors.append(f"{key} is {actual} bytes gzip, over budget {limit}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print measured sizes as JSON")
    args = parser.parse_args()

    budget = load_budget()
    sizes = measure_frontend()
    errors = validate_budget_contract(budget) + validate_interim_sizes(budget, sizes)
    if args.json:
        print(json.dumps({"sizes": sizes, "errors": errors}, indent=2, sort_keys=True))
    if errors:
        for error in errors:
            print(f"frontend performance budget: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
