"""System settings are lazy, validated, and never contain SMTP passwords."""

import os
import stat

import pytest

from r10n_backend.settings import PDFProfile, Settings, load_settings, save_settings, settings_path


def test_loading_defaults_does_not_create_config_directories(tmp_path, monkeypatch):
    destination = tmp_path / "settings"
    monkeypatch.setenv("R10N_CONFIG_DIR", str(destination))

    settings = load_settings()

    assert settings.theme == "dark"
    assert settings.smtp_profiles == {}
    assert not destination.exists()


def test_settings_save_is_private_and_contains_only_non_secret_profiles(tmp_path, monkeypatch):
    destination = tmp_path / "settings"
    monkeypatch.setenv("R10N_CONFIG_DIR", str(destination))
    settings = Settings(
        accessible=True,
        output_directory=str(tmp_path / "outputs"),
        active_pdf_profile="certificate",
        pdf_profiles={
            "certificate": PDFProfile(
                template_pdf=str(tmp_path / "template.pdf"),
                output_directory=str(tmp_path / "outputs"),
                fields={
                    "name": {
                        "x": 100,
                        "y": 200,
                        "font_size": 20,
                        "alignment": "center",
                    }
                },
            )
        },
    )

    path = save_settings(settings)

    assert path == settings_path()
    assert load_settings().accessible is True
    assert b"password" not in path.read_bytes().lower()
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_invalid_or_future_settings_are_not_silently_reset(tmp_path, monkeypatch):
    destination = tmp_path / "settings"
    destination.mkdir()
    monkeypatch.setenv("R10N_CONFIG_DIR", str(destination))
    path = settings_path()
    path.write_text('{"version": 99, "theme":"dark"}', encoding="utf-8")

    with pytest.raises(ValueError, match="newer than"):
        load_settings()

    path.write_text(
        '{"version":1,"smtp_profiles":{"work":{"password":"plaintext"}}}', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="extra_forbidden"):
        load_settings()
