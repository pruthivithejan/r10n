#!/usr/bin/env python3
"""
Enhanced CLI for r10n (routine automation)
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
    generate_blog_mdx,
    generate_contacts,
    optimize_images,
    send_emails_outlook,
    send_same_email,
)

console = Console()
VERSION = "2.0.0"

# Load environment variables
env_path = Path("workspace/.env")
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
    Set R10N_NO_BANNER=1 (or legacy AUTOMATIONS_NO_BANNER=1) to suppress.
    """
    if not sys.stdout.isatty() or os.getenv("R10N_NO_BANNER") or os.getenv("AUTOMATIONS_NO_BANNER"):
        return

    banner = """╔═══════════════════════════════════╗
║                                   ║
║  ██████╗  ██╗ ██████╗ ███╗   ██╗  ║
║  ██╔══██╗███║██╔═══██╗████╗  ██║  ║
║  ██████╔╝╚██║██║   ██║██╔██╗ ██║  ║
║  ██╔══██╗ ██║██║   ██║██║╚██╗██║  ║
║  ██║  ██║ ██║╚██████╔╝██║ ╚████║  ║
║  ╚═╝  ╚═╝ ╚═╝ ╚═════╝ ╚═╝  ╚═══╝  ║
║                                   ║
╚═══════════════════════════════════╝"""

    subtitle = f"r10n • v{VERSION} by Pruthivi Thejan (pruthivithejan.me)"
    console.print(f"[bold cyan]{banner}[/]")
    console.print(f"[dim]{subtitle.center(62)}[/]")


def display_header(title: str, description: str = ""):
    """Display a formatted header"""
    content = f"[bold cyan]{title}[/bold cyan]"
    if description:
        content += f"\n[dim]{description}[/dim]"

    console.print(Panel.fit(content, border_style="cyan"))


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


@click.group(invoke_without_command=True)
@click.version_option(version=VERSION)
@click.pass_context
def main(ctx: click.Context):
    """r10n (routine automation) - Automate repetitive routines"""
    display_banner()
    # If no subcommand, show help (preserve default Click behavior)
    if ctx.invoked_subcommand is None and not ctx.resilient_parsing:
        click.echo(ctx.get_help())


@main.command()
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--config", "-c", help="Configuration file path")
@click.option("--input", "-in", help="Input file path")
@click.option("--output", "-o", help="Output directory")
@click.option("--prefix", "-p", help="Contact name prefix")
def contacts(interactive, config, input, output, prefix):
    """Generate VCF contact cards from phone numbers"""

    if interactive:
        display_header("Contact Generation", "Convert phone numbers to VCF contact cards")

        # Get input file
        input = input or Prompt.ask(
            "\n[cyan]Input file path[/]", default="workspace/inputs/contacts/numbers.txt"
        )

        # Check if file exists
        if not Path(input).exists():
            console.print(f"[red]Input file not found: {input}[/]")
            if Confirm.ask("Would you like to create an example file?"):
                example_content = "0771234567\n0712345678\n+94771234567"
                Path(input).parent.mkdir(parents=True, exist_ok=True)
                with open(input, "w") as f:
                    f.write(example_content)
                console.print(f"[green]Created example file: {input}[/]")
            else:
                return

        # Get prefix
        prefix = prefix or Prompt.ask("[cyan]Contact name prefix[/]", default="Contact")

        # Get output path
        output = output or Prompt.ask(
            "[cyan]Output file path[/]",
            default=f"workspace/outputs/contacts/{prefix.lower()}_contacts.vcf",
        )

        # Display summary
        console.print("\n[bold]Summary:[/]")
        console.print(f"  Input: {input}")
        console.print(f"  Prefix: {prefix}")
        console.print(f"  Output: {output}")

        if not Confirm.ask("\n[cyan]Proceed with contact generation?[/]"):
            console.print("[yellow]Cancelled[/]")
            return

    else:
        # Non-interactive mode
        input = input or "workspace/inputs/contacts/numbers.txt"
        output = output or "workspace/outputs/contacts/contacts.vcf"
        prefix = prefix or "Contact"

    # Run the automation
    try:
        console.print("\n[cyan]Generating contacts...[/]")
        results = generate_contacts.generate_vcf_from_file(input, output, prefix)

        # Display results
        console.print("\n[bold green]✅ Contact generation complete![/]")
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


