"""Validated, per-user settings shared with the native Go frontend."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from platformdirs import user_config_path
from pydantic import BaseModel, ConfigDict, Field


class SMTPProfile(BaseModel):
    """Non-secret connection and message settings for an SMTP account."""

    model_config = ConfigDict(extra="forbid")

    smtp_server: str
    smtp_port: int = Field(ge=1, le=65535)
    email: str
    subject: str
    use_tls: bool = True


class PDFField(BaseModel):
    """Position and typography for one personalized PDF field."""

    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0)
    y: float = Field(ge=0)
    font_size: float = Field(gt=0)
    font_weight: int | Literal["bold", "normal"] = 400
    alignment: Literal["left", "center", "right"] = "left"
    color: tuple[float, float, float] = (0, 0, 0)
    max_width: float | None = Field(default=None, gt=0)
    font_path: str | None = None


class PDFProfile(BaseModel):
    """Saved PDF template settings containing no credentials or source data."""

    model_config = ConfigDict(extra="forbid")

    template_pdf: str = Field(min_length=1)
    output_directory: str = Field(min_length=1)
    font_family: str = "Helvetica"
    fields: dict[str, PDFField] = Field(min_length=1)


class Settings(BaseModel):
    """Versioned r10n preferences and reusable, non-secret presets."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    theme: Literal["dark", "light", "system"] = "dark"
    accessible: bool = False
    reduced_motion: bool = False
    output_directory: str = ""
    active_smtp_profile: str = ""
    smtp_profiles: dict[str, SMTPProfile] = Field(default_factory=dict)
    active_pdf_profile: str = ""
    pdf_profiles: dict[str, PDFProfile] = Field(default_factory=dict)


def settings_directory() -> Path:
    """Resolve the same system configuration path as the native frontend."""
    override = os.getenv("R10N_CONFIG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(user_config_path(appname="r10n", appauthor=False))


def settings_path() -> Path:
    """Return the system settings file path without creating it."""
    return settings_directory() / "config.json"


def load_settings() -> Settings:
    """Load validated settings, returning built-in defaults when absent."""
    path = settings_path()
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Settings()
    try:
        settings = Settings.model_validate_json(content)
    except Exception as error:
        raise ValueError(f"Invalid r10n settings at {path}: {error}") from error
    if settings.version > 1:
        raise ValueError(f"Settings version {settings.version} is newer than this backend supports")
    if settings.active_smtp_profile and settings.active_smtp_profile not in settings.smtp_profiles:
        raise ValueError("The active SMTP profile does not exist in r10n settings")
    if settings.active_pdf_profile and settings.active_pdf_profile not in settings.pdf_profiles:
        raise ValueError("The active PDF profile does not exist in r10n settings")
    return settings


def save_settings(settings: Settings) -> Path:
    """Validate and atomically save owner-private system settings."""
    validated = Settings.model_validate(settings.model_dump(mode="python"))
    if (
        validated.active_smtp_profile
        and validated.active_smtp_profile not in validated.smtp_profiles
    ):
        raise ValueError("The active SMTP profile does not exist in r10n settings")
    if validated.active_pdf_profile and validated.active_pdf_profile not in validated.pdf_profiles:
        raise ValueError("The active PDF profile does not exist in r10n settings")
    destination = settings_path()
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        destination.parent.chmod(0o700)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".r10n-config-",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            if os.name == "posix":
                os.fchmod(temporary.fileno(), 0o600)
            json.dump(validated.model_dump(mode="json"), temporary, indent=2)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
        if os.name == "posix":
            destination.chmod(0o600)
        return destination
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
