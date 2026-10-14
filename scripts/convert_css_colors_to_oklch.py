"""Retired duplicate color converter; use the registry-backed native command."""

import sys


def main() -> int:
    """Direct callers to the maintained command without modifying files."""
    print(
        "Use r10n colors --path PATH --dry-run to preview conversion.\n"
        "For writes, review the preview, then use r10n colors --path PATH --no-dry-run --yes.\n"
        "Run go run ./cmd/r10n colors --help (or uv run r10n colors --help) for options.\n"
        "This retired script changed no files.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
