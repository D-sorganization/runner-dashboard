"""Unit tests for agent_remediation.py — failure context, policy, and workflow classification."""

from agent_remediation import (
    FailureContext,
    RemediationPolicy,
    WorkflowTypeRule,
    classify_workflow_type,
    load_policy,
)

# ---------------------------------------------------------------------------
# Helper: classify_failure wraps classify_workflow_type with default policy
# ---------------------------------------------------------------------------


def classify_failure(context: FailureContext, policy: RemediationPolicy | None = None) -> WorkflowTypeRule:
    """Thin wrapper so tests can call classify_failure(ctx) as described in the issue."""
    if policy is None:
        policy = load_policy()
    return classify_workflow_type(context, policy)


# ---------------------------------------------------------------------------
# FailureContext.from_dict — valid construction
# ---------------------------------------------------------------------------


def test_failure_context_from_dict_valid() -> None:
    data = {"repository": "Foo", "workflow_name": "CI", "branch": "main"}
    ctx = FailureContext.from_dict(data)
    assert ctx.repository == "Foo"
    assert ctx.workflow_name == "CI"
    assert ctx.branch == "main"


# ---------------------------------------------------------------------------
# classify_failure — "CI Standard" workflow_name → "test" type
# ---------------------------------------------------------------------------


def test_classify_failure_ci_standard_returns_test_type() -> None:
    ctx = FailureContext(repository="Foo", workflow_name="CI Standard", branch="main")
    rule = classify_failure(ctx)
    assert isinstance(rule, WorkflowTypeRule)
    assert rule.workflow_type == "test"


# ---------------------------------------------------------------------------
# classify_failure — "ruff lint check" workflow_name → "lint" type
# ---------------------------------------------------------------------------


def test_classify_failure_ruff_lint_returns_lint_type() -> None:
    ctx = FailureContext(repository="Foo", workflow_name="ruff lint check", branch="main")
    rule = classify_failure(ctx)
    assert isinstance(rule, WorkflowTypeRule)
    assert rule.workflow_type == "lint"


# ---------------------------------------------------------------------------
# RemediationPolicy — default policy loads without error and has sane defaults
# ---------------------------------------------------------------------------


def test_load_policy_returns_remediation_policy() -> None:
    policy = load_policy()
    assert isinstance(policy, RemediationPolicy)
    assert policy.max_same_failure_attempts > 0
    assert "unknown" in policy.workflow_type_rules


# ---------------------------------------------------------------------------
# FailureContext — protected_branch flag is preserved
# ---------------------------------------------------------------------------


def test_failure_context_protected_branch_flag() -> None:
    ctx = FailureContext.from_dict(
        {"repository": "Foo", "workflow_name": "CI", "branch": "main", "protected_branch": True}
    )
    assert ctx.protected_branch is True
