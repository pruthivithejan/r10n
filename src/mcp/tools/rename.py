"""MCP tool for batch renaming files."""

from src.automations.rename_files import rename_files as _rename_files
from src.mcp.server import mcp


@mcp.tool()
def rename_files(
    input_directory: str,
    pattern: str | None = None,
    prefix: str | None = None,
    suffix: str | None = None,
    replace_from: str | None = None,
    replace_to: str | None = None,
    add_date: bool = False,
    add_sequence: bool = False,
    lowercase: bool = False,
    uppercase: bool = False,
    recursive: bool = False,
    dry_run: bool = False,
    file_pattern: str = "*",
) -> dict:
    """Batch rename files using patterns, prefixes, suffixes, and transformations.

    Args:
        input_directory: Directory containing files to rename.
        pattern: Rename pattern with placeholders: {name}, {ext}, {date}, {sequence}.
        prefix: Add prefix to filenames.
        suffix: Add suffix before file extension.
        replace_from: Text to find in filenames.
        replace_to: Replacement text.
        add_date: Prepend current date to filenames.
        add_sequence: Add sequence numbers to filenames.
        lowercase: Convert filenames to lowercase.
        uppercase: Convert filenames to uppercase.
        recursive: Process subdirectories.
        dry_run: Preview changes without renaming.
        file_pattern: Glob pattern to match files (e.g., "*.jpg").
    """
    try:
        result = _rename_files(
            input_directory=input_directory,
            pattern=pattern,
            prefix=prefix,
            suffix=suffix,
            replace_from=replace_from,
            replace_to=replace_to or "",
            add_date=add_date,
            add_sequence=add_sequence,
            lowercase=lowercase,
            uppercase=uppercase,
            recursive=recursive,
            dry_run=dry_run,
            file_pattern=file_pattern,
        )
        return {
            "success": result.success,
            "total_files": result.total_files,
            "renamed": result.renamed,
            "skipped": result.skipped,
            "errors": result.errors,
            "renamed_files": result.renamed_files,
        }
    except Exception as e:
        return {"error": str(e)}
