"""Python bridge for native frontends and the frozen backend entry script.

Catalog output is one JSON object; worker output is the existing v1 JSON Lines
protocol. Legacy mode delegates directly to the Python CLI without wrapping its
streams or exit behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any


def build_catalog() -> dict[str, Any]:
    """Export registry metadata without importing automation implementations.

    Returns:
        Protocol version and all automation schemas in registry display order.
    """
    from src.automation_registry import list_automations
    from src.worker import PROTOCOL_VERSION

    return {
        "protocol": PROTOCOL_VERSION,
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
    """Dispatch catalog, worker, or unmodified legacy CLI execution.

    Args:
        argv: Backend arguments, excluding the executable name. Defaults to
            the process arguments.

    Returns:
        Catalog or worker exit status. Legacy mode normally exits via Typer.

    Raises:
        SystemExit: For argparse usage errors/help or a legacy CLI exit.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    # Do not let argparse interpret any legacy flags, including --help.
    if arguments and arguments[0] == "legacy":
        from src.cli import app

        app(args=arguments[1:], prog_name="r10n")
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("catalog", help="Emit registry metadata as JSON")
    worker_parser = commands.add_parser("worker", help="Run a v1 JSON Lines worker")
    worker_parser.add_argument("automation_id", help="Registered automation identifier")
    commands.add_parser("legacy", help="Pass all remaining arguments to the Python CLI")
    options = parser.parse_args(arguments)

    if options.command == "catalog":
        json.dump(build_catalog(), sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0

    from src.worker import worker_main

    return worker_main(options.automation_id)


if __name__ == "__main__":
    raise SystemExit(main())
