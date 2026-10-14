"""Consistent workspace environment handling for worker and configuration."""

from pathlib import Path
from typing import Any

import pytest

from r10n_backend.__main__ import main
from r10n_backend.environment import load_environment
from r10n_backend.worker import ProtocolCallback


def test_local_env_never_overrides_process_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit environment wins while otherwise missing workspace values load."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "local").mkdir()
    (tmp_path / "local/.env").write_text(
        "R10N_TEST_PRESENT=workspace\nR10N_TEST_MISSING=workspace\n", encoding="utf-8"
    )
    monkeypatch.setenv("R10N_TEST_PRESENT", "process")
    monkeypatch.delenv("R10N_TEST_MISSING", raising=False)
    load_environment()
    import os

    assert os.environ["R10N_TEST_PRESENT"] == "process"
    assert os.environ["R10N_TEST_MISSING"] == "workspace"
    monkeypatch.delenv("R10N_TEST_MISSING")


def test_configure_dispatches_foreground_picker_and_loads_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Backend flags pass paths unchanged to the existing foreground picker."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "local").mkdir()
    (tmp_path / "local/.env").write_text("R10N_TEST_CONFIGURE=workspace\n", encoding="utf-8")
    monkeypatch.delenv("R10N_TEST_CONFIGURE", raising=False)
    calls = []

    def picker(template: str, recipients: str | None, output: str | None) -> str:
        import os

        assert os.environ["R10N_TEST_CONFIGURE"] == "workspace"
        calls.append((template, recipients, output))
        return output or "local/configs/fill-pdfs.json"

    monkeypatch.setattr("r10n_backend.configure.launch_picker", picker)
    assert main(["configure", "--template", "template.pdf"]) == 0
    assert (
        main(
            [
                "configure",
                "--template",
                "template.pdf",
                "--recipients",
                "data.csv",
                "--output",
                "out.json",
            ]
        )
        == 0
    )
    assert calls == [("template.pdf", None, None), ("template.pdf", "data.csv", "out.json")]
    monkeypatch.delenv("R10N_TEST_CONFIGURE")


def test_worker_loads_local_environment_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The worker loads workspace values without replacing explicit env values."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "local").mkdir()
    (tmp_path / "local/.env").write_text(
        "R10N_TEST_WORKER=workspace\nR10N_TEST_EXPLICIT=workspace\n", encoding="utf-8"
    )
    monkeypatch.delenv("R10N_TEST_WORKER", raising=False)
    monkeypatch.setenv("R10N_TEST_EXPLICIT", "process")

    def execute(
        automation_id: str, payload: dict[str, Any], emit: ProtocolCallback
    ) -> dict[str, Any]:
        import os

        assert automation_id == "contacts"
        assert payload == {}
        assert os.environ["R10N_TEST_WORKER"] == "workspace"
        assert os.environ["R10N_TEST_EXPLICIT"] == "process"
        emit({"type": "completed", "success": True})
        return {"success": True}

    monkeypatch.setattr("r10n_backend.worker.run_automation", execute)
    assert main(["worker", "contacts", "--input-json", "{}"]) == 0
    assert '"type": "hello"' in capsys.readouterr().out
    monkeypatch.delenv("R10N_TEST_WORKER")
