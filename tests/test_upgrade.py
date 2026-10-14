"""Tests for binary upgrade helpers in CLI."""

import ssl
import tarfile
import urllib.error
from pathlib import Path

import pytest

from src import cli


class TestNativeExecutableResolution:
    """Keep upgrades pointed at the native app, not its Python backend."""

    def test_native_env_overrides_backend_argv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Native executable and launcher overrides take priority over Python argv."""
        executable = tmp_path / "app" / "r10n"
        executable.parent.mkdir()
        executable.write_bytes(b"\x7fELF")
        command = tmp_path / "r10n"
        monkeypatch.setenv("R10N_EXECUTABLE", str(executable))
        monkeypatch.setenv("R10N_COMMAND_PATH", str(command))
        monkeypatch.setattr(cli.sys, "argv", [str(tmp_path / "r10n-python")])
        monkeypatch.setattr(cli.shutil, "which", lambda _: None)
        assert cli.resolve_current_executable_path() == executable
        assert cli.resolve_command_entry_path() == command
        assert cli.is_standalone_binary(cli.resolve_current_executable_path())

    @pytest.mark.skipif(cli.os.name == "nt", reason="Unix launcher symlink layout")
    def test_override_preserves_launcher_symlink(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The command path keeps the symlink while the native path resolves it."""
        app = tmp_path / ".r10n"
        app.mkdir()
        executable = app / "r10n"
        executable.write_bytes(b"\x7fELF")
        command = tmp_path / "r10n"
        command.symlink_to(executable)
        monkeypatch.setenv("R10N_EXECUTABLE", str(command))
        monkeypatch.setenv("R10N_COMMAND_PATH", str(command))
        assert cli.resolve_current_executable_path() == executable
        assert cli.resolve_command_entry_path() == command

    def test_empty_overrides_keep_legacy_resolution(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty overrides retain installed Python script behavior."""
        executable = tmp_path / "r10n"
        executable.write_bytes(b"#!/usr/bin/python\n")
        monkeypatch.setenv("R10N_EXECUTABLE", "")
        monkeypatch.setenv("R10N_COMMAND_PATH", "")
        monkeypatch.setattr(cli.sys, "argv", [str(executable)])
        assert cli.resolve_current_executable_path() == executable
        assert cli.resolve_command_entry_path() == executable
        assert not cli.is_standalone_binary(executable)

    def test_source_go_shell_does_not_upgrade(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A go run/source build must not upgrade a temporary native executable."""
        executable = tmp_path / "r10n"
        executable.write_bytes(b"\x7fELF")
        monkeypatch.setenv("R10N_EXECUTABLE", str(executable))
        monkeypatch.setenv("R10N_COMMAND_PATH", str(executable))
        monkeypatch.setenv("R10N_SOURCE", "1")
        monkeypatch.setattr(
            cli,
            "fetch_release_data",
            lambda _: pytest.fail("source builds must not contact the release API"),
        )
        cli.upgrade(target_version=None, check=False)
        assert "only for standalone binary installs" in capsys.readouterr().out

    @pytest.mark.skipif(cli.os.name == "nt", reason="Windows in-place upgrade is unsupported")
    def test_upgrade_replaces_entire_native_bundle(self, tmp_path: Path) -> None:
        """Replace both native app and backend while keeping the launcher."""
        install_dir = tmp_path / "bin"
        old_app = install_dir / ".r10n"
        old_app.mkdir(parents=True)
        (old_app / "r10n").write_bytes(b"old-native")
        (old_app / "old-dependency").write_bytes(b"old")
        command = install_dir / "r10n"
        command.symlink_to(".r10n/r10n")
        new_app = tmp_path / "release" / "r10n"
        backend = new_app / "libexec" / "r10n-python"
        backend.mkdir(parents=True)
        (new_app / "r10n").write_bytes(b"new-native")
        (backend / "r10n-python").write_bytes(b"new-backend")
        cli.replace_installed_app(command, new_app)
        assert command.is_symlink()
        assert command.read_bytes() == b"new-native"
        assert (old_app / "libexec/r10n-python/r10n-python").read_bytes() == b"new-backend"
        assert not (old_app / "old-dependency").exists()


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
