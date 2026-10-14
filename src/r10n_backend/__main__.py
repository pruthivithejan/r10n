"""Machine-readable backend entry point for the native r10n frontend."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from importlib.metadata import version
from typing import Any


def build_catalog() -> dict[str, Any]:
    """Export registry metadata without importing automation implementations.

    Returns:
        Protocol version and all automation schemas in registry display order.
    """
    from r10n_backend.registry import list_automations
    from r10n_backend.worker import PROTOCOL_VERSION

    return {
        "protocol": PROTOCOL_VERSION,
        "version": version("r10n"),
        "automations": [
            {
                "id": spec.id,
                "title": spec.title,
                "description": spec.description,
                "category": spec.category,
                "roles": list(spec.roles),
                "confirmation": spec.confirmation,
                "input_schema": spec.input_model.model_json_schema(),
                "field_order": list(spec.input_model.model_fields),
            }
            for spec in list_automations()
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch catalog, JSON Lines worker, or foreground field picker.

    Args:
        argv: Arguments excluding the executable name, or process arguments.

    Returns:
        Backend operation exit status.

    Raises:
        SystemExit: For argparse usage errors or help.
    """
    # JSON and diagnostics use UTF-8 even when Windows redirects streams through
    # a legacy code page. Capture/mocked streams may not support reconfiguration.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("catalog", help="Emit registry metadata as JSON")
    worker_parser = commands.add_parser("worker", help="Run a v1 JSON Lines worker")
    worker_parser.add_argument("automation_id", help="Registered automation identifier")
    worker_parser.add_argument("--input-json", help="Inline JSON input instead of stdin")
    configure_parser = commands.add_parser("configure", help="Open the foreground PDF field picker")
    configure_parser.add_argument("--template", required=True, help="PDF template path")
    configure_parser.add_argument("--recipients", help="Recipient CSV or TXT path")
    configure_parser.add_argument("--output", help="Configuration output path")
    options = parser.parse_args(argv)

    if options.command == "catalog":
        json.dump(build_catalog(), sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0

    if options.command == "configure":
        from r10n_backend.configure import launch_picker
        from r10n_backend.environment import load_environment

        load_environment()
        launch_picker(options.template, options.recipients, options.output)
        return 0

    from r10n_backend.worker import worker_main

    return worker_main(options.automation_id, options.input_json)


if __name__ == "__main__":
    raise SystemExit(main())
