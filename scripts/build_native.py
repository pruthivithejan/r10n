"""Build native release assets with a self-contained Python backend.

Install the project and PyInstaller in the active Python environment first.
Build intermediates stay in dist; Windows' Go embed input is temporary.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    ("Linux", "x86_64"): "r10n-linux-x86_64.tar.gz",
    ("Darwin", "arm64"): "r10n-macos-arm64.tar.gz",
    ("Windows", "x86_64"): "r10n-windows-x86_64.exe",
}


def declared_version(root: Path) -> str:
    """Read and validate the synchronized project and CLI versions.

    Args:
        root: Source checkout containing the project and CLI metadata.

    Returns:
        Stable semantic release version.

    Raises:
        ValueError: If the declarations are missing, invalid, or inconsistent.
    """
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    section = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)", project)
    metadata = re.search(r'^version\s*=\s*"([^"]+)"', section[1], re.MULTILINE) if section else None
    cli = re.search(
        r'^VERSION\s*=\s*"([^"]+)"',
        (root / "src" / "cli.py").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not metadata or not cli or metadata[1] != cli[1]:
        raise ValueError("Missing or mismatched pyproject.toml and src/cli.py versions")
    if not re.fullmatch(r"\d+\.\d+\.\d+", metadata[1]):
        raise ValueError(f"Unsupported release version: {metadata[1]}")
    return metadata[1]


def asset_name(system: str, machine: str) -> str:
    """Return the existing installer-compatible asset name for a host.

    Args:
        system: Platform system name, such as Linux or Windows.
        machine: Platform architecture name, including supported aliases.

    Returns:
        Published asset filename.

    Raises:
        ValueError: If no release asset is built for this platform.
    """
    architecture = {"amd64": "x86_64", "aarch64": "arm64"}.get(machine.lower(), machine.lower())
    try:
        return ASSETS[(system, architecture)]
    except KeyError as error:
        raise ValueError(f"Unsupported release platform: {system} {machine}") from error


def smoke_test(executable: Path, version: str) -> None:
    """Run the bundled contacts worker from outside the source checkout.

    Args:
        executable: Absolute path to the built native executable.
        version: Expected shared release version.

    Raises:
        RuntimeError: If version, events, artifacts, or catalog are incorrect.
        subprocess.CalledProcessError: If the native shell or worker fails.
    """
    environment = os.environ.copy()
    for key in ("R10N_BACKEND", "R10N_PROJECT", "R10N_PYTHON", "PYTHONPATH"):
        environment.pop(key, None)
    environment["R10N_DISABLE_UPDATE_CHECK"] = "1"
    with tempfile.TemporaryDirectory(prefix="r10n-smoke-") as temporary:
        directory = Path(temporary).resolve()
        reported = subprocess.run(
            [str(executable), "--version"],
            cwd=directory,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if reported.stdout.strip() != f"r10n, version {version}":
            raise RuntimeError(f"Native version mismatch: {reported.stdout!r}")
        input_file = directory / "numbers.txt"
        output_file = directory / "contacts.vcf"
        input_file.write_text("+94771234567\n+94777654321\n", encoding="utf-8")
        payload = {
            "input_file": str(input_file),
            "output_file": str(output_file),
            "prefix": "Bundle",
        }
        completed = subprocess.run(
            [
                str(executable),
                "run",
                "contacts",
                "--input-json",
                json.dumps(payload),
                "--json",
                "--yes",
            ],
            cwd=directory,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        events = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
        event_types = {event["type"] for event in events}
        if not {"hello", "started", "progress", "artifact", "completed"} <= event_types:
            raise RuntimeError(f"Incomplete worker protocol: {events!r}")
        result = next(event for event in events if event["type"] == "completed")
        if not result.get("success") or result.get("automation") != "contacts":
            raise RuntimeError(f"Contacts worker failed: {result!r}")
        if (
            not output_file.exists()
            or output_file.read_text(encoding="utf-8").count("BEGIN:VCARD") != 2
        ):
            raise RuntimeError("Contacts worker did not produce the expected VCF")
        catalog = subprocess.run(
            [str(executable), "list", "--json"],
            cwd=directory,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if not any(task["id"] == "contacts" for task in json.loads(catalog.stdout)["automations"]):
            raise RuntimeError("Bundled registry did not contain contacts")


def build(root: Path = ROOT, *, smoke: bool = True) -> Path:
    """Build the host release asset and optionally verify its real worker.

    Args:
        root: Source checkout with Go and Python dependencies available.
        smoke: Whether to execute the bundled contacts verification.

    Returns:
        Path to the host's installer-compatible release asset.

    Raises:
        ValueError: If versions or the host platform are unsupported.
        FileExistsError: If a Windows embed input would be overwritten.
        subprocess.CalledProcessError: If a build command fails.
    """
    root = root.resolve()
    version = declared_version(root)
    asset = asset_name(platform.system(), platform.machine())
    windows = platform.system() == "Windows"
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="native-build-", dir=dist) as temporary:
        staging = Path(temporary)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--name",
                "r10n-python",
                "--onefile" if windows else "--onedir",
                "--distpath",
                str(staging / "python"),
                "--workpath",
                str(staging / "work"),
                "--specpath",
                str(staging),
                "--paths",
                str(root),
                "--collect-all",
                "pypdfium2",
                "--collect-all",
                "PIL",
                "--collect-data",
                "certifi",
                str(root / "src" / "backend.py"),
            ],
            cwd=root,
            check=True,
        )
        if windows:
            payload = root / "internal" / "backend" / "payload" / "backend.bin"
            if payload.exists():
                raise FileExistsError(f"Refusing to overwrite embed input: {payload}")
            payload.parent.mkdir(parents=True, exist_ok=True)
            executable = dist / asset
            shutil.copy2(staging / "python" / "r10n-python.exe", payload)
            try:
                subprocess.run(
                    [
                        "go",
                        "build",
                        "-trimpath",
                        "-ldflags=-s -w",
                        "-tags",
                        "bundled",
                        "-o",
                        str(executable),
                        "./cmd/r10n",
                    ],
                    cwd=root,
                    check=True,
                )
            finally:
                payload.unlink()
        else:
            app = staging / "r10n"
            sidecar = app / "libexec"
            sidecar.mkdir(parents=True)
            # PyInstaller shares native libraries through relative symlinks. Following
            # them here duplicates the Python framework and Pillow libraries in releases.
            shutil.copytree(
                staging / "python" / "r10n-python",
                sidecar / "r10n-python",
                symlinks=True,
            )
            subprocess.run(
                [
                    "go",
                    "build",
                    "-trimpath",
                    "-ldflags=-s -w",
                    "-o",
                    str(app / "r10n"),
                    "./cmd/r10n",
                ],
                cwd=root,
                check=True,
            )
            installed = dist / "r10n"
            if installed.exists():
                shutil.rmtree(installed)
            shutil.move(str(app), installed)
            executable = installed / "r10n"
        if smoke:
            smoke_test(executable, version)
        archive_path = dist / asset
        if not windows:
            with tarfile.open(archive_path, "w:gz") as archive:
                archive.add(dist / "r10n", arcname="r10n")
    return archive_path


def main() -> None:
    """Run the noninteractive host build CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-smoke", action="store_true", help="Build without worker verification"
    )
    args = parser.parse_args()
    print(build(smoke=not args.skip_smoke))


if __name__ == "__main__":
    main()
