---
icon: lucide/terminal
---

# Native Charm shell

Prebuilt r10n releases use a Go frontend powered by Charm's huh and Bubble Tea.
The Python automation core, Pydantic models, and v1 JSON Lines protocol are unchanged.
The Python `uvx` and `uv run r10n` entry points remain available, including their
existing Textual workspace.

## Interactive use

Run `r10n` or `r10n tui` to choose an automation. The picker includes every registered
task and supports `/` filtering by title, category, description, or role.
Run a bare task such as `r10n contacts` to open its guided form directly.

Forms use registry field order, defaults, booleans, nullable inputs, and enum choices.
Numbers and required values get immediate feedback; Pydantic validates the final
payload before execution. Review the input table and confirm before running.
Confirmation starts at **Cancel**, including for email, file renaming, and overwrites.

Arrow keys navigate, Enter advances, and Ctrl+C exits. During execution,
Ctrl+C or Esc terminates the worker and its subprocesses. Known totals display
a progress bar; other tasks display a spinner and live log messages.
Results appear as a table with generated artifact paths.

Set `R10N_ACCESSIBLE=1` for plain prompts and static progress without animation.
Native interactive workflows need an attached terminal; headless workflows must
use JSON inputs or existing command flags instead.

## Scripted use

JSON input names match the Pydantic models, not the old CLI option aliases:

```bash
r10n list
r10n list --json
r10n run contacts \
  --input-json '{"input_file":"/tmp/numbers.txt","output_file":"/tmp/contacts.vcf","prefix":"Customer"}' \
  --json --yes
```

Alternatively use `--input-file inputs.json`, or `--input-file -` to read stdin.
Input must be one JSON object, at most 8 MiB. Unspecified fields use Python defaults.
`--yes` is required without a terminal and authorizes execution without review.
Without `--json`, events and results are printed as plain text and a table.

`--json` forwards original protocol events on stdout, with diagnostics on stderr:
`hello`, `started`, `progress`, `log`, `artifact`, `completed`, `error`, or `cancelled`.
The shell requires protocol version 1, rejects malformed or incomplete streams,
and preserves worker input errors (exit 2), execution failures (exit 1), and
cancellation (exit 130). `completed.success=false` is also a failure.

Existing CLI flags still dispatch to the Python frontend:

```bash
r10n contacts --input numbers.txt --output contacts.vcf
r10n configure
r10n init
r10n status
r10n upgrade --check
r10n legacy --help
```

This compatibility path intentionally retains legacy prompts and flag semantics.
The native shell does not translate them into a second input-validation system.
Legacy commands remain in the terminal's foreground process group so their
prompts and terminal signals work normally. The isolated-worker subtree
cancellation guarantee applies to native form and JSON jobs, not this compatibility path.

## Source development

```bash
uv sync
go run ./cmd/r10n
go test ./...
go vet ./...
uv run pytest
```

Source builds discover the checkout from the working directory or executable
location and run the trusted absolute `src/backend.py` script through
`uv run --project <checkout> python -u <checkout>/src/backend.py`.
The subprocess keeps the caller's working directory, so relative paths stay relative
to the user, not the checkout.

For a source binary run elsewhere, set `R10N_PROJECT` to the checkout.
`R10N_PYTHON` can select an already-configured Python interpreter instead of uv.
`R10N_BACKEND` can select a compatible backend executable for testing/integration;
it is an executable path, never a shell command. Only use a backend you trust.
Source builds do not support the standalone upgrader.

## Release packaging

Build for the host OS after installing Go and the Python project:

```bash
uv run --with pyinstaller python scripts/build_native.py
```

The build performs a real contacts run with absolute temporary paths from outside
the checkout and verifies the generated VCF and catalog.

| Platform | Asset | Backend |
|----------|-------|---------|
| Linux x86_64 | `r10n-linux-x86_64.tar.gz` | Frozen sidecar under `r10n/libexec/r10n-python/` |
| macOS arm64 | `r10n-macos-arm64.tar.gz` | Frozen sidecar under `r10n/libexec/r10n-python/` |
| Windows x86_64 | `r10n-windows-x86_64.exe` | Frozen onefile backend embedded in Go |

Unix installers and upgrades replace the **whole bundle**. Copying only its Go
executable will not provide an automation runtime. Windows extracts its embedded
backend into a content-addressed user cache, verifies existing contents before use,
and never downloads Python at runtime. Windows in-place upgrade remains unsupported;
download the replacement executable from the release.

The Go shell can cross-compile, but the frozen Python runtime and native Python
dependencies must be built on each target platform. GitHub Actions uses native
Linux, macOS, and Windows runners rather than pretending `GOOS` alone packages Python.
Linux runtime compatibility follows the build runner's glibc baseline; the asset
is not a promise of compatibility with every Linux distribution.

Cancellation force-terminates processes without rolling back work already done.
Partially written outputs can remain, and a frozen onefile runtime may leave
temporary extraction files. Windows' content-addressed backend cache also retains
older versions; unused cache directories can be removed when r10n is not running.

`.github/workflows/release.yml` publishes installer-compatible assets and
`SHA256SUMS` after a version increase in `pyproject.toml` on `main`, or a matching
`v*` tag/manual run. It reuses `build-binaries.yml` and validates the CLI version.
The complete Python test suite runs on Python 3.10, 3.11, and 3.12 before the
three native bundles are built and smoke-tested.
Go embeds `pyproject.toml` as its version source. No release is published by a
local build.

Release Go executables are stripped and built with `-trimpath`. Unix packaging
preserves PyInstaller's relative symlinks so the Python runtime and native image
libraries are stored once rather than copied for each library reference.

## Troubleshooting

**Python backend not found:** Reinstall the complete release bundle. For source
builds, run `uv sync` and set `R10N_PROJECT` if running outside the checkout.

**Unsupported protocol:** The native shell and backend are from different releases.
Reinstall together; do not mix sidecars between versions.

**Invalid inputs:** Inspect `r10n list --json` or the worker error event. Existing
CLI aliases such as `--input` map to model names such as `input_file` only in
the compatibility command path.

## See also

- [Install Binary](install-binary.md)
- [Setup Locally](setup-locally.md)
- [Automations](../automations/index.md)
