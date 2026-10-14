"""Test native bundle layouts and noninteractive release validation."""

import json
import os
import subprocess
import sys
import tarfile
import textwrap
from pathlib import Path

import pytest
from PIL import Image
from reportlab.pdfgen import canvas

from scripts import build_native


def make_project(root: Path) -> None:
    """Write the version declarations needed for a packaging fixture."""
    (root / "src").mkdir()
    (root / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")


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
    """Read only the project version, not incidental tool metadata or old CLI code."""
    make_project(tmp_path)
    assert build_native.declared_version(tmp_path) == "1.2.3"
    (tmp_path / "pyproject.toml").write_text('[tool.example]\nversion = "9.9.9"\n')
    with pytest.raises(ValueError, match="Missing"):
        build_native.declared_version(tmp_path)


@pytest.mark.parametrize("system", ["Linux", "Windows"])
def test_build_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, system: str) -> None:
    """Build Unix sidecars and Windows embedded backends without generated residue."""
    make_project(tmp_path)
    commands = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        commands.append(command)
        if "PyInstaller" in command:
            assert command[command.index("--paths") + 1] == str(tmp_path / "src")
            assert command[command.index("--python-option") + 1] == "X utf8"
            assert command[command.index("--copy-metadata") + 1] == "r10n"
            assert command[-1] == str(tmp_path / "src/r10n_backend/__main__.py")
            environment = kwargs["env"]
            assert isinstance(environment, dict)
            assert environment["PYTHONPATH"] == str(tmp_path / "src")
            work = Path(command[command.index("--workpath") + 1])
            work.mkdir()
            (work / "Analysis-00.toc").write_text(
                "r10n_backend/configure/templates/picker.html\nr10n-1.2.3.dist-info/METADATA"
            )
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
                if os.name != "nt":
                    (backend / "_internal" / "shared-library").symlink_to("dependency")
        else:
            assert "-trimpath" in command
            assert "-ldflags=-s -w" in command
            if system == "Windows":
                assert (
                    tmp_path / "internal/backend/payload/backend.bin"
                ).read_bytes() == b"backend"
                assert command[command.index("-tags") + 1] == "bundled"
            Path(command[command.index("-o") + 1]).write_bytes(b"native")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(build_native.platform, "system", lambda: system)
    monkeypatch.setattr(build_native.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(build_native.subprocess, "run", fake_run)
    asset = build_native.build(tmp_path, smoke=False)
    assert asset.exists()
    report = json.loads((tmp_path / "dist" / f"{asset.name}.size.json").read_text())
    assert report["asset_bytes"] == asset.stat().st_size
    assert not (tmp_path / "internal/backend/payload/backend.bin").exists()
    assert not list((tmp_path / "dist").glob("native-build-*"))
    if system == "Linux":
        with tarfile.open(asset) as archive:
            assert "r10n/r10n" in archive.getnames()
            assert "r10n/libexec/r10n-python/r10n-python" in archive.getnames()
            assert "r10n/libexec/r10n-python/_internal/dependency" in archive.getnames()
            if os.name != "nt":
                link = archive.getmember("r10n/libexec/r10n-python/_internal/shared-library")
                assert link.issym()
                assert link.linkname == "dependency"
                assert link.size == 0
        if os.name != "nt":
            installed_link = tmp_path / "dist/r10n/libexec/r10n-python/_internal/shared-library"
            assert installed_link.is_symlink()
            assert installed_link.read_bytes() == b"dependency"
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
            catalog = {"version": "1.2.3", "automations": [{"id": "contacts"}]}
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(catalog))
        assert command[1] == "run"
        assert command[3] == "--input-json"
        assert command[-2:] == ["--json", "--yes"]
        payload = json.loads(command[4])
        assert all(Path(value).is_absolute() for key, value in payload.items() if key != "prefix")
        automation = command[2]
        if automation == "contacts":
            output = Path(payload["output_file"])
            output.write_text(
                f"BEGIN:VCARD\nFN:{payload['prefix']}\nEND:VCARD\n" * 2,
                encoding="utf-8",
            )
        elif automation == "images":
            output = Path(payload["output_directory"])
            output.mkdir()
            with Image.open(Path(payload["input_directory"]) / "sample.png") as image:
                image.save(output / "sample.webp")
        else:
            assert automation == "md2pdf"
            output = Path(payload["output_path"])
            pdf = canvas.Canvas(str(output))
            pdf.drawString(72, 720, "Bundle smoke")
            pdf.save()
        events = [
            {"type": "hello", "protocol": 1},
            {"type": "started"},
            {"type": "progress"},
            {"type": "artifact", "path": str(output)},
            {"type": "completed", "automation": automation, "success": True},
        ]
        return subprocess.CompletedProcess(
            command, 0, stdout="\n".join(json.dumps(event) for event in events)
        )

    monkeypatch.setattr(build_native.subprocess, "run", fake_run)
    build_native.smoke_test(executable, "1.2.3")


