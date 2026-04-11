#!/usr/bin/env python3
"""
r10n (routine automation) CLI
Interactive command-line interface with beautiful terminal UI
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

# Import automation modules
from src.automations import (
    convert_colors,
    fill_pdfs,
    generate_contacts,
    markdown_to_pdf,
    optimize_images,
    rename_files,
    send_same_email,
    validate_csv,
)

console = Console()
VERSION = "2.0.0"

# Load environment variables from local folder if exists
env_path = Path("local/.env")
if env_path.exists():
    load_dotenv(env_path)


def load_config(config_path: str) -> dict[str, Any]:
    """Load configuration from JSON file"""
    path = Path(config_path)
    if not path.exists():
        console.print(f"[red]Configuration file not found: {config_path}[/]")
        return {}

    with open(path) as f:
        return json.load(f)


def display_banner():
    """Display a styled ASCII banner at startup (TTY only).
    Set R10N_NO_BANNER=1 to suppress.
    """
    if not sys.stdout.isatty() or os.getenv("R10N_NO_BANNER"):
        return

    banner = """
  ██████╗  ██╗ ██████╗ ███╗   ██╗
  ██╔══██╗███║██╔═══██╗████╗  ██║
  ██████╔╝╚██║██║   ██║██╔██╗ ██║
  ██╔══██╗ ██║██║   ██║██║╚██╗██║
  ██║  ██║ ██║╚██████╔╝██║ ╚████║
  ╚═╝  ╚═╝ ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
"""
    subtitle = f"r10n v{VERSION} - routine automation"
    console.print(f"[bold cyan]{banner}[/]")
    console.print(f"[dim]{subtitle}[/]")
    console.print()


def display_header(title: str, description: str = ""):
    """Display a formatted header"""
    content = f"[bold cyan]{title}[/bold cyan]"
    if description:
        content += f"\n[dim]{description}[/dim]"

    console.print(Panel.fit(content, border_style="cyan"))
    console.print()


def display_step(step_num: int, total: int, description: str):
    """Display a step indicator"""
    console.print(f"[cyan]Step {step_num}/{total}:[/] {description}")


def display_config(config: dict[str, Any], title: str = "Configuration"):
    """Display configuration in a table"""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    for key, value in config.items():
        # Don't display sensitive information
        if any(sensitive in key.lower() for sensitive in ["password", "key", "secret", "token"]):
            value = "********"
        elif isinstance(value, dict):
            value = json.dumps(value, indent=2)
        elif isinstance(value, list):
            value = ", ".join(str(v) for v in value)

        table.add_row(key, str(value))

    console.print(table)


def get_local_path(subpath: str) -> Path:
    """Get path within local folder, creating if necessary"""
    path = Path("local") / subpath
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@click.group(invoke_without_command=True)
@click.version_option(version=VERSION)
@click.pass_context
def main(ctx: click.Context):
    """r10n - Automate repetitive routines

    Available automations:
    - contacts: Generate VCF contact cards from phone numbers
    - fill-pdfs: Fill PDF templates with data from CSV/TXT files
    - images: Optimize and convert images to WebP
    - email: Send bulk emails with attachments
    - colors: Convert CSS colors to oklch() format
    - rename: Batch rename files with patterns
    - validate: Validate CSV files against schemas
    - md2pdf: Convert Markdown files to PDF
    """
    display_banner()
    if ctx.invoked_subcommand is None and not ctx.resilient_parsing:
        click.echo(ctx.get_help())


# =============================================================================
# CONTACTS AUTOMATION
# =============================================================================


@main.command()
@click.option("--input", "-i", "input_file", help="Input file with phone numbers")
@click.option("--output", "-o", help="Output VCF file path")
@click.option("--prefix", "-p", help="Contact name prefix")
def contacts(input_file, output, prefix):
    """Generate VCF contact cards from phone numbers

    Step-by-step interactive process to convert phone numbers to VCF format.
    """
    display_header("Contact Card Generator", "Convert phone numbers to VCF contact cards")

    total_steps = 3

    # Step 1: Input file
    display_step(1, total_steps, "Select input file")
    if not input_file:
        default_input = "local/inputs/contacts/numbers.txt"
        input_file = Prompt.ask("  Enter path to file with phone numbers", default=default_input)

    # Check if file exists
    if not Path(input_file).exists():
        console.print(f"\n[yellow]File not found: {input_file}[/]")
        if Confirm.ask("  Create example file?"):
            example_path = Path(input_file)
            example_path.parent.mkdir(parents=True, exist_ok=True)
            example_content = """# Phone numbers (one per line)
# Supports formats: 0771234567, +94771234567, 94771234567
0771234567
0712345678
+94771234567"""
            example_path.write_text(example_content)
            console.print(f"[green]  Created: {input_file}[/]")
            console.print("[dim]  Edit this file and run the command again.[/]")
            return
        else:
            console.print("[red]Cancelled.[/]")
            return

    console.print(f"[green]  Using: {input_file}[/]")
    console.print()

    # Step 2: Contact prefix
    display_step(2, total_steps, "Set contact name prefix")
    if not prefix:
        prefix = Prompt.ask("  Enter prefix for contact names", default="Contact")
    console.print(f"[green]  Prefix: {prefix}[/]")
    console.print()

    # Step 3: Output file
    display_step(3, total_steps, "Set output file")
    if not output:
        default_output = f"local/outputs/contacts/{prefix.lower()}_contacts.vcf"
        output = Prompt.ask("  Enter output VCF file path", default=default_output)
    console.print(f"[green]  Output: {output}[/]")
    console.print()

    # Confirmation
    console.print("[bold]Summary:[/]")
    console.print(f"  Input file:  {input_file}")
    console.print(f"  Prefix:      {prefix}")
    console.print(f"  Output file: {output}")
    console.print()

    if not Confirm.ask("Proceed with contact generation?"):
        console.print("[yellow]Cancelled.[/]")
        return

    # Run the automation
    console.print()
    console.print("[cyan]Generating contacts...[/]")

    try:
        results = generate_contacts.generate_vcf_from_file(input_file, output, prefix)

        console.print()
        console.print("[bold green]Done![/]")
        console.print()

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total numbers", str(results.get("total", 0)))
        table.add_row("Valid contacts", str(results.get("valid", 0)))
        table.add_row("Duplicates removed", str(results.get("duplicates", 0)))
        table.add_row("Invalid numbers", str(results.get("invalid", 0)))
        table.add_row("Output file", results.get("output_file", output))
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# FILL PDFS AUTOMATION
# =============================================================================


@main.command("fill-pdfs")
@click.option("--config", "-c", help="PDF fill configuration file")
@click.option("--recipients", "-r", help="Data file (CSV or TXT)")
@click.option("--template", "-t", help="PDF template file (for initial setup)")
def fill_pdfs_cmd(config, recipients, template):
    """Fill PDF templates with data from CSV/TXT files

    Interactive process: configure field positions visually, preview a sample,
    then generate all filled PDFs.
    """
    import subprocess
    import tempfile

    display_header("PDF Filler", "Fill PDF templates with data from CSV/TXT files")

    # Step 1: Data file
    display_step(1, 2, "Select data file")
    default_recipients = "local/inputs/fill-pdfs/data.csv"
    if not recipients:
        recipients = Prompt.ask(
            "  Enter path to data file (CSV or TXT)", default=default_recipients
        )

    if not Path(recipients).exists():
        console.print(f"\n[yellow]File not found: {recipients}[/]")
        if Confirm.ask("  Create example file?"):
            recipients_path = Path(recipients)
            recipients_path.parent.mkdir(parents=True, exist_ok=True)
            example_content = """Name,Position
