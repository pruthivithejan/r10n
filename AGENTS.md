# r10n contributor and agent guidelines

r10n automates repetitive workflows through one native Go CLI and a Python
automation backend. Every entry point (`go run`, installed binary, `uv run`,
and `uvx`) presents the same native commands and Charm terminal interface.

## Architecture and ownership

```text
cmd/r10n/                         Small Go executable entry point
internal/cli/                     Public routing, flags, init/status/upgrade/configure
internal/tui/                     Charm picker, forms, review and progress
internal/backend/                 Python process client and bundle discovery
src/r10n_backend/
  __main__.py                     Backend modes: catalog, worker, configure
  registry.py                     Automation metadata, Pydantic inputs, adapters
  worker.py                       Versioned JSON Lines execution protocol
  launcher.py                     Thin uv/uvx bridge to matching native executable
  automations/                    Python workflow implementations
  configure/templates/            Browser PDF configuration assets
configs/                          Default templates embedded by Go init
scripts/                          Shared developer checks, build and version preparation
tests/                            Python tests; Go tests live beside Go implementation
docs/                             Zensical documentation
local/                            Ignored user inputs, outputs, configs and secrets
```

Go owns all public commands and UI. Python owns catalog validation, automation
execution and the configure web service, not a second CLI/TUI framework.
Do not duplicate automation schemas or execution rules in Go.
The backend supports `catalog`, `worker AUTOMATION_ID` (one JSON object on stdin),
and `configure --template PATH [--recipients PATH] [--output PATH]`.
Worker stdout is JSON Lines only; diagnostics belong on stderr.

## Toolchains and developer commands

Install Go (version from `go.mod`), Python 3.10–3.12 and uv.
Use committed `go.sum` and `uv.lock`; never replace locked sync with unconstrained pip installs.

```bash
./setup.sh setup                 # uv sync --locked, Go modules, Lefthook installation
go run ./cmd/r10n                # Primary development entry point
go run ./cmd/r10n init           # Initialize current local/ layout
uv run --locked r10n            # Thin launcher, same native behavior
./setup.sh lint                  # Read-only Go/Python checks
./setup.sh test                  # Both test suites
./setup.sh format                # Explicit Python Black and Go gofmt rewrites
./setup.sh check                 # Full checks including docs
./setup.sh docs                  # Zensical build
./setup.sh build                 # Locked build-only environment, host-native frozen bundle
./setup.sh dev                   # Restore contributor tools after build
```

`scripts/check.py` is shared by hooks and CI. Pre-commit checks staged Go with
**gofmt check**, never silent writes/restaging. Staged paths use NUL-separated
Git output and argument arrays, so spaces are safe. Partially staged code is
rejected rather than checking a different version. Pre-push checks full Go
format/tidy/vet/test, Python lock/versions/Black/Ruff/ty/pytest and docs.

## Automation requirements

- Support absolute input/output paths from outside the checkout; do not assume `local/` exists.
- Support `uvx` and local installation through the same native launcher.
- Register a Pydantic input model and adapter in the Python registry.
- Add public aliases/routing in Go only when needed; reuse registry field definitions.
- Show a header, guided inputs, resolved summary, confirmation and clear results interactively.
- Headless execution must be fully specified and use `--yes`; never prompt on redirected stdin.
- Require confirmation before destructive or externally visible work, including sending email.
- Missing inputs must give actionable errors; native `init` creates examples safely without overwriting.
- Preserve protocol errors, cancellation, artifact paths and process cleanup guarantees.

## Code quality

Python: type hints on functions, Google-style public docstrings, specific helpful
exceptions, standard-library/third-party/local import order, module-level constants.
Use Black (100 columns), Ruff and ty with the project configuration.
Go: gofmt, idiomatic errors and package boundaries; vet and test every package.
Prefer a single source of truth and simple explicit rules over additional abstractions.
Do not introduce a Python public CLI or terminal UI framework.

## Testing and builds

Python tests belong in `tests/test_<module>.py`; Go tests beside their package.
Test missing files, empty/invalid inputs, validation, absolute paths and cancellation.
Use temporary directories and mocks instead of touching real user data or sending email.
Aim for >80% coverage of automation modules.

CI runs Python 3.10, 3.11 and 3.12, checks both languages, `uv lock --check` and
`go mod tidy -diff`, then builds on native Linux x86_64, macOS arm64 and Windows x86_64.
Go cross-compilation alone cannot package native Python dependencies.
Build dependencies are a separate locked `build` group; developer tools must not leak into runtime.
PyInstaller must collect r10n distribution metadata and configure `picker.html`.
Keep Unix runtime symlinks intact and Go `-trimpath -ldflags="-s -w"`.
Native smoke tests run outside checkout and validate contacts, optimized images and generated PDFs.
Bundle size/duplicate reports are evidence, not arbitrary platform-specific limits.

## Documentation

Every automation gets `docs/automations/<name>.md`, an index card and navigation
in `zensical.toml`. Include overview/features, instant and local quick starts,
interactive and fully specified `--yes` examples, parameter table, input/output
formats, configuration, troubleshooting and related links.
Preserve current CLI aliases in examples; JSON input uses registry model field names.
Describe native Go behavior consistently for installed binaries and uv launchers.

## Versioning and releases

`pyproject.toml` `[project].version` is the **only human-edited version**.
Regenerate `uv.lock` with `uv lock`; Go embeds pyproject metadata and the Python
backend uses `importlib.metadata.version("r10n")`. Frozen metadata must be copied.
Check metadata agreement with:

```bash
uv run --locked python scripts/release_version.py --check
go run ./cmd/r10n --version
uv run --locked python -c 'from importlib.metadata import version; print(version("r10n"))'
```

Before committing shipped behavior, choose the highest-impact semantic bump:
fix → patch, feature → minor, breaking change → major. Minor versions do not
require intervening patch releases. **The explicitly requested architecture batch
is 0.12.2**, an exception to the usual minor rule; do not rewrite 0.12.1 or its tag.
`scripts/release_version.py [patch|minor|major]` prepares metadata only, never commits,
tags or pushes. `--dry-run` previews the next version.

`.github/workflows/release.yml` publishes binaries and SHA256SUMS after a version
bump on main (or a matching tag/manual workflow). Do not manually publish a release
or add scripts bypassing that workflow.

Use `<type>(<scope>): <description>` commit messages (`feat`, `fix`, `docs`,
`refactor`, `test`, `chore`). Review remotes before publication. Ask before
irreversible operations, history rewrites or publishing; never commit secrets,
local data, coverage output or generated native assets. Do not delete data outside
the checkout. Obsolete setup/migration scripts only explain native init and safe
manual migration; they must not move user files.
