---
icon: material/console
---

# Run on Terminal

Run r10n directly from your terminal without cloning or installing anything. Perfect for quick, one-off automation tasks.

## Prerequisites

You need Python 3.10+ and uv installed on your system.

### Install uv

=== "macOS / Linux"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

Verify installation:

```bash
uv --version
```

## Running Automations

Use `uvx` to run any r10n automation:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n <command>
```

### Available Automations

All feature guides linked below:

| Automation | Command | Description |
|------------|---------|-------------|
| [Contacts](automations/contacts.md) | `contacts` | Generate VCF contact cards |
| [Certificates](automations/certificates.md) | `certificates` | Create PDF certificates |
| [Images](automations/images.md) | `images` | Optimize images to WebP |
| [Email](automations/email.md) | `email` | Send bulk emails |

Additional commands: `init` (setup folders), `status` (check setup)

See [Automations Index](automations/index.md) for a visual summary.

## Contacts

Generate VCF contact cards from phone numbers.

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts
```

The interactive prompts will ask for:

1. **Input file** - Text file with phone numbers (one per line)
2. **Prefix** - Name prefix for contacts (e.g., "Customer")
3. **Output file** - Where to save the VCF file

### Input File Format

Create a text file with phone numbers:

```text
# Sri Lankan numbers (comments start with #)
0771234567
0781234567
+94791234567
```

### Example

```bash
$ uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts

Step 1/3: Select input file
  Enter path to file with phone numbers: numbers.txt
Step 2/3: Set contact name prefix
  Enter prefix for contact names: Customer
Step 3/3: Set output file
  Enter output VCF file path: contacts.vcf

Proceed with contact generation? [y/n]: y

Done!
┌─────────────────────┬──────────────┐
│ Total numbers       │ 50           │
│ Valid contacts      │ 48           │
│ Duplicates removed  │ 1            │
│ Invalid numbers     │ 1            │
│ Output file         │ contacts.vcf │
└─────────────────────┴──────────────┘
```

## Certificates

Generate PDF certificates from a template.

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n certificates
```

The interactive prompts will ask for:

1. **Config file** - JSON file with certificate settings
2. **Template** - PDF template file
3. **Recipients** - TXT or CSV file with names
4. **Output directory** - Where to save certificates

### Recipients File Format

=== "TXT (Tab-separated)"

    ```text
    John Doe	Team Lead
    Jane Smith	Developer
    Bob Johnson	Designer
    ```

=== "CSV"

    ```csv
    name,position
    John Doe,Team Lead
    Jane Smith,Developer
    Bob Johnson,Designer
    ```

### Example

```bash
$ uvx --from git+https://github.com/pruthivithejan/r10n.git r10n certificates

Step 1/4: Select configuration
  Enter path to configuration file: config.json
Step 2/4: Select PDF template
  Enter path to PDF template: template.pdf
Step 3/4: Select recipients file
  Enter path to recipients file: recipients.csv
Step 4/4: Set output directory
  Enter output directory: ./certificates

Proceed with certificate generation? [y/n]: y

Generating certificates...

Done!
┌───────────────────┬──────────────────────┐
│ Total recipients  │ 25                   │
│ Generated         │ 25                   │
│ Failed            │ 0                    │
│ Output directory  │ ./certificates       │
└───────────────────┴──────────────────────┘
```

## Images

Optimize and convert images to WebP format.

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images
```

The interactive prompts will ask for:

1. **Input directory** - Folder with images
2. **Output directory** - Where to save optimized images
3. **Quality** - Compression quality (1-100)
4. **Max size** - Maximum file size in MB
5. **Filenames** - Keep original or use prefix

### Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- TIFF (.tiff)
- WebP (.webp)

### Example

```bash
$ uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images

Step 1/5: Select input directory
  Enter path to directory with images: ./photos
  Found 20 images in: ./photos
Step 2/5: Set output directory
  Enter output directory: ./optimized
Step 3/5: Set image quality
  Enter quality percentage (1-100): 85
Step 4/5: Set maximum file size
  Enter maximum file size in MB: 1.0
Step 5/5: Set output filenames
  Keep original filenames or use prefix? [keep/prefix]: keep

Proceed with optimization? [y/n]: y

Done!
┌────────────────┬──────────────┐
│ Processed      │ 20           │
│ Skipped        │ 0            │
│ Failed         │ 0            │
│ Output directory│ ./optimized │
└────────────────┴──────────────┘
```

## Email

Send bulk personalized emails with attachments.

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email
```

The interactive prompts will ask for:

1. **Config file** - JSON file with SMTP settings
2. **Recipients** - CSV file with Name and Email columns
3. **Body template** - Text file with email content
4. **Certificates directory** - Folder with PDF attachments

### Config File Format

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "email": "your-email@gmail.com",
  "password": "your-app-password",
  "subject": "Your Certificate",
  "use_tls": true
}
```

!!! warning "Gmail Users"
    Use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### Recipients File Format

```csv
Name,Email
John Doe,john@example.com
Jane Smith,jane@example.com
```

### Body Template

```text
Dear {name},

Congratulations! Please find your certificate attached.

Best regards,
The Team
```

Use `{name}` to personalize the email with the recipient's name.

## Tips

### Create Alias

For frequent use, create a shell alias:

=== "Bash / Zsh"

    Add to `~/.bashrc` or `~/.zshrc`:
    ```bash
    alias r10n='uvx --from git+https://github.com/pruthivithejan/r10n.git r10n'
    ```

    Then use:
    ```bash
    r10n contacts
    ```

=== "PowerShell"

    Add to your PowerShell profile:
    ```powershell
    function r10n { uvx --from git+https://github.com/pruthivithejan/r10n.git r10n $args }
    ```

### Specify Version

Run a specific version:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git@v2.0.0 r10n contacts
```

### Non-Interactive Mode

Pass all options via command line for scripting:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts \
  --input numbers.txt \
  --prefix Customer \
  --output contacts.vcf
```
