"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _disable_tool_installation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never reach a real package manager from the test suite."""
    monkeypatch.setenv("R10N_DISABLE_TOOL_INSTALL", "1")
