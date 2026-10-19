"""Machine-readable backend entry point for the native r10n frontend."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path
from typing import Any


def build_catalog() -> dict[str, Any]:
    """Export registry metadata without importing automation implementations.

    Returns:
        Protocol version and all automation schemas in registry display order.
    """
    from r10n_backend.registry import list_automations
    from r10n_backend.settings import load_settings
    from r10n_backend.worker import PROTOCOL_VERSION

    settings = load_settings()
    return {
        "protocol": PROTOCOL_VERSION,
        "version": version("r10n"),
        "automations": [
            {
                "id": spec.id,
                "title": spec.title,
                "description": spec.description,
                "category": spec.category,
                "roles": list(spec.roles),
                "confirmation": spec.confirmation,
                "input_schema": spec.input_schema(),
                "field_order": list(spec.input_model.model_fields),
                "setup_hint": (
                    "Create a PDF template profile first with `r10n configure`."
                    if spec.id == "fill-pdfs" and not settings.pdf_profiles
                    else (
                        "Create an SMTP profile first with `r10n config add-smtp-profile <name>`."
                        if spec.id == "email" and not settings.smtp_profiles
                        else ""
                    )
                ),
            }
            for spec in list_automations()
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch catalog, JSON Lines worker, or foreground field picker.

    Args:
        argv: Arguments excluding the executable name, or process arguments.

    Returns:
        Backend operation exit status.

    Raises:
        SystemExit: For argparse usage errors or help.
    """
    # JSON and diagnostics use UTF-8 even when Windows redirects streams through
    # a legacy code page. Capture/mocked streams may not support reconfiguration.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("catalog", help="Emit registry metadata as JSON")
    worker_parser = commands.add_parser("worker", help="Run a v2 JSON Lines worker")
    worker_parser.add_argument("automation_id", help="Registered automation identifier")
    worker_parser.add_argument("--input-json", help="Inline JSON input instead of stdin")
    commands.add_parser("secret-set", help="Store a profile password in the OS credential store")
    commands.add_parser(
        "secret-delete", help="Delete a profile password from the OS credential store"
    )
    inspect_parser = commands.add_parser(
        "pdf-inspect", help="Inspect a template and recipient fields"
    )
    inspect_parser.add_argument("--template", required=True, help="PDF template path")
    inspect_parser.add_argument("--recipients", help="CSV/XLSX/TXT recipient file")
    commands.add_parser("pdf-preview", help="Render a private sample PDF to terminal text")
    options = parser.parse_args(argv)

    if options.command == "catalog":
        json.dump(build_catalog(), sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0

    if options.command == "pdf-inspect":
        result = inspect_pdf(options.template, options.recipients)
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    if options.command == "pdf-preview":
        result = preview_pdf(json.load(sys.stdin))
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    if options.command in {"secret-set", "secret-delete"}:
        request = json.load(sys.stdin)
        profile = request.get("profile")
        if not isinstance(profile, str) or not profile.strip():
            raise ValueError("An SMTP profile name is required")
        from r10n_backend.secrets import delete_secret, set_secret

        if options.command == "secret-set":
            secret = request.get("secret")
            if not isinstance(secret, str) or not secret:
                raise ValueError("A non-empty password is required")
            set_secret(profile, secret)
        else:
            delete_secret(profile)
        json.dump({"saved": True}, sys.stdout)
        sys.stdout.write("\n")
        return 0

    from r10n_backend.worker import worker_main

    return worker_main(options.automation_id, options.input_json)


def inspect_pdf(template: str, recipients: str | None = None) -> dict[str, Any]:
    """Return the first-page dimensions and merge-field names for terminal setup."""
    from pypdf import PdfReader

    from r10n_backend.automations.fill_pdfs import load_recipients

    template_path = Path(template).expanduser().resolve()
    reader = PdfReader(template_path)
    page = reader.pages[0]
    fields = []
    sample = {}
    if recipients:
        rows = load_recipients(str(Path(recipients).expanduser().resolve()))
        if rows:
            sample = {str(key): str(value) for key, value in rows[0].items()}
            fields = sorted(
                key
                for key in sample
                if key.lower() not in {"email", "e-mail", "email_address", "email address"}
            )
    return {
        "template_pdf": str(template_path),
        "page_width": float(page.mediabox.width),
        "page_height": float(page.mediabox.height),
        "fields": fields,
        "sample": sample,
    }


def preview_pdf(payload: dict[str, Any]) -> dict[str, Any]:
    """Render a private PDF sample into a low-resolution terminal-safe preview."""
    import pypdfium2 as pdfium

    from r10n_backend.automations.fill_pdfs import fill_certificate

    template = str(Path(payload["template_pdf"]).expanduser().resolve())
    profile = payload["profile"]
    sample = dict(payload.get("sample", {}))
    for field_name in profile.get("fields", {}):
        sample.setdefault(field_name, field_name.replace("_", " ").title())
    with tempfile.TemporaryDirectory(prefix="r10n-pdf-preview-") as directory:
        preview_path = Path(directory) / "preview.pdf"
        fill_certificate(template, profile, sample, str(preview_path))
        document = pdfium.PdfDocument(str(preview_path))
        try:
            bitmap = document[0].render(scale=0.4).to_pil().convert("L")
            bitmap.thumbnail((72, 20))
            ramp = " .:-=+*#%@"
            width, height = bitmap.size
            lines = [
                "".join(
                    ramp[min(len(ramp) - 1, bitmap.getpixel((x, y)) * len(ramp) // 256)]
                    for x in range(width)
                )
                for y in range(height)
            ]
        finally:
            document.close()
    return {"ascii_preview": "\n".join(lines), "width": width, "height": height}


if __name__ == "__main__":
    raise SystemExit(main())
