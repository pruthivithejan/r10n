#!/usr/bin/env bash
# Non-mutating checks are separate from explicit formatting/setup commands.
set -euo pipefail
cd "$(dirname "$0")"
command="${1:-help}"
if [ "$#" -gt 0 ]; then shift; fi
case "$command" in
  setup|dev)
    uv sync --locked
    go mod download
    uv run --locked lefthook install
    echo "Ready. Run: go run ./cmd/r10n"
    ;;
  run) go run ./cmd/r10n "$@" ;;
  lint)
    uv run --locked python scripts/check.py go
    uv run --locked python scripts/check.py python
    ;;
  test)
    go test ./...
    uv run --locked pytest "$@"
    ;;
  format)
    uv run --locked black src tests scripts
    uv run --locked python scripts/check.py go-format
    ;;
  build)
    # Deliberately omit dev tooling from the PyInstaller collection environment.
    uv sync --locked --no-dev --group build
    uv run --locked --no-dev --group build python scripts/build_native.py "$@"
    ;;
  check) uv run --locked python scripts/check.py all ;;
  docs) uv run --locked zensical build --clean ;;
  version)
    go run ./cmd/r10n --version
    uv run --locked python -c 'from importlib.metadata import version; print("Python package:", version("r10n"))'
    ;;
  help)
    echo "Usage: ./setup.sh {setup|dev|run|lint|test|format|build|check|docs|version}"
    echo "setup/dev: locked Python dependencies, Go modules, and Git hooks"
    echo "run: native CLI (arguments passed through); setup edits per-user preferences"
    echo "lint/check: read-only checks; format: explicitly rewrites Go/Python formatting"
    echo "test: Go and Python suites; build: host-native frozen release and outside-checkout smoke"
    echo "After build, run ./setup.sh dev to restore contributor tools."
    ;;
  *) echo "Unknown command: $command. Run ./setup.sh help." >&2; exit 2 ;;
esac
