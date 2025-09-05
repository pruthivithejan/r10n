#!/usr/bin/env python3
"""
Migration script to help users migrate from old data structure to new workspace structure
"""

import json
import shutil
from pathlib import Path
from typing import List, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table

console = Console()


def find_data_files() -> List[Tuple[Path, Path]]:
    """
    Find files in old data structure and suggest new locations.
    
    Returns:
        List of (old_path, new_path) tuples
    """
    migrations = []
    
    # Define migration mappings
    mappings = [
        # Email files
        ("data/emails/email_list.csv", "workspace/inputs/email/recipients.csv"),
        ("data/emails/email_list.txt", "workspace/inputs/email/recipients.txt"),
        ("data/emails/email.txt", "workspace/inputs/email/email_template.txt"),
        ("data/emails/email_config.json", "workspace/configs/email.json"),
        ("data/emails/attachments", "workspace/inputs/email/attachments"),
        
        # Outlook email files
        ("data/outlook/recipients.txt", "workspace/inputs/email/outlook_recipients.txt"),
        ("data/outlook/email.txt", "workspace/inputs/email/outlook_template.txt"),
        ("data/outlook/email_config.json", "workspace/configs/outlook_email.json"),
        ("data/outlook/certificates", "workspace/inputs/email/certificates"),
        
        # Certificate files
        ("data/certificates/recipients.txt", "workspace/inputs/certificates/recipients.txt"),
        ("data/certificates/config.json", "workspace/configs/certificates.json"),
        ("data/certificates/templates/*.pdf", "templates/certificates/"),
        ("data/certificates/output", "workspace/outputs/certificates"),
        
        # Phone numbers / Contacts
        ("data/phone_numbers/numbers.txt", "workspace/inputs/contacts/numbers.txt"),
        ("data/phone_numbers/*.txt", "workspace/inputs/contacts/"),
        ("data/phone_numbers/*.vcf", "workspace/outputs/contacts/"),
        
        # Blog files
        ("data/blog_config.json", "workspace/configs/blog.json"),
        ("data/blog/*.txt", "workspace/inputs/blog/"),
        ("data/blog/*.mdx", "workspace/outputs/blog/"),
        
        # Image files
        ("data/images/*.{jpg,jpeg,png,gif,bmp}", "workspace/inputs/images/"),
        ("data/images/optimized", "workspace/outputs/images/"),
    ]
    
    data_path = Path("data")
    if not data_path.exists():
        return migrations
    
    # Process each mapping
    for old_pattern, new_location in mappings:
        old_path = Path(old_pattern)
        
        if "*" in str(old_path):
            # Handle glob patterns
            base_dir = old_path.parent
            pattern = old_path.name
            if base_dir.exists():
                for file in base_dir.glob(pattern):
                    if file.is_file():
                        new_path = Path(new_location) / file.name
                        migrations.append((file, new_path))
                    elif file.is_dir() and not new_location.endswith("/"):
                        migrations.append((file, Path(new_location)))
        else:
            # Handle specific files/directories
            if old_path.exists():
                if old_path.is_dir():
                    migrations.append((old_path, Path(new_location)))
                else:
                    migrations.append((old_path, Path(new_location)))
    
    return migrations


def migrate_file(old_path: Path, new_path: Path, dry_run: bool = False) -> bool:
    """
    Migrate a single file or directory.
    
    Args:
        old_path: Source path
        new_path: Destination path
        dry_run: If True, only show what would be done
    
    Returns:
        True if successful
    """
    try:
        if dry_run:
            console.print(f"  Would migrate: {old_path} → {new_path}")
            return True
        
        # Create destination directory
        if new_path.suffix:  # It's a file
            new_path.parent.mkdir(parents=True, exist_ok=True)
        else:  # It's a directory
            new_path.mkdir(parents=True, exist_ok=True)
        
        # Copy file or directory
        if old_path.is_dir():
            if new_path.exists():
                # Merge directories
                for item in old_path.iterdir():
                    dest = new_path / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
            else:
                shutil.copytree(old_path, new_path)
        else:
            shutil.copy2(old_path, new_path)
        
        console.print(f"  ✓ Migrated: {old_path} → {new_path}", style="green")
        return True
        
    except Exception as e:
        console.print(f"  ✗ Failed: {old_path} → {new_path}: {e}", style="red")
        return False


