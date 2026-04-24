"""Static source integrity checks for frontend/index.html.

These tests do not execute JavaScript — they assert that the compiled single-file
frontend contains the structural markers expected by the dashboard design contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_INDEX_HTML = Path(__file__).parent.parent / "frontend" / "index.html"


def _read_index() -> str:
    return _INDEX_HTML.read_text(encoding="utf-8")


def _index_lines() -> list[str]:
    return _read_index().splitlines()


# ---------------------------------------------------------------------------
# Required tab/component function markers
# ---------------------------------------------------------------------------

_REQUIRED_FUNCTIONS = [
    "function FleetTab",
    "function HistoryTab",
    "function QueueTab",
    "function MachinesTab",
    "function OrgTab",
    "function TestsTab",
    "function StatsTab",
    "function ReportsTab",
    "function ScheduledJobsTab",
    "function LocalAppsTab",
    "function RemediationTab",
    "function WorkflowsTab",
    "function CredentialsTab",
    "function AssessmentsTab",
    "function FeatureRequestsTab",
    "function MaxwellTab",
    "function FleetOrchestrationTab",
    "function DashboardHelp",
]

# RunnerPlanTab is not yet implemented in the frontend; tracked for a future PR.
_XFAIL_FUNCTIONS = [
    "function RunnerPlanTab",
]


@pytest.mark.parametrize("marker", _REQUIRED_FUNCTIONS)
def test_required_function_present(marker: str) -> None:
    content = _read_index()
    assert marker in content, f"Expected '{marker}' in frontend/index.html"


@pytest.mark.xfail(reason="RunnerPlanTab not yet implemented in frontend/index.html", strict=True)
def test_runner_plan_tab_present() -> None:
    content = _read_index()
    assert "function RunnerPlanTab" in content


# ---------------------------------------------------------------------------
# HeavyTestsTab must NOT appear
# ---------------------------------------------------------------------------


def test_heavy_tests_tab_absent() -> None:
    content = _read_index()
    assert "HeavyTestsTab" not in content, "HeavyTestsTab was found — use TestsTab instead"


# ---------------------------------------------------------------------------
# TestsTab specifically (not HeavyTestsTab)
# ---------------------------------------------------------------------------


def test_tests_tab_function_present() -> None:
    content = _read_index()
    assert "function TestsTab" in content


# ---------------------------------------------------------------------------
# dangerouslySetInnerHTML safety check
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "dangerouslySetInnerHTML at line ~3914 uses renderMarkdown() wrapper "
        "rather than DOMPurify.sanitize inline; DOMPurify integration is pending"
    ),
    strict=False,
)
def test_dangerous_set_inner_html_sanitized() -> None:
    """Every dangerouslySetInnerHTML usage must appear within 5 lines of
    DOMPurify.sanitize or a comment that explains why it is safe."""
    lines = _index_lines()
    violations: list[int] = []
    for lineno, line in enumerate(lines):
        if "dangerouslySetInnerHTML" not in line:
            continue
        window_start = max(0, lineno - 5)
        window_end = min(len(lines), lineno + 6)
        window = "\n".join(lines[window_start:window_end])
        has_sanitize = "DOMPurify.sanitize" in window
        has_safe_comment = re.search(r"//.*safe|//.*sanitize|//.*trusted", window, re.IGNORECASE) is not None
        if not (has_sanitize or has_safe_comment):
            violations.append(lineno + 1)
    assert not violations, (
        f"dangerouslySetInnerHTML at line(s) {violations} has no nearby DOMPurify.sanitize or safety comment"
    )


# ---------------------------------------------------------------------------
# Icons helper must expose I.play, I.flask, and I.activity
# ---------------------------------------------------------------------------


def test_icons_helper_has_play() -> None:
    content = _read_index()
    assert "I.play" in content


def test_icons_helper_has_flask() -> None:
    content = _read_index()
    assert "I.flask" in content


def test_icons_helper_has_activity() -> None:
    content = _read_index()
    assert "I.activity" in content
