"""Tests for the versioned automation worker protocol."""

import json

from r10n_backend.__main__ import main
from r10n_backend.worker import PROTOCOL_VERSION, find_artifacts, run_automation


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

    def test_worker_command_writes_json_lines(self, tmp_path, capsys):
        """The backend worker command accepts inline input and emits JSONL."""
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
        assert main(["worker", "contacts", "--input-json", payload]) == 0
        events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert events[0] == {"type": "hello", "protocol": PROTOCOL_VERSION}
        assert events[-1]["type"] == "completed"

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
