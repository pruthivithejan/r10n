"""Versioned JSON Lines worker protocol for r10n automations."""

from __future__ import annotations

import contextlib
import json
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from pydantic import ValidationError

from src.automation_registry import get_automation, normalize_result

PROTOCOL_VERSION = 1
ProtocolCallback = Callable[[dict[str, Any]], None]


class EventTextWriter:
    """Convert legacy line-oriented output into structured log events."""

    def __init__(self, emit: ProtocolCallback, level: str = "info") -> None:
        self.emit = emit
        self.level = level
        self._buffer = ""

    def write(self, text: str) -> int:
        """Buffer text and emit complete lines.

        Args:
            text: Text written by an automation.

        Returns:
            Number of characters consumed.
        """
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self.emit({"type": "log", "level": self.level, "message": line})
        return len(text)

    def flush(self) -> None:
        """Emit an incomplete buffered line."""
        if self._buffer.strip():
            self.emit({"type": "log", "level": self.level, "message": self._buffer})
        self._buffer = ""


def _json_safe(value: Any) -> Any:
    """Return a recursively JSON-compatible value."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def find_artifacts(result: dict[str, Any]) -> list[str]:
    """Discover existing output paths in a result dictionary.

    Args:
        result: Normalized automation result.

    Returns:
        Unique artifact paths in encounter order.
    """
    artifacts: list[str] = []

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, str(child_key))
        elif isinstance(value, list):
            for item in value:
                visit(item, key)
        elif isinstance(value, str) and any(
            token in key.lower()
            for token in ("output", "artifact", "manifest", "report", "cleaned")
        ):
            path = Path(value).expanduser()
            if path.exists():
                normalized = str(path.resolve())
                if normalized not in artifacts:
                    artifacts.append(normalized)

    visit(result)
    return artifacts


def run_automation(
    automation_id: str,
    payload: dict[str, Any],
    emit: ProtocolCallback,
) -> dict[str, Any]:
    """Validate and execute one registered automation.

    Args:
        automation_id: Stable automation identifier.
        payload: Raw input values.
        emit: Callback receiving protocol events.

    Returns:
        Normalized result dictionary.
    """
    spec = get_automation(automation_id)
    validated = spec.validate(payload)
    emit(
        {
            "type": "started",
            "protocol": PROTOCOL_VERSION,
            "automation": automation_id,
            "inputs": validated.model_dump(mode="json"),
        }
    )

    def adapter_emit(event_type: str, data: dict[str, Any]) -> None:
        emit({"type": event_type, **_json_safe(data)})

    output_writer = EventTextWriter(emit)
    error_writer = EventTextWriter(emit, level="error")
    with contextlib.redirect_stdout(output_writer), contextlib.redirect_stderr(error_writer):
        result = spec.executor(validated, adapter_emit)
    output_writer.flush()
    error_writer.flush()

    normalized = _json_safe(normalize_result(result))
    for artifact_path in find_artifacts(normalized):
        emit({"type": "artifact", "path": artifact_path})
    emit(
        {
            "type": "completed",
            "automation": automation_id,
            "success": normalized.get("success", True),
            "result": normalized,
        }
    )
    return normalized


def write_json_event(stream: TextIO, event: dict[str, Any]) -> None:
    """Write and flush one JSON Lines protocol event."""
    stream.write(json.dumps(_json_safe(event), ensure_ascii=False) + "\n")
    stream.flush()


def worker_main(automation_id: str, input_json: str | None = None) -> int:
    """Run the worker protocol over standard input and output.

    Args:
        automation_id: Registered automation identifier.
        input_json: Optional inline JSON payload. When omitted, stdin is read.

    Returns:
        Process exit status.
    """
    protocol_stdout = sys.stdout

    def emit(event: dict[str, Any]) -> None:
        write_json_event(protocol_stdout, event)

    emit({"type": "hello", "protocol": PROTOCOL_VERSION})
    try:
        raw_payload = input_json if input_json is not None else sys.stdin.read()
        payload = json.loads(raw_payload or "{}")
        if not isinstance(payload, dict):
            raise ValueError("Automation input must be a JSON object")
        run_automation(automation_id, payload, emit)
        return 0
    except (KeyError, ValidationError, ValueError, json.JSONDecodeError) as error:
        emit({"type": "error", "error": str(error), "kind": "input"})
        return 2
    except KeyboardInterrupt:
        emit({"type": "cancelled", "automation": automation_id})
        return 130
    except Exception as error:
        event: dict[str, Any] = {"type": "error", "error": str(error), "kind": "execution"}
        if os.getenv("R10N_DEBUG"):
            event["traceback"] = traceback.format_exc()
        emit(event)
        return 1