def test_bundle_report_counts_symlinks_not_copies(tmp_path: Path) -> None:
    """Catch the library-copy regression without platform-specific byte ceilings."""
    (tmp_path / "original").write_bytes(b"library")
    (tmp_path / "copy").write_bytes(b"library")
    if os.name != "nt":
        (tmp_path / "reference").symlink_to("original")
    report = build_native.bundle_report(tmp_path)
    assert report["bytes"] == 14
    assert report["duplicate_bytes"] == 7
    assert report["symlinks"] == (0 if os.name == "nt" else 1)


def test_bundle_requires_configure_assets(tmp_path: Path) -> None:
    """Fail closed when package data is not collected."""
    make_project(tmp_path)
    with pytest.raises(RuntimeError, match=r"picker\.html"):
        build_native.validate_bundle(tmp_path, tmp_path)


@pytest.mark.parametrize("package", ["typer", "textual", "rich", "pandas", "numpy"])
def test_bundle_rejects_obsolete_runtime(tmp_path: Path, package: str) -> None:
    """Inspect analysis archives as well as loose files for forbidden dependencies."""
    make_project(tmp_path)
    (tmp_path / "Analysis.toc").write_text(
        f"picker.html\nr10n-1.2.3.dist-info/METADATA\n"
        f"('{package}.obsolete', 'unused', 'PYMODULE')",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="Unused runtime"):
        build_native.validate_bundle(tmp_path, tmp_path)


def test_bundle_requires_distribution_metadata(tmp_path: Path) -> None:
    """Frozen importlib.metadata must not silently fall back to a different version."""
    make_project(tmp_path)
    (tmp_path / "picker.html").write_text("picker", encoding="utf-8")
    with pytest.raises(RuntimeError, match="distribution metadata"):
        build_native.validate_bundle(tmp_path, tmp_path)


def test_bundle_allows_vendor_numpy_shim(tmp_path: Path) -> None:
    """A source filename must not be mistaken for a collected top-level package."""
    make_project(tmp_path)
    (tmp_path / "Analysis.toc").write_text(
        "picker.html\nr10n-1.2.3.dist-info/METADATA\n"
        "('setuptools._distutils.compat.numpy', "
        "'/site-packages/setuptools/_distutils/compat/numpy.py', 'PYMODULE')",
        encoding="utf-8",
    )
    build_native.validate_bundle(tmp_path, tmp_path)


def test_bundle_accepts_escaped_windows_metadata_path(tmp_path: Path) -> None:
    """Onefile metadata exists only in TOCs whose Windows paths are repr-escaped."""
    make_project(tmp_path)
    metadata = repr("r10n-1.2.3.dist-info\\METADATA")
    (tmp_path / "Analysis.toc").write_text(
        f"picker.html\n({metadata}, 'source', 'DATA')\n", encoding="utf-8"
    )
    build_native.validate_bundle(tmp_path, tmp_path)


def test_bundle_allows_declared_dependency(tmp_path: Path) -> None:
    """Do not ban a genuine runtime dependency solely because it was once unused."""
    make_project(tmp_path)
    with (tmp_path / "pyproject.toml").open("a", encoding="utf-8") as file:
        file.write('dependencies = ["rich>=1"]\n')
    (tmp_path / "Analysis.toc").write_text(
        "picker.html\nr10n-1.2.3.dist-info/METADATA\n('rich.console', 'module', 'PYMODULE')",
        encoding="utf-8",
    )
    build_native.validate_bundle(tmp_path, tmp_path)


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
