---
icon: material/folder-cog
---

# Setup locally

Use Go and Python together for native CLI development and repeated automations.
For a ready-to-run application without toolchains, [install a binary](install-binary.md).

## Requirements

- Go (version specified in `go.mod`)
- Python 3.10–3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git; Bash for the convenience `setup.sh` commands

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
./setup.sh setup
go run ./cmd/r10n init
go run ./cmd/r10n
```

`setup` installs locked Python dependencies, downloads Go modules and enables
Lefthook. `init` creates ignored user data and examples, without overwriting
existing files. The old workspace setup/migration scripts are retired.

## File layout

```text
r10n/
├── cmd/r10n/                    Native executable
├── internal/
│   ├── cli/                     Commands, flags and operations
│   ├── tui/                     Charm picker/forms/progress
│   └── backend/                 Python client
├── src/r10n_backend/             Python registry, worker and automations
├── configs/                     Default init templates
├── scripts/                     Developer checks and packaging
├── tests/                       Python tests
└── local/                       Ignored user data
    ├── inputs/
    ├── outputs/
    └── configs/
```

Use native `init` to create examples, then edit `local/configs`.
Keep credentials in ignored environment/config files, never source control.
Native Go options such as `R10N_ACCESSIBLE` must be exported in your shell.

## Run an automation

Go is the primary developer entry point:

```bash
go run ./cmd/r10n contacts
go run ./cmd/r10n images
go run ./cmd/r10n configure --template /path/to/template.pdf
```

The package launcher offers exactly the same native commands:

```bash
uv run --locked r10n contacts \
  --input local/inputs/contacts/numbers.txt \
  --output local/outputs/contacts/contacts.vcf \
  --yes
uv run --locked r10n run images --input-file local/configs/images.json --yes
```

Headless executions require `--yes` and all necessary input flags or JSON.
It skips confirmation, not validation. Bare commands guide you interactively.
Absolute paths work outside the checkout; relative paths use your current directory.

## Developer commands

| Command | Purpose |
|---------|---------|
| `./setup.sh setup` / `dev` | Sync locked contributor dependencies and install hooks |
| `./setup.sh run [args]` | Run native Go CLI |
| `./setup.sh lint` | Read-only Go/Python validation |
| `./setup.sh test` | Both test suites |
| `./setup.sh format` | Explicit Black and gofmt rewrites |
| `./setup.sh check` | Complete toolchain, tests and docs checks |
| `./setup.sh docs` | Clean Zensical build |
| `./setup.sh build` | Build-only locked environment and native smoke tests |
| `./setup.sh version` | Compare Go and Python metadata versions |

The shared checks enforce Go fmt/tidy/vet/test and Python lock/version/Black/Ruff/ty/pytest.
Pre-commit checks changed Go files without rewriting staging; pre-push checks everything.
Partially staged code must be fully staged or stashed before checking.
Build removes developer dependencies from its runtime environment; run `dev` afterward.
On Windows, use Git Bash for `setup.sh`, or invoke the listed uv/Go commands directly.

## Update

```bash
git pull
uv sync --locked
go mod download
```

Installed binaries use `r10n upgrade`. Source builds should update source, not
overwrite themselves with a binary release.

## Troubleshooting

**Missing dependencies:** Run `uv sync --locked` and `go mod download`.

**No matching native release:** An unpublished source checkout requires Go
for launcher compilation. Published launchers can download checksum-verified binaries.

**Legacy `workspace/` data:** Run `r10n init`, copy needed inputs/configs manually
into `local/`, and retain originals until results are checked. No automatic
migration deletes or moves user files.

**Permission denied:** Choose a writable output directory; never run as root
just to bypass input/output permissions.

## See also

- [Native shell and packaging](native-shell.md)
- [Automations](../automations/index.md)
- [Contributor guidelines](https://github.com/pruthivithejan/r10n/blob/main/AGENTS.md)
