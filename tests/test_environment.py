"""The native backend does not discover cwd-relative environment files."""

from pathlib import Path
from typing import Any

import pytest

from r10n_backend.worker import ProtocolCallback, worker_main


def test_worker_does_not_load_a_project_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A worker ignores legacy .env files but retains process environment."""
    import os

    monkeypatch.chdir(tmp_path)
    (tmp_path / "local").mkdir()
    (tmp_path / "local/.env").write_text("R10N_TEST_WORKER=local\n", encoding="utf-8")
    monkeypatch.delenv("R10N_TEST_WORKER", raising=False)
    monkeypatch.setenv("R10N_TEST_PROCESS", "provided")

    def execute(
        automation_id: str, payload: dict[str, Any], emit: ProtocolCallback
    ) -> dict[str, Any]:
        assert automation_id == "contacts"
        assert payload == {}
        assert "R10N_TEST_WORKER" not in os.environ
        assert os.environ["R10N_TEST_PROCESS"] == "provided"
        return {"success": True}

    monkeypatch.setattr("r10n_backend.worker.run_automation", execute)

    assert worker_main("contacts", "{}") == 0
    assert '"type": "hello"' in capsys.readouterr().out