John Doe,Team Lead
Jane Smith,Developer
Bob Johnson,Designer"""
            recipients_path.write_text(example_content)
            console.print(f"[green]  Created: {recipients}[/]")
            console.print("[dim]  Edit this file and run the command again.[/]")
            return
        else:
            console.print("[red]Cancelled.[/]")
            return

    console.print(f"[green]  Using: {recipients}[/]")
    console.print()

    # Step 2: Configuration
    display_step(2, 2, "Configuration")
    default_config = "local/configs/fill-pdfs.json"
    if not config:
        config = Prompt.ask("  Enter path to configuration file", default=default_config)

    # If config doesn't exist, open visual picker to create it
    config_exists = Path(config).exists()
    if not config_exists:
        console.print(f"\n[yellow]Config not found: {config}[/]")
        console.print("[cyan]  Opening visual picker to configure field positions...[/]")
        console.print()

        # Get template path
        if not template:
            template = Prompt.ask(
                "  Enter path to PDF template",
                default="local/inputs/fill-pdfs/template.pdf",
            )
        if not Path(template).exists():
            console.print(f"[red]  Template not found: {template}[/]")
            console.print("[dim]  Add your PDF template and try again.[/]")
            return

        from src.configure import launch_picker

        try:
            launch_picker(
                template_pdf=template,
                recipients_file=recipients,
                output_config=config,
            )
            console.print(f"[green]  Config saved: {config}[/]")
        except Exception as e:
            console.print(f"[red]  Visual picker error: {e}[/]")
            return
    else:
        console.print(f"[green]  Using: {config}[/]")

    console.print()

    # Preview loop: generate a sample certificate and let user approve or re-edit
    while True:
        cfg = load_config(config)
        if not cfg:
            console.print("[red]Failed to load configuration.[/]")
            return

        template_path = cfg.get("template_pdf", "")
        if not Path(template_path).exists():
            console.print(f"[red]Template not found: {template_path}[/]")
            return

        # Load first recipient for preview
        try:
            all_recipients = fill_pdfs.load_recipients(recipients)
        except Exception as e:
            console.print(f"[red]Error loading recipients: {e}[/]")
            return

        if not all_recipients:
            console.print("[red]No valid recipients found in the file.[/]")
            return

        first_recipient = all_recipients[0]
        console.print(f"[cyan]Generating preview for:[/] {first_recipient.get('name', 'Unknown')}")

        # Generate a single preview certificate
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            preview_path = tmp.name

        try:
            fill_pdfs.fill_certificate(template_path, cfg, first_recipient, preview_path)
            console.print(f"[green]  Preview generated.[/]")

            # Open the preview PDF
            try:
                if sys.platform == "darwin":
                    subprocess.run(["open", preview_path], check=True)
                elif sys.platform == "win32":
                    os.startfile(preview_path)
                else:
                    subprocess.run(["xdg-open", preview_path], check=True)
                console.print("[dim]  Preview opened in your default PDF viewer.[/]")
            except Exception:
                console.print(f"[dim]  Preview saved at: {preview_path}[/]")

            console.print()
            approved = Confirm.ask("Does the preview look correct?", default=True)

            if approved:
                # Clean up preview
                Path(preview_path).unlink(missing_ok=True)
                break
            else:
                # Clean up preview and re-open picker
                Path(preview_path).unlink(missing_ok=True)
                console.print()
                console.print("[cyan]Re-opening visual picker to edit configuration...[/]")
                from src.configure import launch_picker

                try:
                    launch_picker(
                        template_pdf=template_path,
                        recipients_file=recipients,
                        output_config=config,
                    )
                    console.print(f"[green]  Config updated: {config}[/]")
                    console.print()
                except Exception as e:
                    console.print(f"[red]  Visual picker error: {e}[/]")
                    return

        except Exception as e:
            Path(preview_path).unlink(missing_ok=True)
            console.print(f"[red]Error generating preview: {e}[/]")
            return

    # Generate all filled PDFs
    output_dir = cfg.get("output_directory", "local/outputs/fill-pdfs")
    os.makedirs(output_dir, exist_ok=True)

    console.print()
    console.print(f"[cyan]Generating {len(all_recipients)} PDFs...[/]")

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(cfg, f)
            temp_config = f.name

        results = fill_pdfs.fill_certificates_from_file(
            recipients, temp_config, base_dir="local"
        )

        os.unlink(temp_config)

        console.print()
        console.print("[bold green]Done![/]")
        console.print()

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total recipients", str(results.get("total", 0)))
        table.add_row("Generated", str(results.get("generated", 0)))
        table.add_row("Failed", str(results.get("failed", 0)))
        table.add_row("Output directory", output_dir)
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# IMAGES AUTOMATION
# =============================================================================


@main.command()
@click.option("--input", "-i", "input_dir", help="Input directory with images")
@click.option("--output", "-o", help="Output directory")
@click.option("--quality", "-q", type=int, help="Image quality (1-100)")
@click.option("--max-size", "-s", type=float, help="Maximum file size in MB")
@click.option("--prefix", "-p", help="Prefix for output filenames")
@click.option("--preserve-names", is_flag=True, help="Keep original filenames")
def images(input_dir, output, quality, max_size, prefix, preserve_names):
    """Optimize and convert images to WebP format

    Step-by-step interactive process to batch optimize images.
    """
    display_header("Image Optimizer", "Convert and optimize images for web use")

    total_steps = 5

    # Step 1: Input directory
    display_step(1, total_steps, "Select input directory")
    default_input = "local/inputs/images"
    if not input_dir:
        input_dir = Prompt.ask("  Enter path to directory with images", default=default_input)

    if not Path(input_dir).exists():
        console.print(f"\n[yellow]Directory not found: {input_dir}[/]")
        if Confirm.ask("  Create directory?"):
            Path(input_dir).mkdir(parents=True, exist_ok=True)
            console.print(f"[green]  Created: {input_dir}[/]")
            console.print("[dim]  Add your images to this folder and run again.[/]")
            return
        else:
            console.print("[red]Cancelled.[/]")
            return

    # Count images
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
    image_files = [f for f in Path(input_dir).iterdir() if f.suffix.lower() in image_exts]
    console.print(f"[green]  Found {len(image_files)} images in: {input_dir}[/]")
    console.print()

    if len(image_files) == 0:
        console.print("[yellow]No images found. Add images and try again.[/]")
        return

    # Step 2: Output directory
    display_step(2, total_steps, "Set output directory")
    default_output = "local/outputs/images"
    if not output:
        output = Prompt.ask("  Enter output directory", default=default_output)
    console.print(f"[green]  Output: {output}[/]")
    console.print()

    # Step 3: Quality
    display_step(3, total_steps, "Set image quality")
    if quality is None:
        quality = IntPrompt.ask("  Enter quality percentage (1-100)", default=85)
    console.print(f"[green]  Quality: {quality}%[/]")
    console.print()

    # Step 4: Max file size
    display_step(4, total_steps, "Set maximum file size")
    if max_size is None:
        max_size_str = Prompt.ask("  Enter maximum file size in MB", default="1.0")
        max_size = float(max_size_str)
    console.print(f"[green]  Max size: {max_size}MB[/]")
    console.print()

    # Step 5: Filename prefix or preserve names
    display_step(5, total_steps, "Set output filenames")
    if not preserve_names and not prefix:
        choice = Prompt.ask(
            "  Keep original filenames or use prefix?", choices=["keep", "prefix"], default="keep"
        )
        if choice == "keep":
            preserve_names = True
        else:
            prefix = Prompt.ask("  Enter filename prefix", default="img")

    if preserve_names:
        console.print("[green]  Keeping original filenames[/]")
    else:
        console.print(f"[green]  Using prefix: {prefix}[/]")
    console.print()

    # Confirmation
    console.print("[bold]Summary:[/]")
    console.print(f"  Input:    {input_dir} ({len(image_files)} images)")
    console.print(f"  Output:   {output}")
    console.print(f"  Quality:  {quality}%")
    console.print(f"  Max size: {max_size}MB")
    console.print("  Format:   WebP")
    console.print()

    if not Confirm.ask("Proceed with optimization?"):
        console.print("[yellow]Cancelled.[/]")
        return

    # Run the automation
    console.print()
    console.print("[cyan]Optimizing images...[/]")
    console.print()

    try:
        results = optimize_images.optimize_images(
            input_dir=input_dir,
            output_dir=output,
            prefix=prefix or "img",
            max_size_mb=max_size,
            quality=quality,
            preserve_filename=preserve_names,
        )

        console.print()
        console.print("[bold green]Done![/]")
        console.print()

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Processed", str(results.get("processed", 0)))
        table.add_row("Skipped", str(results.get("skipped", 0)))
        table.add_row("Failed", str(results.get("failed", 0)))
        table.add_row("Output directory", output)
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# EMAIL AUTOMATION
# =============================================================================


@main.command()
@click.option("--config", "-c", help="Email configuration file")
@click.option("--recipients", "-r", help="Recipients CSV file")
@click.option("--body", "-b", help="Email body template file")
@click.option("--attachments-dir", "-d", help="Directory with PDF attachments")
def email(config, recipients, body, attachments_dir):
    """Send bulk personalized emails with attachments

    Step-by-step interactive process to send emails with certificate attachments.
    """
    display_header("Email Sender", "Send personalized emails with attachments")

    total_steps = 4

    # Step 1: Configuration
    display_step(1, total_steps, "Select email configuration")
    default_config = "local/configs/email.json"
    if not config:
        config = Prompt.ask("  Enter path to email configuration", default=default_config)

    if not Path(config).exists():
        console.print(f"\n[yellow]Config not found: {config}[/]")
        if Confirm.ask("  Create example configuration?"):
            config_path = Path(config)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            example_config = {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "email": "your-email@gmail.com",
                "password": "your-app-password",
                "subject": "Your Certificate",
                "use_tls": True,
            }
            config_path.write_text(json.dumps(example_config, indent=2))
            console.print(f"[green]  Created: {config}[/]")
            console.print("[dim]  Edit this file with your SMTP credentials.[/]")
            console.print("[dim]  For Gmail, use an App Password.[/]")
            return
        else:
            console.print("[red]Cancelled.[/]")
            return

    console.print(f"[green]  Using: {config}[/]")
    console.print()

    # Step 2: Recipients file
    display_step(2, total_steps, "Select recipients file")
    default_recipients = "local/inputs/email/recipients.csv"
    if not recipients:
        recipients = Prompt.ask(
            "  Enter path to recipients CSV (Name,Email columns)", default=default_recipients
        )

    if not Path(recipients).exists():
        console.print(f"\n[yellow]File not found: {recipients}[/]")
        if Confirm.ask("  Create example file?"):
            recipients_path = Path(recipients)
            recipients_path.parent.mkdir(parents=True, exist_ok=True)
            example_content = """Name,Email
