"""Test native bundle layouts and noninteractive release validation."""

import json
import os
import subprocess
import sys
import tarfile
import textwrap
from pathlib import Path

import pytest

from scripts import build_native


def make_project(root: Path) -> None:
    """Write the version declarations needed for a packaging fixture."""
    (root / "src").mkdir()
    (root / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")
    (root / "src" / "cli.py").write_text('VERSION = "1.2.3"\n', encoding="utf-8")


@pytest.mark.parametrize(
    ("system", "machine", "asset"),
    [
        ("Linux", "x86_64", "r10n-linux-x86_64.tar.gz"),
        ("Darwin", "aarch64", "r10n-macos-arm64.tar.gz"),
        ("Windows", "AMD64", "r10n-windows-x86_64.exe"),
    ],
)
def test_asset_names(system: str, machine: str, asset: str) -> None:
    """Preserve names consumed by the installer and upgrade command."""
    assert build_native.asset_name(system, machine) == asset


def test_unsupported_platform() -> None:
    """Do not silently ship a host build under another architecture's name."""
    with pytest.raises(ValueError, match="Unsupported release platform"):
        build_native.asset_name("Linux", "arm64")


def test_declared_versions(tmp_path: Path) -> None:
    """Validate project and CLI agreement before building."""
    make_project(tmp_path)
    assert build_native.declared_version(tmp_path) == "1.2.3"
    (tmp_path / "src" / "cli.py").write_text('VERSION = "1.2.4"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="mismatched"):
        build_native.declared_version(tmp_path)


@pytest.mark.parametrize("system", ["Linux", "Windows"])
def test_build_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, system: str) -> None:
    """Build Unix sidecars and Windows embedded backends without generated residue."""
    make_project(tmp_path)
    commands = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        commands.append(command)
        if "PyInstaller" in command:
            output = Path(command[command.index("--distpath") + 1])
            output.mkdir()
            if system == "Windows":
                (output / "r10n-python.exe").write_bytes(b"backend")
            else:
                backend = output / "r10n-python"
                backend.mkdir()
                (backend / "r10n-python").write_bytes(b"backend")
                (backend / "_internal").mkdir()
                (backend / "_internal" / "dependency").write_bytes(b"dependency")
        else:
            if system == "Windows":
                assert (
                    tmp_path / "internal/backend/payload/backend.bin"
                ).read_bytes() == b"backend"
                assert command[2:4] == ["-tags", "bundled"]
            Path(command[command.index("-o") + 1]).write_bytes(b"native")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(build_native.platform, "system", lambda: system)
    monkeypatch.setattr(build_native.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(build_native.subprocess, "run", fake_run)
    asset = build_native.build(tmp_path, smoke=False)
    assert asset.exists()
    assert not (tmp_path / "internal/backend/payload/backend.bin").exists()
    assert not list((tmp_path / "dist").glob("native-build-*"))
    if system == "Linux":
        with tarfile.open(asset) as archive:
            assert "r10n/r10n" in archive.getnames()
            assert "r10n/libexec/r10n-python/r10n-python" in archive.getnames()
            assert "r10n/libexec/r10n-python/_internal/dependency" in archive.getnames()
        assert "-tags" not in commands[-1]
    else:
        assert asset.read_bytes() == b"native"


def test_smoke_runs_worker_outside_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Smoke verification exercises native commands, worker output, and catalog."""
    executable = tmp_path / "r10n"
    executable.write_bytes(b"native")
    monkeypatch.setenv("R10N_BACKEND", "/unrelated/backend")
    monkeypatch.setenv("R10N_PROJECT", "/unrelated/checkout")
    monkeypatch.setenv("R10N_PYTHON", "/unrelated/python")

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        assert kwargs["cwd"] != tmp_path
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        assert not {"R10N_BACKEND", "R10N_PROJECT", "R10N_PYTHON"} & environment.keys()
        assert command[0] == str(executable)
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, stdout="r10n, version 1.2.3\n")
        if "list" in command:
            catalog = {"automations": [{"id": "contacts"}]}
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(catalog))
        assert command[1:4] == ["run", "contacts", "--input-json"]
        assert command[-2:] == ["--json", "--yes"]
        payload = json.loads(command[4])
        assert Path(payload["input_file"]).is_absolute()
        output = Path(payload["output_file"])
        assert output.is_absolute()
        output.write_text("BEGIN:VCARD\nEND:VCARD\n" * 2, encoding="utf-8")
        events = [
            {"type": "hello", "protocol": 1},
            {"type": "started"},
            {"type": "progress"},
            {"type": "artifact", "path": str(output)},
            {"type": "completed", "automation": "contacts", "success": True},
        ]
        return subprocess.CompletedProcess(
            command, 0, stdout="\n".join(json.dumps(event) for event in events)
        )

    monkeypatch.setattr(build_native.subprocess, "run", fake_run)
    build_native.smoke_test(executable, "1.2.3")


@pytest.mark.skipif(sys.version_info < (3, 11), reason="The release resolver runs on Python 3.11")
@pytest.mark.parametrize(
    ("event", "ref", "old", "expected"),
    [
        ("push", "refs/heads/main", "1.2.3", "false"),
        ("push", "refs/heads/main", "1.2.2", "true"),
        ("push", "refs/tags/v1.2.3", "1.2.3", "true"),
        ("workflow_dispatch", "refs/heads/main", "1.2.3", "true"),
    ],
)
def test_release_trigger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    event: str,
    ref: str,
    old: str,
    expected: str,
) -> None:
    """Execute the release workflow's resolver without publishing anything."""
    make_project(tmp_path)
    workflow = (build_native.ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    code = textwrap.dedent(workflow.split("        run: |\n", 1)[1].split("\n  build:", 1)[0])
    output = tmp_path / "outputs"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REF", ref)
    monkeypatch.setenv("GITHUB_REF_NAME", ref.rsplit("/", 1)[1])
    monkeypatch.setenv("GITHUB_EVENT_NAME", event)
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("BEFORE", "a" * 40)

    def fake_check_output(command: list[str], **kwargs: object) -> str:
        if command == ["git", "rev-parse", "HEAD"]:
            return "b" * 40 + "\n"
        assert command == ["git", "show", f"{os.environ['BEFORE']}:pyproject.toml"]
        return f'[project]\nversion = "{old}"\n'

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    monkeypatch.setattr(
        subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 1, "")
    )
    exec(compile(code, "release.yml", "exec"), {})
    assert f"publish={expected}\n" in output.read_text(encoding="utf-8")
