"""Declarative automation catalog used by every r10n interface.

The registry is intentionally independent from Typer and Textual. An automation
defines its validated inputs and execution adapter once, allowing terminal UIs,
scripts, and future frontends to share the same contract.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EventCallback = Callable[[str, dict[str, Any]], None]
Executor = Callable[[BaseModel, EventCallback], Any]


class AutomationInput(BaseModel):
    """Base model for automation inputs."""

    model_config = ConfigDict(extra="forbid")


class ContactsInput(AutomationInput):
    """Inputs for contact-card generation."""

    input_file: str = Field(
        "local/inputs/contacts/numbers.txt",
        description="Text file containing one phone number per line",
        json_schema_extra={"ui:widget": "file"},
    )
    output_file: str = Field(
        "local/outputs/contacts/contacts.vcf",
        description="VCF file to create",
        json_schema_extra={"ui:widget": "save_file"},
    )
    prefix: str = Field("Contact", min_length=1, description="Contact name prefix")


class FillPdfsInput(AutomationInput):
    """Inputs for filling PDF templates."""

    recipients_file: str = Field(
        "local/inputs/fill-pdfs/data.csv",
        description="CSV or TXT recipient data",
        json_schema_extra={"ui:widget": "file"},
    )
    config_file: str = Field(
        "local/configs/fill-pdfs.json",
        description="Field placement configuration from r10n configure",
        json_schema_extra={"ui:widget": "file"},
    )
    base_dir: str = Field("local", description="Base directory for relative config paths")


class ImagesInput(AutomationInput):
    """Inputs for image optimization."""

    input_directory: str = Field(
        "local/inputs/images",
        description="Directory containing source images",
        json_schema_extra={"ui:widget": "directory"},
    )
    output_directory: str = Field(
        "local/outputs/images",
        description="Directory for optimized WebP images",
        json_schema_extra={"ui:widget": "directory"},
    )
    quality: int = Field(85, ge=1, le=100, description="WebP quality percentage")
    max_size_mb: float = Field(1.0, gt=0, description="Maximum output size in megabytes")
    prefix: str = Field("img", description="Output filename prefix")
    preserve_filenames: bool = Field(True, description="Keep the original filenames")


class WebsiteImagesInput(AutomationInput):
    """Inputs for downloading images from a website."""

    url: str = Field(..., min_length=1, description="Website URL to crawl")
    output_directory: str = Field(
        "local/outputs/website-images",
        description="Directory for downloaded images",
        json_schema_extra={"ui:widget": "directory"},
    )
    output_format: Literal["webp", "jpg", "png"] = Field(
        "webp", description="Converted image format"
    )
    quality: int = Field(85, ge=1, le=100, description="JPG/WebP quality percentage")
    timeout: int = Field(5, ge=1, description="Request timeout in seconds")
    max_pages: int = Field(50, ge=0, description="Maximum pages to crawl; 0 means unlimited")


class LogosInput(AutomationInput):
    """Inputs for downloading brand logos."""

    names: str = Field(..., min_length=1, description="Comma-separated company or brand names")
    output_directory: str = Field(
        "local/outputs/logos",
        description="Directory for downloaded SVG files",
        json_schema_extra={"ui:widget": "directory"},
    )
    timeout: int = Field(5, ge=1, description="Request timeout in seconds")
    max_candidates: int = Field(20, ge=1, description="Maximum candidate URLs per logo")
    overwrite: bool = Field(False, description="Replace existing logo files")
    write_manifest: bool = Field(True, description="Write a JSON result manifest")


class EmailInput(AutomationInput):
    """Inputs for sending personalized email."""

    config_file: str = Field(
        "local/configs/email.json",
        description="SMTP and message configuration",
        json_schema_extra={"ui:widget": "file"},
    )
    recipients_file: str = Field(
        "local/inputs/email/recipients.csv",
        description="CSV containing Name and Email columns",
        json_schema_extra={"ui:widget": "file"},
    )
    body_file: str = Field(
        "local/inputs/email/body.txt",
        description="Plain-text email body template",
        json_schema_extra={"ui:widget": "file"},
    )
    attachments_directory: str = Field(
        "local/outputs/fill-pdfs",
        description="Directory containing personalized PDF attachments",
        json_schema_extra={"ui:widget": "directory"},
    )


class ColorsInput(AutomationInput):
    """Inputs for CSS color conversion."""

    path: str = Field(
        "local/inputs/colors",
        description="Directory containing CSS files",
        json_schema_extra={"ui:widget": "directory"},
    )
    file: str | None = Field(
        None,
        description="Optional single CSS file; takes precedence over the directory",
        json_schema_extra={"ui:widget": "file"},
    )
    dry_run: bool = Field(True, description="Preview changes without writing files")
    create_backups: bool = Field(True, description="Create .bak files before modifying CSS")


class RenameInput(AutomationInput):
    """Inputs for batch file renaming."""

    input_directory: str = Field(
        "local/inputs/rename",
        description="Directory containing files to rename",
        json_schema_extra={"ui:widget": "directory"},
    )
    pattern: str | None = Field(None, description="Pattern using {name}, {ext}, and {sequence}")
    prefix: str | None = Field(None, description="Text to add before each filename")
    suffix: str | None = Field(None, description="Text to add before each extension")
    replace_from: str | None = Field(None, description="Text to replace")
    replace_to: str | None = Field(None, description="Replacement text")
    add_date: bool = Field(False, description="Add the current date")
    add_sequence: bool = Field(False, description="Add sequence numbers")
    lowercase: bool = Field(False, description="Convert filenames to lowercase")
    uppercase: bool = Field(False, description="Convert filenames to uppercase")
    recursive: bool = Field(False, description="Process nested directories")
    dry_run: bool = Field(True, description="Preview renames without changing files")
    file_pattern: str = Field("*", description="Glob pattern used to select files")


class ValidateCsvInput(AutomationInput):
    """Inputs for CSV validation."""

    input_file: str = Field(
        "local/inputs/validate/data.csv",
        description="CSV file to validate",
        json_schema_extra={"ui:widget": "file"},
    )
    schema_file: str | None = Field(
        None,
        description="Optional r10n JSON validation schema",
        json_schema_extra={"ui:widget": "file"},
    )
    strict: bool = Field(False, description="Treat warnings as validation failures")
    trim_whitespace: bool = Field(True, description="Trim values before validating")
    report_file: str | None = Field(
        None,
        description="Optional path for a validation report",
        json_schema_extra={"ui:widget": "save_file"},
    )
    report_format: Literal["text", "json", "html"] = Field(
        "text", description="Validation report format"
    )
    clean_invalid: bool = Field(False, description="Write a cleaned CSV when validation fails")


class MarkdownToPdfInput(AutomationInput):
    """Inputs for Markdown-to-PDF conversion."""

    input_path: str = Field(
        "local/inputs/markdown",
        description="Markdown file or directory",
        json_schema_extra={"ui:widget": "path"},
    )
    output_path: str | None = Field(
        None,
        description="Optional output PDF or directory; generated beside the input by default",
        json_schema_extra={"ui:widget": "path"},
    )
    css_file: str | None = Field(
        None,
        description="Optional custom CSS file",
        json_schema_extra={"ui:widget": "file"},
    )
    page_size: Literal["A4", "Letter", "Legal"] = Field("A4", description="PDF page size")
    include_toc: bool = Field(False, description="Include a table of contents")
    syntax_highlighting: bool = Field(True, description="Highlight fenced code blocks")
    recursive: bool = Field(False, description="Process nested directories")


@dataclass(frozen=True)
class AutomationSpec:
    """Metadata and execution contract for one automation."""

    id: str
    title: str
    description: str
    category: str
    roles: tuple[str, ...]
    input_model: type[AutomationInput]
    executor: Executor
    confirmation: str | None = None

    def validate(self, payload: dict[str, Any]) -> AutomationInput:
        """Validate a raw payload using this automation's input model.

        Args:
            payload: Untrusted input values from a CLI or UI.

        Returns:
            Validated automation input model.

        Raises:
            pydantic.ValidationError: If the payload is invalid.
        """
        return self.input_model.model_validate(payload)


def normalize_result(result: Any) -> dict[str, Any]:
    """Convert automation return values to a JSON-safe dictionary.

    Args:
        result: Automation result object.

    Returns:
        JSON-compatible result dictionary.
    """
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if is_dataclass(result) and not isinstance(result, type):
        return asdict(result)
    if isinstance(result, dict):
        return result
    return {"result": result}


def _run_contacts(inputs: BaseModel, emit: EventCallback) -> dict[str, Any]:
    from src.automations.generate_contacts import generate_vcf_from_file

    values = ContactsInput.model_validate(inputs)
    emit("progress", {"current": 0, "total": 1, "message": "Generating VCF contacts"})
    result = generate_vcf_from_file(values.input_file, values.output_file, values.prefix)
    emit("progress", {"current": 1, "total": 1, "message": "Contacts generated"})
    return result


def _run_fill_pdfs(inputs: BaseModel, emit: EventCallback) -> dict[str, Any]:
    from src.automations.fill_pdfs import fill_certificates_from_file

    values = FillPdfsInput.model_validate(inputs)
    emit("log", {"message": "Loading PDF configuration and recipient data"})
    return fill_certificates_from_file(
        values.recipients_file,
        values.config_file,
        base_dir=values.base_dir,
    )


def _run_images(inputs: BaseModel, emit: EventCallback) -> dict[str, Any]:
    from src.automations.optimize_images import optimize_images

    values = ImagesInput.model_validate(inputs)
    emit("log", {"message": "Optimizing images"})
    return optimize_images(
        input_dir=values.input_directory,
        output_dir=values.output_directory,
        quality=values.quality,
        max_size_mb=values.max_size_mb,
        prefix=values.prefix,
        preserve_filename=values.preserve_filenames,
    )


def _run_website_images(inputs: BaseModel, emit: EventCallback) -> dict[str, Any]:
    from src.automations.download_website_images import download_website_images

    values = WebsiteImagesInput.model_validate(inputs)
    emit("log", {"message": f"Crawling {values.url}"})
    return download_website_images(
        url=values.url,
        output_dir=values.output_directory,
        output_format=values.output_format,
        quality=values.quality,
        timeout=values.timeout,
        max_pages=None if values.max_pages == 0 else values.max_pages,
    )


def _run_logos(inputs: BaseModel, emit: EventCallback) -> dict[str, Any]:
    from src.automations.download_logos import download_logos

    values = LogosInput.model_validate(inputs)

    def on_progress(item: dict[str, Any]) -> None:
        emit("log", {"message": f"Processed {item.get('company_name', 'logo')}"})

    return download_logos(
        names=values.names,
        output_dir=values.output_directory,
        timeout=values.timeout,
        max_candidates=values.max_candidates,
        overwrite=values.overwrite,
        write_manifest=values.write_manifest,
        progress_callback=on_progress,
    )


def _run_email(inputs: BaseModel, emit: EventCallback) -> dict[str, Any]:
    from src.automations.send_same_email import send_from_file

    values = EmailInput.model_validate(inputs)
    emit("log", {"message": "Connecting to the configured SMTP server"})
    return send_from_file(
        email_list_file=values.recipients_file,
        body_file=values.body_file,
        config_file=values.config_file,
        certificates_dir=values.attachments_directory,
    )


def _run_colors(inputs: BaseModel, emit: EventCallback) -> dict[str, Any]:
    from src.automations.convert_colors import convert_colors

    values = ColorsInput.model_validate(inputs)
    emit("log", {"message": "Scanning CSS color values"})
    return convert_colors(
        path=values.path,
        file=values.file,
        dry_run=values.dry_run,
        no_backup=not values.create_backups,
    )


def _run_rename(inputs: BaseModel, emit: EventCallback) -> dict[str, Any]:
    from src.automations.rename_files import rename_files

    values = RenameInput.model_validate(inputs)
    emit("log", {"message": "Previewing renames" if values.dry_run else "Renaming files"})
    result = rename_files(
        input_directory=values.input_directory,
        pattern=values.pattern,
        prefix=values.prefix,
        suffix=values.suffix,
        replace_from=values.replace_from,
        replace_to=values.replace_to,
        add_date=values.add_date,
        add_sequence=values.add_sequence,
        lowercase=values.lowercase,
        uppercase=values.uppercase,
        recursive=values.recursive,
        dry_run=values.dry_run,
        file_pattern=values.file_pattern,
    )
    return normalize_result(result)


def _run_validate(inputs: BaseModel, emit: EventCallback) -> dict[str, Any]:
    from src.automations.validate_csv import clean_csv, generate_report, validate_csv

    values = ValidateCsvInput.model_validate(inputs)
    emit("log", {"message": "Validating CSV rows"})
    result = validate_csv(
        input_file=values.input_file,
        schema_file=values.schema_file,
        strict_mode=values.strict,
        trim_whitespace=values.trim_whitespace,
    )
    normalized = normalize_result(result)
    if values.report_file:
        generate_report(result, values.report_file, values.report_format)
        normalized["report_file"] = values.report_file
    if values.clean_invalid and not result.is_valid:
        cleaned_path = str(Path(values.input_file).with_suffix(".cleaned.csv"))
        clean_csv(values.input_file, cleaned_path, trim_whitespace=True)
        normalized["cleaned_file"] = cleaned_path
    return normalized


def _run_markdown_to_pdf(inputs: BaseModel, emit: EventCallback) -> dict[str, Any]:
    from src.automations.markdown_to_pdf import convert_directory, convert_markdown_to_pdf

    values = MarkdownToPdfInput.model_validate(inputs)
    source = Path(values.input_path)
    emit("log", {"message": "Converting Markdown to PDF"})
    if source.is_dir():
        return convert_directory(
            input_dir=values.input_path,
            output_dir=values.output_path,
            recursive=values.recursive,
            css_file=values.css_file,
            page_size=values.page_size,
        )
    return convert_markdown_to_pdf(
        input_path=values.input_path,
        output_path=values.output_path,
        css_file=values.css_file,
        page_size=values.page_size,
        include_toc=values.include_toc,
        syntax_highlighting=values.syntax_highlighting,
    )


AUTOMATIONS = (
    AutomationSpec(
        id="contacts",
        title="Generate contacts",
        description="Create a VCF contact list from phone numbers.",
        category="People",
        roles=("operations", "sales", "events"),
        input_model=ContactsInput,
        executor=_run_contacts,
    ),
    AutomationSpec(
        id="fill-pdfs",
        title="Fill PDF templates",
        description="Generate personalized PDFs from structured recipient data.",
        category="Documents",
        roles=("operations", "people", "events"),
        input_model=FillPdfsInput,
        executor=_run_fill_pdfs,
    ),
    AutomationSpec(
        id="images",
        title="Optimize images",
        description="Compress and convert batches of images to WebP.",
        category="Media",
        roles=("marketing", "design", "web"),
        input_model=ImagesInput,
        executor=_run_images,
    ),
    AutomationSpec(
        id="website-images",
        title="Download website images",
        description="Crawl a website and save converted image assets by page.",
        category="Media",
        roles=("marketing", "design", "web"),
        input_model=WebsiteImagesInput,
        executor=_run_website_images,
    ),
    AutomationSpec(
        id="logos",
        title="Download logos",
        description="Find and download company logos from SVGL.",
        category="Media",
        roles=("marketing", "design", "sales"),
        input_model=LogosInput,
        executor=_run_logos,
    ),
    AutomationSpec(
        id="email",
        title="Send personalized email",
        description="Send personalized messages with matching PDF attachments.",
        category="Communication",
        roles=("operations", "people", "events", "sales"),
        input_model=EmailInput,
        executor=_run_email,
        confirmation="This automation sends real email to every valid recipient.",
    ),
    AutomationSpec(
        id="colors",
        title="Convert CSS colors",
        description="Convert legacy CSS color values to OKLCH.",
        category="Web",
        roles=("design", "web"),
        input_model=ColorsInput,
        executor=_run_colors,
        confirmation="Disable dry run only when you are ready to modify CSS files.",
    ),
    AutomationSpec(
        id="rename",
        title="Batch rename files",
        description="Preview or apply consistent filename transformations.",
        category="Files",
        roles=("operations", "marketing", "design"),
        input_model=RenameInput,
        executor=_run_rename,
        confirmation="Disable dry run only when you are ready to rename files.",
    ),
    AutomationSpec(
        id="validate",
        title="Validate CSV data",
        description="Validate CSV rows against an optional reusable schema.",
        category="Data",
        roles=("operations", "finance", "people"),
        input_model=ValidateCsvInput,
        executor=_run_validate,
    ),
    AutomationSpec(
        id="md2pdf",
        title="Convert Markdown to PDF",
        description="Turn Markdown files or directories into styled PDFs.",
        category="Documents",
        roles=("operations", "marketing", "documentation"),
        input_model=MarkdownToPdfInput,
        executor=_run_markdown_to_pdf,
    ),
)

AUTOMATION_BY_ID = {automation.id: automation for automation in AUTOMATIONS}


def get_automation(automation_id: str) -> AutomationSpec:
    """Return an automation specification by stable identifier.

    Args:
        automation_id: Stable automation identifier.

    Returns:
        Matching automation specification.

    Raises:
        KeyError: If the automation does not exist.
    """
    try:
        return AUTOMATION_BY_ID[automation_id]
    except KeyError as error:
        raise KeyError(f"Unknown automation: {automation_id}") from error


def list_automations() -> tuple[AutomationSpec, ...]:
    """Return all registered automations in display order."""
    return AUTOMATIONS
