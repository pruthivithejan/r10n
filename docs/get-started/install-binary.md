---
icon: lucide/cloud-download
---

# Install Binary

Install the complete standalone r10n application, then run it directly from your terminal.

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

The installer prints the r10n logo, reports the release's expected size, and
shows actual transfer progress. It verifies the downloaded archive against
`SHA256SUMS`, installs the complete app under `~/.local/bin/.r10n`, and creates
the `~/.local/bin/r10n` launcher. The bundle contains the Python automation
worker; Python is not required to run it.

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

The native Charm picker lets you search by automation or role, complete a validated form,
review inputs, and follow live results. Existing flags such as
`r10n contacts --input numbers.txt --output contacts.vcf --yes` are parsed and executed by the same Go frontend. Headless runs require `--yes` and complete inputs. See the
[Native Charm shell](native-shell.md) guide for JSON-driven runs and keyboard controls.

If `r10n` is not found, add this to your shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then restart the terminal.

---

## Upgrade

Update a standalone Unix installation to the latest release:

```bash
r10n upgrade
```

Check only (no install):

```bash
r10n upgrade --check
```

Install a specific version (for example, the 0.13.1 release):

```bash
r10n upgrade --version v0.13.1
```

The updater shows the r10n logo and byte-based progress with received and total
megabytes, using the same terminal palette as the forms. Narrow terminals keep
the numeric status without wrapping the live meter. Accessible and reduced-motion
modes print static progress lines instead. It asks before replacing the complete application bundle. For
scripts, review the target with `upgrade --check`, then explicitly authorize:

```bash
r10n upgrade --yes
```

The downloaded release is checksum-verified and tested before replacement.
If installed validation fails, the previous bundle is restored. In-place
upgrades apply only to standalone Unix installations; update a `uv`/`uvx`
package through its package manager instead.

---

## Optional installer flags

Install a specific version:

```bash
sh install.sh --version v0.13.1
```

Install to a custom directory:

```bash
sh install.sh --install-dir "$HOME/bin"
```

---

## Troubleshooting

### Unsupported catalog protocol during an older upgrade

The `0.12.x` updater requires protocol 1, while `0.13.x` uses protocol 2.
An older updater can reject the new bundle with
`unsupported catalog protocol 2 (expected 1)` before replacing the installation.
The existing application remains intact.

Use the checksum-verified installer once to move from `0.12.x` to `0.13.1`:

```bash
curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh | sh -s -- --version v0.13.1
r10n --version
r10n upgrade --check
```

Starting with `0.13.1`, the updater validates the target release's supported
protocol and requires its catalog and execution events to agree, instead of
assuming the target must use the updater's own protocol. The normal Go/Python
worker connection still requires the matching protocol; validation is not skipped.

### Permission denied during upgrade

Install to a writable path such as `~/.local/bin`, then retry:

```bash
r10n upgrade
```

### TLS certificate verification failed during upgrade

The native upgrader verifies TLS using the operating system's certificate roots. If your network uses a custom proxy certificate, configure the system trust store; on supported Unix systems `SSL_CERT_FILE` can point to a trusted CA bundle.

If your installed binary is older and fails before it can use the fixed upgrader, reinstall once with the installer instead of `r10n upgrade`:

```bash
curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh | sh
```

Then verify:

```bash
r10n --version
```

### Unsupported platform

The installer supports:

- Linux x86_64
- macOS arm64

Windows x86_64 users can install the standalone executable from
[GitHub Releases](https://github.com/pruthivithejan/r10n/releases). Other
platforms do not currently have a prebuilt artifact.

---

## Next Steps

- [Run on Terminal](run-on-terminal.md) — Use r10n without installing
- [Terminal configuration](terminal-configuration.md) — Save preferences and profiles
- [Automations](../automations/index.md) — Explore all commands
