# r10n contributor and agent guidelines

r10n automates repetitive workflows through one native Go CLI and a Python
automation worker. The standalone binary, `uv run`, and `uvx` share the same
commands, Charm terminal UI, registry contract, and worker protocol.

## Architecture and ownership

```text
cmd/r10n/                         Native executable entry point
internal/cli/                     Commands, flags, settings and upgrades
internal/tui/                     Charm picker, forms, review and progress
internal/backend/                 Python process client and bundle discovery
internal/settings/                Per-user settings and profile schema
internal/brand/                   Generated terminal identity
src/r10n_backend/
  __main__.py                     Backend modes and package launcher
  registry.py                     Automation metadata, Pydantic inputs, adapters
  worker.py                       Versioned JSON Lines execution protocol
  settings.py / secrets.py        Per-user preferences and OS credential store
  automations/                    Python workflow implementations
scripts/                          Developer checks, packaging and version tooling
tests/                            Python tests; Go tests beside implementation
docs/                             Zensical documentation
```

Go owns public commands, terminal interactions, system settings UI, upgrades,
and release progress. Python owns automation schemas, validation, execution,
and per-user profile resolution. Do not add a second Python CLI/TUI or duplicate
the registry's automation rules in Go.

Python backend modes include `catalog`, `worker AUTOMATION_ID`, secret-store
operations, and PDF inspection/preview. Worker stdout is JSON Lines only;
diagnostics belong on stderr. Treat the catalog and worker protocol versions
as a shared Go/Python contract and update tests in both languages when it changes.

## Settings, paths, and secrets

- Do not create, discover, or document project-local `local/`, `workspace/`,
  `configs/`, or `.env` trees for normal product use.
- Store preferences and non-secret named profiles in the OS per-user settings
  directory. Keep the Go and Python paths and JSON schemas in sync.
- Store SMTP passwords only in an OS credential service. Never place a secret
  in settings JSON, command-line arguments, output, fixtures, or logs.
- Inputs and explicit output paths retain their caller-selected meaning. Use
  `r10n-output/` as the default output root; do not silently relocate bare paths.
- `R10N_CONFIG_DIR` is a test/deployment override. It must not default to the
  current working directory or trigger filesystem creation when read.

## Toolchains and developer commands

Install Go (version from `go.mod`), Python 3.10–3.12 and uv for source
development. Use committed `go.sum` and `uv.lock`; do not replace locked sync
with unconstrained pip installs.

```bash
./setup.sh setup                 # Contributor tools, Go modules and hooks
go run ./cmd/r10n                # Native development entry point
./setup.sh lint                  # Read-only Go/Python checks
./setup.sh test                  # Both test suites
./setup.sh format                # Explicit Black and gofmt rewrites
./setup.sh check                 # Full checks including docs
./setup.sh build                 # Host-native bundle and outside-checkout smoke tests
./setup.sh docs                  # Zensical build
```

`setup.sh` is developer tooling only. It must not initialize runtime folders or
write project-local user configuration.

Hooks and CI share `scripts/check.py`. Pre-commit checks staged Go with gofmt
without silently writing or restaging files. Pre-push checks Go format/tidy/vet/test,
Python lock/versions/Black/Ruff/ty/pytest, and documentation.

## Automation requirements

- Support absolute paths outside the checkout and preserve the caller's working directory.
- Register one Pydantic model and adapter in the Python registry; derive forms
  and catalog metadata from that source of truth.
- Keep errors actionable and tests isolated with temporary paths/mocks. Never
  touch real user data or send email in tests.
- Interactive work must show a header, labeled validated inputs, a resolved
  summary, explicit confirmation, and clear status/results.
- Headless runs require complete inputs and `--yes`; never prompt on redirected
  stdin. `--yes` skips review, not validation.
- Keep keyboard instructions discoverable, focus visible, status readable
  without color, and cancellation behavior testable.
- Honor accessible linear prompts and reduced-motion settings. Do not animate
  status when motion is disabled.
- Preserve worker error codes, cancellation, artifact paths, output redaction,
  and process cleanup guarantees.

## Code quality

Python functions require type hints and public functions require Google-style
docstrings. Use specific helpful exceptions, standard-library/third-party/local
import order, module-level constants, Black (100 columns), Ruff, and ty.

Go code must be gofmt-formatted and use idiomatic errors and package boundaries.
Do not add Charm dependencies unless they serve a real UI need; do not import
Crush internal packages or copy code without license review.

## Testing and builds

Python tests belong in `tests/test_<module>.py`; Go tests belong beside their
package. Cover invalid and empty inputs, missing files, absolute paths, settings
round trips, secret handling, accessible/reduced-motion behavior, and cancellation.

CI runs Python 3.10, 3.11 and 3.12, verifies `uv.lock` and `go.mod`, then builds
on native Linux x86_64, macOS arm64 and Windows x86_64 runners. Go
cross-compilation alone cannot package native Python dependencies. Build
dependencies use a separate locked `build` group.

Native bundles must include r10n distribution metadata for
`importlib.metadata.version("r10n")`; they must not carry browser-picker assets
or unused Python CLI/TUI frameworks. Preserve Unix runtime symlinks and Go
`-trimpath -ldflags="-s -w"`. Smoke tests run outside the checkout and verify
the catalog, worker, contacts, images, and PDF output.

## Documentation

Each automation needs `docs/automations/<name>.md`, an index card, and navigation
in `zensical.toml`. Document the installed terminal flow, `uvx` when relevant,
accurate parameters/defaults, input/output formats, system profile requirements,
troubleshooting, and related links. Do not describe project-local configuration
folders or browser-based setup. Document `--yes` as skipping confirmation,
not validation.

## Versioning and releases

`pyproject.toml` `[project].version` is the only human-edited version. Regenerate
`uv.lock` with `uv lock`; Go embeds pyproject metadata and the Python backend
uses installed distribution metadata. Verify before release:

```bash
uv run --locked python scripts/release_version.py --check
go run ./cmd/r10n --version
uv run --locked python -c 'from importlib.metadata import version; print(version("r10n"))'
```

Choose a semantic version bump based on the highest-impact shipped change:
fix → patch, feature → minor, breaking change → major. The release preparation
script never commits, tags, or pushes.

`.github/workflows/release.yml` publishes binaries and checksums after a version
bump on main. Preserve release asset names and compatibility required by older
installed updaters; a bridge release alone does not help users who skip releases.
Do not publish manually or rewrite history.

Use `<type>(<scope>): <description>` commit messages. Review configured remotes
before publication. Ask before irreversible actions or publishing. Never commit
secrets, user data, coverage output, or generated native assets.