@main.command()
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--config", "-c", help="Email configuration file")
@click.option("--recipients", "-r", help="Recipients file (CSV)")
@click.option("--body", "-b", help="Email body template file")
@click.option("--type", "-t", type=click.Choice(["bulk", "personalized"]), help="Email type")
def email(interactive, config, recipients, body, type):
    """Send bulk or personalized emails"""

    if interactive:
        display_header("Email Automation", "Send bulk or personalized emails with templates")

        # Choose email type
        email_type = type or Prompt.ask(
            "\n[cyan]Email type[/]", choices=["bulk", "personalized"], default="bulk"
        )

        # Get configuration
        config = config or "workspace/configs/email.json"
        if not Path(config).exists():
            console.print(f"[yellow]Config file not found: {config}[/]")
            console.print("[cyan]Creating default configuration...[/]")
            # The setup script should have created this

        # Load and display config
        cfg = load_config(config)
        if cfg:
            display_config(
                {k: v for k, v in cfg.items() if "password" not in k.lower()}, "Email Configuration"
            )

        # Get recipients file
        recipients = recipients or Prompt.ask(
            "\n[cyan]Recipients file[/]", default="workspace/inputs/email/recipients.csv"
        )

        # Get email body template
        body = body or Prompt.ask(
            "[cyan]Email body template[/]", default="workspace/inputs/email/email_template.txt"
        )

        # Preview
        if Path(recipients).exists():
            with open(recipients) as f:
                lines = f.readlines()[:3]
            console.print("\n[dim]Preview of recipients (first 3):[/]")
            for line in lines:
                console.print(f"  {line.strip()}")

        if not Confirm.ask("\n[cyan]Send emails?[/]"):
            console.print("[yellow]Cancelled[/]")
            return

    else:
        # Non-interactive mode
        config = config or "workspace/configs/email.json"
        recipients = recipients or "workspace/inputs/email/recipients.csv"
        body = body or "workspace/inputs/email/email_template.txt"
        email_type = type or "bulk"

    # Run the appropriate automation
    try:
        console.print(f"\n[cyan]Sending {email_type} emails...[/]")

        if email_type == "bulk":
            results = send_same_email.send_from_file(recipients, body, config)
        else:
            results = send_emails_outlook.send_from_file(recipients, body, config)

        # Display results
        console.print("\n[bold green]✅ Email sending complete![/]")
        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total emails", str(results.get("total", 0)))
        table.add_row("Sent successfully", str(results.get("sent", 0)))
        table.add_row("Failed", str(results.get("failed", 0)))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


