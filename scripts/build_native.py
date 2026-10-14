"""Build native release assets with a self-contained Python backend.

Install the project and PyInstaller in the active Python environment first.
Build intermediates stay in dist; Windows' Go embed input is temporary.
"""

from __future__ import annotations

import argparse
import hashlib
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
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    ("Linux", "x86_64"): "r10n-linux-x86_64.tar.gz",
    ("Darwin", "arm64"): "r10n-macos-arm64.tar.gz",
    ("Windows", "x86_64"): "r10n-windows-x86_64.exe",
}


def declared_version(root: Path) -> str:
    """Read the sole human-edited release version from project metadata.

    Args:
        root: Source checkout containing project metadata.

    Returns:
        Stable semantic release version.

    Raises:
        ValueError: If the declaration is missing or invalid.
    """
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    section = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)", project)
    metadata = re.search(r'^version\s*=\s*"([^"]+)"', section[1], re.MULTILINE) if section else None
    if not metadata:
        raise ValueError("Missing pyproject.toml project version")
    if not re.fullmatch(r"\d+\.\d+\.\d+", metadata[1]):
        raise ValueError(f"Unsupported release version: {metadata[1]}")
    return metadata[1]


def bundle_report(directory: Path) -> dict[str, Any]:
    """Describe bundle size without counting symlinks as duplicated libraries.

    Args:
        directory: Frozen runtime directory to inspect.

    Returns:
        JSON-compatible size, symlink, and content-duplicate statistics.
    """
    files = [path for path in directory.rglob("*") if path.is_file() and not path.is_symlink()]
    groups: dict[str, list[str]] = {}
    sizes: dict[str, int] = {}
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        groups.setdefault(digest, []).append(str(path.relative_to(directory)))
        sizes[digest] = path.stat().st_size
    duplicates = [
        {"bytes": sizes[digest], "paths": paths}
        for digest, paths in groups.items()
        if len(paths) > 1 and sizes[digest] > 0
    ]
    return {
        "bytes": sum(path.stat().st_size for path in files),
        "files": len(files),
        "symlinks": sum(path.is_symlink() for path in directory.rglob("*")),
        "duplicate_bytes": sum(
            sizes[digest] * (len(paths) - 1) for digest, paths in groups.items() if len(paths) > 1
        ),
        "duplicates": duplicates,
    }


def validate_bundle(directory: Path, root: Path) -> None:
    """Reject missing configure assets and obsolete frozen UI runtimes.

    Args:
        directory: PyInstaller output, including its analysis archive listing.
        root: Source checkout supplying declared runtime dependencies.

    Raises:
        RuntimeError: If required package data is missing or obsolete modules leaked in.
    """
    paths = [path.relative_to(directory) for path in directory.rglob("*")]
    contents = "\n".join(str(path) for path in paths)
    # Analysis TOCs include modules compressed into PYZ/onefile, not just loose files.
    analysis = ""
    for path in directory.rglob("*.toc"):
        analysis += "\n" + path.read_text(encoding="utf-8")
    contents += analysis
    if "picker.html" not in contents:
        raise RuntimeError("Frozen backend is missing configure/templates/picker.html")
    if not re.search(r"r10n-[^/\\'\"]+\.dist-info[/\\]METADATA", contents):
        raise RuntimeError("Frozen backend is missing r10n distribution metadata")
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    dependencies = re.search(r"(?s)dependencies\s*=\s*\[(.*?)\]", project)
    declared = dependencies[1].lower() if dependencies else ""
    for package in ("typer", "textual", "rich", "pandas", "numpy"):
        if re.search(rf'["\']{package}(?:[<>=!~;\["\'])', declared):
            continue
        # TOC entries begin with the collected module/destination, followed by its
        # source path. A vendor shim such as setuptools._distutils.compat.numpy
        # is not NumPy, even though its source filename happens to be numpy.py.
        collected_module = re.search(rf"(?i)\(\s*['\"]{package}(?:[./\\'\"])", analysis)
        loose_package = any(
            package in path.parts
            or (
                path.name == f"{package}.py"
                and (path.parent == Path(".") or path.parent.name == "_internal")
            )
            for path in paths
        )
        if collected_module or loose_package:
            raise RuntimeError(f"Unused runtime dependency leaked into frozen backend: {package}")


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
    """Run contacts, image optimization and PDF conversion outside the checkout.

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
        catalog_data = json.loads(catalog.stdout)
        if catalog_data.get("version") != version:
            raise RuntimeError(f"Frozen Python metadata version mismatch: {catalog_data!r}")
        if not any(task["id"] == "contacts" for task in catalog_data["automations"]):
            raise RuntimeError("Bundled registry did not contain contacts")
        from PIL import Image
        from pypdf import PdfReader

        images = directory / "images"
        images.mkdir()
        optimized = directory / "optimized"
        Image.new("RGB", (32, 24), color=(42, 80, 140)).save(images / "sample.png")
        markdown = directory / "document.md"
        markdown.write_text("# Bundle smoke\n\nGenerated outside the checkout.\n", encoding="utf-8")
        pdf = directory / "document.pdf"
        jobs = [
            (
                "images",
                {"input_directory": str(images), "output_directory": str(optimized)},
            ),
            ("md2pdf", {"input_path": str(markdown), "output_path": str(pdf)}),
        ]
        for automation, inputs in jobs:
            completed = subprocess.run(
                [
                    str(executable),
                    "run",
                    automation,
                    "--input-json",
                    json.dumps(inputs),
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
            results = [event for event in events if event["type"] == "completed"]
            if (
                not results
                or not results[-1].get("success")
                or results[-1].get("automation") != automation
            ):
                raise RuntimeError(f"{automation} smoke failed: {events!r}")
        webp = list(optimized.glob("*.webp"))
        if len(webp) != 1:
            raise RuntimeError("Image worker did not produce one WebP")
        with Image.open(webp[0]) as image:
            if image.format != "WEBP" or image.size != (32, 24):
                raise RuntimeError("Image worker produced an invalid WebP")
        reader = PdfReader(pdf)
        if len(reader.pages) != 1 or "Bundle smoke" not in (reader.pages[0].extract_text() or ""):
            raise RuntimeError("PDF worker did not produce expected content")


def build(root: Path = ROOT, *, smoke: bool = True) -> Path:
    """Build the host release asset and optionally verify its real worker.

    Args:
        root: Source checkout with Go and Python dependencies available.
        smoke: Whether to execute bundled worker and artifact verification.

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
                str(root / "src"),
                "--copy-metadata",
                "r10n",
                "--add-data",
                f"{root / 'src/r10n_backend/configure/templates'}{os.pathsep}r10n_backend/configure/templates",
                "--collect-all",
                "pypdfium2",
                "--collect-all",
                "PIL",
                "--collect-data",
                "certifi",
                str(root / "src" / "r10n_backend" / "__main__.py"),
            ],
            cwd=root,
            env={**os.environ, "PYTHONPATH": str(root / "src")},
            check=True,
        )
        validate_bundle(staging, root)
        report = bundle_report(staging / "python")
        print("Frozen runtime report:", json.dumps(report, indent=2))
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
        report["asset_bytes"] = archive_path.stat().st_size
        (dist / f"{asset}.size.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
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
