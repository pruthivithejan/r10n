---
icon: lucide/rocket
---

# Get started

r10n runs as a native terminal application. Install the standalone binary for
regular use, or run a released version with `uvx`.

## Recommended: install the binary

The installer verifies checksums, shows download progress, and installs the
complete application bundle:

```bash
curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh | sh
r10n
```

See [Install Binary](install-binary.md) for supported platforms and upgrade
instructions.

## Try it with uvx

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n
```

`uvx` needs Python 3.10+ and may use Go to build an unpublished version. Use the
standalone binary when you want a self-contained installed command.

## Choose an automation

Run `r10n` for the searchable picker, or open a guided form directly:

```bash
r10n contacts
r10n images
r10n --help
```

The UI validates inputs and asks for confirmation before execution. Headless
commands require complete inputs and `--yes`.

## Set up the terminal

```bash
r10n setup
r10n config path
```

Preferences and reusable profiles are saved in the operating system's per-user
configuration directory, not in the current project. Use the
[Terminal configuration](terminal-configuration.md) guide to set accessibility
options, output defaults, PDF profiles, and SMTP credentials.

## Explore

- [Run on Terminal](run-on-terminal.md) — use `uvx` or command-line flags
- [Install Binary](install-binary.md) — install and upgrade the standalone app
- [Terminal configuration](terminal-configuration.md) — edit system preferences and profiles
- [Automations](../automations/index.md) — browse the available tasks
