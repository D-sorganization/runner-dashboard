"""Static contract tests for the typed frontend storage layer (#423)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STORAGE = REPO_ROOT / "frontend" / "src" / "lib" / "storage.ts"
APP = REPO_ROOT / "frontend" / "src" / "legacy" / "App.tsx"
PACKAGE = REPO_ROOT / "package.json"


def _read(path: Path) -> str:
    assert path.exists(), f"expected {path} to exist"
    return path.read_text(encoding="utf-8")


def test_storage_layer_exports_typed_zod_helpers() -> None:
    source = _read(STORAGE)

    assert 'from "zod"' in source
    assert "export type StorageKey" in source
    assert "getItem<T>(" in source
    assert "schema: ZodType<T>" in source
    assert "setItem<T>(" in source
    assert "schema.safeParse" in source


def test_storage_layer_has_registry_migrations_and_quota_fallback() -> None:
    source = _read(STORAGE)

    for key in [
        "issuesSourceFilter",
        "workflowsMobileFilters",
        "maxwellMobileChatHistory",
        "assistant:transcript",
    ]:
        assert key in source
    assert "storageMigrations" in source
    assert "QuotaExceededError" in source
    assert "memoryStorage" in source
    assert "__toaster" in source


def test_maxwell_chat_uses_typed_storage_and_privacy_toggle() -> None:
    source = _read(APP)

    assert "STORAGE_KEYS" in source
    assert "maxwellChatMessagesSchema" in source
    assert "maxwellMobileChatHistoryDisabled" in source
    assert "Do not save chat history" in source
    assert "removeStorageItem(STORAGE_KEYS.maxwellMobileChatHistory" in source


def test_zod_is_declared_as_frontend_dependency() -> None:
    source = _read(PACKAGE)
    assert '"zod"' in source
