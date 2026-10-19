---
icon: lucide/mail
---

# Email

Send personalized emails to recipients from a CSV, with optional PDF attachments.

## Overview

The email automation uses a named SMTP profile, a recipients CSV, and a plain
text body template. SMTP credentials are stored in the operating system's
credential manager, separate from the non-secret profile settings.

## Configure a secure SMTP profile

Create a profile in the terminal. The password prompt does not echo input:

```bash
r10n config add-smtp-profile work
```

Edit server, port, sender, subject, or TLS settings later:

```bash
r10n config edit-smtp-profile work
```

Rotate its password with `r10n config set-secret work`. Passwords are not saved
in the JSON settings file. r10n refuses to fall back to plaintext when the OS
does not provide a secure credential service.

For a one-process run, you can provide `R10N_SMTP_WORK_PASSWORD` directly in the
environment. Do not put credentials in a project `.env` file.

## Run

Create a CSV with `Name` and `Email` columns and a text body template. Then
start the guided terminal form:

```bash
r10n email
```

For a headless send, inspect all paths and recipients first. `--yes` sends real
email without an interactive review:

```bash
r10n email \
  --smtp-profile work \
  --recipients /path/to/recipients.csv \
  --body /path/to/message.txt \
  --attachments-dir /path/to/pdfs \
  --yes
```

`--attachments-dir` is optional and defaults to `r10n-output/fill-pdfs`.
Attachments are matched to recipients by normalized name; for example,
`Alex_Morgan.pdf` can match `Alex Morgan`.

`uvx` is also supported for released versions:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email
```

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--smtp-profile` | — | No | Active profile or `default` | Saved system SMTP profile |
| `--recipients` | `-r` | Yes | — | CSV containing `Name` and `Email` |
| `--body` | `-b` | Yes | — | Plain text message template |
| `--attachments-dir` | `-d` | No | `r10n-output/fill-pdfs` | Optional PDF attachment folder |
| `--yes` | `-y` | No | `false` | Skip interactive confirmation |

## Input files

Recipients CSV:

```csv
Name,Email
Alex Morgan,alex@example.com
Sam Lee,sam@example.com
```

Body template:

```text
Dear {name},

Your certificate is attached.

Regards,
The Team
```

The `{name}` placeholder is replaced with the recipient name.

## Security and troubleshooting

**Authentication failed:** Check the selected SMTP profile, server settings,
and credential with `r10n config set-secret work`. Gmail usually requires an
App Password rather than the account password.

**Connection refused:** Verify SMTP hostname, port, firewall rules, and TLS
settings. Common TLS submission ports are 587 and 465.

**Attachment not found:** Check the attachment directory and ensure filenames
match recipient names.

Before a bulk send, verify the recipient CSV and send a test message. Email
providers may enforce rate limits, and `--yes` can send messages immediately.

## See also

- [Terminal configuration](../get-started/terminal-configuration.md)
- [Fill PDFs](fill-pdfs.md)
- [Get started](../get-started/index.md)
