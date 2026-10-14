"""Retired workspace setup entry point; use the native ``r10n init`` command."""

import sys


def main() -> int:
    """Explain the replacement without creating obsolete directories."""
    print(
        "scripts/setup.py is retired. Run ./setup.sh setup for developer tools,\n"
        "then go run ./cmd/r10n init (or uv run r10n init) for local/ data directories.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
