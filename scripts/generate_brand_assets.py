"""Generate r10n's solid block wordmark, R favicon, and terminal logo."""

from __future__ import annotations

import json
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORDMARK_PATH = ROOT / "assets" / "brand" / "r10n-wordmark.txt"
TOKENS_PATH = ROOT / "assets" / "brand" / "tokens.json"
ASSETS_BRAND = ROOT / "assets" / "brand"
DOC_ASSETS = ROOT / "docs" / "assets" / "brand"
RUNTIME_BRAND = ROOT / "internal" / "brand"
INSTALLER_PATH = ROOT / "install.sh"
INSTALLER_START = "      # BEGIN GENERATED R10N ASCII"
INSTALLER_END = "      # END GENERATED R10N ASCII"

# One source cell measured from JetBrains Mono at 100px: the block glyph is
# 60.205 wide and 101.953 tall, and the wordmark sets 1.16 line-height.
CELL_WIDTH = 1.0
INK_HEIGHT = 1.6934
ROW_PITCH = 1.9268


def read_logo() -> tuple[list[str], dict[str, str]]:
    """Read the canonical solid logo and the gradient token pair."""
    lines = WORDMARK_PATH.read_text(encoding="utf-8").splitlines()
    if not lines or any(set(line) - {" ", "█"} for line in lines):
        raise ValueError("The logo must contain only spaces and full blocks (█).")
    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    return lines, tokens


def number(value: float) -> str:
    """Format a coordinate without trailing zeros."""
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def cells(lines: list[str]) -> set[tuple[int, int]]:
    """Return every filled cell as (row, column)."""
    return {
        (row, column)
        for row, line in enumerate(lines)
        for column, cell in enumerate(line)
        if cell == "█"
    }


def glyph_columns(lines: list[str]) -> list[tuple[int, int]]:
    """Return contiguous filled column runs, one per glyph."""
    width = max(len(line) for line in lines)
    filled = [
        any(column < len(line) and line[column] == "█" for line in lines) for column in range(width)
    ]
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for column, ink in enumerate([*filled, False]):
        if ink and start is None:
            start = column
        elif not ink and start is not None:
            runs.append((start, column))
            start = None
    return runs


def render_glyphs(
    lines: list[str],
    *,
    from_column: int = 0,
    to_column: int | None = None,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    scale: float = 1.0,
) -> str:
    """Render solid cells as row runs, keeping the seam between lines."""
    to_column = max(len(line) for line in lines) if to_column is None else to_column
    rectangles: list[str] = []
    for row, line in enumerate(lines):
        column = from_column
        while column < to_column:
            cell = line[column] if column < len(line) else " "
            if cell == " ":
                column += 1
                continue
            start = column
            while column < to_column:
                cell = line[column] if column < len(line) else " "
                if cell != "█":
                    break
                column += 1
            rectangles.append(
                f'<rect x="{number(x_offset + (start - from_column) * CELL_WIDTH * scale)}" '
                f'y="{number(y_offset + row * ROW_PITCH * scale)}" '
                f'width="{number((column - start) * CELL_WIDTH * scale)}" '
                f'height="{number(INK_HEIGHT * scale)}"/>'
            )
    return "".join(rectangles)


def gradient_defs(tokens: dict[str, str], height: float) -> str:
    """Return the vertical palette gradient shared by the wordmark and favicon."""
    return (
        '<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" '
        f'x1="0" y1="0" x2="0" y2="{number(height)}">'
        f'<stop offset="0" stop-color="{tokens["light_blue"].lower()}"/>'
        f'<stop offset="1" stop-color="{tokens["frozen_water"].lower()}"/>'
        "</linearGradient></defs>"
    )


def render_wordmark(lines: list[str], tokens: dict[str, str], *, color: str | None = None) -> str:
    """Render the transparent solid wordmark without shadows or fonts."""
    width = max(len(line) for line in lines)
    height = (len(lines) - 1) * ROW_PITCH + INK_HEIGHT
    paint = f'<g fill="{color}">' if color else f'{gradient_defs(tokens, height)}<g fill="url(#g)">'
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {number(height)}" role="img" aria-labelledby="title desc">'
        '<title id="title">r10n routine automation</title>'
        '<desc id="desc">Solid block letters spell r10n.</desc>'
        f"{paint}{render_glyphs(lines)}</g></svg>\n"
    )


def render_favicon(
    lines: list[str], tokens: dict[str, str], side: float = 16, *, color: str | None = None
) -> str:
    """Center only the R glyph on a transparent square."""
    from_column, to_column = glyph_columns(lines)[0]
    height = (len(lines) - 1) * ROW_PITCH + INK_HEIGHT
    scale = (side - 2) / height
    width = (to_column - from_column) * CELL_WIDTH * scale
    left = (side - width) / 2
    body = render_glyphs(
        lines,
        from_column=from_column,
        to_column=to_column,
        x_offset=left,
        y_offset=1.0,
        scale=scale,
    )
    paint = f'<g fill="{color}">' if color else f'{gradient_defs(tokens, side)}<g fill="url(#g)">'
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {number(side)} {number(side)}" role="img" aria-labelledby="title">'
        '<title id="title">r10n R</title>'
        f"{paint}{body}</g></svg>\n"
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
    """Regenerate the native CLI logo, docs wordmark, and R favicon."""
    lines, tokens = read_logo()
    wordmark = render_wordmark(lines, tokens)
    favicon = render_favicon(lines, tokens)
    ink = tokens["doc_ink"]
    dark_wordmark = render_wordmark(lines, tokens, color=ink)
    dark_favicon = render_favicon(lines, tokens, color=ink)
    DOC_ASSETS.mkdir(parents=True, exist_ok=True)
    ASSETS_BRAND.mkdir(parents=True, exist_ok=True)
    RUNTIME_BRAND.mkdir(parents=True, exist_ok=True)
    (RUNTIME_BRAND / "logo.txt").write_text(
        WORDMARK_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (ASSETS_BRAND / "r10n-wordmark.svg").write_text(wordmark, encoding="utf-8")
    (ASSETS_BRAND / "r10n-favicon.svg").write_text(favicon, encoding="utf-8")
    (ASSETS_BRAND / "r10n-wordmark-dark.svg").write_text(dark_wordmark, encoding="utf-8")
    (ASSETS_BRAND / "r10n-favicon-dark.svg").write_text(dark_favicon, encoding="utf-8")
    (DOC_ASSETS / "r10n.svg").write_text(wordmark, encoding="utf-8")
    (DOC_ASSETS / "r10n-dark.svg").write_text(dark_wordmark, encoding="utf-8")
    (DOC_ASSETS / "favicon.svg").write_text(favicon, encoding="utf-8")
    (DOC_ASSETS / "favicon-dark.svg").write_text(dark_favicon, encoding="utf-8")
    update_installer_banner(lines)


if __name__ == "__main__":
    main()
