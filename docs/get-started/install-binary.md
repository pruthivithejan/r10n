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

The installer downloads the correct app archive for your OS/architecture, verifies checksums, installs the extracted app under `~/.local/bin/.r10n`, and creates the `~/.local/bin/r10n` launcher.

The release workflow publishes the binaries and `SHA256SUMS` automatically after a version bump on `main`, so `install.sh` always targets the latest published release.

---

## Verify

```bash
r10n --version
r10n --help
```

Run the terminal UI:

```bash
r10n
```

The terminal workspace lets you search by automation or role, complete a validated form,
review the exact inputs, and follow live results. Use `r10n --help` or a direct subcommand
such as `r10n contacts --input numbers.txt` when you prefer the traditional CLI.

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

### TLS certificate verification failed during upgrade

`r10n upgrade` uses the packaged certifi CA store for GitHub downloads. If your network uses a custom proxy certificate, set `SSL_CERT_FILE` to that CA bundle and retry.

If your installed binary is older and fails before it can use the fixed upgrader, reinstall once with the installer instead of `r10n upgrade`:

```bash
curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh | sh
```

Then verify:

```bash
r10n --version
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
