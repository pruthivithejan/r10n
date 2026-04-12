"""Tests for binary upgrade helpers in CLI."""

import pytest

from src import cli


class TestDetectPlatformAssetName:
    """Test asset name resolution for current platform."""

    def test_linux_x86_64(self, monkeypatch):
        """Maps Linux x86_64 to expected asset name."""
        monkeypatch.setattr(cli.platform, "system", lambda: "Linux")
        monkeypatch.setattr(cli.platform, "machine", lambda: "x86_64")
        assert cli.detect_platform_asset_name() == "r10n-linux-x86_64"

    def test_darwin_arm64_alias(self, monkeypatch):
        """Maps Darwin aarch64 alias to arm64 asset name."""
        monkeypatch.setattr(cli.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(cli.platform, "machine", lambda: "aarch64")
        assert cli.detect_platform_asset_name() == "r10n-macos-arm64"

    def test_darwin_x86_64_is_unsupported(self, monkeypatch):
        """macOS Intel is not built, so it must raise unsupported platform."""
        monkeypatch.setattr(cli.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(cli.platform, "machine", lambda: "x86_64")
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            cli.detect_platform_asset_name()

    def test_windows_amd64_alias(self, monkeypatch):
        """Maps Windows amd64 alias to .exe asset name."""
        monkeypatch.setattr(cli.platform, "system", lambda: "Windows")
        monkeypatch.setattr(cli.platform, "machine", lambda: "amd64")
        assert cli.detect_platform_asset_name() == "r10n-windows-x86_64.exe"

    def test_unsupported_platform_raises(self, monkeypatch):
        """Unsupported platform combinations raise a runtime error."""
        monkeypatch.setattr(cli.platform, "system", lambda: "Linux")
        monkeypatch.setattr(cli.platform, "machine", lambda: "arm64")
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            cli.detect_platform_asset_name()


class TestVersionHelpers:
    """Test semantic version parsing and comparison."""

    def test_normalize_version_strips_v(self):
        """Removes v prefix and parses numeric parts."""
        assert cli.normalize_version("v2.10.3") == (2, 10, 3)

    def test_is_newer_version(self):
        """Compares numeric version parts correctly."""
        assert cli.is_newer_version("2.1.0", "2.0.9") is True
        assert cli.is_newer_version("2.0.0", "2.0.0") is False
        assert cli.is_newer_version("1.9.9", "2.0.0") is False


class TestChecksumParsing:
    """Test SHA-256 sum parsing."""

    def test_parse_sha256_sums(self):
        """Parses standard sha256sum file content."""
        content = "abc123  r10n-linux-x86_64\ndef456 *r10n-macos-arm64\n\n# comment\n"
        result = cli.parse_sha256_sums(content)

        assert result["r10n-linux-x86_64"] == "abc123"
        assert result["r10n-macos-arm64"] == "def456"
