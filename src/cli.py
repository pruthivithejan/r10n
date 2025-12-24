#!/usr/bin/env python3
"""
r10n (routine automation) CLI
Interactive command-line interface with beautiful terminal UI
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

# Import automation modules
from src.automations import (
    fill_certificates,
    generate_contacts,
    optimize_images,
    send_same_email,
)

console = Console()
VERSION = "2.0.0"

# Load environment variables from local folder if exists
env_path = Path("local/.env")
if env_path.exists():
    load_dotenv(env_path)


def load_config(config_path: str) -> Dict[str, Any]:
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


def display_config(config: Dict[str, Any], title: str = "Configuration"):
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
    - certificates: Generate personalized PDF certificates
    - images: Optimize and convert images to WebP
    - email: Send bulk emails with attachments
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
        input_file = Prompt.ask(
            "  Enter path to file with phone numbers",
            default=default_input
        )

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
        prefix = Prompt.ask(
            "  Enter prefix for contact names",
            default="Contact"
        )
    console.print(f"[green]  Prefix: {prefix}[/]")
    console.print()

    # Step 3: Output file
    display_step(3, total_steps, "Set output file")
    if not output:
        default_output = f"local/outputs/contacts/{prefix.lower()}_contacts.vcf"
        output = Prompt.ask(
            "  Enter output VCF file path",
            default=default_output
        )
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
# CERTIFICATES AUTOMATION
# =============================================================================


@main.command()
@click.option("--config", "-c", help="Certificate configuration file")
@click.option("--recipients", "-r", help="Recipients data file")
@click.option("--template", "-t", help="PDF template file")
@click.option("--output", "-o", help="Output directory")
def certificates(config, recipients, template, output):
    """Generate personalized PDF certificates

    Step-by-step interactive process to create certificates from a template.
    """
    display_header("Certificate Generator", "Create personalized PDF certificates from templates")

    total_steps = 4

    # Step 1: Configuration file
    display_step(1, total_steps, "Select configuration")
    default_config = "local/configs/certificates.json"
    if not config:
        config = Prompt.ask(
            "  Enter path to configuration file",
            default=default_config
        )

    # Load config or create example
    if not Path(config).exists():
        console.print(f"\n[yellow]Config not found: {config}[/]")
        if Confirm.ask("  Create example configuration?"):
            config_path = Path(config)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            example_config = {
                "template_pdf": "local/inputs/certificates/template.pdf",
                "output_directory": "local/outputs/certificates",
                "font_family": "Helvetica",
                "fields": {
                    "name": {
                        "x": 300,
                        "y": 400,
                        "font_size": 36,
                        "font_weight": "bold",
                        "alignment": "center",
                        "color": [0, 0, 0]
                    },
                    "position": {
                        "x": 300,
                        "y": 350,
                        "font_size": 24,
                        "font_weight": "normal",
                        "alignment": "center",
                        "color": [50, 50, 50]
                    }
                }
            }
            config_path.write_text(json.dumps(example_config, indent=2))
            console.print(f"[green]  Created: {config}[/]")
            console.print("[dim]  Edit this file to match your template layout.[/]")
        else:
            console.print("[red]Cancelled.[/]")
            return

    cfg = load_config(config)
    if cfg:
        console.print(f"[green]  Using: {config}[/]")
    console.print()

    # Step 2: Template PDF
    display_step(2, total_steps, "Select PDF template")
    default_template = cfg.get("template_pdf", "local/inputs/certificates/template.pdf")
    if not template:
        template = Prompt.ask(
            "  Enter path to PDF template",
            default=default_template
        )

    if not Path(template).exists():
        console.print(f"[red]  Template not found: {template}[/]")
        console.print("[dim]  Please add your PDF template file and try again.[/]")
        return

    console.print(f"[green]  Using: {template}[/]")
    console.print()

    # Step 3: Recipients file
    display_step(3, total_steps, "Select recipients file")
    default_recipients = "local/inputs/certificates/recipients.txt"
    if not recipients:
        recipients = Prompt.ask(
            "  Enter path to recipients file (TXT or CSV)",
            default=default_recipients
        )

    if not Path(recipients).exists():
        console.print(f"\n[yellow]File not found: {recipients}[/]")
        if Confirm.ask("  Create example file?"):
            recipients_path = Path(recipients)
            recipients_path.parent.mkdir(parents=True, exist_ok=True)
            example_content = """# Recipients file (one per line)
