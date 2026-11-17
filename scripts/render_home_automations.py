"""Render the homepage automation cards from the shared registry."""

from __future__ import annotations

from html import escape
from pathlib import Path

from r10n_backend.registry import list_automations

ROOT = Path(__file__).resolve().parent.parent
FRAGMENT = ROOT / "overrides" / "partials" / "home-automations.html"

# Registry identifiers map to their documentation folders.
DOC_SLUGS = {
    "contacts": "contacts",
    "fill-pdfs": "fill-pdfs",
    "images": "images",
    "website-images": "website-images",
    "logos": "logos",
    "email": "email",
    "colors": "colors",
    "rename": "rename-files",
    "validate": "validate-csv",
    "md2pdf": "markdown-to-pdf",
    "video": "video",
}


def render_cards() -> str:
    """Return one linked card per documented automation."""
    cards: list[str] = []
    for automation in list_automations():
        slug = DOC_SLUGS.get(automation.id)
        if slug is None:
            raise KeyError(f"No documentation folder for automation: {automation.id}")
        cards.append(
            f'<a class="r10n-card" href="{{{{ \'automations/{slug}/\' | url }}}}">\n'
            f'  <span class="r10n-card__meta">{escape(automation.category)}</span>\n'
            f'  <span class="r10n-card__title">{escape(automation.title)}</span>\n'
            f'  <span class="r10n-card__body">{escape(automation.description)}</span>\n'
            "</a>"
        )
    return "\n".join(cards) + "\n"


def main() -> None:
    """Write the generated automation-card fragment."""
    FRAGMENT.parent.mkdir(parents=True, exist_ok=True)
    FRAGMENT.write_text(render_cards(), encoding="utf-8")


if __name__ == "__main__":
    main()
