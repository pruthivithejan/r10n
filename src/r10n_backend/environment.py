"""Workspace environment loading shared by backend operations."""

from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    """Load the caller's local/.env without overriding process environment."""
    env_path = Path("local/.env")
    if env_path.is_file():
        load_dotenv(env_path, override=False)