@main.command()
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--config", "-c", help="Certificate configuration file")
@click.option("--recipients", "-r", help="Recipients data file")
@click.option("--template", "-t", help="PDF template file")
@click.option("--output", "-o", help="Output directory")
def certificates(interactive, config, recipients, template, output):
    """Generate personalized PDF certificates"""

    if interactive:
        display_header(
            "Certificate Generation", "Create personalized PDF certificates from templates"
        )

        # Get configuration
        config = config or "workspace/configs/certificates.json"
        cfg = load_config(config)

        if cfg:
            display_config(cfg, "Certificate Configuration")

        # Get template (default from config if available)
        default_template = cfg.get("template_pdf", "templates/certificates/template.pdf")
        template = template or Prompt.ask(
            "\n[cyan]PDF template file[/]", default=default_template
        )

        if not Path(template).exists():
            console.print(f"[red]Template not found: {template}[/]")
            console.print("[yellow]Please add your PDF template to this location[/]")
            return

        # Get recipients (default from input_directory/input_file in config if available)
        default_input_dir = cfg.get("input_directory", "workspace/inputs/certificates")
        default_recipients = cfg.get("input_file", str(Path(default_input_dir) / "recipients.txt"))
        recipients = recipients or Prompt.ask(
            "[cyan]Recipients file[/]", default=default_recipients
        )

        # Get output directory
        output = output or Prompt.ask(
            "[cyan]Output directory[/]", default="workspace/outputs/certificates"
        )

        if not Confirm.ask("\n[cyan]Generate certificates?[/]"):
            console.print("[yellow]Cancelled[/]")
            return

    else:
        config = config or "workspace/configs/certificates.json"
        # Load config to honor input_directory/input_file default for non-interactive
        cfg = load_config(config)
        default_input_dir = cfg.get("input_directory", "workspace/inputs/certificates")
        recipients = recipients or cfg.get("input_file", str(Path(default_input_dir) / "recipients.txt"))
        output = output or "workspace/outputs/certificates"

    # Run the automation
    try:
        console.print("\n[cyan]Generating certificates...[/]")

        # Update config with paths using keys expected by fill_certificates
        cfg = load_config(config)
        if template:
            cfg["template_pdf"] = template
        # Always set output directory explicitly
        cfg["output_directory"] = output

        # Save updated config temporarily
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(cfg, f)
            temp_config = f.name

        # Use project root as base when paths are project-relative
        results = fill_certificates.fill_certificates_from_file(
            recipients, temp_config, base_dir=str(Path("workspace"))
        )

        # Clean up temp file
        os.unlink(temp_config)

        # Display results
        console.print("\n[bold green]✅ Certificate generation complete![/]")
        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total recipients", str(results.get("total", 0)))
        table.add_row("Generated successfully", str(results.get("generated", 0)))
        table.add_row("Failed", str(results.get("failed", 0)))
        table.add_row("Output directory", output)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


@main.command()
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--input", "-in", help="Input directory containing images")
@click.option("--output", "-o", help="Output directory for optimized images")
@click.option("--quality", "-q", type=int, help="Image quality (1-100)")
@click.option("--max-size", "-s", type=float, help="Maximum file size in MB")
@click.option("--prefix", "-p", help="Prefix for renamed files")
def images(interactive, input, output, quality, max_size, prefix):
    """Optimize and convert images to WebP format"""

    if interactive:
        display_header("Image Optimization", "Convert and optimize images for web use")

        # Get input directory
        input = input or Prompt.ask("\n[cyan]Input directory[/]", default="workspace/inputs/images")

        if not Path(input).exists():
            console.print(f"[red]Input directory not found: {input}[/]")
            return

        # Count images
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
        images = [f for f in Path(input).iterdir() if f.suffix.lower() in image_exts]
        console.print(f"[green]Found {len(images)} images[/]")

        # Get output directory
        output = output or Prompt.ask(
            "[cyan]Output directory[/]", default="workspace/outputs/images"
        )

        # Get quality
        quality = quality or IntPrompt.ask("[cyan]Image quality (1-100)[/]", default=85)

        # Get max size
        max_size = max_size or float(Prompt.ask("[cyan]Maximum file size (MB)[/]", default="1.0"))

        # Get prefix
        prefix = prefix or Prompt.ask("[cyan]File name prefix[/]", default="img")

        # Summary
        console.print("\n[bold]Settings:[/]")
        console.print(f"  Input: {input}")
        console.print(f"  Output: {output}")
        console.print(f"  Quality: {quality}%")
        console.print(f"  Max size: {max_size}MB")
        console.print(f"  Prefix: {prefix}")

        if not Confirm.ask("\n[cyan]Optimize images?[/]"):
            console.print("[yellow]Cancelled[/]")
            return

    else:
        input = input or "workspace/inputs/images"
        output = output or "workspace/outputs/images"
        quality = quality or 85
        max_size = max_size or 1.0
        prefix = prefix or "img"

    # Run the automation
    try:
        console.print("\n[cyan]Optimizing images...[/]")

        results = optimize_images.optimize_images(
            input_dir=input, output_dir=output, prefix=prefix, max_size_mb=max_size, quality=quality
        )

        # Display results
        console.print("\n[bold green]✅ Image optimization complete![/]")
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


