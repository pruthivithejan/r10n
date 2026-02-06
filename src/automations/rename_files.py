"""
File Renamer automation.

Batch rename files with patterns, prefixes, suffixes, dates, and sequences.
Supports preview mode (dry run) before applying changes.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class RenameConfig:
    """Configuration for file renaming operations."""

    input_directory: str
    pattern: str | None = None
    prefix: str | None = None
    suffix: str | None = None
    replace_from: str | None = None
    replace_to: str | None = None
    add_date: bool = False
    add_sequence: bool = False
    sequence_start: int = 1
    sequence_padding: int = 3
    lowercase: bool = False
    uppercase: bool = False
    recursive: bool = False
    dry_run: bool = False
    file_pattern: str = "*"
    date_format: str = "%Y%m%d"


@dataclass
class RenameResult:
    """Result of a file renaming operation."""

    success: bool
    total_files: int
    renamed: int
    skipped: int
    errors: list[dict[str, Any]] = field(default_factory=list)
    renamed_files: list[dict[str, str]] = field(default_factory=list)


# Characters not allowed in filenames on various systems
INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(filename: str, replace_spaces: bool = False) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.

    Args:
        filename: The filename to sanitize
        replace_spaces: If True, replace spaces with underscores

    Returns:
        Sanitized filename
    """
    # Strip leading/trailing whitespace from entire filename first
    filename = filename.strip()

    # Split name and extension
    path = Path(filename)
    name = path.stem
    ext = path.suffix

    # Strip leading/trailing whitespace from name
    name = name.strip()

    # Remove invalid characters
    name = INVALID_CHARS.sub("", name)

    # Handle leading dots (but preserve extension dots)
    while name.startswith(".") and len(name) > 1:
        name = name[1:]

    # Replace spaces if requested
    if replace_spaces:
        name = name.replace(" ", "_")

    # If name is empty after sanitization, use a default
    if not name:
        name = "unnamed"

    return name + ext


def apply_pattern(
    original_name: str,
    pattern: str | None = None,
    date_format: str = "%Y%m%d",
    datetime_format: str = "%Y%m%d_%H%M%S",
    sequence: int | None = None,
    sequence_padding: int = 3,
) -> str:
    """
    Apply a naming pattern to a filename.

    Supported placeholders:
    - {name}: Filename without extension
    - {ext}: File extension (without dot)
    - {original}: Full original filename
    - {date}: Current date
    - {datetime}: Current datetime
    - {sequence}: Sequence number (if provided)

    Args:
        original_name: Original filename
        pattern: Pattern string with placeholders
        date_format: Format for {date} placeholder
        datetime_format: Format for {datetime} placeholder
        sequence: Sequence number for {sequence} placeholder
        sequence_padding: Zero-padding width for sequence

    Returns:
        New filename with pattern applied
    """
    path = Path(original_name)
    name = path.stem
    ext = path.suffix.lstrip(".")

    if pattern is None:
        return original_name

    now = datetime.now()

    result = pattern

    # Replace placeholders
    result = result.replace("{name}", name)
    result = result.replace("{ext}", ext)
    result = result.replace("{original}", original_name)
    result = result.replace("{date}", now.strftime(date_format))
    result = result.replace("{datetime}", now.strftime(datetime_format))

    if sequence is not None:
        result = result.replace("{sequence}", str(sequence).zfill(sequence_padding))

    # Add extension back if not in pattern and {original} not used
    # (since {original} already includes the extension)
    if "{ext}" not in pattern and "{original}" not in pattern and ext:
        result = result + "." + ext

    return result