John Doe,john@example.com
Jane Smith,jane@example.com"""
            recipients_path.write_text(example_content)
            console.print(f"[green]  Created: {recipients}[/]")
            console.print("[dim]  Edit this file and run again.[/]")
            return
        else:
            console.print("[red]Cancelled.[/]")
            return

    console.print(f"[green]  Using: {recipients}[/]")
    console.print()

    # Step 3: Email body template
    display_step(3, total_steps, "Select email body template")
    default_body = "local/inputs/email/template.txt"
    if not body:
        body = Prompt.ask("  Enter path to email body template", default=default_body)

    if not Path(body).exists():
        console.print(f"\n[yellow]File not found: {body}[/]")
        if Confirm.ask("  Create example template?"):
            body_path = Path(body)
            body_path.parent.mkdir(parents=True, exist_ok=True)
            example_content = """Dear {name},

Congratulations! Please find your certificate attached.

Best regards,
The Team"""
            body_path.write_text(example_content)
            console.print(f"[green]  Created: {body}[/]")
            console.print("[dim]  Use {{name}} for personalization.[/]")
            return
        else:
            console.print("[red]Cancelled.[/]")
            return

    console.print(f"[green]  Using: {body}[/]")
    console.print()

    # Step 4: Attachments directory
    display_step(4, total_steps, "Select attachments directory")
    default_attachments = "local/outputs/fill-pdfs"
    if not attachments_dir:
        attachments_dir = Prompt.ask(
            "  Enter path to directory with PDF attachments", default=default_attachments
        )

    if not Path(attachments_dir).exists():
        console.print(f"[yellow]  Directory not found: {attachments_dir}[/]")
        console.print("[dim]  Emails will be sent without attachments.[/]")
    else:
        pdf_count = len(list(Path(attachments_dir).glob("*.pdf")))
        console.print(f"[green]  Found {pdf_count} PDFs in: {attachments_dir}[/]")
    console.print()

    # Confirmation
    console.print("[bold]Summary:[/]")
    console.print(f"  Config:       {config}")
    console.print(f"  Recipients:   {recipients}")
    console.print(f"  Body:         {body}")
    console.print(f"  Attachments:  {attachments_dir}")
    console.print()

    console.print("[bold yellow]Warning:[/] This will send real emails!")
    if not Confirm.ask("Proceed with sending emails?"):
        console.print("[yellow]Cancelled.[/]")
        return

    # Run the automation
    console.print()
    console.print("[cyan]Sending emails...[/]")
    console.print()

    try:
        results = send_same_email.send_from_file(
            email_list_file=recipients,
            body_file=body,
            config_file=config,
            certificates_dir=attachments_dir,
        )

        console.print()
        console.print("[bold green]Done![/]")
        console.print()

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total recipients", str(results.get("total", 0)))
        table.add_row("Sent successfully", str(results.get("sent", 0)))
        table.add_row("Failed", str(results.get("failed", 0)))
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# COLORS AUTOMATION
# =============================================================================


@main.command()
@click.option("--path", "-p", "dir_path", help="Directory containing CSS files")
@click.option("--file", "-f", "file_path", help="Single CSS file to process")
@click.option("--no-backup", is_flag=True, help="Don't create backup files")
@click.option(
    "--all", "-a", "process_all", is_flag=True, help="Process all files without prompting"
)
def colors(dir_path, file_path, no_backup, process_all):
    """Convert CSS colors to oklch() format

    Converts hex, hsl, rgb, and named colors to modern oklch() notation.
    Backup files (.bak) are created by default.
    """
    display_header("CSS Color Converter", "Convert colors to perceptual oklch() format")

    total_steps = 2

    # Step 1: Select file or directory
    display_step(1, total_steps, "Select CSS file or directory")

    if file_path:
        # Single file mode
        if not Path(file_path).exists():
            console.print(f"[red]File not found: {file_path}[/]")
            return
        if not file_path.endswith(".css"):
            console.print(f"[yellow]Warning: {file_path} may not be a CSS file[/]")
        console.print(f"[green]  Using file: {file_path}[/]")
        target_path = None
        target_file = file_path
    elif dir_path:
        # Directory mode
        if not Path(dir_path).exists():
            console.print(f"[red]Directory not found: {dir_path}[/]")
            return
        console.print(f"[green]  Using directory: {dir_path}[/]")
        target_path = dir_path
        target_file = None
    else:
        # Interactive mode
        choice = Prompt.ask(
            "  Process a single file or directory?", choices=["file", "directory"], default="file"
        )

        if choice == "file":
            target_file = Prompt.ask("  Enter path to CSS file", default="styles.css")
            if not Path(target_file).exists():
                console.print(f"[red]File not found: {target_file}[/]")
                return
            target_path = None
            console.print(f"[green]  Using file: {target_file}[/]")
        else:
            default_path = (
                "." if not Path("local/inputs/colors").exists() else "local/inputs/colors"
            )
            target_path = Prompt.ask(
                "  Enter path to directory with CSS files", default=default_path
            )
            if not Path(target_path).exists():
                console.print(f"[red]Directory not found: {target_path}[/]")
                return
            target_file = None
            console.print(f"[green]  Using directory: {target_path}[/]")

    console.print()

    # Step 2: Backup option
    display_step(2, total_steps, "Backup option")

    if not no_backup:
        console.print("[green]  Backup: Enabled (.bak files will be created)[/]")
    else:
        console.print("[yellow]  Backup: Disabled[/]")

    console.print()

    # Summary
    console.print("[bold]Summary:[/]")
    if target_file:
        console.print(f"  File:   {target_file}")
    else:
        console.print(f"  Directory: {target_path}")
    console.print(f"  Backup: {'Disabled' if no_backup else 'Enabled'}")
    console.print()

    if not process_all and not Confirm.ask("Proceed with color conversion?"):
        console.print("[yellow]Cancelled.[/]")
        return

    # Run the automation
    console.print()
    console.print("[cyan]Converting CSS colors to oklch()...[/]")
    console.print()

    try:
        results = convert_colors.convert_colors(
            path=target_path or ".",
            file=target_file,
            dry_run=False,
            no_backup=no_backup,
        )

        console.print()
        console.print("[bold green]Done![/]")
        console.print()

        # Results table
        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Files found", str(results.get("files_found", 0)))
        table.add_row("Files modified", str(results.get("files_modified", 0)))
        table.add_row("Total color changes", str(results.get("total_changes", 0)))
        console.print(table)

        # Show changes if any
        if results.get("total_changes", 0) > 0:
            console.print()
            console.print("[bold]Changes made:[/]")
            for file_result in results.get("files", []):
                if file_result.get("changes", 0) > 0:
                    console.print(
                        f"\n[cyan]{file_result['file']}[/] ({file_result['changes']} changes)"
                    )
                    for change in file_result.get("change_details", [])[:5]:
                        console.print(
                            f"  Line {change['line']}: [red]{change['orig']}[/] → [green]{change['repl']}[/]"
                        )
                    if file_result.get("changes", 0) > 5:
                        console.print(f"  ... and {file_result['changes'] - 5} more")

            if not no_backup:
                console.print()
                console.print("[dim]Backup files created with .bak extension[/]")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[yellow]{e}[/]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# RENAME FILES AUTOMATION
# =============================================================================


@main.command()
@click.option("--input", "-i", "input_dir", help="Input directory with files")
@click.option(
    "--pattern", "-p", help="Rename pattern with placeholders: {name}, {ext}, {date}, {sequence}"
)
@click.option("--prefix", help="Add prefix to filenames")
@click.option("--suffix", help="Add suffix to filenames")
@click.option("--replace-from", help="Text to replace in filenames")
@click.option("--replace-to", help="Replacement text")
@click.option("--lowercase", is_flag=True, help="Convert filenames to lowercase")
@click.option("--uppercase", is_flag=True, help="Convert filenames to uppercase")
@click.option("--add-date", is_flag=True, help="Add current date to filenames")
@click.option("--add-sequence", is_flag=True, help="Add sequence numbers")
@click.option("--recursive", "-r", is_flag=True, help="Process subdirectories")
@click.option("--dry-run", "-n", is_flag=True, help="Preview changes without renaming")
@click.option("--file-pattern", help="File glob pattern to match (e.g., '*.jpg')")
def rename(
    input_dir,
    pattern,
    prefix,
    suffix,
    replace_from,
    replace_to,
    lowercase,
    uppercase,
    add_date,
    add_sequence,
    recursive,
    dry_run,
    file_pattern,
):
    """Rename files in bulk with patterns and transformations

    Step-by-step interactive process to rename multiple files.
    """
    display_header("File Renamer", "Batch rename files with patterns and transformations")

    total_steps = 4

    # Step 1: Input directory
    display_step(1, total_steps, "Select input directory")
    default_input = "local/inputs/rename"
    if not input_dir:
        input_dir = Prompt.ask("  Enter path to directory with files", default=default_input)

    if not Path(input_dir).exists():
        console.print(f"\n[yellow]Directory not found: {input_dir}[/]")
        if Confirm.ask("  Create directory?"):
            Path(input_dir).mkdir(parents=True, exist_ok=True)
            console.print(f"[green]  Created: {input_dir}[/]")
            console.print("[dim]  Add your files to this folder and run again.[/]")
            return
        else:
            console.print("[red]Cancelled.[/]")
            return

    # Count files
    files = list(Path(input_dir).iterdir()) if not recursive else list(Path(input_dir).rglob("*"))
    file_count = len([f for f in files if f.is_file()])
    console.print(f"[green]  Found {file_count} files in: {input_dir}[/]")
    console.print()

    if file_count == 0:
        console.print("[yellow]No files found. Add files and try again.[/]")
        return

    # Step 2: Rename strategy
    display_step(2, total_steps, "Select rename strategy")

    if not any(
        [pattern, prefix, suffix, replace_from, lowercase, uppercase, add_date, add_sequence]
    ):
        strategy = Prompt.ask(
            "  Choose rename strategy",
            choices=["pattern", "prefix", "suffix", "replace", "case", "date", "sequence"],
            default="prefix",
        )

        if strategy == "pattern":
            pattern = Prompt.ask(
                "  Enter pattern (use {name}, {ext}, {date}, {sequence})",
                default="{name}_{date}{ext}",
            )
        elif strategy == "prefix":
            prefix = Prompt.ask("  Enter prefix", default="renamed_")
        elif strategy == "suffix":
            suffix = Prompt.ask("  Enter suffix", default="_processed")
        elif strategy == "replace":
            replace_from = Prompt.ask("  Enter text to replace")
            replace_to = Prompt.ask("  Enter replacement text", default="")
        elif strategy == "case":
            case_choice = Prompt.ask(
                "  Convert to", choices=["lowercase", "uppercase"], default="lowercase"
            )
            lowercase = case_choice == "lowercase"
            uppercase = case_choice == "uppercase"
        elif strategy == "date":
            add_date = True
        elif strategy == "sequence":
            add_sequence = True

    console.print()

    # Step 3: File filter
    display_step(3, total_steps, "Filter files (optional)")
    if not file_pattern:
        filter_choice = Prompt.ask(
            "  Filter by file pattern?",
            choices=["all", "images", "documents", "custom"],
            default="all",
        )
        if filter_choice == "images":
            file_pattern = "*.{jpg,jpeg,png,gif,webp,bmp}"
        elif filter_choice == "documents":
            file_pattern = "*.{pdf,doc,docx,txt,md}"
        elif filter_choice == "custom":
            file_pattern = Prompt.ask("  Enter glob pattern", default="*.*")
        # else: file_pattern stays None for all files

    if file_pattern:
        console.print(f"[green]  Filter: {file_pattern}[/]")
    else:
        console.print("[green]  Filter: All files[/]")
    console.print()

    # Step 4: Dry run option
    display_step(4, total_steps, "Preview changes")
    if not dry_run:
        dry_run = Confirm.ask("  Preview changes before renaming (dry run)?", default=True)

    console.print(f"[green]  Dry run: {'Yes' if dry_run else 'No'}[/]")
    console.print()

    # Build configuration summary
    console.print("[bold]Summary:[/]")
    console.print(f"  Input:     {input_dir} ({file_count} files)")
    if pattern:
        console.print(f"  Pattern:   {pattern}")
    if prefix:
        console.print(f"  Prefix:    {prefix}")
    if suffix:
        console.print(f"  Suffix:    {suffix}")
    if replace_from:
        console.print(f"  Replace:   '{replace_from}' → '{replace_to or ''}'")
    if lowercase:
        console.print("  Case:      lowercase")
    if uppercase:
        console.print("  Case:      UPPERCASE")
    if add_date:
        console.print("  Add date:  Yes")
    if add_sequence:
        console.print("  Sequence:  Yes")
    if recursive:
        console.print("  Recursive: Yes")
    console.print()

    if not dry_run and not Confirm.ask("Proceed with renaming files?"):
        console.print("[yellow]Cancelled.[/]")
        return

    # Run the automation
    console.print()
    console.print("[cyan]Renaming files...[/]")
    console.print()

    try:
        result = rename_files.rename_files(
            input_directory=input_dir,
            pattern=pattern,
            prefix=prefix,
            suffix=suffix,
            replace_from=replace_from,
            replace_to=replace_to or "",
            add_date=add_date,
            add_sequence=add_sequence,
            lowercase=lowercase,
            uppercase=uppercase,
            recursive=recursive,
            dry_run=dry_run,
            file_pattern=file_pattern or "*",
        )

        console.print()
        if dry_run:
            console.print("[bold yellow]Dry Run Preview:[/]")
        else:
            console.print("[bold green]Done![/]")
        console.print()

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total files", str(result.total_files))
        table.add_row("Renamed" if not dry_run else "Would rename", str(result.renamed))
        table.add_row("Skipped", str(result.skipped))
        table.add_row("Errors", str(len(result.errors)))
        console.print(table)

        # Show renamed files (result.renamed_files is a list of dicts)
        if result.renamed_files:
            console.print()
            console.print("[bold]Changes:[/]")
            for item in result.renamed_files[:10]:
                old_name = item.get("old", item.get("original", ""))
                new_name = item.get("new", item.get("renamed", ""))
                console.print(f"  [red]{old_name}[/] → [green]{new_name}[/]")
            if len(result.renamed_files) > 10:
                console.print(f"  ... and {len(result.renamed_files) - 10} more")

        if dry_run:
            console.print()
            if Confirm.ask("Apply these changes?"):
                result = rename_files.rename_files(
                    input_directory=input_dir,
                    pattern=pattern,
                    prefix=prefix,
                    suffix=suffix,
                    replace_from=replace_from,
                    replace_to=replace_to or "",
                    add_date=add_date,
                    add_sequence=add_sequence,
                    lowercase=lowercase,
                    uppercase=uppercase,
                    recursive=recursive,
                    dry_run=False,
                    file_pattern=file_pattern or "*",
                )
                console.print("[bold green]Files renamed successfully![/]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# VALIDATE CSV AUTOMATION
# =============================================================================


@main.command()
@click.option("--input", "-i", "input_file", help="Input CSV file to validate")
@click.option("--schema", "-s", help="JSON schema file for validation")
@click.option("--output", "-o", help="Output file for validation report")
@click.option("--strict", is_flag=True, help="Enable strict validation mode")
@click.option("--clean", is_flag=True, help="Clean and fix data issues")
@click.option(
    "--format",
    "-f",
    "report_format",
    type=click.Choice(["text", "json", "html"]),
    help="Report format",
)
def validate(input_file, schema, output, strict, clean, report_format):
    """Validate CSV files against a schema

    Step-by-step interactive process to validate and optionally clean CSV data.
    """
    display_header("CSV Validator", "Validate and clean CSV data against schemas")

    total_steps = 4

    # Step 1: Input file
    display_step(1, total_steps, "Select CSV file")
    default_input = "local/inputs/validate/data.csv"
    if not input_file:
        input_file = Prompt.ask("  Enter path to CSV file", default=default_input)

    if not Path(input_file).exists():
        console.print(f"\n[yellow]File not found: {input_file}[/]")
        if Confirm.ask("  Create example CSV file?"):
            input_path = Path(input_file)
            input_path.parent.mkdir(parents=True, exist_ok=True)
            example_content = """name,email,age,department
