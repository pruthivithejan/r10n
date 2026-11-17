"""Render the homepage automation cards from the shared registry."""

from __future__ import annotations

import sys
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


def main() -> int:
    """Write the card fragment, or verify it with --check."""
    output = render_cards()
    if sys.argv[1:] == ["--check"]:
        if not FRAGMENT.exists() or FRAGMENT.read_text(encoding="utf-8") != output:
            print(
                "Homepage automation cards are stale; run scripts/render_home_automations.py",
                file=sys.stderr,
            )
            return 1
        return 0
    if sys.argv[1:]:
        print("Usage: render_home_automations.py [--check]", file=sys.stderr)
        return 2
    FRAGMENT.parent.mkdir(parents=True, exist_ok=True)
    FRAGMENT.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
