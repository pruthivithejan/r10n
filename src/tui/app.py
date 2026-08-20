"""Textual application for discovering and running r10n automations."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, ClassVar

from pydantic import ValidationError
from rich.markup import escape
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.suggester import Suggester
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    Pretty,
    ProgressBar,
    RichLog,
    Select,
    Static,
)
from textual.widgets.option_list import Option

from src.automation_registry import AutomationSpec, get_automation, list_automations
from src.worker import PROTOCOL_VERSION

FIELD_ID_PREFIX = "field--"


class PathSuggester(Suggester):
    """Offer filesystem completions without blocking form entry."""

    def __init__(self) -> None:
        super().__init__(use_cache=False)

    async def get_suggestion(self, value: str) -> str | None:
        """Return the first path matching the current input.

        Args:
            value: Current path input.

        Returns:
            Completed path, or None when no match exists.
        """
        if not value or value.endswith((" ", "\n")):
            return None
        candidate = Path(value).expanduser()
        parent = candidate.parent
        prefix = candidate.name.lower()
        try:
            matches = sorted(
                (child for child in parent.iterdir() if child.name.lower().startswith(prefix)),
                key=lambda child: (not child.is_dir(), child.name.lower()),
            )
        except OSError:
            return None
        if not matches:
            return None
        match = matches[0]
        suggestion = str(match)
        if value.startswith("~"):
            home = str(Path.home())
            suggestion = suggestion.replace(home, "~", 1)
        if match.is_dir():
            suggestion += os.sep
        return suggestion


def worker_command() -> list[str]:
    """Return the command prefix used to start an r10n worker.

    Returns:
        Command arguments that work in source and frozen installations.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "src.cli"]


def _schema_type(schema: dict[str, Any]) -> str | None:
    """Extract a concrete JSON Schema type from optional unions."""
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        return schema_type
    for choice in schema.get("anyOf", []):
        if choice.get("type") != "null":
            return str(choice.get("type"))
    return None


def _schema_enum(schema: dict[str, Any]) -> list[Any] | None:
    """Extract enum values from direct or optional JSON Schema fields."""
    if isinstance(schema.get("enum"), list):
        return list(schema["enum"])
    for choice in schema.get("anyOf", []):
        if isinstance(choice.get("enum"), list):
            return list(choice["enum"])
    return None


class ReviewScreen(ModalScreen[bool]):
    """Review validated inputs before an automation starts."""

    CSS = """
    ReviewScreen {
        align: center middle;
        background: $background 70%;
    }

    #review-dialog {
        width: min(88, 92%);
        max-height: 90%;
        padding: 1 2;
        border: tall $accent;
        background: $surface;
    }

    #review-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #review-warning {
        color: $warning;
        margin: 1 0;
    }

    #review-actions {
        height: auto;
        align-horizontal: right;
        margin-top: 1;
    }

    #review-actions Button {
        margin-left: 1;
    }
    """

    def __init__(self, spec: AutomationSpec, payload: dict[str, Any]) -> None:
        super().__init__()
        self.spec = spec
        self.payload = payload

    def compose(self) -> ComposeResult:
        """Compose the review dialog."""
        with Vertical(id="review-dialog"):
            yield Static(f"Review · {self.spec.title}", id="review-title")
            yield Pretty(self.payload)
            if self.spec.confirmation:
                yield Static(self.spec.confirmation, id="review-warning")
            with Horizontal(id="review-actions"):
                yield Button("Back", id="review-back")
                yield Button("Run automation", id="review-run", variant="primary")

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        """Return the user's review decision."""
        self.dismiss(event.button.id == "review-run")


