"""Exercise the real Go CLI and Python engine without external services."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def native_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the native frontend once for cross-language integration tests."""
    go = shutil.which("go")
    if go is None:
        pytest.skip("Go is required for native integration tests")
    binary = tmp_path_factory.mktemp("native") / ("r10n.exe" if os.name == "nt" else "r10n")
    subprocess.run(
        [go, "build", "-o", str(binary), "./cmd/r10n"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return binary


@pytest.fixture
def native_environment() -> dict[str, str]:
    """Use the installed test interpreter and explicitly selected source backend."""
    environment = os.environ.copy()
    for key in ("R10N_BACKEND", "R10N_NATIVE", "R10N_MANAGED", "R10N_SOURCE"):
        environment.pop(key, None)
    environment.update(
        R10N_PROJECT=str(ROOT),
        R10N_PYTHON=sys.executable,
        R10N_DISABLE_UPDATE_CHECK="1",
        PYTHONPATH=str(ROOT / "src"),
    )
    return environment


def invoke(
    binary: Path,
    directory: Path,
    environment: dict[str, str],
    *arguments: str,
    payload: dict[str, Any] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke the real executable with bounded execution and captured diagnostics."""
    return subprocess.run(
        [str(binary), *arguments],
        cwd=directory,
        env=environment,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )


def completed_result(process: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    """Require a successful, uncontaminated JSON Lines protocol exchange."""
    assert process.returncode == 0, process.stdout + process.stderr
    events = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
    assert events[0]["type"] == "hello"
    completed = [event for event in events if event["type"] == "completed"]
    assert len(completed) == 1
    assert completed[0]["success"] is True
    return completed[0]["result"]


def test_contacts_flags_preserve_caller_directory(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """Short flags reach the shared worker without changing relative-path meaning."""
    (tmp_path / "numbers.txt").write_text("+94771234567\n+94777654321\n", encoding="utf-8")
    process = invoke(
        native_binary,
        tmp_path,
        native_environment,
        "contacts",
        "-i",
        "numbers.txt",
        "-o",
        "exports/people.vcf",
        "-p",
        "Customer",
        "--yes",
        "--json",
    )
    completed_result(process)
    output = (tmp_path / "exports" / "people.vcf").read_text(encoding="utf-8")
    assert output.count("BEGIN:VCARD") == 2
    assert "Customer" in output


def test_json_stdin_uses_same_worker(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """JSON stdin and public flags share the same execution contract."""
    (tmp_path / "numbers.txt").write_text("+94771234567\n", encoding="utf-8")
    process = invoke(
        native_binary,
        tmp_path,
        native_environment,
        "run",
        "contacts",
        "--input-file",
        "-",
        "--yes",
        "--json",
        payload={"input_file": "numbers.txt", "output_file": "stdin.vcf"},
    )
    completed_result(process)
    # Explicit bare filenames remain relative to the caller's current directory.
    assert (tmp_path / "stdin.vcf").is_file()


def test_source_backend_cannot_be_shadowed_by_caller_package(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """Source jobs run the trusted absolute backend entry, not a CWD lookalike."""
    unrelated = tmp_path / "r10n_backend"
    unrelated.mkdir()
    (unrelated / "__init__.py").write_text(
        'raise RuntimeError("Caller package must not be imported")\n', encoding="utf-8"
    )
    process = invoke(native_binary, tmp_path, native_environment, "list", "--json")
    assert process.returncode == 0, process.stdout + process.stderr
    assert json.loads(process.stdout)["version"] == version("r10n")


def test_worker_protocol_and_files_use_utf8(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """Unicode input/output must not depend on the Windows pipe's code page."""
    (tmp_path / "numbers.txt").write_text("+94771234567\n", encoding="utf-8")
    prefix = "日本語 ✓"
    process = invoke(
        native_binary,
        tmp_path,
        native_environment,
        "contacts",
        "-i",
        "numbers.txt",
        "-o",
        "exports/unicode.vcf",
        "-p",
        prefix,
        "--yes",
        "--json",
    )
    completed_result(process)
    events = [json.loads(line) for line in process.stdout.splitlines()]
    started = next(event for event in events if event["type"] == "started")
    assert "inputs" not in started
    assert "prefix" in started["input_fields"]
    assert prefix in (tmp_path / "exports" / "unicode.vcf").read_text(encoding="utf-8")


def test_images_flags_produce_webp(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """Pillow remains functional behind the native image command."""
    source = tmp_path / "input"
    source.mkdir()
    Image.new("RGB", (32, 24), "red").save(source / "sample.png")
    process = invoke(
        native_binary,
        tmp_path,
        native_environment,
        "images",
        "-i",
        "input",
        "-o",
        "output",
        "-q",
        "80",
        "--preserve-names",
        "--yes",
        "--json",
    )
    completed_result(process)
    outputs = list((tmp_path / "output").glob("*.webp"))
    assert len(outputs) == 1
    with Image.open(outputs[0]) as image:
        assert image.format == "WEBP"
        assert image.size == (32, 24)


def test_markdown_flags_produce_readable_pdf(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """Markdown and ReportLab work without importing a Python CLI framework."""
    (tmp_path / "document.md").write_text("# Native integration\n\nA test document.\n")
    process = invoke(
        native_binary,
        tmp_path,
        native_environment,
        "md2pdf",
        "-i",
        "document.md",
        "-o",
        "document.pdf",
        "--page-size",
        "Letter",
        "--yes",
        "--json",
    )
    completed_result(process)
    reader = PdfReader(tmp_path / "document.pdf")
    assert len(reader.pages) == 1
    assert "Native integration" in reader.pages[0].extract_text()


def test_fill_pdf_flags_render_recipient(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """The Go frontend consumes named profiles from system configuration."""
    template = tmp_path / "template.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=400, height=300)
    writer.write(template)
    (tmp_path / "recipients.csv").write_text("Name\nAlice Smith\n", encoding="utf-8")
    config = {
        "template_pdf": str(template),
        "output_directory": str(tmp_path / "filled"),
        "font_family": "Helvetica",
        "fields": {"name": {"x": 100, "y": 150, "font_size": 18}},
    }
    config_directory = tmp_path / "system-config"
    config_directory.mkdir()
    (config_directory / "config.json").write_text(
        json.dumps(
            {
                "version": 1,
                "active_pdf_profile": "conference",
                "pdf_profiles": {"conference": config},
            }
        ),
        encoding="utf-8",
    )
    environment = native_environment | {"R10N_CONFIG_DIR": str(config_directory)}
    process = invoke(
        native_binary,
        tmp_path,
        environment,
        "fill-pdfs",
        "-c",
        "conference",
        "-r",
        "recipients.csv",
        "--yes",
        "--json",
    )
    completed_result(process)
    outputs = list((tmp_path / "filled").glob("*.pdf"))
    assert len(outputs) == 1
    assert "Alice Smith" in PdfReader(outputs[0]).pages[0].extract_text()


def test_rename_preview_and_explicit_execution(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """Dry-run and execution payloads preserve the worker's file-safety behavior."""
    source = tmp_path / "files"
    source.mkdir()
    (source / "sample.txt").write_text("keep me", encoding="utf-8")
    preview = invoke(
        native_binary,
        tmp_path,
        native_environment,
        "rename",
        "-i",
        "files",
        "--prefix",
        "new_",
        "--dry-run",
        "--yes",
        "--json",
    )
    completed_result(preview)
    assert (source / "sample.txt").is_file()
    assert not (source / "new_sample.txt").exists()
    execution = invoke(
        native_binary,
        tmp_path,
        native_environment,
        "run",
        "rename",
        "--input-file",
        "-",
        "--yes",
        "--json",
        payload={"input_directory": "files", "prefix": "new_", "dry_run": False},
    )
    completed_result(execution)
    assert (source / "new_sample.txt").read_text(encoding="utf-8") == "keep me"


def test_validate_flags_write_report(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """CSV reporting aliases produce artifacts through the canonical schema."""
    (tmp_path / "data.csv").write_text("Name,Email\nAlice,alice@example.com\n", encoding="utf-8")
    process = invoke(
        native_binary,
        tmp_path,
        native_environment,
        "validate",
        "-i",
        "data.csv",
        "-o",
        "report.json",
        "-f",
        "json",
        "--yes",
        "--json",
    )
    completed_result(process)
    assert isinstance(json.loads((tmp_path / "report.json").read_text()), dict)


def test_colors_preview_does_not_modify_input(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """A JSON dry-run previews CSS conversion without side effects."""
    original = ".sample { color: #ff0000; }\n"
    (tmp_path / "style.css").write_text(original, encoding="utf-8")
    process = invoke(
        native_binary,
        tmp_path,
        native_environment,
        "run",
        "colors",
        "--input-file",
        "-",
        "--yes",
        "--json",
        payload={"file": "style.css", "dry_run": True},
    )
    completed_result(process)
    assert (tmp_path / "style.css").read_text(encoding="utf-8") == original
    assert not list(tmp_path.glob("*.bak"))


@pytest.fixture
def website(tmp_path: Path) -> Iterator[str]:
    """Serve a self-contained image page on loopback, never the public network."""
    Image.new("RGB", (16, 16), "blue").save(tmp_path / "sample.png")
    (tmp_path / "index.html").write_text('<html><img src="/sample.png"></html>', encoding="utf-8")

    class Handler(SimpleHTTPRequestHandler):
        """Serve the fixture directory without noisy HTTP request logs."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(tmp_path), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            """Suppress request diagnostics in test output."""

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/index.html"
        finally:
            server.shutdown()
            thread.join(timeout=5)


def test_website_images_flags_use_loopback_fixture(
    native_binary: Path,
    native_environment: dict[str, str],
    tmp_path: Path,
    website: str,
) -> None:
    """The downloader and image conversion run end to end without internet access."""
    process = invoke(
        native_binary,
        tmp_path,
        native_environment,
        "website-images",
        "-u",
        website,
        "-o",
        "downloaded",
        "-f",
        "png",
        "--max-pages",
        "1",
        "--yes",
        "--json",
    )
    completed_result(process)
    assert list((tmp_path / "downloaded").rglob("*.png"))


def test_init_is_removed_without_creating_project_folders(
    native_binary: Path, native_environment: dict[str, str], tmp_path: Path
) -> None:
    """The removed project-local initializer does not scaffold anything."""
    initialized = invoke(native_binary, tmp_path, native_environment, "init")
    assert initialized.returncode == 2
    assert "r10n setup" in initialized.stderr
    assert not (tmp_path / "local").exists()
