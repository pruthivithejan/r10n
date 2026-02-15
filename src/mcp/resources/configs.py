"""MCP resources exposing r10n config templates and automation info."""

import json
from pathlib import Path

from src.mcp.server import mcp

# Resolve configs directory relative to project root
CONFIGS_DIR = Path(__file__).parent.parent.parent.parent / "configs"


@mcp.resource("r10n://automations")
def list_automations() -> str:
    """List all available r10n automations with descriptions."""
    automations = [
        {
            "name": "generate_contacts",
            "description": "Generate VCF contact cards from phone numbers",
            "required_params": ["input_file"],
        },
        {
            "name": "generate_certificates",
            "description": "Create personalized PDF certificates from templates",
            "required_params": ["recipients_file", "config_file"],
        },
        {
            "name": "optimize_images",
            "description": "Optimize and convert images to WebP format",
            "required_params": ["input_dir"],
        },
        {
            "name": "send_email",
            "description": "Send bulk personalized emails with attachments",
            "required_params": ["email_list_file", "subject", "body_template", "config_file"],
        },
        {
            "name": "convert_colors",
            "description": "Convert CSS colors to oklch() format",
            "required_params": ["path"],
        },
        {
            "name": "rename_files",
            "description": "Batch rename files with patterns and transformations",
            "required_params": ["input_directory"],
        },
        {
            "name": "validate_csv",
            "description": "Validate CSV files against schemas",
            "required_params": ["input_file"],
        },
        {
            "name": "convert_markdown_to_pdf",
            "description": "Convert Markdown documents to PDF",
            "required_params": ["input_path"],
        },
    ]
    return json.dumps(automations, indent=2)


def _read_config(name: str) -> str:
    """Read a config template file and return its contents."""
    config_path = CONFIGS_DIR / f"{name}.default.json"
    if config_path.exists():
        return config_path.read_text()
    return json.dumps({"error": f"Config template not found: {name}"})


@mcp.resource("r10n://configs/certificates")
def certificates_config() -> str:
    """Default configuration template for certificate generation."""
    return _read_config("certificates")


@mcp.resource("r10n://configs/email")
def email_config() -> str:
    """Default configuration template for email sending."""
    return _read_config("email")


@mcp.resource("r10n://configs/images")
def images_config() -> str:
    """Default configuration template for image optimization."""
    return _read_config("images")


@mcp.resource("r10n://configs/blog")
def blog_config() -> str:
    """Default configuration template for blog generation."""
    return _read_config("blog")
