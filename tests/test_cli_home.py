"""Tests for the persistent r10n home terminal UI."""

import subprocess
import sys

from typer.testing import CliRunner

from src import cli


class TestHomeTerminalUi:
    """Test the no-argument persistent home screen."""

    def test_no_args_shows_home_until_exit(self, monkeypatch):
        """Running r10n without args opens the home UI and exits on command."""
        monkeypatch.setattr(cli, "maybe_notify_update", lambda subcommand: None)
        runner = CliRunner()

        result = runner.invoke(cli.app, input="exit\n")

        assert result.exit_code == 0
        assert f"r10n v{cli.VERSION} - routine automation" in result.output
        assert "Type an automation command to run it." in result.output
        assert "Press Ctrl+C to exit." in result.output

    def test_home_runs_existing_commands_and_stays_open(self, monkeypatch):
        """Home input routes through the existing Typer command table."""
        monkeypatch.setattr(cli, "maybe_notify_update", lambda subcommand: None)
        runner = CliRunner()

        result = runner.invoke(cli.app, input="status\nexit\n")

        assert result.exit_code == 0
        assert "Status" in result.output
        assert "Quick Start:" in result.output
        assert result.output.count("Enter a command, flags included.") >= 2

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
