from pathlib import Path


def ensure_directory(path: str | Path) -> Path:
    """
    Ensure a directory exists, create it if it doesn't.

    Args:
        path (Union[str, Path]): Directory path

    Returns:
        Path: Path object of the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_files_by_extension(directory: str | Path, extension: str) -> list[Path]:
    """
    Get all files with a specific extension in a directory.

    Args:
        directory (Union[str, Path]): Directory to search in
        extension (str): File extension to look for (with or without dot)

    Returns:
        List[Path]: List of matching file paths
    """
    if not extension.startswith("."):
        extension = f".{extension}"

    directory = Path(directory)
    return list(directory.glob(f"**/*{extension}"))
