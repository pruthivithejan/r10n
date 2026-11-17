"""External tool discovery and on-demand installation."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from r10n_backend import deps


@pytest.fixture(autouse=True)
def _isolate_tool_directories(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not pick up ffmpeg from the developer machine."""
    monkeypatch.setattr(deps, "_search_directories", list)


def test_find_tool_prefers_the_system_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """A PATH binary wins over cached locations."""
    monkeypatch.setattr(deps.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    assert deps.find_tool("ffmpeg") == "/usr/bin/ffmpeg"


def test_find_tool_checks_the_per_user_tools_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A binary installed into the r10n tools directory is discovered."""
    binary = tmp_path / "ffmpeg"
    binary.write_text("", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("R10N_TOOLS_DIR", str(tmp_path))
    monkeypatch.setattr(deps, "_search_directories", lambda: [tmp_path])
    monkeypatch.setattr(deps.shutil, "which", lambda name: None)
    assert deps.find_tool("ffmpeg") == str(binary)


def test_ensure_tool_returns_an_installed_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    """No package manager is touched when the tool already exists."""
    monkeypatch.setattr(deps.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    assert deps.ensure_tool("ffmpeg") == "/usr/bin/ffmpeg"


def test_ensure_tool_respects_the_disable_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests and offline runs can forbid automatic installation."""
    monkeypatch.setattr(deps.shutil, "which", lambda name: None)
    monkeypatch.setenv("R10N_DISABLE_TOOL_INSTALL", "1")
    with pytest.raises(deps.ToolUnavailableError, match="ffmpeg is required"):
        deps.ensure_tool("ffmpeg")


def test_install_uses_homebrew_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Homebrew is the first macOS installer and needs no sudo."""
    calls: list[list[str]] = []

    def run(command, **kwargs):
        calls.append(command)
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(deps.sys, "platform", "darwin")
    monkeypatch.setattr(
        deps.shutil, "which", lambda name: "/opt/homebrew/bin/brew" if name == "brew" else None
    )
    monkeypatch.setattr(deps.subprocess, "run", run)
    monkeypatch.setattr(deps, "find_tool", lambda name: "/opt/homebrew/bin/ffmpeg")

    deps.install_tool("ffmpeg")

    assert calls == [["/opt/homebrew/bin/brew", "install", "ffmpeg"]]


def test_install_uses_non_interactive_sudo_on_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Linux package managers run unattended under sudo."""
    calls: list[list[str]] = []

    def run(command, **kwargs):
        calls.append(command)
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(deps.sys, "platform", "linux")
    monkeypatch.setattr(deps.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(
        deps.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"apt-get", "sudo"} else None,
    )
    monkeypatch.setattr(deps.subprocess, "run", run)
    monkeypatch.setattr(deps, "find_tool", lambda name: "/usr/bin/ffmpeg")

    deps.install_tool("ffmpeg")

    assert calls == [["sudo", "-n", "/usr/bin/apt-get", "install", "-y", "ffmpeg"]]


def test_install_falls_back_to_the_next_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed manager does not stop the remaining ones."""
    calls: list[list[str]] = []

    def run(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            return CompletedProcess(command, 1, "", "brew failed")
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(deps.sys, "platform", "darwin")
    monkeypatch.setattr(
        deps.shutil,
        "which",
        lambda name: (
            f"/opt/homebrew/bin/{name}"
            if name in {"brew", "port"}
            else "/usr/bin/sudo" if name == "sudo" else None
        ),
    )
    monkeypatch.setattr(deps.subprocess, "run", run)
    monkeypatch.setattr(deps, "find_tool", lambda name: "/opt/homebrew/bin/ffmpeg")

    deps.install_tool("ffmpeg")

    assert calls[0] == ["/opt/homebrew/bin/brew", "install", "ffmpeg"]
    assert calls[1] == ["sudo", "-n", "/opt/homebrew/bin/port", "install", "ffmpeg"]


def test_install_failure_reports_the_manual_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed install surfaces the exact command to run by hand."""
    monkeypatch.setattr(deps.sys, "platform", "darwin")
    monkeypatch.setattr(
        deps.shutil, "which", lambda name: "/opt/homebrew/bin/brew" if name == "brew" else None
    )
    monkeypatch.setattr(
        deps.subprocess,
        "run",
        lambda command, **kwargs: CompletedProcess(command, 1, "", "network failed"),
    )
    monkeypatch.setattr(deps, "find_tool", lambda name: None)

    with pytest.raises(deps.ToolUnavailableError, match="brew install ffmpeg"):
        deps.install_tool("ffmpeg")


def test_unknown_tools_are_rejected() -> None:
    """Only known tools can be resolved."""
    with pytest.raises(deps.ToolUnavailableError, match="Unknown external tool"):
        deps.find_tool("not-a-tool")
