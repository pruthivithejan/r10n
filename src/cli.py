#!/usr/bin/env python3
"""
r10n (routine automation) CLI
Interactive command-line interface with beautiful terminal UI
"""

import json
import os
import platform
import shutil
import ssl
import stat
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, cast

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

console = Console()
VERSION = "0.11.2"
RELEASE_REPO = "pruthivithejan/r10n"
RELEASES_API = f"https://api.github.com/repos/{RELEASE_REPO}/releases"
UPDATE_CHECK_INTERVAL_SECONDS = 24 * 60 * 60
UPDATE_CHECK_TIMEOUT_SECONDS = 4
app = typer.Typer(
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode="rich",
    help=(
        "r10n - Automate repetitive routines\n\n"
        "Available automations:\n"
        "- contacts: Generate VCF contact cards from phone numbers\n"
        "- fill-pdfs: Fill PDF templates with data from CSV/TXT files\n"
        "- images: Optimize and convert images to WebP\n"
        "- website-images: Download website images and convert format\n"
        "- logos: Download company logos from SVGL\n"
        "- email: Send bulk emails with attachments\n"
        "- colors: Convert CSS colors to oklch() format\n"
        "- rename: Batch rename files with patterns\n"
        "- validate: Validate CSV files against schemas\n"
        "- md2pdf: Convert Markdown files to PDF"
    ),
    context_settings={"help_option_names": ["-h", "--help"]},
)

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


def display_banner(force: bool = False) -> None:
    """Display a styled ASCII banner at startup (TTY only).
    Set R10N_NO_BANNER=1 to suppress.
    """
    if (not force and not sys.stdout.isatty()) or os.getenv("R10N_NO_BANNER"):
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


