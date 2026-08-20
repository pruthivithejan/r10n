"""Tests for the versioned automation worker protocol."""

import json

from typer.testing import CliRunner

from src import cli
from src.worker import PROTOCOL_VERSION, find_artifacts, run_automation


class TestWorkerProtocol:
    """Verify structured worker execution and artifact reporting."""

    def test_runs_contacts_and_emits_lifecycle_events(self, tmp_path):
        """A worker validates input, runs the automation, and reports output."""
        input_file = tmp_path / "numbers.txt"
        output_file = tmp_path / "contacts.vcf"
        input_file.write_text("0771234567\n0712345678\n", encoding="utf-8")
        events = []

        result = run_automation(
            "contacts",
            {
                "input_file": str(input_file),
                "output_file": str(output_file),
                "prefix": "Guest",
            },
            events.append,
        )

        assert result["valid"] == 2
        assert output_file.exists()
        assert [event["type"] for event in events] == [
            "started",
            "progress",
            "progress",
            "artifact",
            "completed",
        ]
        assert events[0]["protocol"] == PROTOCOL_VERSION
        assert events[-1]["result"]["output_file"] == str(output_file)

    def test_hidden_worker_command_writes_json_lines(self, tmp_path, monkeypatch):
        """The CLI worker command is machine-readable and omitted from help."""
        monkeypatch.setenv("R10N_DISABLE_UPDATE_CHECK", "1")
        input_file = tmp_path / "numbers.txt"
        output_file = tmp_path / "contacts.vcf"
        input_file.write_text("0771234567\n", encoding="utf-8")
        payload = json.dumps(
            {
                "input_file": str(input_file),
                "output_file": str(output_file),
                "prefix": "Guest",
            }
        )
        runner = CliRunner()

        result = runner.invoke(cli.app, ["_worker", "contacts", "--input-json", payload])

        assert result.exit_code == 0
        events = [json.loads(line) for line in result.output.splitlines()]
        assert events[0] == {"type": "hello", "protocol": PROTOCOL_VERSION}
        assert events[-1]["type"] == "completed"

        help_result = runner.invoke(cli.app, ["--help"])
        assert "_worker" not in help_result.output

    def test_artifacts_only_include_existing_output_paths(self, tmp_path):
        """Artifact discovery ignores missing paths and ordinary strings."""
        report = tmp_path / "report.json"
        report.write_text("{}", encoding="utf-8")

        artifacts = find_artifacts(
            {
                "report_file": str(report),
                "output_file": str(tmp_path / "missing.txt"),
                "message": str(report),
            }
        )

        assert artifacts == [str(report.resolve())]
