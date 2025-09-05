#!/usr/bin/env python3
"""
Smart setup script for Automation Toolkit
One-command initialization of the entire project workspace
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Dict, Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()


def create_directory_structure():
    """Create the workspace and templates directory structure"""
    directories = [
        "workspace/configs",
        "workspace/inputs/email",
        "workspace/inputs/certificates",
        "workspace/inputs/contacts",
        "workspace/inputs/images",
        "workspace/inputs/blog",
        "workspace/outputs/email",
        "workspace/outputs/certificates",
        "workspace/outputs/contacts",
        "workspace/outputs/images",
        "workspace/outputs/blog",
        "workspace/cache",
        "templates/email",
        "templates/certificates",
        "templates/blog",
        "templates/images",
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Creating workspace directories...", total=len(directories))
        
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            progress.advance(task)
    
    return True


def copy_default_configs():
    """Copy default configuration files to workspace"""
    config_mappings = {
        "configs/email.default.json": "workspace/configs/email.json",
        "configs/certificates.default.json": "workspace/configs/certificates.json",
        "configs/images.default.json": "workspace/configs/images.json",
        "configs/blog.default.json": "workspace/configs/blog.json",
    }
    
    copied = []
    skipped = []
    
    for source, dest in config_mappings.items():
        source_path = Path(source)
        dest_path = Path(dest)
        
        if not source_path.exists():
            # We'll create a default config if source doesn't exist yet
            create_default_config(dest_path.name)
            copied.append(dest_path.name)
        elif not dest_path.exists():
            shutil.copy(source_path, dest_path)
            copied.append(dest_path.name)
        else:
            skipped.append(dest_path.name)
    
    if copied:
        console.print(f"[green]✓[/] Copied {len(copied)} default config files")
    if skipped:
        console.print(f"[yellow]⚠[/] Skipped {len(skipped)} existing config files")
    
    return True


def create_default_config(filename: str):
    """Create a default configuration file if it doesn't exist"""
    config_path = Path("workspace/configs") / filename
    
    configs = {
        "email.json": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "your-email@example.com",
            "sender_password": "your-app-password",
            "sender_name": "Your Name",
            "organization": "Your Organization",
            "rate_limit": {
                "delay_seconds": 3,
                "batch_size": 5,
                "batch_delay_seconds": 60
            },
            "template": {
                "subject": "Your Email Subject",
                "use_html": False,
                "variables": ["name", "email"]
            }
        },
        "certificates.json": {
            "template_path": "templates/certificates/template.pdf",
            "output_dir": "workspace/outputs/certificates",
            "font": {
                "name": "Helvetica-Bold",
                "size": 24,
                "color": [0, 0, 0]
            },
            "fields": {
                "name": {"x": 300, "y": 400, "font_size": 30},
                "course": {"x": 300, "y": 350, "font_size": 20},
                "date": {"x": 300, "y": 300, "font_size": 16},
                "achievement": {"x": 300, "y": 250, "font_size": 18}
            }
        },
        "images.json": {
            "output_dir": "workspace/outputs/images",
            "max_file_size_mb": 1.0,
            "quality": 85,
            "max_dimensions": {
                "width": 1920,
                "height": 1080
            },
            "output_format": "webp",
            "preserve_metadata": False,
            "sequential_naming": {
                "enabled": True,
                "prefix": "img",
                "start_number": 1,
                "padding": 3
            }
        },
        "blog.json": {
            "output_dir": "workspace/outputs/blog",
            "default_author": "Your Name",
            "default_tags": ["blog", "article"],
            "openai_api_key": "",
            "proofreading": {
                "enabled": True,
                "model": "gpt-3.5-turbo",
                "max_tokens": 4000
            },
            "mdx_template": {
                "include_reading_time": True,
                "include_table_of_contents": False,
                "image_optimization": True
            }
        }
    }
    
    config_name = filename.replace(".json", "")
    for key, default_config in configs.items():
        if config_name in key:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return True
    
    return False


def create_env_file():
    """Create .env file from template"""
    env_template = """# Automation Toolkit Environment Variables
# Copy this file to workspace/.env and update with your actual values

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your-email@example.com
EMAIL_PASSWORD=your-app-password
SENDER_NAME=Your Name

# API Keys
OPENAI_API_KEY=sk-your-openai-api-key

# Default Settings
DEFAULT_EMAIL_DELAY=3
DEFAULT_BATCH_SIZE=5
DEFAULT_IMAGE_QUALITY=85
DEFAULT_IMAGE_MAX_WIDTH=1920
DEFAULT_IMAGE_MAX_HEIGHT=1080

# Organization Info
ORGANIZATION_NAME=Your Organization
ORGANIZATION_WEBSITE=https://example.com
ORGANIZATION_PHONE=+1234567890
"""
    
    env_path = Path("workspace/.env")
    env_example_path = Path(".env.example")
    
    # Create .env.example in root if it doesn't exist
    if not env_example_path.exists():
        with open(env_example_path, 'w') as f:
            f.write(env_template)
        console.print("[green]✓[/] Created .env.example template")
    
    # Create workspace/.env if it doesn't exist
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write(env_template)
        console.print("[green]✓[/] Created workspace/.env - [yellow]Please update with your credentials[/]")
        return True
    else:
        console.print("[yellow]⚠[/] workspace/.env already exists - skipped")
        return False


