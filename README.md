# r10n

**Routine Automation** — automate repetitive tasks with one native CLI.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Go](https://img.shields.io/badge/Go-native-00ADD8.svg)](https://go.dev/)
[![uv](https://img.shields.io/badge/uv-Package%20Manager-green.svg)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- Generate VCF contacts, fill PDF templates and convert Markdown to PDF
- Optimize images, download website images and company logos
- Send personalized email, validate CSV data and batch rename files
- Convert CSS colors to perceptually consistent `oklch()`
- Searchable Charm picker, validated forms, input review and cancellable progress
- Scriptable native flags and JSON execution with explicit headless safety
- One Go frontend and Python execution engine across binaries, `uv run` and `uvx`

## Quick start

### Install a self-contained binary

No Python or uv is required:

```bash
curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh -o install.sh
sh install.sh
r10n
```

The installer verifies release checksums. Update an installed bundle with
`r10n upgrade`; Windows users download the replacement executable.

### Run instantly

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n
```

The thin Python launcher resolves a matching native executable: it builds a
source checkout when Go is available, or downloads the matching published
release with checksum verification. It never substitutes a Python CLI/UI.
An unreleased source version requires Go if no matching release is available.

### Develop locally

Install Go (see `go.mod`), Python 3.10–3.12 and uv:

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
./setup.sh setup
go run ./cmd/r10n init
go run ./cmd/r10n
# The same native behavior through the package launcher:
uv run --locked r10n --help
```

`init` creates ignored `local/inputs`, `local/outputs` and `local/configs`
with examples. It does not overwrite existing user files.

## Usage

Run `r10n` or `r10n tui` to open the picker, or a bare automation command
such as `r10n contacts` for guided inputs. `/` filters tasks; arrows navigate;
Enter advances; Ctrl+C exits. Ctrl+C or Esc cancels active jobs.
Set `R10N_ACCESSIBLE=1` for plain prompts and static progress.

Public commands and aliases are handled by Go:

```bash
r10n --help
r10n contacts --input /path/to/numbers.txt --output /path/to/contacts.vcf --yes
r10n images --input /path/to/images --output /path/to/optimized --yes
r10n configure --template /path/to/template.pdf
r10n status
r10n upgrade --check
```

Every headless execution requires `--yes` and fully specified inputs.
It authorizes running without interactive review; it does not bypass validation.
Keep email and destructive operations interactive until their inputs are verified.

Use registry field names for JSON rather than flag aliases:

```bash
r10n list --json
r10n run contacts \
  --input-json '{"input_file":"/path/to/numbers.txt","output_file":"/path/to/contacts.vcf"}' \
  --json --yes
r10n run images --input-file local/configs/images.json --yes
```

`--input-file -` reads one JSON object from stdin. `--json` emits versioned worker
events on stdout and diagnostics on stderr. Cancellation may leave partial outputs.

## Architecture and tooling

```text
cmd/r10n/                         Native executable
internal/cli/                     Routing, flags and operations
internal/tui/                     Charm UI
internal/backend/                 Python process client
src/r10n_backend/                 Registry, worker, automations and configure web service
scripts/                          Shared checks, native packaging and version preparation
```

The Python package has no public CLI/TUI framework. Registry schemas are the
source of automation defaults and validation. Python backend modes are `catalog`,
`worker AUTOMATION_ID` and `configure`; the public command surface belongs to Go.

```bash
./setup.sh lint                  # Format, lint, type, lock and Go checks (read-only)
./setup.sh test                  # Go + Python tests
./setup.sh format                # Explicit Black + gofmt rewrites
./setup.sh check                 # Complete checks and documentation build
./setup.sh build                 # Host-native bundle and real artifact smoke tests
./setup.sh dev                   # Restore dev tooling after isolated build sync
```

Lefthook checks changed Go files with gofmt before commit without altering staged
changes. Pre-push and CI enforce full Go/Python checks, including module/lock
consistency. Python CI covers 3.10, 3.11 and 3.12. Native bundles use target-platform
build runners; Unix sidecar symlinks are preserved and Windows embeds the backend.
Builds validate contacts, image optimization and PDF generation outside the checkout
and produce JSON size/duplicate reports.

## Releases

`pyproject.toml` is the only human-edited version. Go embeds it; Python uses
installed distribution metadata. The generated `uv.lock` package version must agree.

```bash
uv run --locked python scripts/release_version.py --check
uv run --locked python scripts/release_version.py patch --dry-run
# Prepare, review, and commit separately; this never publishes:
uv run --locked python scripts/release_version.py patch
```

A version bump committed on main triggers `.github/workflows/release.yml`,
which builds native assets, SHA256SUMS and the GitHub release. Do not publish
manually through local scripts. Architecture batch 0.12.2 is explicitly requested;
the completed 0.12.1 release remains unchanged.

## Documentation

- [Get started](https://pruthivithejan.github.io/r10n/get-started/)
- [Automations](https://pruthivithejan.github.io/r10n/automations/)
- [Native shell and packaging](docs/get-started/native-shell.md)
- [Contributor guidelines](AGENTS.md)

MIT — see [LICENSE](LICENSE). By [Pruthivi Thejan](https://github.com/pruthivithejan).
