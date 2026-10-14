---
icon: lucide/terminal
---

# Native Charm shell

Every r10n entry point uses the same Go frontend: standalone binary, `go run`,
`uv run r10n` and `uvx`. Charm's huh forms and Bubble Tea progress surround
the Python automation engine; there is no separate Python command interface.

## Interactive use

Run `r10n` or `r10n tui` for the searchable automation picker, or a bare task
such as `r10n contacts` for its guided form. `/` filters by title, category,
description or role. Arrows navigate, Enter advances and Ctrl+C exits.

Forms follow registry defaults, booleans, nullable inputs and enums.
Python validates the payload; review resolved inputs and confirm before running.
Cancellation is the safe default, including for email, renames and overwrites.
During jobs Ctrl+C or Esc terminates the worker and its subprocesses.
Known totals show a progress bar; other jobs show a spinner and live logs.
Results include generated artifact paths.

Set `R10N_ACCESSIBLE=1` for plain prompts and static progress.
Native Go environment options must be exported in the shell; Python `.env`
loading is not a substitute for exporting frontend settings.

## Scripted use

Go routes both public flags and registry-driven jobs:

```bash
r10n contacts --input /tmp/numbers.txt --output /tmp/contacts.vcf --yes
r10n list --json
r10n run contacts \
  --input-json '{"input_file":"/tmp/numbers.txt","output_file":"/tmp/contacts.vcf","prefix":"Customer"}' \
  --json --yes
r10n run images --input-file /path/to/images.json --yes
```

JSON field names match registry models, not public flag aliases.
`--input-file -` reads stdin. Input must be one JSON object, at most 8 MiB.
Unspecified fields use registry defaults. Headless runs require `--yes` and
complete inputs, never prompts. `--yes` skips review, not validation.

`--json` forwards protocol events on stdout and diagnostics on stderr:
`hello`, `started`, `progress`, `log`, `artifact`, `completed`, `error`, `cancelled`.
Input errors exit 2, execution failures exit 1 and cancellation exits 130.
Malformed/incomplete streams and `completed.success=false` fail the command.

Go also owns operational commands:

```bash
r10n init
r10n status
r10n configure --template /path/to/template.pdf --output /path/to/config.json
r10n upgrade --check
```

The configure frontend launches Python's local web service. It includes the
packaged PDF picker asset; it does not dispatch to another CLI implementation.

## Source development

```bash
./setup.sh setup
go run ./cmd/r10n
uv run --locked r10n --help
./setup.sh check
```

Go routing lives in `internal/cli`, Charm UI in `internal/tui` and the Python
client in `internal/backend`. Python lives under `src/r10n_backend`.
Backend modes are `catalog`, `worker AUTOMATION_ID` (stdin JSON), and
`configure --template [--recipients] [--output]`.
The thin launcher builds/resolves or checksum-downloads the matching Go executable.
An unpublished version needs a local Go toolchain if no matching binary exists.

Source builds find the checkout or use `R10N_PROJECT` when run elsewhere.
Python runs the trusted absolute backend entry with the checkout's `src` on its
import path, while retaining the caller's working directory so relative user
paths are not rebased. A lookalike package in the caller's directory cannot
replace the source backend.
`R10N_PYTHON` selects an already-configured interpreter; `R10N_BACKEND`
selects a trusted backend executable, never a shell command.

## Release packaging

```bash
./setup.sh build
./setup.sh dev  # Restore developer tools after build-only locked sync
```

Build dependencies come from the separate locked `build` group, not unconstrained
pip installs or the developer environment. PyInstaller includes distribution
metadata for `importlib.metadata.version("r10n")` and configure `picker.html`.
The build rejects unused old UI/data runtimes if they are not declared dependencies.

Smoke verification runs outside the checkout with absolute temporary paths.
It validates the native version/catalog, generated VCF, optimized WebP dimensions,
and PDF content. Each build writes a size/duplicate JSON report beside its asset.
These reports expose library-copy regressions without brittle platform byte limits.

| Platform | Asset | Backend |
|----------|-------|---------|
| Linux x86_64 | `r10n-linux-x86_64.tar.gz` | Frozen `r10n/libexec/r10n-python/` sidecar |
| macOS arm64 | `r10n-macos-arm64.tar.gz` | Frozen `r10n/libexec/r10n-python/` sidecar |
| Windows x86_64 | `r10n-windows-x86_64.exe` | Embedded frozen backend |

Unix installs/upgrades replace the whole bundle, not only its Go executable.
Applying an upgrade requires confirmation, or `--yes` without a terminal.
Before replacement, the updater checks the requested native/backend version
and runs a contacts job outside the checkout; installed validation failures
restore the old bundle. `upgrade --check` never installs or prompts.
Python-managed `uv`/`uvx` caches must be updated through the Python package,
not modified by native in-place upgrade.
Windows extracts and verifies its backend in a private content-addressed cache;
download a replacement executable instead of using in-place upgrade.
End users need neither Python nor uv.

Go executables use `-trimpath -ldflags="-s -w"`; Unix copies preserve relative
symlinks so shared Python/native libraries are not duplicated.
Native Python dependencies require native Linux/macOS/Windows runners;
Go cross-compilation alone is insufficient. Linux compatibility follows the
runner's glibc baseline, not every distribution.

Cancellation does not roll back outputs. Partial files and extraction caches may
remain; remove unused cache directories only when no r10n process is running.

`.github/workflows/release.yml` builds/publishes matching versioned assets and
SHA256SUMS after a project version bump on main (or matching tag/manual workflow).
`pyproject.toml` is the sole edited version, embedded by Go and checked against
generated `uv.lock` and installed Python metadata. Local builds never publish.
CI checks both languages and Python 3.10–3.12 before platform bundle builds.

## Troubleshooting

**Backend not found:** Reinstall the complete bundle. For source builds, run
`uv sync --locked` and set `R10N_PROJECT` outside the checkout.

**Unsupported protocol/version:** Do not mix sidecars and frontends from different releases.

**Invalid inputs:** Inspect `r10n list --json`. Public aliases such as `--input`
map to registry names like `input_file`; JSON must use the latter.

**Legacy workspace:** `scripts/setup.py` and `scripts/migrate.py` are retired.
Run native `init`, then copy old inputs/configs into `local/` manually, keeping
the originals until outputs have been verified.

## See also

- [Install Binary](install-binary.md)
- [Setup Locally](setup-locally.md)
- [Automations](../automations/index.md)