John Doe,john@example.com,30,Engineering
Jane Smith,jane@example.com,25,Marketing
Bob Johnson,bob@example.com,35,Sales"""
            input_path.write_text(example_content)
            console.print(f"[green]  Created: {input_file}[/]")
            console.print("[dim]  Edit this file and run again.[/]")
            return
        else:
            console.print("[red]Cancelled.[/]")
            return

    # Count rows
    with open(input_file, encoding="utf-8") as f:
        row_count = sum(1 for _ in f) - 1  # Subtract header
    console.print(f"[green]  Using: {input_file} ({row_count} rows)[/]")
    console.print()

    # Step 2: Schema file
    display_step(2, total_steps, "Select validation schema")
    default_schema = "local/configs/csv_schema.json"
    if not schema:
        use_schema = Confirm.ask("  Use a validation schema?", default=True)
        if use_schema:
            schema = Prompt.ask("  Enter path to JSON schema file", default=default_schema)

    if schema and not Path(schema).exists():
        console.print(f"\n[yellow]Schema not found: {schema}[/]")
        if Confirm.ask("  Create example schema?"):
            schema_path = Path(schema)
            schema_path.parent.mkdir(parents=True, exist_ok=True)
            example_schema = {
                "fields": {
                    "name": {"type": "string", "required": True, "min_length": 1},
                    "email": {"type": "email", "required": True},
                    "age": {"type": "integer", "required": False, "min": 0, "max": 150},
                    "department": {
                        "type": "string",
                        "enum": ["Engineering", "Marketing", "Sales", "HR"],
                    },
                }
            }
            schema_path.write_text(json.dumps(example_schema, indent=2))
            console.print(f"[green]  Created: {schema}[/]")
            console.print("[dim]  Edit this schema and run again.[/]")
            return
        else:
            schema = None

    if schema:
        console.print(f"[green]  Using schema: {schema}[/]")
    else:
        console.print("[yellow]  No schema - basic validation only[/]")
    console.print()

    # Step 3: Validation options
    display_step(3, total_steps, "Validation options")

    if not strict:
        strict = Confirm.ask("  Enable strict mode (fail on warnings)?", default=False)
    console.print(f"[green]  Strict mode: {'Yes' if strict else 'No'}[/]")

    if not clean:
        clean = Confirm.ask("  Clean data (trim whitespace, fix issues)?", default=False)
    console.print(f"[green]  Clean data: {'Yes' if clean else 'No'}[/]")
    console.print()

    # Step 4: Output options
    display_step(4, total_steps, "Report options")

    if not report_format:
        report_format = Prompt.ask(
            "  Report format", choices=["text", "json", "html"], default="text"
        )
    console.print(f"[green]  Format: {report_format}[/]")

    if not output:
        save_report = Confirm.ask("  Save report to file?", default=False)
        if save_report:
            default_output = f"local/outputs/validate/report.{report_format}"
            output = Prompt.ask("  Enter output file path", default=default_output)

    if output:
        console.print(f"[green]  Output: {output}[/]")
    console.print()

    # Summary
    console.print("[bold]Summary:[/]")
    console.print(f"  Input:   {input_file} ({row_count} rows)")
    console.print(f"  Schema:  {schema or 'None'}")
    console.print(f"  Strict:  {'Yes' if strict else 'No'}")
    console.print(f"  Clean:   {'Yes' if clean else 'No'}")
    console.print(f"  Format:  {report_format}")
    if output:
        console.print(f"  Output:  {output}")
    console.print()

    if not Confirm.ask("Proceed with validation?"):
        console.print("[yellow]Cancelled.[/]")
        return

    # Run the automation
    console.print()
    console.print("[cyan]Validating CSV...[/]")
    console.print()

    try:
        result = validate_csv.validate_csv(
            input_file=input_file,
            schema_file=schema,
            strict_mode=strict,
            trim_whitespace=clean,
        )

        console.print()
        if result.is_valid:
            console.print("[bold green]Validation Passed![/]")
        else:
            console.print("[bold red]Validation Failed![/]")
        console.print()

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green" if result.is_valid else "red")
        table.add_row("Total rows", str(result.total_rows))
        table.add_row("Valid rows", str(result.valid_rows))
        table.add_row("Invalid rows", str(result.invalid_rows))
        table.add_row("Errors", str(len(result.errors)))
        table.add_row("Warnings", str(len(result.warnings)))
        console.print(table)

        # Show errors
        if result.errors:
            console.print()
            console.print("[bold red]Errors:[/]")
            for error in result.errors[:10]:
                console.print(f"  • {error}")
            if len(result.errors) > 10:
                console.print(f"  ... and {len(result.errors) - 10} more errors")

        # Show warnings
        if result.warnings:
            console.print()
            console.print("[bold yellow]Warnings:[/]")
            for warning in result.warnings[:5]:
                console.print(f"  • {warning}")
            if len(result.warnings) > 5:
                console.print(f"  ... and {len(result.warnings) - 5} more warnings")

        # Generate report if requested
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            validate_csv.generate_report(result, output, report_format)
            console.print()
            console.print(f"[green]Report saved to: {output}[/]")

        # Clean data if requested
        if clean and not result.is_valid:
            console.print()
            if Confirm.ask("Clean the data and save a corrected file?"):
                cleaned_path = str(Path(input_file).with_suffix(".cleaned.csv"))
                validate_csv.clean_csv(input_file, cleaned_path, trim_whitespace=True)
                console.print(f"[green]Cleaned data saved to: {cleaned_path}[/]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# MARKDOWN TO PDF AUTOMATION
# =============================================================================


@main.command()
@click.option("--input", "-i", "input_path", help="Input markdown file or directory")
@click.option("--output", "-o", help="Output PDF file or directory")
@click.option("--css", "-c", help="Custom CSS file for styling")
@click.option("--page-size", type=click.Choice(["A4", "Letter", "Legal"]), help="Page size")
@click.option("--toc", is_flag=True, help="Include table of contents")
@click.option("--syntax-highlight", is_flag=True, help="Enable syntax highlighting for code")
@click.option("--recursive", "-r", is_flag=True, help="Process subdirectories")
def md2pdf(input_path, output, css, page_size, toc, syntax_highlight, recursive):
    """Convert Markdown files to PDF

    Step-by-step interactive process to convert markdown to styled PDFs.
    """
    display_header("Markdown to PDF", "Convert markdown files to beautifully styled PDFs")

    total_steps = 4

    # Step 1: Input file/directory
    display_step(1, total_steps, "Select input")
    default_input = "local/inputs/markdown"
    if not input_path:
        input_path = Prompt.ask("  Enter path to markdown file or directory", default=default_input)

    input_p = Path(input_path)
    if not input_p.exists():
        console.print(f"\n[yellow]Path not found: {input_path}[/]")
        if Confirm.ask("  Create example markdown file?"):
            if input_p.suffix == ".md":
                input_p.parent.mkdir(parents=True, exist_ok=True)
            else:
                input_p.mkdir(parents=True, exist_ok=True)
                input_p = input_p / "example.md"

            example_content = """# Sample Document