@main.command()
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--input", "-in", help="Input text file with blog content")
@click.option("--config", "-c", help="Blog configuration file")
@click.option("--title", "-t", help="Blog title")
@click.option("--author", "-a", help="Blog author")
@click.option("--tags", multiple=True, help="Blog tags")
def blog(interactive, input, config, title, author, tags):
    """Generate MDX blog files with AI proofreading"""

    if interactive:
        display_header(
            "Blog MDX Generation", "Create well-structured MDX blog posts with AI assistance"
        )

        # Get input file
        input = input or Prompt.ask(
            "\n[cyan]Input blog content file[/]", default="workspace/inputs/blog/post.txt"
        )

        if not Path(input).exists():
            console.print(f"[red]Input file not found: {input}[/]")
            return

        # Get configuration
        config = config or "workspace/configs/blog.json"
        cfg = load_config(config)

        # Get title
        title = title or Prompt.ask("[cyan]Blog title[/]")

        # Get author
        author = author or Prompt.ask(
            "[cyan]Author name[/]", default=cfg.get("default_author", "Your Name")
        )

        # Get tags
        if not tags:
            tags_str = Prompt.ask(
                "[cyan]Tags (comma-separated)[/]",
                default=", ".join(cfg.get("default_tags", ["blog"])),
            )
            tags = [t.strip() for t in tags_str.split(",")]

        # Summary
        console.print("\n[bold]Blog Settings:[/]")
        console.print(f"  Title: {title}")
        console.print(f"  Author: {author}")
        console.print(f"  Tags: {', '.join(tags)}")

        if not Confirm.ask("\n[cyan]Generate MDX blog?[/]"):
            console.print("[yellow]Cancelled[/]")
            return

    else:
        if not input:
            console.print("[red]Input file is required[/]")
            return
        config = config or "workspace/configs/blog.json"

    # Run the automation
    try:
        console.print("\n[cyan]Generating MDX blog post...[/]")

        results = generate_blog_mdx.generate_blog_mdx(
            input_file=input,
            config_file=config,
            title=title,
            author=author,
            tags=list(tags) if tags else None,
        )

        # Display results
        if results.get("success"):
            console.print("\n[bold green]✅ Blog MDX generated successfully![/]")
            table = Table(show_header=False)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")

            metadata = results.get("metadata", {})
            table.add_row("Title", metadata.get("title", ""))
            table.add_row("Author", metadata.get("author", ""))
            table.add_row("Date", metadata.get("date", ""))
            table.add_row("Tags", ", ".join(metadata.get("tags", [])))
            table.add_row("Output", results.get("output_path", ""))

            console.print(table)
        else:
            console.print(f"[red]Failed: {results.get('error', 'Unknown error')}[/]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


@main.command()
def status():
    """Check the status of your workspace"""
    display_header("Workspace Status", "Current configuration and setup")

    checks = []

    # Check virtual environment
    if Path(".venv").exists():
        checks.append(("Virtual Environment", "✅ Active", "green"))
    else:
        checks.append(("Virtual Environment", "❌ Not found", "red"))

    # Check workspace
    if Path("workspace").exists():
        checks.append(("Workspace Directory", "✅ Created", "green"))
    else:
        checks.append(("Workspace Directory", "❌ Missing", "red"))

    # Check configs
    config_files = (
        list(Path("workspace/configs").glob("*.json")) if Path("workspace/configs").exists() else []
    )
    if config_files:
        checks.append(("Configuration Files", f"✅ {len(config_files)} found", "green"))
    else:
        checks.append(("Configuration Files", "❌ None found", "red"))

    # Check .env
    if Path("workspace/.env").exists():
        checks.append(("Environment File", "✅ Configured", "green"))
    else:
        checks.append(("Environment File", "❌ Missing", "red"))

    # Display table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Status")

    for component, status, color in checks:
        table.add_row(component, f"[{color}]{status}[/{color}]")

    console.print(table)

    # Show quick tips
    console.print("\n[bold yellow]Quick Tips:[/]")
    console.print("  • Run [cyan]make setup[/] to initialize workspace")
    console.print("  • Run [cyan]make help[/] to see all available commands")
    console.print("  • Use [cyan]--interactive[/] flag for guided execution")


if __name__ == "__main__":
    main()
