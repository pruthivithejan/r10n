# This file makes the automations directory a Python package

from . import (
    convert_colors,
    fill_pdfs,
    generate_contacts,
    markdown_to_pdf,
    optimize_images,
    rename_files,
    send_same_email,
    validate_csv,
)

__all__ = [
    "convert_colors",
    "fill_pdfs",
    "generate_contacts",
    "markdown_to_pdf",
    "optimize_images",
    "rename_files",
    "send_same_email",
    "validate_csv",
]
