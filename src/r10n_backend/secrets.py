"""OS credential-store access for r10n's named SMTP profiles."""

from __future__ import annotations

import os
import re

SERVICE = "r10n:smtp"


def _environment_name(profile: str) -> str:
    """Map a profile name to its explicit per-process credential override."""
    safe_name = re.sub(r"[^A-Za-z0-9]", "_", profile).upper()
    return f"R10N_SMTP_{safe_name}_PASSWORD"


def get_secret(profile: str) -> str | None:
    """Read an SMTP password from a one-run environment override or keyring."""
    if value := os.getenv(_environment_name(profile)):
        return value
    try:
        import keyring
    except ImportError:
        return None
    backend = keyring.get_keyring()
    if getattr(backend, "priority", 0) <= 0:
        return None
    return keyring.get_password(SERVICE, profile)


def set_secret(profile: str, secret: str) -> None:
    """Store a password in the platform's secure credential service."""
    if not profile or not secret:
        raise ValueError("An SMTP profile name and non-empty password are required")
    try:
        import keyring
    except ImportError as error:
        raise RuntimeError("No secure operating system credential store is available") from error
    backend = keyring.get_keyring()
    if getattr(backend, "priority", 0) <= 0:
        raise RuntimeError(
            "No secure operating system credential store is available; "
            "set a per-process R10N_SMTP_<PROFILE>_PASSWORD variable instead"
        )
    keyring.set_password(SERVICE, profile, secret)


def delete_secret(profile: str) -> None:
    """Remove a profile password from the OS credential service."""
    try:
        import keyring
        from keyring.errors import PasswordDeleteError
    except ImportError:
        return
    backend = keyring.get_keyring()
    if getattr(backend, "priority", 0) <= 0:
        return
    try:
        keyring.delete_password(SERVICE, profile)
    except PasswordDeleteError:
        pass
