"""Test that backend/**/*.py contains no dead code after return/raise (issue #329)."""

from __future__ import annotations

import ast
import pathlib

BACKEND_DIR = pathlib.Path(__file__).parent.parent / "backend"


def _is_terminal_node(node: ast.AST) -> bool:
    """Return True for statements that terminate control flow."""
    return isinstance(node, (ast.Return, ast.Raise))


def test_no_unreachable_code() -> None:
    violations: list[str] = []
    for path in BACKEND_DIR.rglob("*.py"):
        if path.name == "__init__.py" or "tests" in str(path):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # Check function body
            for i, stmt in enumerate(node.body[:-1]):
                if _is_terminal_node(stmt):
                    next_stmt = node.body[i + 1]
                    violations.append(
                        f"{path}:{next_stmt.lineno}: dead code after {type(stmt).__name__} in {node.name}"
                    )
            # Check except handlers
            for stmt in node.body:
                if isinstance(stmt, ast.Try):
                    for handler in stmt.handlers:
                        for i, hstmt in enumerate(handler.body[:-1]):
                            if _is_terminal_node(hstmt):
                                next_stmt = handler.body[i + 1]
                                violations.append(
                                    f"{path}:{next_stmt.lineno}: dead code after "
                                    f"{type(hstmt).__name__} in except handler of {node.name}"
                                )

    assert not violations, "\n".join(violations)
