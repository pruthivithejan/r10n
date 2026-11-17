"""Locate external binaries and install them on demand.

Automations should not bundle heavyweight system tools. Resolve the binary from
the system first, then ask the platform package manager to install it.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_cache_dir

DEFAULT_TIMEOUT = 900.0
WINGET_FLAGS = ("--accept-source-agreements", "--accept-package-agreements", "--silent")


class ToolUnavailableError(RuntimeError):
    """Raised when a required external tool cannot be found or installed."""


@dataclass(frozen=True)
class ToolSpec:
    """Description of one external tool and its package names."""

    binary: str
    packages: Mapping[str, str]


TOOLS: Mapping[str, ToolSpec] = {
    "ffmpeg": ToolSpec(
        binary="ffmpeg",
        packages={
            "brew": "ffmpeg",
            "port": "ffmpeg",
            "apt-get": "ffmpeg",
            "dnf": "ffmpeg",
            "zypper": "ffmpeg",
            "pacman": "ffmpeg",
            "apk": "ffmpeg",
            "winget": "Gyan.FFmpeg",
            "choco": "ffmpeg",
            "scoop": "ffmpeg",
        },
    ),
}

MANAGER_ARGUMENTS: Mapping[str, tuple[str, ...]] = {
    "brew": ("install",),
    "port": ("install",),
    "apt-get": ("install", "-y"),
    "dnf": ("install", "-y"),
    "zypper": ("--non-interactive", "install"),
    "pacman": ("-S", "--noconfirm"),
    "apk": ("add",),
    "winget": ("install", "-e", "--id"),
    "choco": ("install", "-y", "--no-progress"),
    "scoop": ("install",),
}

MANAGER_REQUIRES_ROOT: Mapping[str, bool] = {
    "brew": False,
    "port": True,
    "apt-get": True,
    "dnf": True,
    "zypper": True,
    "pacman": True,
    "apk": True,
    "winget": False,
    "choco": False,
    "scoop": False,
}

PLATFORM_MANAGERS: Mapping[str, tuple[str, ...]] = {
    "darwin": ("brew", "port"),
    "linux": ("apt-get", "dnf", "zypper", "pacman", "apk"),
    "win32": ("winget", "choco", "scoop"),
}


def _spec(name: str) -> ToolSpec:
    """Return the spec for a known tool.

    Args:
        name: Stable tool name, such as ``ffmpeg``.

    Returns:
        Matching tool specification.

    Raises:
        ToolUnavailableError: If the tool is not known.
    """
    try:
        return TOOLS[name]
    except KeyError as error:
        raise ToolUnavailableError(f"Unknown external tool: {name}") from error


def _is_root() -> bool:
    """Return whether the current POSIX process runs as root."""
    return hasattr(os, "geteuid") and os.geteuid() == 0


def _search_directories() -> list[Path]:
    """Return directories that package managers may install binaries into."""
    directories: list[Path] = []
    override = os.environ.get("R10N_TOOLS_DIR")
    if override:
        directories.append(Path(override))
    directories.append(Path(user_cache_dir("r10n")) / "tools" / "bin")
    if sys.platform == "darwin":
        directories.extend((Path("/opt/homebrew/bin"), Path("/usr/local/bin")))
    else:
        directories.extend((Path("/usr/local/bin"), Path("/usr/bin")))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        directories.extend(
            (
                Path(local_app_data) / "Microsoft" / "WinGet" / "Links",
                Path(local_app_data) / "Programs",
            )
        )
    program_data = os.environ.get("PROGRAMDATA")
    if program_data:
        directories.append(Path(program_data) / "chocolatey" / "bin")
    return directories


def _executable_names(binary: str) -> tuple[str, ...]:
    """Return candidate filenames for the current platform."""
    if os.name == "nt":
        return (f"{binary}.exe", binary)
    return (binary,)


def find_tool(name: str) -> str | None:
    """Return the path of an installed tool without installing anything.

    Args:
        name: Stable tool name, such as ``ffmpeg``.

    Returns:
        Absolute path to the executable, or ``None`` when it is missing.
    """
    spec = _spec(name)
    found = shutil.which(spec.binary)
    if found:
        return found
    for directory in _search_directories():
        for filename in _executable_names(spec.binary):
            candidate = directory / filename
            if candidate.is_file() and (os.name == "nt" or os.access(candidate, os.X_OK)):
                return str(candidate)
    return None


def _available_managers() -> list[str]:
    """Return installed package managers that can install tools."""
    managers: list[str] = []
    for manager in PLATFORM_MANAGERS.get(sys.platform, ()):
        if shutil.which(manager) is None:
            continue
        if MANAGER_REQUIRES_ROOT[manager] and not _is_root() and shutil.which("sudo") is None:
            continue
        managers.append(manager)
    return managers


def _install_command(manager: str, spec: ToolSpec) -> list[str]:
    """Build the non-interactive install command for one manager."""
    executable = shutil.which(manager) or manager
    command = [executable, *MANAGER_ARGUMENTS[manager], spec.packages[manager]]
    if manager == "winget":
        command.extend(WINGET_FLAGS)
    if MANAGER_REQUIRES_ROOT[manager] and not _is_root():
        command = ["sudo", "-n", *command]
    return command


def _manual_hint(spec: ToolSpec) -> str:
    """Return a copyable install command for the current system."""
    managers = _available_managers()
    if not managers:
        return "install it with your system package manager"
    manager = managers[0]
    command = [manager, *MANAGER_ARGUMENTS[manager], spec.packages[manager]]
    if manager == "winget":
        command.extend(WINGET_FLAGS)
    prefix = "sudo " if MANAGER_REQUIRES_ROOT[manager] and not _is_root() else ""
    return f"`{prefix}{shlex.join(command)}`"


def _timeout() -> float:
    """Return the install timeout in seconds."""
    raw = os.environ.get("R10N_TOOL_INSTALL_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        return max(30.0, float(raw))
    except ValueError:
        return DEFAULT_TIMEOUT


def install_tool(name: str) -> None:
    """Install a tool through the first available package manager.

    Args:
        name: Stable tool name, such as ``ffmpeg``.

    Raises:
        ToolUnavailableError: If every supported package manager fails.
    """
    spec = _spec(name)
    failures: list[str] = []
    for manager in _available_managers():
        command = _install_command(manager, spec)
        print(f"r10n: installing {name} with {manager}", file=sys.stderr)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=_timeout(),
                check=False,
                env={
                    **os.environ,
                    "DEBIAN_FRONTEND": "noninteractive",
                    "HOMEBREW_NO_AUTO_UPDATE": "1",
                },
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            failures.append(f"{manager}: {error}")
            continue
        if completed.returncode == 0:
            if find_tool(name):
                return
            failures.append(f"{manager}: installed but {spec.binary} is still missing")
            continue
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        failures.append(f"{manager}: {detail[-1] if detail else 'installation failed'}")
    message = f"{name} is required but could not be installed automatically."
    if failures:
        message += " " + "; ".join(failures)
    raise ToolUnavailableError(f"{message} Try {_manual_hint(spec)}.")


def ensure_tool(name: str, *, install: bool = True) -> str:
    """Return an installed tool, installing it when allowed.

    Args:
        name: Stable tool name, such as ``ffmpeg``.
        install: Try the platform package manager when the tool is missing.

    Returns:
        Absolute path to the executable.

    Raises:
        ToolUnavailableError: If the tool is missing and cannot be installed.
    """
    found = find_tool(name)
    if found:
        return found
    if install and os.environ.get("R10N_DISABLE_TOOL_INSTALL") != "1":
        install_tool(name)
        found = find_tool(name)
        if found:
            return found
    spec = _spec(name)
    raise ToolUnavailableError(
        f"{name} is required. Try {_manual_hint(spec)}." if install else f"{name} is required."
    )
