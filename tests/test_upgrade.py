"""Tests for binary upgrade helpers in CLI."""

import ssl
import tarfile
import urllib.error

import pytest

from src import cli


class TestDetectPlatformAssetName:
    """Test asset name resolution for current platform."""

    def test_linux_x86_64(self, monkeypatch):
        """Maps Linux x86_64 to expected asset name."""
        monkeypatch.setattr(cli.platform, "system", lambda: "Linux")
        monkeypatch.setattr(cli.platform, "machine", lambda: "x86_64")
        assert cli.detect_platform_asset_name() == "r10n-linux-x86_64.tar.gz"

    def test_darwin_arm64_alias(self, monkeypatch):
        """Maps Darwin aarch64 alias to arm64 asset name."""
        monkeypatch.setattr(cli.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(cli.platform, "machine", lambda: "aarch64")
        assert cli.detect_platform_asset_name() == "r10n-macos-arm64.tar.gz"

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


class TestUpgradeNetworking:
    """Test upgrade network helper behavior."""

    def test_fetch_release_data_uses_https_context(self, monkeypatch):
        """GitHub API requests should use the hardened HTTPS context."""
        sentinel_context = object()
        captured = {}

        class FakeResponse:
            """Small context manager for urlopen responses."""

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"tag_name":"v0.9.0","assets":[]}'

        def fake_urlopen(request, timeout, context):
            captured["timeout"] = timeout
            captured["context"] = context
            captured["url"] = request.full_url
            return FakeResponse()

        monkeypatch.setattr(cli, "create_https_context", lambda: sentinel_context)
        monkeypatch.setattr(cli.urllib.request, "urlopen", fake_urlopen)

        result = cli.fetch_release_data(timeout=7)

        assert result["tag_name"] == "v0.9.0"
        assert captured["timeout"] == 7
        assert captured["context"] is sentinel_context
        assert captured["url"].endswith("/releases/latest")

    def test_format_network_error_explains_certificate_failures(self):
        """Certificate verification failures should get a concrete recovery hint."""
        reason = ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED")
        message = cli.format_network_error(urllib.error.URLError(reason))

        assert "TLS certificate verification failed" in message
        assert "SSL_CERT_FILE" in message

    def test_extract_release_archive_returns_app_dir(self, tmp_path):
        """Release archives should extract to a runnable onedir app layout."""
        app_dir = tmp_path / "build" / "r10n"
        app_dir.mkdir(parents=True)
        executable = app_dir / "r10n"
        executable.write_text("#!/bin/sh\n", encoding="utf-8")

        archive_path = tmp_path / "r10n-linux-x86_64.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(app_dir, arcname="r10n")

        extracted = cli.extract_release_archive(archive_path, tmp_path / "extract")

        assert extracted == tmp_path / "extract" / "r10n"
        assert (extracted / "r10n").exists()

    def test_extract_release_archive_rejects_unsafe_paths(self, tmp_path):
        """Archives cannot write outside the extraction directory."""
        archive_path = tmp_path / "unsafe.tar.gz"
        payload = tmp_path / "payload.txt"
        payload.write_text("bad", encoding="utf-8")
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(payload, arcname="../payload.txt")

        with pytest.raises(RuntimeError, match="Unsafe archive path"):
            cli.extract_release_archive(archive_path, tmp_path / "extract")
