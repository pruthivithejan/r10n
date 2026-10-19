---
icon: lucide/square-terminal
---

# Run on Terminal

Use uv to run r10n without cloning or installing the application yourself.
All entry points open the same native Go/Charm interface.

## Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and verify:

```bash
uv --version
```

The package launcher needs Python 3.10+ (uv can provision it).
It resolves/builds a matching Go executable when the Go toolchain is available,
or downloads the matching published native release and verifies its checksum.
Unreleased versions and platforms without release assets require Go.
For no Python tooling at all, [install the standalone bundle](install-binary.md).

## Run instantly

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n --help
```

The first command opens the native picker; the second lists public commands.
uv caches the package environment and the launcher may cache the matching native
executable. It does not run a separate Python command interface.

| Key | Action |
|-----|--------|
| `/` | Filter automation search |
| Arrow keys | Move through automations |
| Enter | Select or advance |
| Ctrl+C | Exit or cancel active work |
| Esc | Cancel active progress |

Select a task for generated forms, validated inputs, review and confirmation.
Run a bare command such as `r10n contacts` to open its form directly.
Set `R10N_ACCESSIBLE=1` for plain prompts and static progress.

## CLI flag examples

The native Go frontend preserves automation flag aliases.
For scripting/non-terminal input, provide all needed values and `--yes`.
This authorizes execution without review, not without validation.

### Contacts

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts \
  --input /path/to/numbers.txt --prefix Customer \
  --output /path/to/customers.vcf --yes
```

Input text contains one phone number per line:

```text
+94771234567
+94777654321
```

### Images

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images \
  --input /path/to/photos --output /path/to/optimized --quality 85 --yes
```

### CSS color preview

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors \
  --file /path/to/styles.css --dry-run --yes
```

Review the preview before opting into writes with `--no-dry-run`.

### Fill PDFs

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n fill-pdfs \
  --config conference --recipients /path/to/participants.csv --yes
```

Create a named profile with `r10n configure --template /path/to/template.pdf`.
See [Terminal configuration](terminal-configuration.md) and
[Fill PDFs](../automations/fill-pdfs.md).

### Email

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email \
  --smtp-profile work --recipients /path/to/recipients.csv \
  --body /path/to/message.txt --attachments-dir /path/to/attachments --yes
```

`--yes` can send real email. Verify recipients, credentials and content in
interactive mode before unattended use.

## JSON workflows

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n list --json
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n run contacts \
  --input-json '{"input_file":"/path/to/numbers.txt","output_file":"/path/to/contacts.vcf"}' \
  --json --yes
```

Registry field names, not flag aliases, are used in JSON.
`--input-file PATH` reads a file; `--input-file -` reads stdin.
See [Native shell](native-shell.md) for protocol events and error codes.

## Tips and troubleshooting

- Use absolute paths outside the checkout; relative paths follow your current directory.
- Run `r10n COMMAND --help` to inspect current flags.
- Missing files are not downloaded or silently generated during execution; prepare inputs first.
- If there is no matching published release, install Go or use a released version.
- Behind a firewall, configure your network's proxy and certificate trust for the installer or uv.
- Cancellation stops subprocesses but may leave partial outputs.

## See also

- [Install Binary](install-binary.md)
- [Terminal configuration](terminal-configuration.md)
- [Automations](../automations/index.md)
