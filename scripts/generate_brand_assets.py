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


def read_logo() -> tuple[list[str], str]:
    """Read the canonical striped logo and its single primary foreground."""
    lines = ASCII_PATH.read_text(encoding="utf-8").splitlines()
    if not lines or any(set(line) - {" ", "▀"} for line in lines):
        raise ValueError("The logo must contain only spaces and upper-half stripe blocks (▀).")
    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    return lines, tokens["brand_neon"]


def render_glyphs(lines: list[str], *, x_offset: float = 0, y_offset: float = 0) -> str:
    """Render upper-half blocks as horizontal, separated stripes."""
    rectangles: list[str] = []
    for row, line in enumerate(lines):
        if set(line) - {" ", "▀"}:
            raise ValueError("Only spaces and upper-half stripe blocks (▀) can be rendered.")
        top = y_offset + row * 2
        column = 0
        while column < len(line):
            if line[column] == " ":
                column += 1
                continue
            start = column
            while column < len(line) and line[column] == "▀":
                column += 1
            rectangles.append(
                f'<rect x="{x_offset + start:g}" y="{top:g}" '
                f'width="{column - start}" height="1"/>'
            )
    return "".join(rectangles)


def render_wordmark(lines: list[str], color: str) -> str:
    """Render the transparent striped wordmark without fonts, outlines, or shadows."""
    width = max(len(line) for line in lines)
    height = len(lines) * 2 - 1
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '
        f'{width} {height}" role="img" aria-labelledby="title desc">'
        '<title id="title">r10n routine automation</title>'
        '<desc id="desc">Horizontal primary-turquoise stripes spell r10n.</desc>'
        f'<g fill="{color}">{render_glyphs(lines)}</g></svg>\n'
    )


def render_favicon(lines: list[str], color: str) -> str:
    """Center only the seven-column R crop on a transparent square."""
    letter_rows = [line[:7] for line in lines]
    side = len(lines) * 2 + 2
    left = (side - 7) / 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {side} {side}" '
        'role="img" aria-labelledby="title">'
        '<title id="title">r10n R</title>'
        f'<g fill="{color}">{render_glyphs(letter_rows, x_offset=left, y_offset=1.5)}'
        "</g></svg>\n"
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
    lines, color = read_logo()
    DOC_ASSETS.mkdir(parents=True, exist_ok=True)
    RUNTIME_BRAND.mkdir(parents=True, exist_ok=True)
    (RUNTIME_BRAND / "logo.txt").write_text(
        ASCII_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (DOC_ASSETS / "r10n.svg").write_text(render_wordmark(lines, color), encoding="utf-8")
    (DOC_ASSETS / "favicon.svg").write_text(render_favicon(lines, color), encoding="utf-8")
    update_installer_banner(lines)


if __name__ == "__main__":
    main()