def display_migration_plan(migrations: List[Tuple[Path, Path]]):
    """Display the migration plan in a table."""
    table = Table(title="Migration Plan", show_header=True, header_style="bold cyan")
    table.add_column("Old Location", style="yellow")
    table.add_column("→", style="cyan", justify="center")
    table.add_column("New Location", style="green")
    
    for old_path, new_path in migrations:
        old_str = str(old_path).replace(str(Path.home()), "~")
        new_str = str(new_path).replace(str(Path.home()), "~")
        table.add_row(old_str, "→", new_str)
    
    console.print(table)


@click.command()
@click.option('--dry-run', is_flag=True, help='Show what would be migrated without doing it')
@click.option('--auto', is_flag=True, help='Automatically migrate without prompting')
@click.option('--backup', is_flag=True, default=True, help='Keep backup of old data directory')
def main(dry_run, auto, backup):
    """Migrate from old data structure to new workspace structure."""
    
    console.print(Panel.fit(
        "[bold cyan]Data Migration Tool[/bold cyan]\n"
        "Migrate your existing data to the new workspace structure",
        border_style="cyan"
    ))
    
    # Check if old data exists
    if not Path("data").exists():
        console.print("[yellow]No 'data' directory found. Nothing to migrate.[/]")
        return
    
    # Check if workspace exists
    if not Path("workspace").exists():
        console.print("[yellow]Creating workspace directory...[/]")
        Path("workspace").mkdir(exist_ok=True)
    
    # Find files to migrate
    console.print("\n[cyan]Scanning for files to migrate...[/]")
    migrations = find_data_files()
    
    if not migrations:
        console.print("[yellow]No files found to migrate.[/]")
        return
    
    console.print(f"\n[green]Found {len(migrations)} items to migrate[/]\n")
    
    # Display migration plan
    display_migration_plan(migrations)
    
    if dry_run:
        console.print("\n[yellow]Dry run mode - no files will be migrated[/]")
        console.print("\nFiles that would be migrated:")
        for old_path, new_path in migrations:
            migrate_file(old_path, new_path, dry_run=True)
        return
    
    # Confirm migration
    if not auto:
        if not Confirm.ask("\n[cyan]Proceed with migration?[/]"):
            console.print("[red]Migration cancelled[/]")
            return
    
    # Perform migration
    console.print("\n[cyan]Migrating files...[/]")
    
    success_count = 0
    fail_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Migrating files...", total=len(migrations))
        
        for old_path, new_path in migrations:
            if migrate_file(old_path, new_path):
                success_count += 1
            else:
                fail_count += 1
            progress.advance(task)
    
    # Show results
    console.print(f"\n[bold]Migration Results:[/]")
    console.print(f"  ✓ Successfully migrated: {success_count} items", style="green")
    if fail_count > 0:
        console.print(f"  ✗ Failed: {fail_count} items", style="red")
    
    # Handle backup
    if backup and success_count > 0:
        console.print("\n[cyan]Original data directory has been preserved[/]")
        console.print("[yellow]You can safely delete the 'data' directory once you've verified the migration[/]")
    elif not backup and success_count == len(migrations):
        if Confirm.ask("\n[yellow]Delete the old 'data' directory?[/]"):
            shutil.rmtree("data")
            console.print("[green]✓ Old data directory removed[/]")
    
    console.print("\n[bold green]✅ Migration complete![/]")
    console.print("\n[yellow]Next steps:[/]")
    console.print("1. Review migrated files in workspace/")
    console.print("2. Update any custom scripts that reference old paths")
    console.print("3. Test automations with: make contacts")
    console.print("4. Once verified, you can delete the old 'data' directory")


if __name__ == "__main__":
    main()
