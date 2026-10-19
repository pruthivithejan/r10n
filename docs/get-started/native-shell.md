---
icon: lucide/terminal
---

# Native terminal UI

The installed command uses a native Go interface built with Charm libraries and
the existing Python automation worker. Forms, validation, progress, and command
line execution use one registry contract.

## Navigate and run

Open the searchable automation picker:

```bash
r10n
```

Use `/` to search, arrow keys to move, and Enter to select or advance through
forms. Press Escape or Ctrl+C to go back or cancel the active operation. The
UI reviews resolved inputs before execution, shows progress and artifacts, and
reports errors in plain text.

Run a guided form directly with a task name, or use flags for scripting:

```bash
r10n contacts
r10n contacts --input /path/to/numbers.txt --output /path/to/contacts.vcf --yes
r10n list --json
```

Headless runs must include all required inputs and `--yes`. This skips the
confirmation prompt, not input validation. To inspect the JSON schema and
available operations, use `r10n list --json`.

## Accessible prompts and motion

Choose persistent preferences with `r10n setup`, or use one-run overrides:

```bash
r10n --accessible contacts
r10n --no-motion contacts
```

Accessible mode uses linear, screen-reader-friendly prompts and static textual
progress. Reduced-motion mode keeps the interactive layout but removes animated
spinners. The UI also provides clear key instructions, visible focus, readable
text statuses, and honors the `NO_COLOR` environment variable.

## System settings and profiles

```bash
r10n config path
r10n config edit
r10n configure --template /path/to/template.pdf
r10n config add-smtp-profile work
```

Settings, PDF profiles, and non-secret SMTP profile details live in the
operating system's per-user config directory. SMTP credentials are stored in
the platform credential manager. Inputs and outputs remain ordinary paths
selected by the user; no project-local config tree is created.

See [Terminal configuration](terminal-configuration.md) for profile editing,
import/export, output defaults, and secure credentials.

## JSON Lines and JSON input

Use the registry's field names in JSON, not flag aliases:

```bash
r10n run contacts \
  --input-json '{"input_file":"/path/to/numbers.txt","output_file":"/path/to/contacts.vcf"}' \
  --json --yes
```

`--input-file PATH` reads a JSON object from a file; `--input-file -` reads
stdin. JSON output streams `hello`, `started`, `progress`, `log`, `artifact`,
`completed`, `error`, and `cancelled` events to stdout. Diagnostics stay on
stderr. Input errors exit 2, execution failures exit 1, and cancellation exits
130.

## Download and upgrade

The installer verifies the selected release checksum and reports received and
total megabytes. In-place Unix upgrades use the same byte-based progress and
validate the complete app bundle before replacing it:

```bash
r10n upgrade --check
r10n upgrade
```

`--check` does not install anything. Windows users should download the new
release executable from GitHub Releases. `uv`/`uvx`-managed installations are
updated through uv, not by replacing a standalone bundle.

## Contributor development

These commands are only for maintainers working from a source checkout:

```bash
./setup.sh setup
./setup.sh test
./setup.sh check
./setup.sh build
```

Go code lives in `internal/cli`, `internal/tui`, and `internal/backend`.
Python code in `src/r10n_backend` defines the automation registry and worker.
The standalone release packages the worker beside the Go frontend on Unix and
embeds it in the Windows executable.

See the [contributor guidelines](https://github.com/pruthivithejan/r10n/blob/main/AGENTS.md)
for build and test instructions.
