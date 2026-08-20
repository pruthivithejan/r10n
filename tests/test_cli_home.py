"""Tests for the r10n CLI entry experience."""

import subprocess
import sys

from typer.testing import CliRunner

from src import cli


class TestHomeTerminalUi:
    """Test the no-argument Textual workspace entry point."""

    def test_no_args_launches_tui(self, monkeypatch):
        """Running r10n without args launches the Textual application."""
        monkeypatch.setattr(cli, "maybe_notify_update", lambda subcommand: None)
        launches = []
        monkeypatch.setattr(cli, "launch_tui", lambda: launches.append(True))
        runner = CliRunner()

        result = runner.invoke(cli.app)

        assert result.exit_code == 0
        assert launches == [True]

    def test_existing_scriptable_commands_still_work(self, monkeypatch):
        """Existing Typer subcommands remain available without the TUI."""
        monkeypatch.setattr(cli, "maybe_notify_update", lambda subcommand: None)
        runner = CliRunner()

        result = runner.invoke(cli.app, ["status"])

        assert result.exit_code == 0
        assert "Status" in result.output
        assert "Quick Start:" in result.output

    def test_help_omits_completion_flags(self):
        """Typer shell completion options are intentionally hidden."""
        runner = CliRunner()

        result = runner.invoke(cli.app, ["--help"])

        assert result.exit_code == 0
        assert "--install-completion" not in result.output
        assert "--show-completion" not in result.output

    def test_cli_import_does_not_load_automation_modules(self):
        """Importing the CLI should not eagerly import heavyweight automations."""
        script = (
            "import sys; import src.cli; "
            "mods=('src.automations.markdown_to_pdf','src.automations.optimize_images',"
            "'src.automations.fill_pdfs'); "
            "print(any(mod in sys.modules for mod in mods))"
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
        )

        assert result.stdout.strip() == "False"
