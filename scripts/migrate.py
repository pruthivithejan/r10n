"""Retired legacy workspace migration; no user data is moved automatically."""

import sys


def main() -> int:
    """Explain safe manual migration without overwriting existing data."""
    print(
        "scripts/migrate.py is retired. Run r10n init to create local/ directories.\n"
        "Copy legacy workspace inputs/configs into local/inputs and local/configs yourself;\n"
        "retain the original files until outputs are verified. No files were changed.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
