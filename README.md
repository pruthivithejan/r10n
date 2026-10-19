# r10n

**Routine automation in an accessible, keyboard-first terminal.**

![r10n ASCII wordmark](docs/assets/brand/r10n.svg)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Go](https://img.shields.io/badge/Go-native-00ADD8.svg)](https://go.dev/)
[![uv](https://img.shields.io/badge/uv-Package%20Manager-green.svg)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

r10n combines a native Go terminal interface with Python automations. It helps
you generate contacts, personalize PDFs, optimize images, send email, validate
CSV data, and handle other repetitive tasks.

## Install

The standalone installer is the recommended way to use r10n. It verifies the
release checksum and shows real download progress:

```bash
curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh | sh
r10n
```

The installer currently supports Linux x86_64 and macOS arm64. Windows x86_64
users can download the standalone `.exe` from the
[releases page](https://github.com/pruthivithejan/r10n/releases). The installed
application includes its Python worker; Python and uv are not needed at runtime.

To use a released version without a persistent standalone install:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n
```

## Use

Run `r10n` to open the searchable automation picker, or start an automation
directly:

```bash
r10n contacts
r10n images
r10n list
```

Forms validate inputs and review the operation before running. `r10n --help`
lists command-line options. Noninteractive execution requires complete inputs
and `--yes`; that skips confirmation, not validation.

Set up terminal preferences, reusable profiles, and secure credentials from
the terminal:

```bash
r10n setup
r10n config path
r10n configure --template /path/to/template.pdf
r10n config add-smtp-profile work
```

Settings and named profiles are saved in the operating system's per-user config
directory. SMTP passwords are stored in the OS credential manager, not in the
settings file. `r10n config edit` changes preferences; use `r10n config
edit-smtp-profile NAME` or `r10n configure` to update profiles.

Use `r10n --accessible` for plain linear prompts and static progress, or
`r10n --no-motion` to disable animated progress. These options can also be set
as terminal preferences with `r10n setup`.

## Configuration and outputs

`r10n config path` prints the system settings file location. The file can be
edited directly, or through `r10n setup` and the profile commands. Imports and
exports use explicit paths; exports never include credential values.

Inputs and outputs are ordinary paths that you choose. The default output root
is `./r10n-output`; change it in `r10n setup` to use another directory. r10n
does not create a project-local configuration tree or load project `.env` files.

## Developer checks

The following commands are for contributors working in a source checkout, not
for setting up the installed application:

```bash
./setup.sh setup
./setup.sh test
./setup.sh check
./setup.sh build
```

Go owns command routing, Charm forms, progress, and release downloads. Python
owns the registry and automation worker. Both communicate through a versioned
JSON Lines contract. The native build packages the matching worker and smoke
tests the bundle outside the checkout.

## Documentation

- [Get started](https://pruthivithejan.github.io/r10n/get-started/)
- [Terminal configuration](https://pruthivithejan.github.io/r10n/get-started/terminal-configuration/)
- [Automations](https://pruthivithejan.github.io/r10n/automations/)
- [Contributor guidelines](AGENTS.md)

MIT — see [LICENSE](LICENSE). By [Pruthivi Thejan](https://github.com/pruthivithejan).
