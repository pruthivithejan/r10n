---
icon: lucide/settings-2
---

# Terminal configuration

Preferences and reusable profiles are stored in one versioned file in your
operating system's per-user configuration directory. No project-local config
folder is created.

## Preferences and accessibility

Open the guided preference form:

```bash
r10n setup
```

It can set the terminal theme, linear accessible prompts, reduced motion, and
the default output directory. The defaults are also available as command-line
overrides:

```bash
r10n --accessible
r10n --no-motion
```

`--accessible` uses plain, linear prompts and static textual progress.
`--no-motion` keeps the regular form layout but removes animated progress
indicators. The terminal UI displays key actions and keeps status readable
without color.

Inspect or edit the settings file:

```bash
r10n config path
r10n config edit
```

`config path` prints the exact file location without creating it. The directory
and file are created with private permissions when settings are first saved.
You can edit the JSON directly, or export a non-secret copy with
`r10n config export /path/to/settings-backup.json`.

## Output directory

By default, generated output goes under `./r10n-output` relative to the
directory where you run r10n. Use `r10n setup` to select another default root.
Individual automation flags can still use any explicit input or output path.

## PDF profiles

Configure a PDF template in the terminal:

```bash
r10n configure --template /path/to/template.pdf
```

The guided form inspects optional recipient data, lets you place fields using
PDF-point coordinates, previews a sample, and saves the profile to system
settings. Give the profile a name to store more than one template. Run
`r10n fill-pdfs --help` to see how to select a named profile and recipient file.

## SMTP profiles and credentials

Add an email account from a hidden-password prompt:

```bash
r10n config add-smtp-profile work
```

Use the terminal form to edit non-secret connection details:

```bash
r10n config edit-smtp-profile work
```

Rotate or remove the credential separately:

```bash
r10n config set-secret work
r10n config delete-secret work
```

Passwords are stored in the operating system's credential manager. They are
not written to the settings JSON, command history, or command-line arguments.
If no secure credential service is available, r10n refuses to store a password
in plaintext. For a one-run alternative, provide
`R10N_SMTP_WORK_PASSWORD` in the process environment; do not put it in a project
`.env` file.

`r10n config export` never includes passwords. `r10n config import PATH` reviews
and imports a legacy JSON profile into system settings; any imported SMTP
password is moved into the credential manager.

## See also

- [Install Binary](install-binary.md)
- [Native shell](native-shell.md)
- [Email automation](../automations/email.md)
- [Fill PDFs automation](../automations/fill-pdfs.md)
