"""
Utility functions for automation modules
Handles configuration loading and path resolution for both old and new structures
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def get_workspace_path(category: str, subfolder: str = "") -> Path:
    """
    Get the appropriate workspace path, supporting both old and new structures.

    Args:
        category: The category (e.g., 'inputs', 'outputs', 'configs')
        subfolder: Optional subfolder (e.g., 'email', 'contacts')

    Returns:
        Path object for the requested directory
    """
    # Try new structure first
    new_path = Path("workspace") / category
    if subfolder:
        new_path = new_path / subfolder

    if new_path.exists() or Path("workspace").exists():
        # Use new structure
        new_path.mkdir(parents=True, exist_ok=True)
        return new_path

    # Fall back to old structure
    old_mappings = {
        "inputs/email": "data/emails",
        "inputs/contacts": "data/phone_numbers",
        "inputs/certificates": "data/certificates",
        "outputs/email": "data/emails/sent",
        "outputs/contacts": "data/phone_numbers",
        "outputs/certificates": "data/certificates/output",
        "outputs/images": "data/images/optimized",
        "configs": "data",
    }

    key = f"{category}/{subfolder}" if subfolder else category
    old_path = Path(old_mappings.get(key, f"data/{subfolder or category}"))
    old_path.mkdir(parents=True, exist_ok=True)
    return old_path


def load_config(
    config_path: Optional[str] = None,
    default_config: Optional[Dict[str, Any]] = None,
    category: str = "",
) -> Dict[str, Any]:
    """
    Load configuration from file, with fallback to defaults.

    Args:
        config_path: Path to configuration file
        default_config: Default configuration dictionary
        category: Category for finding default config (e.g., 'email', 'certificates')

    Returns:
        Configuration dictionary
    """
    config = default_config or {}

    if config_path:
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
            return config

    # Try to find config in standard locations
    possible_paths = []

    if category:
        # New structure
        possible_paths.append(Path("workspace/configs") / f"{category}.json")
        # Default configs
        possible_paths.append(Path("configs") / f"{category}.default.json")
        # Old structure
        possible_paths.append(Path("data") / f"{category}_config.json")

    for path in possible_paths:
        if path.exists():
            with open(path) as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
            return config

    return config


def resolve_path(
    path: str, base_dir: Optional[Path] = None, category: str = "", subfolder: str = ""
) -> Path:
    """
    Resolve a path, handling both absolute and relative paths.

    Args:
        path: The path to resolve
        base_dir: Base directory for relative paths
        category: Category for workspace paths (e.g., 'inputs', 'outputs')
        subfolder: Subfolder within category

    Returns:
        Resolved Path object
    """
    path_obj = Path(path)

    # If absolute path, return as is
    if path_obj.is_absolute():
        return path_obj

    # If it's a simple filename and we have category info
    if len(path_obj.parts) == 1 and category:
        workspace_dir = get_workspace_path(category, subfolder)
        return workspace_dir / path

    # If we have a base directory
    if base_dir:
        return base_dir / path

    # Return as is (relative to current directory)
    return path_obj


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to directory

    Returns:
        The path object
    """
    if path.suffix:  # It's a file
        path.parent.mkdir(parents=True, exist_ok=True)
    else:  # It's a directory
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable, checking both system env and workspace .env.

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        Environment variable value or default
    """
    # Check system environment first
    value = os.getenv(key)
    if value:
        return value

    # Try to load from workspace .env
    env_path = Path("workspace/.env")
    if env_path.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path)
            value = os.getenv(key, default)
        except ImportError:
            # dotenv not available, use default
            value = default
    else:
        value = default

    return value


def format_results(
    success: bool,
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Format automation results in a consistent way.

    Args:
        success: Whether the operation was successful
        message: Success or error message
        data: Additional data to include
        error: Error details if failed

    Returns:
        Formatted results dictionary
    """
    result = {"success": success, "message": message}

    if data:
        result.update(data)

    if error:
        result["error"] = error

    return result


def migrate_config(
    old_path: Path, new_path: Path, mappings: Optional[Dict[str, str]] = None
) -> bool:
    """
    Migrate configuration from old structure to new structure.

    Args:
        old_path: Path to old configuration
        new_path: Path to new configuration
        mappings: Optional key mappings for config transformation

    Returns:
        True if migration successful
    """
    if not old_path.exists():
        return False

    try:
        with open(old_path) as f:
            old_config = json.load(f)

        if mappings:
            new_config = {}
            for old_key, new_key in mappings.items():
                if old_key in old_config:
                    new_config[new_key] = old_config[old_key]
            # Include unmapped keys as well
            for key, value in old_config.items():
                if key not in mappings:
                    new_config[key] = value
        else:
            new_config = old_config

        new_path.parent.mkdir(parents=True, exist_ok=True)
        with open(new_path, "w") as f:
            json.dump(new_config, f, indent=2)

        return True
    except Exception:
        return False