## Introduction

This is a sample markdown document that will be converted to PDF.

## Features

- **Bold text** and *italic text*
- Lists and bullet points
- Code blocks with syntax highlighting

```python
def hello_world():
    print("Hello, World!")
```

## Conclusion

Markdown to PDF conversion is easy with r10n!
"""
            input_p.write_text(example_content)
            console.print(f"[green]  Created: {input_p}[/]")
            console.print("[dim]  Edit this file and run again.[/]")
            return
        else:
            console.print("[red]Cancelled.[/]")
            return

    if input_p.is_file():
        console.print(f"[green]  Using file: {input_path}[/]")
        file_count = 1
    else:
        # Count markdown files
        if recursive:
            md_files = list(input_p.rglob("*.md"))
        else:
            md_files = list(input_p.glob("*.md"))
        file_count = len(md_files)
        console.print(f"[green]  Found {file_count} markdown files in: {input_path}[/]")

        if file_count == 0:
            console.print("[yellow]No markdown files found. Add .md files and try again.[/]")
            return
    console.print()

    # Step 2: Output path
    display_step(2, total_steps, "Set output")
    if not output:
        if input_p.is_file():
            default_output = str(input_p.with_suffix(".pdf"))
        else:
            default_output = "local/outputs/pdf"
        output = Prompt.ask("  Enter output path", default=default_output)
    console.print(f"[green]  Output: {output}[/]")
    console.print()

    # Step 3: Styling options
    display_step(3, total_steps, "Styling options")

    if not page_size:
        page_size = Prompt.ask("  Page size", choices=["A4", "Letter", "Legal"], default="A4")
    console.print(f"[green]  Page size: {page_size}[/]")

    if not css:
        use_css = Confirm.ask("  Use custom CSS file?", default=False)
        if use_css:
            css = Prompt.ask("  Enter CSS file path", default="local/configs/pdf_style.css")
            if not Path(css).exists():
                console.print(f"[yellow]  CSS file not found, using default styling[/]")
                css = None

    if css:
        console.print(f"[green]  Custom CSS: {css}[/]")
    else:
        console.print("[green]  Using default styling[/]")
    console.print()

    # Step 4: Additional options
    display_step(4, total_steps, "Additional options")

    if not toc:
        toc = Confirm.ask("  Include table of contents?", default=False)
    console.print(f"[green]  Table of contents: {'Yes' if toc else 'No'}[/]")

    if not syntax_highlight:
        syntax_highlight = Confirm.ask("  Enable syntax highlighting for code?", default=True)
    console.print(f"[green]  Syntax highlighting: {'Yes' if syntax_highlight else 'No'}[/]")
    console.print()

    # Summary
    console.print("[bold]Summary:[/]")
    console.print(f"  Input:      {input_path} ({file_count} file{'s' if file_count > 1 else ''})")
    console.print(f"  Output:     {output}")
    console.print(f"  Page size:  {page_size}")
    console.print(f"  CSS:        {css or 'Default'}")
    console.print(f"  TOC:        {'Yes' if toc else 'No'}")
    console.print(f"  Highlight:  {'Yes' if syntax_highlight else 'No'}")
    console.print()

    if not Confirm.ask("Proceed with conversion?"):
        console.print("[yellow]Cancelled.[/]")
        return

    # Run the automation
    console.print()
    console.print("[cyan]Converting markdown to PDF...[/]")
    console.print()

    try:
        if input_p.is_file():
            result = markdown_to_pdf.convert_markdown_to_pdf(
                input_path=input_path,
                output_path=output,
                css_file=css,
                page_size=page_size or "A4",
                include_toc=toc,
                syntax_highlighting=syntax_highlight,
            )

            console.print()
            if result.get("success"):
                console.print("[bold green]Done![/]")
            else:
                console.print("[bold red]Conversion failed![/]")
            console.print()

            table = Table(show_header=False)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Input", str(result.get("input", input_path)))
            table.add_row("Output", str(result.get("output", output)))
            if result.get("pages"):
                table.add_row("Pages", str(result.get("pages")))
            console.print(table)
        else:
            result = markdown_to_pdf.convert_directory(
                input_dir=input_path,
                output_dir=output,
                recursive=recursive,
                css_file=css,
                page_size=page_size or "A4",
            )

            console.print()
            console.print("[bold green]Done![/]")
            console.print()

            table = Table(show_header=False)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Total files", str(result.get("total", 0)))
            table.add_row("Converted", str(result.get("converted", 0)))
            table.add_row("Failed", str(result.get("failed", 0)))
            table.add_row("Output directory", str(output))
            console.print(table)

            if result.get("errors"):
                console.print()
                console.print("[bold red]Errors:[/]")
                for error in result.get("errors", [])[:5]:
                    console.print(f"  • {error}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# CONFIGURE (VISUAL FIELD PICKER)
# =============================================================================


@main.command()
@click.option("--template", "-t", required=True, help="PDF template file")
@click.option("--recipients", "-r", help="CSV file (for column headers)")
@click.option(
    "--output", "-o", default="local/configs/fill-pdfs.json", help="Output config path"
)
def configure(template, recipients, output):
    """Launch visual field picker for PDF fill configuration

    Opens a browser-based tool where you can click on a PDF template
    to place fields, configure styling, preview results, and save the config.
    """
    from src.configure import launch_picker

    display_header("Visual Field Picker", "Click on the template to place text fields")

    if not Path(template).exists():
        console.print(f"[red]Template not found: {template}[/]")
        return

    if recipients and not Path(recipients).exists():
        console.print(f"[yellow]Recipients file not found: {recipients}[/]")
        console.print("[dim]  Continuing without CSV headers.[/]")
        recipients = None

    console.print(f"[green]  Template: {template}[/]")
    if recipients:
        console.print(f"[green]  Recipients: {recipients}[/]")
    console.print(f"[green]  Output config: {output}[/]")
    console.print()
    console.print("[cyan]Opening visual picker in your browser...[/]")
    console.print("[dim]  Place fields by clicking, then click Save Config when done.[/]")
    console.print()

    try:
        saved_path = launch_picker(
            template_pdf=template,
            recipients_file=recipients,
            output_config=output,
        )
        console.print()
        console.print(f"[bold green]Configuration saved to: {saved_path}[/]")
        console.print(
            "[dim]  Run [cyan]r10n fill-pdfs --config "
            f"{saved_path}[/cyan] to generate filled PDFs.[/]"
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# STATUS COMMAND
# =============================================================================


@main.command()
def status():
    """Check the status of your local setup"""
    display_header("Status", "Check your local folder setup")

    checks = []

    # Check local folder
    if Path("local").exists():
        checks.append(("Local folder", "Created", "green"))
    else:
        checks.append(("Local folder", "Not found", "yellow"))

    # Check subdirectories
    for subdir in ["configs", "inputs", "outputs"]:
        path = Path("local") / subdir
        if path.exists():
            checks.append((f"  local/{subdir}/", "Created", "green"))
        else:
            checks.append((f"  local/{subdir}/", "Missing", "yellow"))

    # Check configs
    config_files = (
        list(Path("local/configs").glob("*.json")) if Path("local/configs").exists() else []
    )
    if config_files:
        checks.append(("Configuration files", f"{len(config_files)} found", "green"))
    else:
        checks.append(("Configuration files", "None found", "yellow"))

    # Check .env
    if Path("local/.env").exists():
        checks.append(("Environment file", "Configured", "green"))
    else:
        checks.append(("Environment file", "Missing (optional)", "dim"))

    # Display table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Status")

    for component, status, color in checks:
        table.add_row(component, f"[{color}]{status}[/{color}]")

    console.print(table)
    console.print()

    console.print("[bold]Quick Start:[/]")
    console.print("  r10n contacts       Generate VCF contact cards")
    console.print("  r10n fill-pdfs      Fill PDF templates with data")
    console.print("  r10n images         Optimize images to WebP")
    console.print("  r10n email          Send bulk emails")
    console.print("  r10n colors         Convert CSS colors to oklch()")
    console.print("  r10n rename         Batch rename files")
    console.print("  r10n validate       Validate CSV files")
    console.print("  r10n md2pdf         Convert Markdown to PDF")


@main.command()
def init():
    """Initialize the local folder structure"""
    display_header("Initialize", "Create local folder structure")

    folders = [
        "local/configs",
        "local/inputs/contacts",
        "local/inputs/fill-pdfs",
        "local/inputs/images",
        "local/inputs/email",
        "local/inputs/rename",
        "local/inputs/validate",
        "local/inputs/markdown",
        "local/outputs/contacts",
        "local/outputs/fill-pdfs",
        "local/outputs/images",
        "local/outputs/rename",
        "local/outputs/validate",
        "local/outputs/pdf",
    ]

    console.print("Creating folder structure...")
    console.print()

    for folder in folders:
        path = Path(folder)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]  Created: {folder}/[/]")
        else:
            console.print(f"[dim]  Exists:  {folder}/[/]")

    console.print()
    console.print("[bold green]Done![/]")
    console.print()
    console.print("Run [cyan]r10n status[/] to check your setup.")
    console.print("Run [cyan]r10n <command>[/] to start an automation.")


if __name__ == "__main__":
    main()