# Format: Name<TAB>Position
# Or use CSV with headers: name,position
John Doe	Team Lead
Jane Smith	Developer
Bob Johnson	Designer"""
            recipients_path.write_text(example_content)
            console.print(f"[green]  Created: {recipients}[/]")
            console.print("[dim]  Edit this file and run the command again.[/]")
            return
        else:
            console.print("[red]Cancelled.[/]")
            return

    console.print(f"[green]  Using: {recipients}[/]")
    console.print()

    # Step 4: Output directory
    display_step(4, total_steps, "Set output directory")
    default_output = cfg.get("output_directory", "local/outputs/certificates")
    if not output:
        output = Prompt.ask(
            "  Enter output directory",
            default=default_output
        )
    console.print(f"[green]  Output: {output}[/]")
    console.print()

    # Confirmation
    console.print("[bold]Summary:[/]")
    console.print(f"  Config:     {config}")
    console.print(f"  Template:   {template}")
    console.print(f"  Recipients: {recipients}")
    console.print(f"  Output:     {output}")
    console.print()

    if not Confirm.ask("Proceed with certificate generation?"):
        console.print("[yellow]Cancelled.[/]")
        return

    # Run the automation
    console.print()
    console.print("[cyan]Generating certificates...[/]")

    try:
        # Update config with paths
        cfg["template_pdf"] = template
        cfg["output_directory"] = output

        # Save updated config temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(cfg, f)
            temp_config = f.name

        results = fill_certificates.fill_certificates_from_file(
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
        table.add_row("Output directory", output)
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
        input_dir = Prompt.ask(
            "  Enter path to directory with images",
            default=default_input
        )

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
        output = Prompt.ask(
            "  Enter output directory",
            default=default_output
        )
    console.print(f"[green]  Output: {output}[/]")
    console.print()

    # Step 3: Quality
    display_step(3, total_steps, "Set image quality")
    if quality is None:
        quality = IntPrompt.ask(
            "  Enter quality percentage (1-100)",
            default=85
        )
    console.print(f"[green]  Quality: {quality}%[/]")
    console.print()

    # Step 4: Max file size
    display_step(4, total_steps, "Set maximum file size")
    if max_size is None:
        max_size_str = Prompt.ask(
            "  Enter maximum file size in MB",
            default="1.0"
        )
        max_size = float(max_size_str)
    console.print(f"[green]  Max size: {max_size}MB[/]")
    console.print()

    # Step 5: Filename prefix or preserve names
    display_step(5, total_steps, "Set output filenames")
    if not preserve_names and not prefix:
        choice = Prompt.ask(
            "  Keep original filenames or use prefix?",
            choices=["keep", "prefix"],
            default="keep"
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
    console.print(f"  Format:   WebP")
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
            preserve_filename=preserve_names
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
@click.option("--certificates-dir", "-d", help="Directory with certificate attachments")
def email(config, recipients, body, certificates_dir):
    """Send bulk personalized emails with attachments

    Step-by-step interactive process to send emails with certificate attachments.
    """
    display_header("Email Sender", "Send personalized emails with attachments")

    total_steps = 4

    # Step 1: Configuration
    display_step(1, total_steps, "Select email configuration")
    default_config = "local/configs/email.json"
    if not config:
        config = Prompt.ask(
            "  Enter path to email configuration",
            default=default_config
        )

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
                "use_tls": True
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
            "  Enter path to recipients CSV (Name,Email columns)",
            default=default_recipients
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
        body = Prompt.ask(
            "  Enter path to email body template",
            default=default_body
        )

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

    # Step 4: Certificates directory
    display_step(4, total_steps, "Select certificates directory")
    default_certs = "local/outputs/certificates"
    if not certificates_dir:
        certificates_dir = Prompt.ask(
            "  Enter path to directory with PDF certificates",
            default=default_certs
        )

    if not Path(certificates_dir).exists():
        console.print(f"[yellow]  Directory not found: {certificates_dir}[/]")
        console.print("[dim]  Emails will be sent without attachments.[/]")
    else:
        cert_count = len(list(Path(certificates_dir).glob("*.pdf")))
        console.print(f"[green]  Found {cert_count} certificates in: {certificates_dir}[/]")
    console.print()

    # Confirmation
    console.print("[bold]Summary:[/]")
    console.print(f"  Config:       {config}")
    console.print(f"  Recipients:   {recipients}")
    console.print(f"  Body:         {body}")
    console.print(f"  Certificates: {certificates_dir}")
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
            certificates_dir=certificates_dir
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
    config_files = list(Path("local/configs").glob("*.json")) if Path("local/configs").exists() else []
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
    console.print("  r10n contacts    Generate VCF contact cards")
    console.print("  r10n certificates    Generate PDF certificates")
    console.print("  r10n images    Optimize images to WebP")
    console.print("  r10n email    Send bulk emails")


@main.command()
def init():
    """Initialize the local folder structure"""
    display_header("Initialize", "Create local folder structure")

    folders = [
        "local/configs",
        "local/inputs/contacts",
        "local/inputs/certificates",
        "local/inputs/images",
        "local/inputs/email",
        "local/outputs/contacts",
        "local/outputs/certificates",
        "local/outputs/images",
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
