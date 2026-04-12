---
icon: lucide/cloud-download
---

# Install Binary

Install `r10n` as a standalone binary using `curl`, then run it directly from your terminal.

---

## Prerequisites

- macOS or Linux
- `curl`

---

## Install with curl

Quick install:

```bash
curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh | sh
```

Safer two-step install:

```bash
curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh -o install.sh
sh install.sh
```

The installer downloads the correct binary for your OS/architecture, verifies checksums, and installs to `~/.local/bin/r10n`.

---

## Verify

```bash
r10n --version
r10n --help
```

If `r10n` is not found, add this to your shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then restart the terminal.

---

## Upgrade

Update to the latest release:

```bash
r10n upgrade
```

Check only (no install):

```bash
r10n upgrade --check
```

Install a specific version:

```bash
r10n upgrade --version v2.0.0
```

---

## Optional installer flags

Install a specific version:

```bash
sh install.sh --version v2.0.0
```

Install to a custom directory:

```bash
sh install.sh --install-dir "$HOME/bin"
```

---

## Troubleshooting

### Permission denied during upgrade

Install to a writable path such as `~/.local/bin`, then retry:

```bash
r10n upgrade
```

### Unsupported platform

Current prebuilt binaries support:

- Linux x86_64
- macOS arm64
- Windows x86_64 (release artifact only)

Use [Run on Terminal](run-on-terminal.md) with `uvx` if your platform is not yet available.

---

## Next Steps

- [Run on Terminal](run-on-terminal.md) — Use r10n without installing
- [Setup Locally](setup-locally.md) — Full local source setup
- [Automations](../automations/index.md) — Explore all commands
