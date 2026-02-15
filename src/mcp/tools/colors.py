"""MCP tool for converting CSS colors to oklch() format."""

from src.automations.convert_colors import convert_colors as _convert_colors
from src.mcp.server import mcp


@mcp.tool()
def convert_colors(
    path: str,
    file: str | None = None,
    dry_run: bool = False,
    no_backup: bool = False,
    excludes: list[str] | None = None,
) -> dict:
    """Convert CSS color codes (hex, rgb, hsl, named) to oklch() format.

    Args:
        path: Directory containing CSS files to process.
        file: Single CSS file to process (overrides path).
        dry_run: Preview changes without modifying files.
        no_backup: Skip creating .bak backup files.
        excludes: Additional directory names to exclude from search.
    """
    try:
        return _convert_colors(
            path=path,
            file=file,
            dry_run=dry_run,
            no_backup=no_backup,
            excludes=excludes,
        )
    except Exception as e:
        return {"error": str(e)}