def detect_platform_asset_name() -> str:
    """Return the release asset name for the current OS and architecture."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    machine_aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "aarch64": "arm64",
    }
    normalized_machine = machine_aliases.get(machine, machine)

    if system == "linux" and normalized_machine == "x86_64":
        return "r10n-linux-x86_64.tar.gz"
    elif system == "darwin" and normalized_machine == "arm64":
        return "r10n-macos-arm64.tar.gz"
    elif system == "windows":
        if normalized_machine == "x86_64":
            return "r10n-windows-x86_64.exe"

    raise RuntimeError(f"Unsupported platform: {system}/{machine}")


def normalize_version(version: str) -> tuple[int, ...]:
    """Convert a semantic version string into a comparable tuple."""
    cleaned = version.strip().lstrip("v")
    if not cleaned:
        return (0,)

    parts = []
    for part in cleaned.split("."):
        if not part.isdigit():
            break
        parts.append(int(part))

    return tuple(parts or [0])


def is_newer_version(candidate: str, current: str) -> bool:
    """Return True when candidate represents a newer version than current."""
    candidate_parts = list(normalize_version(candidate))
    current_parts = list(normalize_version(current))

    max_len = max(len(candidate_parts), len(current_parts))
    candidate_parts.extend([0] * (max_len - len(candidate_parts)))
    current_parts.extend([0] * (max_len - len(current_parts)))

    return tuple(candidate_parts) > tuple(current_parts)


def fetch_release_data(version: str | None = None, timeout: int = 30) -> dict[str, Any]:
    """Fetch release metadata from GitHub Releases API."""
    if version:
        tag = version if version.startswith("v") else f"v{version}"
        url = f"{RELEASES_API}/tags/{tag}"
    else:
        url = f"{RELEASES_API}/latest"

    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "r10n-upgrade",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(
        request, timeout=timeout, context=create_https_context()
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def find_asset_download_url(release_data: dict[str, Any], asset_name: str) -> str:
    """Find an asset download URL in a release payload by filename."""
    assets = release_data.get("assets", [])
    for asset in assets:
        if asset.get("name") == asset_name and asset.get("browser_download_url"):
            return str(asset["browser_download_url"])

    raise RuntimeError(f"Release asset not found: {asset_name}")


def download_to_path(url: str, destination: Path) -> None:
    """Download a URL to a destination path."""
    request = urllib.request.Request(url, headers={"User-Agent": "r10n-upgrade"})
    with (
        urllib.request.urlopen(request, timeout=60, context=create_https_context()) as response,
        open(destination, "wb") as output,
    ):
        shutil.copyfileobj(response, output)


def create_https_context() -> ssl.SSLContext:
    """Create an HTTPS context with the packaged certifi CA bundle when available."""
    context = ssl.create_default_context()
    try:
        import certifi
    except ImportError:
        return context

    context.load_verify_locations(cafile=certifi.where())
    return context


def format_network_error(error: urllib.error.URLError) -> str:
    """Format network errors with a more useful TLS certificate hint."""
    reason = error.reason
    reason_text = str(reason)
    if (
        isinstance(reason, ssl.SSLCertVerificationError)
        or "CERTIFICATE_VERIFY_FAILED" in reason_text
    ):
        return (
            "Network error: TLS certificate verification failed while contacting GitHub. "
            "r10n uses the bundled certifi CA store; if your network uses a custom "
            "proxy certificate, set SSL_CERT_FILE to that CA bundle and retry."
        )

    return f"Network error: {reason}"


def parse_sha256_sums(checksum_content: str) -> dict[str, str]:
    """Parse a sha256sum file into a filename -> hash mapping."""
    checksums: dict[str, str] = {}
    for line in checksum_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.split()
        if len(parts) < 2:
            continue

        checksum = parts[0].lower()
        filename = parts[-1].lstrip("*")
        checksums[filename] = checksum

    return checksums


def compute_file_sha256(file_path: Path) -> str:
    """Compute the SHA-256 hash of a file."""
    hasher = sha256()
    with open(file_path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def resolve_current_executable_path() -> Path:
    """Resolve the currently running executable path."""
    return resolve_command_entry_path().resolve()


def resolve_command_entry_path() -> Path:
    """Return the command path the user runs, preserving launcher symlinks."""
    argv0 = Path(sys.argv[0])
    if argv0.exists() and argv0.name in {"r10n", "r10n.exe"}:
        argv_path = argv0.absolute()
        launcher_path = argv_path.parent.parent / "r10n"
        if (
            argv_path.parent.name == ".r10n"
            and launcher_path.exists()
            and launcher_path.resolve() == argv_path.resolve()
        ):
            return launcher_path
        return argv_path

    executable = shutil.which("r10n")
    if executable:
        return Path(executable)

    raise RuntimeError("Could not determine current executable path.")


def is_standalone_binary(executable_path: Path) -> bool:
    """Return True when the executable appears to be a compiled binary."""
    if executable_path.suffix.lower() == ".exe":
        return True

    try:
        with open(executable_path, "rb") as handle:
            prefix = handle.read(2)
    except OSError:
        return False

    return prefix != b"#!"


def is_archive_asset(asset_name: str) -> bool:
    """Return True when a release asset is an installable app archive."""
    return asset_name.endswith(".tar.gz")


def extract_release_archive(archive_path: Path, destination: Path) -> Path:
    """Extract a release archive and return the extracted app directory."""
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()

    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            member_path = (destination / member.name).resolve()
            if os.path.commonpath([str(destination_root), str(member_path)]) != str(
                destination_root
            ):
                raise RuntimeError(f"Unsafe archive path: {member.name}")

        try:
            archive.extractall(destination, filter="data")
        except TypeError:
            archive.extractall(destination)

    app_dir = destination / "r10n"
    executable = app_dir / "r10n"
    if not executable.exists():
        raise RuntimeError("Release archive did not contain r10n/r10n")

    return app_dir


def replace_installed_app(command_path: Path, new_app_dir: Path) -> None:
    """Install an extracted onedir app and point the r10n launcher at it."""
    if os.name == "nt":
        raise RuntimeError(
            "In-place upgrade is not supported on Windows. "
            "Please reinstall from the latest release binary."
        )

    install_dir = command_path.parent
    if not os.access(install_dir, os.W_OK):
        raise PermissionError(f"No write permission for install directory: {install_dir}")

    app_dir = install_dir / ".r10n"
    staged_app_dir = install_dir / ".r10n.new"
    backup_app_dir = install_dir / ".r10n.bak"
    staged_launcher = install_dir / "r10n.new"

    shutil.rmtree(staged_app_dir, ignore_errors=True)
    shutil.rmtree(backup_app_dir, ignore_errors=True)
    if staged_launcher.exists() or staged_launcher.is_symlink():
        staged_launcher.unlink()

    try:
        shutil.copytree(new_app_dir, staged_app_dir, symlinks=True)
        executable = staged_app_dir / "r10n"
        mode = executable.stat().st_mode
        executable.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        if app_dir.exists():
            shutil.move(str(app_dir), str(backup_app_dir))
        shutil.move(str(staged_app_dir), str(app_dir))

        os.symlink(".r10n/r10n", staged_launcher)
        os.replace(staged_launcher, command_path)
        shutil.rmtree(backup_app_dir, ignore_errors=True)
    except Exception:
        if staged_launcher.exists() or staged_launcher.is_symlink():
            staged_launcher.unlink()
        shutil.rmtree(staged_app_dir, ignore_errors=True)
        if backup_app_dir.exists():
            if app_dir.exists():
                shutil.rmtree(app_dir, ignore_errors=True)
            shutil.move(str(backup_app_dir), str(app_dir))
        raise


def get_update_cache_path() -> Path:
    """Return the location of the update check cache file."""
    cache_root = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_root / "r10n" / "update_check.json"


def load_update_cache() -> dict[str, Any]:
    """Load cached update check data from disk."""
    cache_path = get_update_cache_path()
    if not cache_path.exists():
        return {}

    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_update_cache(data: dict[str, Any]) -> None:
    """Persist update check cache data to disk."""
    cache_path = get_update_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data), encoding="utf-8")


def should_check_for_updates(cache_data: dict[str, Any]) -> bool:
    """Decide whether an update check should be performed now."""
    checked_at = cache_data.get("checked_at")
    if not isinstance(checked_at, (int, float)):
        return True
    return (time.time() - float(checked_at)) >= UPDATE_CHECK_INTERVAL_SECONDS


def maybe_notify_update(subcommand: str | None) -> None:
    """Display a non-blocking update notice when a newer version exists."""
    if os.getenv("R10N_DISABLE_UPDATE_CHECK"):
        return
    if subcommand in {None, "upgrade", "_worker"}:
        return

    cache_data = load_update_cache()
    latest_version = cache_data.get("latest_version") if isinstance(cache_data, dict) else None

    if should_check_for_updates(cache_data):
        try:
            release_data = fetch_release_data(timeout=UPDATE_CHECK_TIMEOUT_SECONDS)
            latest_version = str(release_data.get("tag_name", "")).lstrip("v")
            save_update_cache(
                {
                    "checked_at": int(time.time()),
                    "latest_version": latest_version,
                }
            )
        except Exception:
            return

    if (
        isinstance(latest_version, str)
        and latest_version
        and is_newer_version(latest_version, VERSION)
    ):
        console.print(
            "[dim yellow]Update available: "
            f"v{latest_version} (current v{VERSION}). "
            "Run [cyan]r10n upgrade[/] to update.[/]"
        )


def replace_current_executable(current_executable: Path, new_binary: Path) -> None:
    """Atomically replace the current executable with a new binary."""
    if os.name == "nt":
        raise RuntimeError(
            "In-place upgrade is not supported on Windows. "
            "Please reinstall from the latest release binary."
        )

    if not os.access(current_executable.parent, os.W_OK):
        raise PermissionError(
            f"No write permission for install directory: {current_executable.parent}"
        )

    backup_path = current_executable.with_name(f"{current_executable.name}.bak")
    staged_path = current_executable.with_name(f"{current_executable.name}.new")

    shutil.copy2(current_executable, backup_path)
    try:
        shutil.copy2(new_binary, staged_path)
        mode = staged_path.stat().st_mode
        staged_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.replace(staged_path, current_executable)
        backup_path.unlink(missing_ok=True)
    except Exception:
        if backup_path.exists():
            os.replace(backup_path, current_executable)
        if staged_path.exists():
            staged_path.unlink()
        raise


def version_callback(value: bool) -> None:
    """Print the current r10n version and exit."""
    if value:
        typer.echo(f"r10n, version {VERSION}")
        raise typer.Exit()


def launch_tui() -> None:
    """Load and start the interactive Textual workspace."""
    from src.tui import run_tui

    run_tui(VERSION)


@app.callback(invoke_without_command=True)
def cli(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """r10n - Automate repetitive routines

    Available automations:
    - contacts: Generate VCF contact cards from phone numbers
    - fill-pdfs: Fill PDF templates with data from CSV/TXT files
    - images: Optimize and convert images to WebP
    - website-images: Download website images and convert format
    - logos: Download company logos from SVGL
    - email: Send bulk emails with attachments
    - colors: Convert CSS colors to oklch() format
    - rename: Batch rename files with patterns
    - validate: Validate CSV files against schemas
    - md2pdf: Convert Markdown files to PDF
    """
    if not ctx.resilient_parsing and ctx.invoked_subcommand is None:
        launch_tui()
        raise typer.Exit()

    display_banner()
    if not ctx.resilient_parsing:
        maybe_notify_update(ctx.invoked_subcommand)


@app.command("_worker", hidden=True)
def worker_command(
    automation_id: str = typer.Argument(..., help="Registered automation identifier"),
    input_json: str | None = typer.Option(
        None,
        "--input-json",
        help="Inline input JSON. Reads stdin when omitted.",
    ),
) -> None:
    """Execute an automation through the internal JSON Lines protocol."""
    from src.worker import worker_main

    raise typer.Exit(code=worker_main(automation_id, input_json))


# =============================================================================
# CONTACTS AUTOMATION
# =============================================================================


@app.command()
def contacts(
    input_file: str | None = typer.Option(
        None, "--input", "-i", help="Input file with phone numbers"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output VCF file path"),
    prefix: str | None = typer.Option(None, "--prefix", "-p", help="Contact name prefix"),
) -> None:
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
        from src.automations import generate_contacts

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


@app.command("fill-pdfs")
def fill_pdfs_cmd(
    config: str | None = typer.Option(None, "--config", "-c", help="PDF fill configuration file"),
    recipients: str | None = typer.Option(
        None, "--recipients", "-r", help="Data file (CSV or TXT)"
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="PDF template file (for initial setup)",
    ),
) -> None:
    """Fill PDF templates with data from CSV/TXT files

    Interactive process: configure field positions visually, preview a sample,
    then generate all filled PDFs.
    """
    import subprocess
    import tempfile

    from src.automations import fill_pdfs

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
            console.print("[green]  Preview generated.[/]")

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

        results = fill_pdfs.fill_certificates_from_file(recipients, temp_config, base_dir="local")

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


@app.command()
def images(
    input_dir: str | None = typer.Option(None, "--input", "-i", help="Input directory with images"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output directory"),
    quality: int | None = typer.Option(None, "--quality", "-q", help="Image quality (1-100)"),
    max_size: float | None = typer.Option(None, "--max-size", "-s", help="Maximum file size in MB"),
    prefix: str | None = typer.Option(None, "--prefix", "-p", help="Prefix for output filenames"),
    preserve_names: bool = typer.Option(False, "--preserve-names", help="Keep original filenames"),
) -> None:
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
        from src.automations import optimize_images

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
# WEBSITE IMAGES AUTOMATION
# =============================================================================


@app.command("website-images")
def website_images(
    website_url: str | None = typer.Option(
        None, "--url", "-u", help="Website URL to scan for images"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output directory"),
    output_format: Literal["jpg", "jpeg", "png", "webp"] | None = typer.Option(
        None,
        "--format",
        "-f",
        case_sensitive=False,
        help="Converted image format",
    ),
    quality: int | None = typer.Option(
        None, "--quality", "-q", help="Image quality for JPG/WebP (1-100)"
    ),
    timeout: int = typer.Option(5, "--timeout", help="Request timeout seconds"),
    max_pages: int | None = typer.Option(
        None,
        "--max-pages",
        help="Maximum same-site pages to scan. Use 0 for no limit",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Run without confirmation"),
) -> None:
    """Download website images and convert them to a chosen format.

    Crawls same-site pages, mirrors page folders, and saves converted raster files.
    """
    display_header("Website Image Downloader", "Download website images into page folders")

    total_steps = 5

    display_step(1, total_steps, "Enter website URL")
    if not website_url:
        website_url = Prompt.ask("  Enter website URL")
    console.print(f"[green]  Website: {website_url}[/]")
    console.print()

    display_step(2, total_steps, "Set output directory")
    if not output:
        output = "local/outputs/website-images"
        if not yes:
            output = Prompt.ask(
                "  Enter output directory",
                default=output,
            )
    console.print(f"[green]  Output: {output}[/]")
    console.print()

    display_step(3, total_steps, "Select output format")
    if not output_format:
        output_format = "webp"
        if not yes:
            output_format = cast(
                Literal["jpg", "jpeg", "png", "webp"],
                Prompt.ask(
                    "  Convert images to",
                    choices=["webp", "jpg", "png"],
                    default=output_format,
                ),
            )
    assert output_format is not None
    console.print(f"[green]  Format: {output_format.lower()}[/]")
    console.print()

    display_step(4, total_steps, "Set quality")
    if quality is None:
        quality = 85
        if not yes:
            quality = IntPrompt.ask("  Enter quality for JPG/WebP (1-100)", default=quality)
    console.print(f"[green]  Quality: {quality}%[/]")
    console.print()

    display_step(5, total_steps, "Set page crawl limit")
    if max_pages is None:
        max_pages = 50
        if not yes:
            max_pages = IntPrompt.ask(
                "  Enter maximum same-site pages to scan (0 for no limit)",
                default=max_pages,
            )
    if max_pages == 0:
        page_limit_summary = "No limit"
    else:
        page_limit_summary = str(max_pages)
    console.print(f"[green]  Max pages: {page_limit_summary}[/]")
    console.print()

    console.print("[bold]Summary:[/]")
    console.print(f"  Website: {website_url}")
    console.print(f"  Output:  {output}")
    console.print(f"  Format:  {output_format.lower()}")
    console.print(f"  Quality: {quality}%")
    console.print(f"  Pages:   {page_limit_summary}")
    console.print()

    if not yes and not Confirm.ask("Proceed with download?"):
        console.print("[yellow]Cancelled.[/]")
        return

    console.print()
    console.print("[cyan]Downloading and converting website images...[/]")
    console.print()

    try:
        from src.automations import download_website_images

        results = download_website_images.download_website_images(
            url=website_url,
            output_dir=output,
            output_format=output_format,
            quality=quality,
            timeout=timeout,
            max_pages=None if max_pages == 0 else max_pages,
        )

        console.print()
        console.print("[bold green]Done![/]")
        console.print()

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Pages scanned", str(results.get("pages_scanned", 0)))
        table.add_row("Images found", str(results.get("found", 0)))
        table.add_row("Downloaded", str(results.get("downloaded", 0)))
        table.add_row("Failed", str(results.get("failed", 0)))
        table.add_row("Output directory", str(results.get("output_directory", output)))
        console.print(table)

        failed_files = [file for file in results.get("files", []) if not file.get("success")]
        if failed_files:
            console.print()
            console.print("[yellow]Some images could not be converted:[/]")
            for file in failed_files[:5]:
                console.print(f"  - {file.get('source_url')}: {file.get('error')}")
            if len(failed_files) > 5:
                console.print(f"  ...and {len(failed_files) - 5} more")

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# LOGOS AUTOMATION
# =============================================================================


@app.command()
def logos(
    names: str | None = typer.Option(
        None,
        "--names",
        "-n",
        help="Comma-separated company or brand names",
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output directory"),
    timeout: int = typer.Option(5, "--timeout", help="Request timeout seconds"),
    max_candidates: int | None = typer.Option(
        None,
        "--max-candidates",
        help="Maximum ranked logo URLs to try per name",
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace existing logo files"),
    no_manifest: bool = typer.Option(False, "--no-manifest", help="Do not write JSON manifest"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Run without confirmation"),
) -> None:
    """Download company logos from the SVGL API.

    Searches SVGL for each requested company or brand name and saves one SVG
    per matched name. Missing SVGL matches are reported as failures.
    """
    display_header("Logo Downloader", "Download company logos from SVGL")

    total_steps = 4

    display_step(1, total_steps, "Enter logo names")
    if not names:
        names = Prompt.ask("  Enter company names separated by commas")

    try:
        from src.automations import download_logos

        company_names = download_logos.parse_logo_names(names)
    except ValueError as error:
        console.print(f"[red]{error}[/]")
        return

    console.print(f"[green]  Logos: {', '.join(company_names)}[/]")
    console.print()

    display_step(2, total_steps, "Set output directory")
    if not output:
        output = "local/outputs/logos"
        if not yes:
            output = Prompt.ask("  Enter output directory", default=output)
    console.print(f"[green]  Output: {output}[/]")
    console.print()

    display_step(3, total_steps, "Set search depth")
    if max_candidates is None:
        max_candidates = 20
        if not yes:
            max_candidates = IntPrompt.ask(
                "  Enter maximum SVGL logo URLs to try per name",
                default=max_candidates,
            )
    if max_candidates < 1:
        console.print("[red]Max candidates must be at least 1.[/]")
        return
    if timeout < 1:
        console.print("[red]Timeout must be at least 1 second.[/]")
        return
    console.print(f"[green]  Max candidates: {max_candidates}[/]")
    console.print()

    display_step(4, total_steps, "Set overwrite behavior")
    if not yes and not overwrite:
        overwrite = Confirm.ask("  Replace existing logo files?", default=False)
    existing_mode = "Replace existing files" if overwrite else "Skip existing files"
    console.print(f"[green]  Existing files: {existing_mode}[/]")
    console.print()

    console.print("[bold]Summary:[/]")
    console.print(f"  Names:      {', '.join(company_names)}")
    console.print(f"  Output:     {output}")
    console.print("  Source:     SVGL API only")
    console.print(f"  Search:     up to {max_candidates} SVGL candidates per name")
    console.print(f"  Existing:   {existing_mode}")
    console.print()

    if not yes and not Confirm.ask("Proceed with logo download?"):
        console.print("[yellow]Cancelled.[/]")
        return

    console.print()
    console.print("[cyan]Searching and downloading logos...[/]")
    console.print()

    try:
        from src.automations import download_logos

        def display_logo_progress(logo_result: dict[str, Any]) -> None:
            company_name = str(logo_result.get("company_name", "Logo"))
            if logo_result.get("skipped"):
                console.print(f"[dim]  Skipped:[/] {company_name}")
            elif logo_result.get("success"):
                console.print(
                    f"[green]  Downloaded:[/] {company_name} -> {logo_result.get('output_file')}"
                )
            else:
                console.print(f"[yellow]  Failed:[/] {company_name}: {logo_result.get('error')}")

        results = download_logos.download_logos(
            names=company_names,
            output_dir=output,
            timeout=timeout,
            max_candidates=max_candidates,
            overwrite=overwrite,
            write_manifest=not no_manifest,
            progress_callback=display_logo_progress,
        )

        console.print()
        console.print("[bold green]Done![/]")
        console.print()

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Requested", str(results.get("requested", 0)))
        table.add_row("Downloaded", str(results.get("downloaded", 0)))
        table.add_row("Skipped", str(results.get("skipped", 0)))
        table.add_row("Failed", str(results.get("failed", 0)))
        table.add_row("Output directory", str(results.get("output_directory", output)))
        if results.get("manifest_file"):
            table.add_row("Manifest", str(results["manifest_file"]))
        console.print(table)

        failed_logos = [logo for logo in results.get("logos", []) if not logo.get("success")]
        if failed_logos:
            console.print()
            console.print("[yellow]Some logos could not be downloaded:[/]")
            for logo in failed_logos[:5]:
                console.print(f"  - {logo.get('company_name')}: {logo.get('error')}")
            if len(failed_logos) > 5:
                console.print(f"  ...and {len(failed_logos) - 5} more")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


# =============================================================================
# EMAIL AUTOMATION
# =============================================================================


@app.command()
def email(
    config: str | None = typer.Option(None, "--config", "-c", help="Email configuration file"),
    recipients: str | None = typer.Option(None, "--recipients", "-r", help="Recipients CSV file"),
    body: str | None = typer.Option(None, "--body", "-b", help="Email body template file"),
    attachments_dir: str | None = typer.Option(
        None,
        "--attachments-dir",
        "-d",
        help="Directory with PDF attachments",
    ),
) -> None:
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
        from src.automations import send_same_email

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


@app.command()
def colors(
    dir_path: str | None = typer.Option(
        None, "--path", "-p", help="Directory containing CSS files"
    ),
    file_path: str | None = typer.Option(None, "--file", "-f", help="Single CSS file to process"),
    no_backup: bool = typer.Option(False, "--no-backup", help="Don't create backup files"),
    process_all: bool = typer.Option(
        False, "--all", "-a", help="Process all files without prompting"
    ),
) -> None:
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
        from src.automations import convert_colors

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


@app.command()
def rename(
    input_dir: str | None = typer.Option(None, "--input", "-i", help="Input directory with files"),
    pattern: str | None = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Rename pattern with placeholders: {name}, {ext}, {date}, {sequence}",
    ),
    prefix: str | None = typer.Option(None, "--prefix", help="Add prefix to filenames"),
    suffix: str | None = typer.Option(None, "--suffix", help="Add suffix to filenames"),
    replace_from: str | None = typer.Option(
        None, "--replace-from", help="Text to replace in filenames"
    ),
    replace_to: str | None = typer.Option(None, "--replace-to", help="Replacement text"),
    lowercase: bool = typer.Option(False, "--lowercase", help="Convert filenames to lowercase"),
    uppercase: bool = typer.Option(False, "--uppercase", help="Convert filenames to uppercase"),
    add_date: bool = typer.Option(False, "--add-date", help="Add current date to filenames"),
    add_sequence: bool = typer.Option(False, "--add-sequence", help="Add sequence numbers"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Process subdirectories"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview changes without renaming"),
    file_pattern: str | None = typer.Option(
        None, "--file-pattern", help="File glob pattern to match (e.g., '*.jpg')"
    ),
) -> None:
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
        from src.automations import rename_files

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


@app.command()
def validate(
    input_file: str | None = typer.Option(None, "--input", "-i", help="Input CSV file to validate"),
    schema: str | None = typer.Option(
        None, "--schema", "-s", help="JSON schema file for validation"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file for validation report"
    ),
    strict: bool = typer.Option(False, "--strict", help="Enable strict validation mode"),
    clean: bool = typer.Option(False, "--clean", help="Clean and fix data issues"),
    report_format: Literal["text", "json", "html"] | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Report format",
    ),
) -> None:
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
        report_format = cast(
            Literal["text", "json", "html"],
            Prompt.ask("  Report format", choices=["text", "json", "html"], default="text"),
        )
    assert report_format is not None
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
        from src.automations import validate_csv

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


@app.command()
def md2pdf(
    input_path: str | None = typer.Option(
        None, "--input", "-i", help="Input markdown file or directory"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output PDF file or directory"),
    css: str | None = typer.Option(None, "--css", "-c", help="Custom CSS file for styling"),
    page_size: Literal["A4", "Letter", "Legal"] | None = typer.Option(
        None, "--page-size", help="Page size"
    ),
    toc: bool = typer.Option(False, "--toc", help="Include table of contents"),
    syntax_highlight: bool = typer.Option(
        False, "--syntax-highlight", help="Enable syntax highlighting for code"
    ),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Process subdirectories"),
) -> None:
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
        page_size = cast(
            Literal["A4", "Letter", "Legal"],
            Prompt.ask("  Page size", choices=["A4", "Letter", "Legal"], default="A4"),
        )
    assert page_size is not None
    console.print(f"[green]  Page size: {page_size}[/]")

    if not css:
        use_css = Confirm.ask("  Use custom CSS file?", default=False)
        if use_css:
            css = Prompt.ask("  Enter CSS file path", default="local/configs/pdf_style.css")
            if not Path(css).exists():
                console.print("[yellow]  CSS file not found, using default styling[/]")
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
        from src.automations import markdown_to_pdf

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


@app.command()
def configure(
    template: str = typer.Option(..., "--template", "-t", help="PDF template file"),
    recipients: str | None = typer.Option(
        None, "--recipients", "-r", help="CSV file (for column headers)"
    ),
    output: str = typer.Option(
        "local/configs/fill-pdfs.json", "--output", "-o", help="Output config path"
    ),
) -> None:
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


@app.command()
def status() -> None:
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
    console.print("  r10n upgrade        Update installed binary")


# =============================================================================
# UPGRADE COMMAND
# =============================================================================


@app.command()
def upgrade(
    target_version: str | None = typer.Option(
        None,
        "--version",
        help="Install a specific version tag (for example: 2.0.0 or v2.0.0)",
    ),
    check: bool = typer.Option(False, "--check", help="Only check for updates"),
) -> None:
    """Upgrade r10n binary from GitHub Releases."""
    display_header("Upgrade", "Update your installed r10n binary")

    try:
        asset_name = detect_platform_asset_name()
    except RuntimeError as error:
        console.print(f"[red]Error: {error}[/]")
        sys.exit(1)

    try:
        command_path = resolve_command_entry_path()
        current_executable = resolve_current_executable_path()
        if not is_standalone_binary(current_executable):
            console.print("[yellow]Upgrade is available only for standalone binary installs.[/]")
            console.print("[dim]Use [cyan]uv sync[/] and [cyan]git pull[/] for source installs.[/]")
            return

        release_data = fetch_release_data(target_version)
        release_tag = str(release_data.get("tag_name") or "")
        release_version = release_tag.lstrip("v")
        if not release_version:
            raise RuntimeError("Release response did not include a valid version tag.")

        binary_name = current_executable.name
        if binary_name.endswith(".exe") and not asset_name.endswith(".exe"):
            asset_name = f"{asset_name}.exe"
        elif not binary_name.endswith(".exe") and asset_name.endswith(".exe"):
            asset_name = asset_name.removesuffix(".exe")

        current_version = VERSION
        newer_available = is_newer_version(release_version, current_version)

        console.print(f"[cyan]Current version:[/] {current_version}")
        console.print(f"[cyan]Latest release:[/] {release_version}")
        console.print(f"[cyan]Asset:[/] {asset_name}")
        console.print()

        if check:
            if newer_available:
                console.print("[bold yellow]Update available.[/]")
                console.print("Run [cyan]r10n upgrade[/] to install it.")
            else:
                console.print("[bold green]You are up to date.[/]")
            return

        if not newer_available and not target_version:
            console.print("[bold green]You are already on the latest version.[/]")
            return

        console.print(f"[cyan]Install path:[/] {command_path}")

        binary_url = find_asset_download_url(release_data, asset_name)
        checksum_url = find_asset_download_url(release_data, "SHA256SUMS")

        with tempfile.TemporaryDirectory(prefix="r10n-upgrade-") as temp_dir:
            temp_path = Path(temp_dir)
            binary_path = temp_path / asset_name
            checksum_path = temp_path / "SHA256SUMS"

            console.print("[cyan]Downloading release assets...[/]")
            download_to_path(binary_url, binary_path)
            download_to_path(checksum_url, checksum_path)

            checksums = parse_sha256_sums(checksum_path.read_text(encoding="utf-8"))
            expected_hash = checksums.get(asset_name)
            if not expected_hash:
                raise RuntimeError(f"Checksum for {asset_name} not found in SHA256SUMS")

            actual_hash = compute_file_sha256(binary_path)
            if actual_hash.lower() != expected_hash.lower():
                raise RuntimeError("Checksum verification failed for downloaded binary")

            console.print("[green]Checksum verified.[/]")
            if is_archive_asset(asset_name):
                extracted_app_dir = extract_release_archive(binary_path, temp_path / "extract")
                replace_installed_app(command_path, extracted_app_dir)
            else:
                replace_current_executable(current_executable, binary_path)

        console.print()
        console.print(f"[bold green]Done! Updated to r10n v{release_version}[/]")

    except urllib.error.HTTPError as error:
        if error.code == 404:
            console.print(
                "[red]Release not found. Check the version tag and published artifacts.[/]"
            )
        elif error.code == 403:
            console.print("[red]GitHub API rate limit reached. Try again later.[/]")
        else:
            console.print(f"[red]HTTP error: {error}[/]")
        sys.exit(1)
    except urllib.error.URLError as error:
        console.print(f"[red]{format_network_error(error)}[/]")
        sys.exit(1)
    except PermissionError as error:
        console.print(f"[red]Permission error: {error}[/]")
        console.print("[yellow]Reinstall to a writable location like ~/.local/bin.[/]")
        sys.exit(1)
    except Exception as error:
        console.print(f"[red]Error: {error}[/]")
        sys.exit(1)


@app.command()
def init() -> None:
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
        "local/outputs/logos",
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


def main() -> None:
    """Run the Typer-powered r10n CLI."""
    app()


if __name__ == "__main__":
    main()