class R10nApp(App[None]):
    """Searchable, schema-driven terminal workspace for r10n."""

    TITLE = "r10n"
    SUB_TITLE = "routine automation"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        Binding("/", "focus_search", "Search"),
        Binding("ctrl+c", "cancel_run", "Cancel run", show=True),
    ]

    CSS = """
    Screen {
        background: #0c1017;
        color: #dce7f5;
    }

    Header {
        background: #111a26;
        color: #eaf4ff;
    }

    #app-shell {
        height: 1fr;
    }

    #catalog-panel {
        width: 34;
        min-width: 27;
        border-right: solid #26384d;
        background: #101721;
        padding: 1;
    }

    #brand {
        text-style: bold;
        color: #67d5ff;
        margin-bottom: 1;
    }

    #search {
        margin-bottom: 1;
        border: tall #37516c;
    }

    #catalog {
        height: 1fr;
        background: transparent;
        border: none;
    }

    #workspace {
        width: 1fr;
        padding: 1 2;
    }

    #automation-title {
        text-style: bold;
        color: #8fe3ff;
        height: auto;
    }

    #automation-meta {
        color: #80a4c3;
        margin-bottom: 1;
        height: auto;
    }

    #automation-description {
        margin-bottom: 1;
        height: auto;
    }

    #form {
        height: 3fr;
        border: round #26384d;
        padding: 1 2;
        background: #0f1620;
    }

    .field-row {
        height: auto;
        margin-bottom: 1;
    }

    .field-label {
        text-style: bold;
        height: 1;
    }

    .field-description {
        color: #7891a8;
        height: auto;
        margin-bottom: 0;
    }

    .field-row Input, .field-row Select {
        width: 1fr;
    }

    #actions {
        height: auto;
        margin: 1 0;
    }

    #actions Button {
        margin-right: 1;
    }

    #run-status {
        width: 1fr;
        content-align: right middle;
        color: #8fa9c0;
    }

    #progress {
        margin-bottom: 1;
    }

    #run-log {
        height: 2fr;
        min-height: 7;
        border: round #26384d;
        background: #090e14;
        padding: 0 1;
    }

    Footer {
        background: #111a26;
    }
    """

    def __init__(self, version: str) -> None:
        super().__init__()
        self.version = version
        self.current_automation_id = ""
        self.filtered_ids = [spec.id for spec in list_automations()]
        self._field_widgets: dict[str, str] = {}
        self._process: subprocess.Popen[str] | None = None
        self._running = False

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header(show_clock=True)
        with Horizontal(id="app-shell"):
            with Vertical(id="catalog-panel"):
                yield Static(f"r10n v{self.version}\nYour automation workspace", id="brand")
                yield Input(placeholder="Search automations or roles…", id="search")
                yield OptionList(
                    *(Option(spec.title, id=spec.id) for spec in list_automations()),
                    id="catalog",
                )
            with Vertical(id="workspace"):
                yield Static("", id="automation-title")
                yield Static("", id="automation-meta")
                yield Static("", id="automation-description")
                yield ScrollableContainer(id="form")
                with Horizontal(id="actions"):
                    yield Button("Review and run", id="run", variant="primary")
                    yield Button("Cancel", id="cancel", variant="error", disabled=True)
                    yield Static("Ready", id="run-status")
                yield ProgressBar(total=100, show_eta=False, id="progress")
                yield RichLog(id="run-log", highlight=True, markup=True, wrap=True)
        yield Footer()

    async def on_mount(self) -> None:
        """Select and render the first registered automation."""
        catalog = self.query_one("#catalog", OptionList)
        catalog.highlighted = 0
        first = list_automations()[0]
        await self._render_automation(first)
        self.query_one("#progress", ProgressBar).display = False

    def action_focus_search(self) -> None:
        """Focus the catalog search input."""
        self.query_one("#search", Input).focus()

    def action_cancel_run(self) -> None:
        """Terminate the active worker process."""
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            self.query_one("#run-status", Static).update("Cancelling…")
        elif not self._running:
            self.exit()

    @on(Input.Changed, "#search")
    async def filter_catalog(self, event: Input.Changed) -> None:
        """Filter automations by title, category, role, or identifier."""
        query = event.value.strip().lower()
        matches = []
        for spec in list_automations():
            haystack = " ".join(
                (spec.id, spec.title, spec.description, spec.category, *spec.roles)
            ).lower()
            if query in haystack:
                matches.append(spec)

        self.filtered_ids = [spec.id for spec in matches]
        catalog = self.query_one("#catalog", OptionList)
        catalog.clear_options()
        catalog.add_options([Option(spec.title, id=spec.id) for spec in matches])
        if matches:
            catalog.highlighted = 0
            await self._render_automation(matches[0])
        else:
            self.current_automation_id = ""
            self.query_one("#automation-title", Static).update("No matching automations")
            self.query_one("#automation-description", Static).update(
                "Try a role such as operations, marketing, people, or design."
            )
            await self.query_one("#form", ScrollableContainer).remove_children()

    @on(OptionList.OptionSelected, "#catalog")
    async def select_automation(self, event: OptionList.OptionSelected) -> None:
        """Render the selected automation form."""
        if event.option.id:
            await self._render_automation(get_automation(str(event.option.id)))

    @on(OptionList.OptionHighlighted, "#catalog")
    async def highlight_automation(self, event: OptionList.OptionHighlighted) -> None:
        """Update the form as keyboard navigation moves through the catalog."""
        if event.option.id and str(event.option.id) != self.current_automation_id:
            await self._render_automation(get_automation(str(event.option.id)))

    async def _render_automation(self, spec: AutomationSpec) -> None:
        """Build an input form from an automation's JSON Schema."""
        self.current_automation_id = spec.id
        self._field_widgets.clear()
        self.query_one("#automation-title", Static).update(spec.title)
        self.query_one("#automation-meta", Static).update(
            f"{spec.category}  ·  {', '.join(spec.roles)}  ·  {spec.id}"
        )
        self.query_one("#automation-description", Static).update(spec.description)
        self.query_one("#run-log", RichLog).clear()
        self.query_one("#run-status", Static).update("Ready")

        form = self.query_one("#form", ScrollableContainer)
        await form.remove_children()
        model_schema = spec.input_model.model_json_schema()
        required = set(model_schema.get("required", []))

        for field_name, field_schema in model_schema.get("properties", {}).items():
            widget_id = f"{FIELD_ID_PREFIX}{field_name.replace('_', '-')}"
            self._field_widgets[field_name] = widget_id
            title = str(field_schema.get("title") or field_name.replace("_", " ").title())
            if field_name in required:
                title += " *"
            description = str(field_schema.get("description") or "")
            default = field_schema.get("default")
            enum = _schema_enum(field_schema)
            field_type = _schema_type(field_schema)
            ui_widget = field_schema.get("ui:widget")
            is_path = ui_widget in {"file", "save_file", "directory", "path"}
            if is_path:
                description += " · Press Tab to accept path completion."

            if enum:
                select_value = default if default in enum else Select.BLANK
                widget = Select(
                    [(str(choice), choice) for choice in enum],
                    value=select_value,
                    allow_blank=field_name not in required,
                    id=widget_id,
                )
            elif field_type == "boolean":
                widget = Checkbox("Enabled", value=bool(default), id=widget_id)
            else:
                input_type = (
                    "integer"
                    if field_type == "integer"
                    else "number" if field_type == "number" else "text"
                )
                widget = Input(
                    value="" if default is None else str(default),
                    placeholder=description,
                    type=input_type,
                    suggester=PathSuggester() if is_path else None,
                    id=widget_id,
                )

            await form.mount(
                Container(
                    Label(title, classes="field-label"),
                    Static(description, classes="field-description"),
                    widget,
                    classes="field-row",
                )
            )

    def _collect_payload(self) -> tuple[AutomationSpec, dict[str, Any]]:
        """Collect and validate values from the active generated form."""
        if not self.current_automation_id:
            raise ValueError("Select an automation first")
        spec = get_automation(self.current_automation_id)
        payload: dict[str, Any] = {}
        schema = spec.input_model.model_json_schema()

        for field_name, widget_id in self._field_widgets.items():
            widget = self.query_one(f"#{widget_id}")
            field_schema = schema["properties"][field_name]
            field_type = _schema_type(field_schema)
            if isinstance(widget, Checkbox):
                payload[field_name] = widget.value
            elif isinstance(widget, Select):
                payload[field_name] = None if widget.value is Select.BLANK else widget.value
            elif isinstance(widget, Input):
                raw_value = widget.value.strip()
                if not raw_value and field_name not in set(schema.get("required", [])):
                    payload[field_name] = None
                elif field_type == "integer":
                    payload[field_name] = int(raw_value)
                elif field_type == "number":
                    payload[field_name] = float(raw_value)
                else:
                    payload[field_name] = raw_value

        validated = spec.validate(payload)
        return spec, validated.model_dump(mode="json")

    @on(Button.Pressed, "#run")
    def review_run(self) -> None:
        """Validate the form and open the review screen."""
        if self._running:
            return
        try:
            spec, payload = self._collect_payload()
        except (ValidationError, ValueError) as error:
            self.query_one("#run-status", Static).update("Check the highlighted inputs")
            self.query_one("#run-log", RichLog).write(f"[red]{error}[/red]")
            return

        self.push_screen(
            ReviewScreen(spec, payload),
            callback=lambda approved: self._start_run(spec, payload) if approved else None,
        )

    def _start_run(self, spec: AutomationSpec, payload: dict[str, Any]) -> None:
        """Prepare the workspace and launch a subprocess worker."""
        self._running = True
        self.query_one("#run", Button).disabled = True
        self.query_one("#cancel", Button).disabled = False
        self.query_one("#run-log", RichLog).clear()
        self.query_one("#run-status", Static).update("Starting…")
        progress = self.query_one("#progress", ProgressBar)
        progress.display = True
        progress.update(total=100, progress=0)
        self.execute_automation(spec.id, payload)

    @work(thread=True, exclusive=True, exit_on_error=False)
    def execute_automation(self, automation_id: str, payload: dict[str, Any]) -> None:
        """Execute an automation worker without blocking terminal rendering."""
        env = os.environ.copy()
        env["R10N_DISABLE_UPDATE_CHECK"] = "1"
        env["R10N_NO_BANNER"] = "1"
        command = [*worker_command(), "_worker", automation_id]
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                env=env,
            )
        except OSError as error:
            self.call_from_thread(
                self._handle_protocol_event,
                {"type": "error", "error": f"Could not start worker: {error}"},
            )
            self.call_from_thread(self._finish_run, 1)
            return
        self._process = process
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(json.dumps(payload))
        process.stdin.close()

        for line in process.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                event = {"type": "log", "message": line.rstrip(), "level": "error"}
            self.call_from_thread(self._handle_protocol_event, event)

        return_code = process.wait()
        self.call_from_thread(self._finish_run, return_code)

    def _handle_protocol_event(self, event: dict[str, Any]) -> None:
        """Render one worker protocol event."""
        event_type = event.get("type")
        log = self.query_one("#run-log", RichLog)
        status = self.query_one("#run-status", Static)
        if event_type == "hello":
            protocol = event.get("protocol")
            if protocol != PROTOCOL_VERSION:
                status.update("Incompatible worker")
                log.write(f"[red]Expected protocol v{PROTOCOL_VERSION}, received v{protocol}[/red]")
                self.action_cancel_run()
            else:
                status.update(f"Worker protocol v{protocol}")
        elif event_type == "started":
            status.update("Running")
            log.write(f"[cyan]Started {event.get('automation')}[/cyan]")
        elif event_type == "log":
            style = "red" if event.get("level") == "error" else "white"
            log.write(f"[{style}]{escape(str(event.get('message', '')))}[/{style}]")
        elif event_type == "progress":
            current = int(event.get("current", 0))
            total = max(1, int(event.get("total", 1)))
            self.query_one("#progress", ProgressBar).update(total=total, progress=current)
            status.update(str(event.get("message") or "Running"))
        elif event_type == "artifact":
            log.write(f"[green]Artifact:[/green] {event.get('path')}")
        elif event_type == "completed":
            if event.get("success", True):
                status.update("Completed")
                log.write("[bold green]Completed successfully[/bold green]")
            else:
                status.update("Completed with errors")
                log.write("[bold yellow]Completed with errors[/bold yellow]")
            log.write(json.dumps(event.get("result", {}), indent=2, ensure_ascii=False))
        elif event_type == "cancelled":
            status.update("Cancelled")
            log.write("[yellow]Automation cancelled[/yellow]")
        elif event_type == "error":
            status.update("Failed")
            log.write(f"[bold red]{event.get('error', 'Unknown error')}[/bold red]")

    def _finish_run(self, return_code: int) -> None:
        """Restore controls after the worker exits."""
        self._running = False
        self._process = None
        self.query_one("#run", Button).disabled = False
        self.query_one("#cancel", Button).disabled = True
        if return_code != 0:
            status = self.query_one("#run-status", Static)
            if return_code < 0:
                status.update("Cancelled")
            else:
                status.update(f"Failed ({return_code})")

    @on(Button.Pressed, "#cancel")
    def cancel_button(self) -> None:
        """Cancel the active subprocess from the visible button."""
        self.action_cancel_run()

    def on_unmount(self) -> None:
        """Ensure a child automation does not outlive the terminal app."""
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()


def run_tui(version: str) -> None:
    """Launch the r10n Textual application.

    Args:
        version: Current r10n version displayed in the workspace.
    """
    R10nApp(version=version).run()
