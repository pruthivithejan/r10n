"""Tests for the versioned automation worker protocol."""

import json
from dataclasses import replace
from email.message import Message
from io import BytesIO
from urllib.error import URLError

import pytest
from PIL import Image

from r10n_backend.__main__ import main
from r10n_backend.registry import get_automation
from r10n_backend.worker import PROTOCOL_VERSION, find_artifacts, run_automation


class TestWorkerProtocol:
    """Verify structured worker execution and artifact reporting."""

    @pytest.mark.parametrize("include_valid, expected", [(False, "failed"), (True, "partial")])
    def test_color_batch_reports_invalid_files(self, tmp_path, include_valid, expected):
        (tmp_path / "broken.css").write_bytes(b"\xff")
        if include_valid:
            (tmp_path / "valid.css").write_text("p { color: #ff0000; }", encoding="utf-8")
        events = []
        run_automation("colors", {"path": str(tmp_path), "dry_run": True}, events.append)
        assert events[-1]["success"] is False
        assert events[-1]["status"] == expected
        assert any("error" in item for item in events[-1]["result"]["files"])

    def test_website_unavailable_reports_failure(self, tmp_path, monkeypatch):
        def unavailable(request, timeout):
            raise URLError("unavailable")

        monkeypatch.setattr("urllib.request.urlopen", unavailable)
        events = []
        run_automation(
            "website-images",
            {"url": "https://example.test/", "output_directory": str(tmp_path)},
            events.append,
        )
        assert events[-1]["success"] is False
        assert events[-1]["status"] == "failed"
        assert events[-1]["result"]["pages"][0]["success"] is False

    def test_website_partial_download_reports_partial(self, tmp_path, monkeypatch):
        image_bytes = BytesIO()
        Image.new("RGB", (4, 4), "red").save(image_bytes, "PNG")

        def respond(request, timeout):
            if request.full_url.endswith("bad.png"):
                raise URLError("unavailable")
            body = (
                b'<img src="/good.png"><img src="/bad.png">'
                if request.full_url.endswith("/")
                else image_bytes.getvalue()
            )

            class Response(BytesIO):
                headers = Message()

            return Response(body)

        monkeypatch.setattr("urllib.request.urlopen", respond)
        events = []
        run_automation(
            "website-images",
            {"url": "https://example.test/", "output_directory": str(tmp_path)},
            events.append,
        )
        assert events[-1]["success"] is False
        assert events[-1]["status"] == "partial"
        assert events[-1]["result"]["downloaded"] == 1
        assert events[-1]["result"]["failed"] == 1

    def test_rename_batch_with_conflict_reports_partial(self, tmp_path):
        (tmp_path / "first.txt").write_text("first", encoding="utf-8")
        (tmp_path / "second.txt").write_text("second", encoding="utf-8")
        (tmp_path / "new_second.txt").write_text("existing", encoding="utf-8")
        events = []
        run_automation(
            "rename",
            {"input_directory": str(tmp_path), "prefix": "new_", "file_pattern": "*.txt"},
            events.append,
        )
        assert events[-1]["success"] is False
        assert events[-1]["status"] == "partial"
        assert events[-1]["result"]["renamed"] >= 1
        assert events[-1]["result"]["errors"]

    def test_logo_batch_with_existing_and_unavailable_reports_partial(self, tmp_path, monkeypatch):
        (tmp_path / "first.svg").write_text("<svg/>", encoding="utf-8")

        def unavailable(request, timeout):
            raise URLError("unavailable")

        monkeypatch.setattr("urllib.request.urlopen", unavailable)
        events = []
        run_automation(
            "logos",
            {"names": "First, Second", "output_directory": str(tmp_path)},
            events.append,
        )
        assert events[-1]["success"] is False
        assert events[-1]["status"] == "partial"
        assert events[-1]["result"]["skipped"] == 1
        assert events[-1]["result"]["failed"] == 1

    def test_missing_image_directory_reports_failure(self, tmp_path):
        events = []
        run_automation(
            "images",
            {
                "input_directory": str(tmp_path / "missing"),
                "output_directory": str(tmp_path / "out"),
            },
            events.append,
        )
        assert events[-1]["success"] is False
        assert events[-1]["status"] == "failed"
        assert "error" in events[-1]["result"]

    def test_image_batch_reports_partial_failure(self, tmp_path):
        source = tmp_path / "images"
        source.mkdir()
        Image.new("RGB", (4, 4), "red").save(source / "valid.png")
        (source / "broken.png").write_bytes(b"not an image")
        events = []
        run_automation(
            "images",
            {"input_directory": str(source), "output_directory": str(tmp_path / "out")},
            events.append,
        )
        assert events[-1]["success"] is False
        assert events[-1]["status"] == "partial"
        assert events[-1]["result"]["processed"] == 1
        assert events[-1]["result"]["failed"] == 1

    def test_markdown_batch_reports_partial_failure(self, tmp_path):
        source = tmp_path / "docs"
        source.mkdir()
        (source / "valid.md").write_text("# Valid", encoding="utf-8")
        (source / "broken.md").write_bytes(b"\xff")
        events = []
        run_automation(
            "md2pdf",
            {"input_path": str(source), "output_path": str(tmp_path / "out")},
            events.append,
        )
        assert events[-1]["success"] is False
        assert events[-1]["status"] == "partial"
        assert events[-1]["result"]["converted"] == 1
        assert events[-1]["result"]["failed"] == 1

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
            },
            get_automation("validate").artifact_fields,
        )

        assert artifacts == [str(report.resolve())]

    def test_artifact_discovery_retains_single_argument_compatibility(self, tmp_path):
        output = tmp_path / "result.pdf"
        output.write_bytes(b"pdf")

        assert find_artifacts({"output_files": [str(output)]}) == [str(output.resolve())]

    def test_nested_artifacts_follow_declared_result_fields(self, tmp_path, monkeypatch):
        """Logo outputs are reported once, in result order, without unrelated paths."""
        directory = tmp_path / "logos"
        directory.mkdir()
        logo = directory / "logo.svg"
        logo.write_text("<svg/>", encoding="utf-8")
        manifest = directory / "logos_manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        result = {
            "output_directory": str(directory),
            "logos": [{"output_file": str(logo)}, {"output_file": str(logo)}],
            "manifest_file": str(manifest),
            "output_unrelated": str(tmp_path),
        }
        spec = replace(get_automation("logos"), executor=lambda inputs, emit: result)
        monkeypatch.setattr("r10n_backend.worker.get_automation", lambda automation_id: spec)
        events = []

        run_automation("logos", {"names": "Example"}, events.append)

        assert [event["path"] for event in events if event["type"] == "artifact"] == [
            str(directory.resolve()),
            str(logo.resolve()),
            str(manifest.resolve()),
        ]