class FileRenamer:
    """Class for batch file renaming operations."""

    def __init__(self, config: RenameConfig):
        """
        Initialize the FileRenamer.

        Args:
            config: Configuration for renaming operations
        """
        self.config = config

    def get_files(self) -> list[Path]:
        """
        Get list of files to rename based on configuration.

        Returns:
            List of Path objects for files to rename
        """
        input_path = Path(self.config.input_directory)

        if not input_path.exists():
            raise FileNotFoundError(f"Directory not found: {self.config.input_directory}")

        if self.config.recursive:
            pattern = f"**/{self.config.file_pattern}"
        else:
            pattern = self.config.file_pattern

        files = []
        for path in input_path.glob(pattern):
            if path.is_file():
                files.append(path)

        # Sort for consistent ordering
        files.sort()
        return files

    def generate_new_name(self, file_path: Path, sequence: int) -> str:
        """
        Generate new filename based on configuration.

        Args:
            file_path: Original file path
            sequence: Sequence number for this file

        Returns:
            New filename (not full path)
        """
        original_name = file_path.name
        new_name = original_name

        # Apply pattern if specified
        if self.config.pattern:
            new_name = apply_pattern(
                original_name,
                pattern=self.config.pattern,
                date_format=self.config.date_format,
                sequence=sequence,
                sequence_padding=self.config.sequence_padding,
            )
        else:
            # Apply individual transformations
            path = Path(new_name)
            stem = path.stem
            ext = path.suffix

            # Replace text
            if self.config.replace_from is not None:
                replace_to = self.config.replace_to if self.config.replace_to is not None else ""
                stem = stem.replace(self.config.replace_from, replace_to)

            # Add prefix
            if self.config.prefix:
                stem = self.config.prefix + stem

            # Add suffix
            if self.config.suffix:
                stem = stem + self.config.suffix

            # Add sequence
            if self.config.add_sequence:
                seq_str = str(sequence).zfill(self.config.sequence_padding)
                stem = f"{seq_str}_{stem}"

            # Add date
            if self.config.add_date:
                date_str = datetime.now().strftime("%Y%m%d")
                stem = f"{date_str}_{stem}"

            new_name = stem + ext

        # Apply case transformation
        if self.config.lowercase:
            new_name = new_name.lower()
        elif self.config.uppercase:
            new_name = new_name.upper()

        return new_name

    def rename(self) -> RenameResult:
        """
        Perform the rename operation.

        Returns:
            RenameResult with operation details
        """
        files = self.get_files()
        result = RenameResult(
            success=True,
            total_files=len(files),
            renamed=0,
            skipped=0,
            errors=[],
            renamed_files=[],
        )

        if not files:
            return result

        sequence = self.config.sequence_start

        for file_path in files:
            old_name = file_path.name
            new_name = self.generate_new_name(file_path, sequence)
            new_path = file_path.parent / new_name

            # Skip if name hasn't changed
            if old_name == new_name:
                result.skipped += 1
                sequence += 1
                continue

            # Check for conflicts (but allow case-only changes on same file)
            # On case-insensitive filesystems, new_path.exists() returns True
            # even for case changes, so we check if it's actually the same file
            is_same_file = new_path.exists() and file_path.resolve() == new_path.resolve()
            is_case_only_change = old_name.lower() == new_name.lower()

            if new_path.exists() and not is_same_file and not is_case_only_change:
                result.skipped += 1
                result.errors.append(
                    {
                        "file": old_name,
                        "error": f"Target already exists: {new_name}",
                    }
                )
                sequence += 1
                continue

            # Record the rename
            result.renamed_files.append(
                {
                    "old": old_name,
                    "new": new_name,
                }
            )

            # Actually rename if not dry run
            if not self.config.dry_run:
                try:
                    file_path.rename(new_path)
                    result.renamed += 1
                except OSError as e:
                    result.errors.append(
                        {
                            "file": old_name,
                            "error": str(e),
                        }
                    )
                    result.success = False
            else:
                result.renamed += 1

            sequence += 1

        if result.errors:
            result.success = False

        return result


def rename_files(
    input_directory: str,
    pattern: str | None = None,
    prefix: str | None = None,
    suffix: str | None = None,
    replace_from: str | None = None,
    replace_to: str | None = None,
    add_date: bool = False,
    add_sequence: bool = False,
    sequence_start: int = 1,
    sequence_padding: int = 3,
    lowercase: bool = False,
    uppercase: bool = False,
    recursive: bool = False,
    dry_run: bool = False,
    file_pattern: str = "*",
    date_format: str = "%Y%m%d",
) -> RenameResult:
    """
    Rename files in a directory with various transformations.

    Args:
        input_directory: Directory containing files to rename
        pattern: Naming pattern with placeholders ({name}, {date}, {sequence}, etc.)
        prefix: Prefix to add to filenames
        suffix: Suffix to add before extension
        replace_from: Text to replace in filenames
        replace_to: Replacement text
        add_date: Add current date to filename
        add_sequence: Add sequence number to filename
        sequence_start: Starting sequence number
        sequence_padding: Zero-padding for sequence numbers
        lowercase: Convert filename to lowercase
        uppercase: Convert filename to uppercase
        recursive: Process subdirectories
        dry_run: Preview changes without applying
        file_pattern: Glob pattern for files to process
        date_format: Format for date in filenames

    Returns:
        RenameResult with operation details

    Raises:
        FileNotFoundError: If input directory doesn't exist
    """
    input_path = Path(input_directory)
    if not input_path.exists():
        raise FileNotFoundError(f"Directory not found: {input_directory}")

    config = RenameConfig(
        input_directory=input_directory,
        pattern=pattern,
        prefix=prefix,
        suffix=suffix,
        replace_from=replace_from,
        replace_to=replace_to,
        add_date=add_date,
        add_sequence=add_sequence,
        sequence_start=sequence_start,
        sequence_padding=sequence_padding,
        lowercase=lowercase,
        uppercase=uppercase,
        recursive=recursive,
        dry_run=dry_run,
        file_pattern=file_pattern,
        date_format=date_format,
    )

    renamer = FileRenamer(config)
    return renamer.rename()


def preview_rename(
    input_directory: str,
    pattern: str | None = None,
    prefix: str | None = None,
    suffix: str | None = None,
    replace_from: str | None = None,
    replace_to: str | None = None,
    add_date: bool = False,
    add_sequence: bool = False,
    sequence_start: int = 1,
    sequence_padding: int = 3,
    lowercase: bool = False,
    uppercase: bool = False,
    recursive: bool = False,
    file_pattern: str = "*",
    date_format: str = "%Y%m%d",
) -> list[dict[str, str]]:
    """
    Preview rename operations without applying changes.

    Args:
        Same as rename_files

    Returns:
        List of dicts with 'old' and 'new' filenames
    """
    result = rename_files(
        input_directory=input_directory,
        pattern=pattern,
        prefix=prefix,
        suffix=suffix,
        replace_from=replace_from,
        replace_to=replace_to,
        add_date=add_date,
        add_sequence=add_sequence,
        sequence_start=sequence_start,
        sequence_padding=sequence_padding,
        lowercase=lowercase,
        uppercase=uppercase,
        recursive=recursive,
        dry_run=True,  # Always dry run for preview
        file_pattern=file_pattern,
        date_format=date_format,
    )

    return result.renamed_files


if __name__ == "__main__":
    print("File Renamer automation")
    print("Use the main CLI: uv run r10n rename")
