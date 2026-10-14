"""Contract tests for the native frontend's Python backend bridge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from src.automation_registry import list_automations
from src.backend import build_catalog
from src.worker import PROTOCOL_VERSION

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_backend(
    *arguments: str,
    input_text: str = "",
    cwd: Path | None = None,
    entry_script: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run the actual backend process with isolated input and captured streams.

    Args:
        arguments: Backend command and arguments.
        input_text: Content supplied to stdin.
        cwd: Optional working directory outside the project.
        entry_script: Execute the file rather than importing it as a module.

    Returns:
        Completed subprocess, including its real exit status and streams.
    """
    environment = os.environ.copy()
    environment["R10N_DISABLE_UPDATE_CHECK"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(PROJECT_ROOT), environment.get("PYTHONPATH")])
    )
    entry = [str(PROJECT_ROOT / "src" / "backend.py")] if entry_script else ["-m", "src.backend"]
    return subprocess.run(
        [sys.executable, "-u", *entry, *arguments],
        input=input_text,
        capture_output=True,
        text=True,
        cwd=cwd or PROJECT_ROOT,
        env=environment,
        timeout=30,
        check=False,
    )


def test_catalog_matches_every_registered_model() -> None:
    """Catalog metadata and schemas are lossless exports of the full registry."""
    result = run_backend("catalog")

    assert result.returncode == 0
    assert result.stderr == ""
    assert len(result.stdout.splitlines()) == 1
    catalog = json.loads(result.stdout)
    assert catalog == build_catalog()
    assert catalog["protocol"] == PROTOCOL_VERSION == 1
    assert len(catalog["automations"]) == len(list_automations())
    for exported, spec in zip(catalog["automations"], list_automations(), strict=True):
        assert exported == {
            "id": spec.id,
            "title": spec.title,
            "description": spec.description,
            "category": spec.category,
            "roles": list(spec.roles),
            "confirmation": spec.confirmation,
            "input_schema": spec.input_model.model_json_schema(),
            "field_order": list(spec.input_model.model_fields),
        }


def test_catalog_preserves_defaults_nullables_enums_and_required_fields() -> None:
    """Frontend forms retain nullable defaults, enum choices, and field order."""
    catalog = {item["id"]: item for item in build_catalog()["automations"]}
    contacts = catalog["contacts"]
    assert contacts["field_order"] == ["input_file", "output_file", "prefix"]
    assert contacts["input_schema"]["properties"]["prefix"]["default"] == "Contact"
    colors = catalog["colors"]["input_schema"]["properties"]
    assert colors["file"]["default"] is None
    assert colors["file"]["anyOf"] == [{"type": "string"}, {"type": "null"}]
    assert colors["dry_run"]["default"] is True
    website = catalog["website-images"]["input_schema"]
    assert website["properties"]["output_format"]["enum"] == ["webp", "jpg", "png"]
    assert website["properties"]["output_format"]["default"] == "webp"
    assert website["required"] == ["url"]
    assert website["additionalProperties"] is False
    assert catalog["contacts"]["confirmation"] is None
    assert isinstance(catalog["email"]["confirmation"], str)