def create_example_files():
    """Create example input files for testing"""
    examples = {
        "workspace/inputs/email/recipients_example.csv": "name,email\nJohn Doe,john@example.com\nJane Smith,jane@example.com",
        "workspace/inputs/email/email_template.txt": "Dear {name},\n\nThis is a template email.\n\nBest regards,\n{sender_name}",
        "workspace/inputs/certificates/recipients_example.txt": "John Doe,Python Mastery,2024-01-15,Excellence in Programming\nJane Smith,Data Science,2024-01-16,Outstanding Achievement",
        "workspace/inputs/contacts/numbers_example.txt": "0771234567\n0712345678\n+94771234567",
        "workspace/inputs/blog/sample_post.txt": "# Sample Blog Post\n\nThis is a sample blog post content.\n\n## Introduction\n\nYour content here...",
    }
    
    created = 0
    for filepath, content in examples.items():
        path = Path(filepath)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                f.write(content)
            created += 1
    
    if created > 0:
        console.print(f"[green]✓[/] Created {created} example files in workspace/inputs/")
    
    return True


def display_setup_summary():
    """Display a summary of the setup process"""
    table = Table(title="Setup Summary", show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    checks = [
        ("Virtual Environment", ".venv exists" if Path(".venv").exists() else "Not found"),
        ("Workspace Directory", "✓ Created" if Path("workspace").exists() else "✗ Missing"),
        ("Configuration Files", "✓ Initialized" if Path("workspace/configs").exists() else "✗ Missing"),
        ("Environment File", "✓ Created" if Path("workspace/.env").exists() else "✗ Missing"),
        ("Example Files", "✓ Created" if Path("workspace/inputs").exists() else "✗ Missing"),
    ]
    
    for component, status in checks:
        table.add_row(component, status)
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def interactive_setup():
    """Run an interactive setup wizard"""
    console.print(Panel.fit(
        "[bold cyan]Automation Toolkit Setup Wizard[/bold cyan]\n"
        "This wizard will help you set up your workspace",
        border_style="cyan"
    ))
    
    # Check if workspace already exists
    if Path("workspace").exists():
        if not Confirm.ask("\n[yellow]Workspace already exists. Continue with setup?[/]"):
            console.print("[red]Setup cancelled[/]")
            return False
    
    console.print("\n[bold]Setting up workspace structure...[/]")
    create_directory_structure()
    
    console.print("\n[bold]Copying configuration templates...[/]")
    copy_default_configs()
    
    console.print("\n[bold]Creating environment file...[/]")
    env_created = create_env_file()
    
    if Confirm.ask("\n[cyan]Create example input files for testing?[/]"):
        create_example_files()
    
    display_setup_summary()
    
    console.print(Panel.fit(
        "[bold green]✅ Setup Complete![/bold green]\n\n"
        "[yellow]Next steps:[/yellow]\n"
        "1. Edit [cyan]workspace/.env[/cyan] with your credentials\n"
        "2. Review config files in [cyan]workspace/configs/[/cyan]\n"
        "3. Run [cyan]make help[/cyan] to see available commands\n"
        "4. Try [cyan]make contacts[/cyan] for a simple test",
        border_style="green"
    ))
    
    return True


@click.command()
@click.option('--init', is_flag=True, help='Run initial setup')
@click.option('--reset', is_flag=True, help='Reset workspace to defaults')
@click.option('--check', is_flag=True, help='Check setup status')
def main(init, reset, check):
    """Automation Toolkit Setup Script"""
    
    if check:
        display_setup_summary()
        sys.exit(0)
    
    if reset:
        if Confirm.ask("[red]This will reset your workspace. Are you sure?[/]"):
            if Path("workspace").exists():
                shutil.rmtree("workspace")
                console.print("[green]✓[/] Workspace reset")
            interactive_setup()
        else:
            console.print("[yellow]Reset cancelled[/]")
        sys.exit(0)
    
    if init:
        # Non-interactive mode for Makefile
        create_directory_structure()
        copy_default_configs()
        create_env_file()
        create_example_files()
        console.print("[green]✓[/] Setup complete!")
    else:
        # Interactive mode
        interactive_setup()


if __name__ == "__main__":
    main()
