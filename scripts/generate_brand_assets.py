"""Generate r10n's official foreground-only wordmark and R favicon."""

from __future__ import annotations

import json
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASCII_PATH = ROOT / "assets" / "brand" / "r10n-ascii.txt"
TOKENS_PATH = ROOT / "assets" / "brand" / "tokens.json"
DOC_ASSETS = ROOT / "docs" / "assets" / "brand"
RUNTIME_BRAND = ROOT / "internal" / "brand"
INSTALLER_PATH = ROOT / "install.sh"
INSTALLER_START = "      # BEGIN GENERATED R10N ASCII"
INSTALLER_END = "      # END GENERATED R10N ASCII"


def read_logo() -> tuple[list[str], str, str]:
    """Read the canonical block logo, neon foreground, and favicon background."""
    lines = ASCII_PATH.read_text(encoding="utf-8").splitlines()
    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    return lines, tokens["brand_neon"], tokens["favicon_background"]


def render_glyphs(lines: list[str], *, x_offset: float = 0, y_offset: float = 0) -> tuple[str, str]:
    """Convert the source block and double-line box glyphs into SVG geometry."""
    rectangles: list[str] = []
    strokes: list[str] = []
    for row, line in enumerate(lines):
        top = y_offset + row * 2
        for column, cell in enumerate(line):
            left = x_offset + column
            if cell == "█":
                rectangles.append(f'<rect x="{left:g}" y="{top:g}" width="1" height="2"/>')
                continue

            vertical_left, vertical_right = left + 0.38, left + 0.62
            horizontal_top, horizontal_bottom = top + 0.82, top + 1.18
            horizontal_direction, vertical_direction = {
                "╔": ("right", "down"),
                "╗": ("left", "down"),
                "╚": ("right", "up"),
                "╝": ("left", "up"),
            }.get(cell, ("", ""))
            if cell == "║" or vertical_direction:
                y1, y2 = top, top + 2
                if vertical_direction == "down":
                    y1 = top + 1
                elif vertical_direction == "up":
                    y2 = top + 1
                strokes.extend(
                    (
                        f'<path d="M{vertical_left:g} {y1:g}V{y2:g}"/>',
                        f'<path d="M{vertical_right:g} {y1:g}V{y2:g}"/>',
                    )
                )
            if cell == "═" or horizontal_direction:
                x1, x2 = left, left + 1
                if horizontal_direction == "right":
                    x1 = left + 0.5
                elif horizontal_direction == "left":
                    x2 = left + 0.5
                strokes.extend(
                    (
                        f'<path d="M{x1:g} {horizontal_top:g}H{x2:g}"/>',
                        f'<path d="M{x1:g} {horizontal_bottom:g}H{x2:g}"/>',
                    )
                )
    return "".join(rectangles), "".join(strokes)


def render_wordmark(lines: list[str], color: str) -> str:
    """Render the complete shadow-free ASCII wordmark as vector geometry."""
    width = max(len(line) for line in lines)
    height = len(lines) * 2
    rectangles, strokes = render_glyphs(lines)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '
        f'{width} {height}" role="img" aria-labelledby="title desc">'
        '<title id="title">r10n routine automation</title>'
        '<desc id="desc">Electric-blue block-letter r10n wordmark.</desc>'
        f'<g fill="{color}" stroke="{color}" stroke-width="0.13" '
        f'stroke-linecap="square">{rectangles}{strokes}</g></svg>\n'
    )


def render_favicon(lines: list[str], color: str, background: str) -> str:
    """Render only the first letter of the canonical wordmark in a square viewBox."""
    letter_rows = [line[2:10] for line in lines]
    rectangles, strokes = render_glyphs(letter_rows, x_offset=2.5)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 12" '
        'role="img" aria-labelledby="title">'
        '<title id="title">r10n R</title>'
        f'<rect width="12" height="12" rx="2" fill="{background}"/>'
        f'<g fill="{color}" stroke="{color}" stroke-width="0.13" '
        f'stroke-linecap="square">{rectangles}{strokes}</g></svg>\n'
    )


def render_installer_banner(lines: list[str]) -> str:
    """Render the canonical ASCII logo as a static POSIX shell printf block."""
    result = [
        INSTALLER_START,
        "      printf '%s\\n' \\",
    ]
    for index, line in enumerate(lines):
        quoted = shlex.quote(line)
        if index == len(lines) - 1:
            result.append(f"        {quoted} >&2")
        else:
            result.append(f"        {quoted} \\")
    result.append(INSTALLER_END)
    return "\n".join(result)


def update_installer_banner(lines: list[str]) -> None:
    """Update only the marked banner block in the standalone installer."""
    content = INSTALLER_PATH.read_text(encoding="utf-8")
    start = content.index(INSTALLER_START)
    end = content.index(INSTALLER_END, start) + len(INSTALLER_END)
    updated = content[:start] + render_installer_banner(lines) + content[end:]
    INSTALLER_PATH.write_text(updated, encoding="utf-8")


def main() -> None:
    """Regenerate the native CLI logo and docs wordmark/favicon."""
    lines, color, favicon_background = read_logo()
    DOC_ASSETS.mkdir(parents=True, exist_ok=True)
    RUNTIME_BRAND.mkdir(parents=True, exist_ok=True)
    (RUNTIME_BRAND / "logo.txt").write_text(
        ASCII_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (DOC_ASSETS / "r10n.svg").write_text(render_wordmark(lines, color), encoding="utf-8")
    (DOC_ASSETS / "favicon.svg").write_text(
        render_favicon(lines, color, favicon_background), encoding="utf-8"
    )
    update_installer_banner(lines)


if __name__ == "__main__":
    main()
