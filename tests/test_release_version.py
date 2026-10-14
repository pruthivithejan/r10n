"""Tests for the tag-backed release version helper."""

from pathlib import Path

import pytest

from scripts.release_version import (
    Version,
    _replace_version,
    next_release_version,
    read_declared_versions,
    update_version_files,
)


class TestVersion:
    """Test semantic version parsing and bumping."""

    def test_parse_accepts_optional_v_prefix(self):
        assert Version.parse("v0.11.1") == Version(0, 11, 1)

    @pytest.mark.parametrize(
        ("kind", "expected"),
        [("patch", "0.11.2"), ("minor", "0.12.0"), ("major", "1.0.0")],
    )
    def test_bump(self, kind, expected):
        assert str(Version(0, 11, 1).bump(kind)) == expected

    def test_parse_rejects_non_stable_version(self):
        with pytest.raises(ValueError, match="Unsupported version"):
            Version.parse("0.11")


def write_version_fixture(root: Path, version: str) -> None:
    """Write the minimal synchronized version fixture used by helper tests."""
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "r10n"\nversion = "{version}"\n', encoding="utf-8"
    )
    (root / "uv.lock").write_text(
        f'[[package]]\nname = "r10n"\nversion = "{version}"\n',
        encoding="utf-8",
    )


def test_read_declared_versions(tmp_path):
    """The generated lockfile agrees with the single project version source."""
    write_version_fixture(tmp_path, "0.11.1")

    assert read_declared_versions(tmp_path) == {
        "pyproject.toml": Version(0, 11, 1),
        "uv.lock": Version(0, 11, 1),
    }


def test_read_declared_versions_rejects_mismatch(tmp_path):
    """Mismatched metadata cannot silently produce a release."""
    write_version_fixture(tmp_path, "0.11.1")
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "r10n"\nversion = "0.11.0"\n', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Version mismatch"):
        read_declared_versions(tmp_path)


def test_next_release_uses_declared_version_when_it_is_ahead_of_tags(tmp_path, monkeypatch):
    """An untagged prior release is still used as the patch baseline."""
    write_version_fixture(tmp_path, "0.11.1")
    monkeypatch.setattr(
        "scripts.release_version.list_release_tags",
        lambda root: [Version(0, 10, 0)],
    )

    assert next_release_version("patch", tmp_path) == Version(0, 11, 2)


def test_replace_version_requires_expected_file_shape():
    """Version updates fail closed when a declaration is absent."""
    with pytest.raises(ValueError, match="Could not find exactly one"):
        _replace_version(
            'name = "r10n"\n',
            r'^(?P<prefix>version = ")(?P<old>[^"]+)(?P<suffix>")$',
            Version(0, 11, 2),
            "fixture",
        )


def test_update_regenerates_lock_instead_of_editing_it(tmp_path, monkeypatch):
    """Update only project metadata by hand; uv is the lockfile writer."""
    write_version_fixture(tmp_path, "0.11.1")
    with (tmp_path / "pyproject.toml").open("a") as file:
        file.write('\n[tool.fixture]\nversion = "9.0.0"\n')

    def fake_run(command, **kwargs):
        assert command == ["uv", "lock"]
        assert kwargs["cwd"] == tmp_path
        assert 'version = "0.11.2"' in (tmp_path / "pyproject.toml").read_text()
        assert 'version = "0.11.1"' in (tmp_path / "uv.lock").read_text()
        (tmp_path / "uv.lock").write_text('[[package]]\nname = "r10n"\nversion = "0.11.2"\n')

    monkeypatch.setattr("scripts.release_version.subprocess.run", fake_run)
    update_version_files(Version(0, 11, 2), tmp_path)
    assert 'version = "9.0.0"' in (tmp_path / "pyproject.toml").read_text()