def test_catalog_keeps_automation_and_cli_imports_lazy() -> None:
    """Importing and exporting the catalog loads neither CLI nor automations."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from src.backend import build_catalog; build_catalog(); "
            "assert 'src.cli' not in sys.modules; "
            "assert not any(name.startswith('src.automations') for name in sys.modules)",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_worker_contacts_uses_absolute_paths_outside_project(tmp_path: Path) -> None:
    """Real worker execution emits original events and creates a usable VCF."""
    input_file = tmp_path / "numbers.txt"
    output_file = tmp_path / "output" / "contacts.vcf"
    input_file.write_text("0771234567\n0712345678\n", encoding="utf-8")
    payload = {
        "input_file": str(input_file.resolve()),
        "output_file": str(output_file.resolve()),
        "prefix": "Guest",
    }

    result = run_backend("worker", "contacts", input_text=json.dumps(payload), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert [event["type"] for event in events] == [
        "hello",
        "started",
        "progress",
        "progress",
        "artifact",
        "completed",
    ]
    assert events[0] == {"type": "hello", "protocol": 1}
    assert events[1]["protocol"] == 1
    assert events[1]["automation"] == "contacts"
    assert events[1]["inputs"] == payload
    assert events[-2]["path"] == str(output_file.resolve())
    assert events[-1]["success"] is True
    assert events[-1]["result"]["valid"] == 2
    assert events[-1]["result"]["output_file"] == str(output_file)
    contents = output_file.read_text(encoding="utf-8")
    assert contents.count("BEGIN:VCARD") == 2
    assert "Guest" in contents


@pytest.mark.parametrize(
    ("automation_id", "payload"),
    [
        ("contacts", "{invalid json"),
        ("contacts", "[]"),
        ("contacts", '{"prefix": ""}'),
        ("not-an-automation", "{}"),
    ],
)
def test_worker_input_errors_have_protocol_events_and_exit_two(
    automation_id: str, payload: str
) -> None:
    """Malformed input, validation, and lookup errors preserve worker status 2."""
    result = run_backend("worker", automation_id, input_text=payload)

    assert result.returncode == 2
    assert result.stderr == ""
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert events[0] == {"type": "hello", "protocol": 1}
    assert len(events) == 2
    assert events[1]["type"] == "error"
    assert events[1]["kind"] == "input"
    assert events[1]["error"]


def test_worker_execution_error_preserves_exit_one(tmp_path: Path) -> None:
    """Missing contact input reports execution failure, not a backend traceback."""
    result = run_backend(
        "worker",
        "contacts",
        input_text=json.dumps({"input_file": str(tmp_path / "missing.txt")}),
        cwd=tmp_path,
    )

    assert result.returncode == 1
    assert result.stderr == ""
    events: list[dict[str, Any]] = [json.loads(line) for line in result.stdout.splitlines()]
    assert events[-1]["type"] == "error"
    assert events[-1]["kind"] == "execution"
    assert "missing.txt" in events[-1]["error"]


def test_legacy_version_is_unwrapped_python_cli_output() -> None:
    """Legacy flags bypass argparse and retain the existing CLI's output/status."""
    expected = subprocess.run(
        [sys.executable, "-m", "src.cli", "--version"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    result = run_backend("legacy", "--version")

    assert result.returncode == expected.returncode == 0
    assert result.stdout == expected.stdout
    assert result.stderr == expected.stderr
    assert result.stdout.startswith("r10n, version ")


def test_legacy_error_preserves_cli_exit_status() -> None:
    """An invalid legacy option is handled by Typer, without protocol wrapping."""
    result = run_backend("legacy", "--not-a-real-option")

    assert result.returncode == 2
    assert "No such option" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    "arguments",
    [(), ("unknown",), ("worker",), ("catalog", "--invalid"), ("worker", "contacts", "extra")],
)
def test_invalid_backend_arguments_have_no_traceback(arguments: tuple[str, ...]) -> None:
    """Argparse produces ordinary usage errors for invalid backend invocations."""
    result = run_backend(*arguments)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "usage:" in result.stderr
    assert "Traceback" not in result.stderr


def test_backend_entry_script_uses_absolute_imports(tmp_path: Path) -> None:
    """The entry file works without a package execution context."""
    result = run_backend("catalog", cwd=tmp_path, entry_script=True)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == build_catalog()


def test_trusted_script_ignores_foreign_src_package(tmp_path: Path) -> None:
    """Source launches must not import a backend from the caller's directory."""
    foreign = tmp_path / "src"
    foreign.mkdir()
    (foreign / "__init__.py").write_text(
        'raise RuntimeError("foreign src package was imported")\n', encoding="utf-8"
    )
    (foreign / "backend.py").write_text(
        'raise RuntimeError("foreign backend was executed")\n', encoding="utf-8"
    )
    result = run_backend("catalog", cwd=tmp_path, entry_script=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == build_catalog()
