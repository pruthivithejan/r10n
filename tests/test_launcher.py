"""Offline native bootstrap tests: forwarding, safe installation, and reuse."""

from __future__ import annotations

import hashlib
import io
import json
import os
import ssl
import tarfile
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from r10n_backend import launcher

ASSET = "r10n-linux-x86_64.tar.gz"


def make_archive(entries: list[tuple[str, bytes | str]]) -> bytes:
    """Build a release-like tarball with ordinary files and relative links."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, value in entries:
            member = tarfile.TarInfo(name)
            if isinstance(value, str):
                member.type = tarfile.SYMTYPE
                member.linkname = value
            else:
                member.size = len(value)
                member.mode = 0o755 if name == "r10n/r10n" else 0o644
            archive.addfile(member, io.BytesIO(value) if isinstance(value, bytes) else None)
    return buffer.getvalue()


@pytest.fixture
def release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Provide an offline release and isolated private cache."""
    content = make_archive(
        [
            ("r10n/r10n", b"native executable"),
            ("r10n/libexec/r10n-python/library", b"native library"),
            ("r10n/libexec/r10n-python/link", "library"),
        ]
    )
    state: dict[str, Any] = {"content": content, "urls": [], "checksum": None}
    monkeypatch.setattr(launcher, "_cache_root", lambda: tmp_path / "cache")
    monkeypatch.setattr(launcher, "_asset", lambda: ASSET)

    def download(url: str, output: Path, limit: int = launcher.MAX_ASSET_BYTES) -> None:
        state["urls"].append(url)
        if url.endswith("SHA256SUMS"):
            digest = state["checksum"] or hashlib.sha256(state["content"]).hexdigest()
            output.write_text(f"{digest}  {ASSET}\n", encoding="utf-8")
        else:
            output.write_bytes(state["content"])

    monkeypatch.setattr(launcher, "_download", download)
    return state


def test_release_is_pinned_verified_and_reused(release: dict[str, Any]) -> None:
    """A verified installation is reused offline and never resolves latest."""
    binary = launcher._cached_native("0.12.2")
    assert binary.read_bytes() == b"native executable"
    assert release["urls"] == [
        f"{launcher.RELEASES}/v0.12.2/SHA256SUMS",
        f"{launcher.RELEASES}/v0.12.2/{ASSET}",
    ]
    assert launcher._cached_native("0.12.2") == binary
    assert len(release["urls"]) == 2
    link = binary.parent / "libexec/r10n-python/link"
    assert link.is_symlink()
    assert os.readlink(link) == "library"
    if os.name != "nt":
        assert binary.stat().st_mode & 0o777 == 0o755
        assert binary.parent.parent.stat().st_mode & 0o777 == 0o700


def test_release_preserves_relative_directory_symlinks(release: dict[str, Any]) -> None:
    """PyInstaller framework-directory links remain links rather than copies."""
    release["content"] = make_archive(
        [
            ("r10n/r10n", b"native"),
            ("r10n/libexec/framework/Versions/A/library", b"library"),
            ("r10n/libexec/framework/Versions/Current", "A"),
            ("r10n/libexec/framework/library", "Versions/Current/library"),
        ]
    )
    binary = launcher._cached_native("0.12.2")
    link = binary.parent / "libexec/framework/Versions/Current"
    assert link.is_symlink()
    assert link.is_dir()
    assert (binary.parent / "libexec/framework/library").read_bytes() == b"library"
    assert launcher._cached_native("0.12.2") == binary


def test_versions_have_separate_cache_directories(release: dict[str, Any]) -> None:
    """Package updates cannot accidentally execute a previously cached version."""
    old = launcher._cached_native("0.12.1")
    new = launcher._cached_native("0.12.2")
    assert old != new
    assert len(release["urls"]) == 4


@pytest.mark.parametrize("mutation", ["file", "extra", "link", "mode", "manifest", "version"])
def test_cache_tampering_is_refused(release: dict[str, Any], mutation: str) -> None:
    """Reuse checks every file/link, not just the frontend executable."""
    binary = launcher._cached_native("0.12.2")
    library = binary.parent / "libexec/r10n-python/library"
    if mutation == "file":
        library.write_bytes(b"tampered")
    elif mutation == "extra":
        (binary.parent / "extra").write_bytes(b"untracked")
    elif mutation == "link":
        link = library.with_name("link")
        link.unlink()
        link.symlink_to("other")
    elif mutation == "mode":
        if os.name == "nt":
            pytest.skip("Windows chmod does not implement Unix executable modes")
        binary.chmod(0o644)
    elif mutation == "manifest":
        (binary.parent.parent / "manifest.json").write_text("invalid", encoding="utf-8")
    else:
        manifest_path = binary.parent.parent / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = "0.99.0"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="integrity check failed"):
        launcher._cached_native("0.12.2")
    assert len(release["urls"]) == 2


def test_checksum_failure_never_installs(release: dict[str, Any], tmp_path: Path) -> None:
    """Unverified executable bytes never reach the active cache."""
    release["checksum"] = "0" * 64
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        launcher._cached_native("0.12.2")
    assert not list((tmp_path / "cache/0.12.2").glob("r10n-*"))
    assert not any(path.is_dir() for path in (tmp_path / "cache/0.12.2").iterdir())


@pytest.mark.parametrize("text", ["", "garbage", f"bad  {ASSET}\n", f"{'0' * 64}  other\n"])
def test_checksum_requires_exact_asset(text: str, tmp_path: Path) -> None:
    """Malformed or missing checksum records fail closed."""
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(text, encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA256SUMS"):
        launcher._expected_checksum(sums, ASSET)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("../outside", b"escape"),
        ("/absolute", b"escape"),
        ("r10n/../../outside", b"escape"),
        ("r10n\\outside", b"escape"),
        ("C:/outside", b"escape"),
        ("r10n/link", "/etc/passwd"),
        ("r10n/link", "../../outside"),
        ("r10n/link", "C:\\outside"),
    ],
)
def test_unsafe_archives_are_rejected(name: str, value: bytes | str, tmp_path: Path) -> None:
    """Traversal paths and unsafe link targets are rejected before extraction."""
    archive = tmp_path / "archive.tar.gz"
    archive.write_bytes(make_archive([(name, value)]))
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(RuntimeError, match="archive"):
        launcher._extract(archive, output)
    assert list(output.iterdir()) == []


def test_archive_cannot_write_through_a_link(tmp_path: Path) -> None:
    """Even an otherwise safe relative symlink cannot parent a file entry."""
    archive = tmp_path / "archive.tar.gz"
    archive.write_bytes(make_archive([("r10n/link", "dir"), ("r10n/link/file", b"data")]))
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(RuntimeError, match="non-directory parent"):
        launcher._extract(archive, output)


def test_hardlinks_and_special_files_are_rejected(tmp_path: Path) -> None:
    """No devices, FIFOs, or hardlinks are accepted in executable releases."""
    for kind in (tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
        archive_path = tmp_path / "archive.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            member = tarfile.TarInfo("r10n/unsafe")
            member.type = kind
            member.linkname = "other"
            archive.addfile(member)
        with pytest.raises(RuntimeError, match="Unsupported"):
            launcher._extract(archive_path, tmp_path / "output")


def test_duplicate_archive_paths_are_rejected(tmp_path: Path) -> None:
    """Duplicate paths cannot replace previously validated extraction entries."""
    archive = tmp_path / "archive.tar.gz"
    archive.write_bytes(make_archive([("r10n/file", b"one"), ("r10n/file", b"two")]))
    with pytest.raises(RuntimeError, match="Duplicate"):
        launcher._extract(archive, tmp_path / "output")


def test_concurrent_installers_publish_one_complete_cache(release: dict[str, Any]) -> None:
    """Concurrent launches wait on the OS lock and reuse the winning install."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        paths = list(executor.map(launcher._cached_native, ["0.12.2"] * 4))
    assert len(set(paths)) == 1
    assert len(release["urls"]) == 2
    assert paths[0].read_bytes() == b"native executable"


def test_cancelled_download_cleans_staging_and_releases_lock(
    release: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Interruption leaves no published or staged executable and permits retry."""
    original = launcher._download

    def interrupted(url: str, output: Path, limit: int = launcher.MAX_ASSET_BYTES) -> None:
        output.write_bytes(b"partial")
        raise KeyboardInterrupt

    monkeypatch.setattr(launcher, "_download", interrupted)
    with pytest.raises(KeyboardInterrupt):
        launcher._cached_native("0.12.2")
    assert not list((tmp_path / "cache/0.12.2").glob("r10n-*"))
    assert not any(path.is_dir() for path in (tmp_path / "cache/0.12.2").iterdir())
    monkeypatch.setattr(launcher, "_download", original)
    assert launcher._cached_native("0.12.2").is_file()


def test_source_build_keeps_caller_cwd_and_forwards_all_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Source launch always builds current Go sources but does not chdir callers."""
    root, caller = tmp_path / "source", tmp_path / "caller"
    root.mkdir()
    caller.mkdir()
    monkeypatch.chdir(caller)
    monkeypatch.delenv("R10N_NATIVE", raising=False)
    monkeypatch.delenv("R10N_MANAGED", raising=False)
    monkeypatch.setattr(launcher, "_source_root", lambda: root)
    monkeypatch.setattr(
        launcher.shutil, "which", lambda command: "/tools/go" if command == "go" else None
    )
    builds: list[list[str]] = []
    handoffs: list[tuple[str, list[str], dict[str, str]]] = []

    def build(command: list[str], *, cwd: Path, check: bool) -> None:
        assert cwd == root
        assert check
        assert Path.cwd() == caller
        builds.append(command)
        Path(command[command.index("-o") + 1]).write_bytes(b"built current Go")

    def execute(path: str, args: list[str], env: dict[str, str]) -> None:
        assert Path.cwd() == caller
        handoffs.append((path, args, env))

    monkeypatch.setattr(launcher.subprocess, "run", build)
    monkeypatch.setattr(launcher.os, "execve", execute)
    arguments = ["contacts", "--input", "relative.txt", "--prefix", "A B"]
    assert launcher.main(arguments) == 0
    assert launcher.main(arguments) == 0
    assert len(builds) == 2
    assert handoffs[0][1] == [str(root / "dist/r10n-dev"), *arguments]
    assert handoffs[0][2]["R10N_PROJECT"] == str(root)
    assert "R10N_MANAGED" not in handoffs[0][2]
    assert Path.cwd() == caller


def test_installed_launcher_uses_metadata_and_managed_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Installed launch pins metadata version and marks the cache non-upgradable."""
    binary = tmp_path / "native"
    captured: dict[str, Any] = {}
    monkeypatch.delenv("R10N_NATIVE", raising=False)
    monkeypatch.setenv("R10N_PROJECT", "/foreign/source")
    monkeypatch.setattr(launcher, "_source_root", lambda: None)
    monkeypatch.setattr(
        launcher, "version", lambda package: "0.12.2" if package == "r10n" else "wrong"
    )

    def cached(package_version: str) -> Path:
        assert package_version == "0.12.2"
        return binary

    def execute(path: str, args: list[str], env: dict[str, str]) -> None:
        captured.update(path=path, args=args, env=env)

    monkeypatch.setattr(launcher, "_cached_native", cached)
    monkeypatch.setattr(launcher.os, "execve", execute)
    assert launcher.main(["--help", "unknown"]) == 0
    assert captured["args"] == [str(binary), "--help", "unknown"]
    assert captured["env"]["R10N_MANAGED"] == "python"
    assert "R10N_PROJECT" not in captured["env"]


def test_explicit_native_override_does_not_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the explicit override is resolved on PATH, never Python r10n."""
    binary = tmp_path / "r10n-native"
    binary.write_bytes(b"native")
    monkeypatch.setenv("R10N_NATIVE", str(binary))
    monkeypatch.setattr(launcher, "_source_root", lambda: None)
    lookups = []
    executed = []

    def which(command: str) -> str:
        lookups.append(command)
        assert command == str(binary)
        return str(binary)

    monkeypatch.setattr(launcher.shutil, "which", which)
    monkeypatch.setattr(launcher.os, "execve", lambda *args: executed.append(args))
    assert launcher.main(["--version"]) == 0
    assert lookups == [str(binary)]
    assert executed[0][1] == [str(binary), "--version"]


def test_override_cannot_recursively_launch_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A misconfigured override cannot recurse into the same entrypoint."""
    binary = tmp_path / "python-r10n"
    monkeypatch.setenv("R10N_NATIVE", str(binary))
    monkeypatch.setattr(launcher, "_source_root", lambda: None)
    monkeypatch.setattr(launcher.shutil, "which", lambda command: str(binary))
    monkeypatch.setattr(launcher.sys, "argv", [str(binary)])
    assert launcher.main([]) == 1
    assert "launcher itself" in capsys.readouterr().err


def test_windows_preserves_native_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows waits for the native process and returns its exact status."""
    binary = tmp_path / "r10n.exe"
    monkeypatch.delenv("R10N_NATIVE", raising=False)
    monkeypatch.setattr(launcher, "_source_root", lambda: None)
    monkeypatch.setattr(launcher, "_cached_native", lambda _: binary)
    monkeypatch.setattr(launcher, "version", lambda _: "0.12.2")
    calls = []
    monkeypatch.setattr(
        launcher.subprocess, "call", lambda *args, **kw: calls.append((args, kw)) or 7
    )
    # No pathlib constructors run inside this branch after OS selection.
    with monkeypatch.context() as windows:
        windows.setattr(launcher.os, "name", "nt")
        assert launcher.main(["validate", "--strict"]) == 7
    assert calls[0][0][0] == [str(binary), "validate", "--strict"]
    assert calls[0][1]["env"]["R10N_MANAGED"] == "python"


def test_unsupported_platform_has_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unsupported hosts never silently download another platform's executable."""
    monkeypatch.setattr(launcher.platform, "system", lambda: "Linux")
    monkeypatch.setattr(launcher.platform, "machine", lambda: "mips")
    with pytest.raises(RuntimeError, match="R10N_NATIVE"):
        launcher._asset()


def test_transport_streams_with_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Real downloader consumes mocked TLS responses and enforces size limits."""
    calls = []

    def open_url(request: Any, **kwargs: Any) -> io.BytesIO:
        assert request.full_url == "https://example.invalid/native"
        assert kwargs["timeout"] == 60
        calls.append(kwargs)
        return io.BytesIO(b"download")

    monkeypatch.setattr(launcher.urllib.request, "urlopen", open_url)
    output = tmp_path / "asset"
    launcher._download("https://example.invalid/native", output, limit=8)
    assert output.read_bytes() == b"download"
    with pytest.raises(RuntimeError, match="allowed size"):
        launcher._download("https://example.invalid/native", output, limit=7)
    assert len(calls) == 2


def test_transport_tls_fallback_keeps_certificate_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unavailable system root store retries with certifi, never insecure TLS."""
    contexts = []

    def open_url(request: Any, **kwargs: Any) -> io.BytesIO:
        contexts.append(kwargs.get("context"))
        if len(contexts) == 1:
            raise urllib.error.URLError(ssl.SSLCertVerificationError(1, "missing root"))
        assert kwargs["context"].verify_mode == ssl.CERT_REQUIRED
        assert kwargs["context"].check_hostname
        return io.BytesIO(b"verified")

    monkeypatch.setattr(launcher.urllib.request, "urlopen", open_url)
    output = tmp_path / "asset"
    launcher._download("https://example.invalid/native", output)
    assert output.read_bytes() == b"verified"
    assert contexts[0] is None
    assert len(contexts) == 2


def test_transport_network_errors_are_not_retried_insecurely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ordinary network failures propagate; fallback applies only to root errors."""
    calls = []

    def open_url(request: Any, **kwargs: Any) -> io.BytesIO:
        calls.append(kwargs)
        raise urllib.error.URLError("network unreachable")

    monkeypatch.setattr(launcher.urllib.request, "urlopen", open_url)
    with pytest.raises(urllib.error.URLError):
        launcher._download("https://example.invalid/native", tmp_path / "asset")
    assert len(calls) == 1


def test_windows_release_executable_is_checksum_verified(
    release: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Windows installs the single-file asset without attempting tar extraction."""
    asset = "r10n-windows-x86_64.exe"
    content = b"windows native binary"
    monkeypatch.setattr(launcher, "_asset", lambda: asset)

    def download(url: str, output: Path, limit: int = launcher.MAX_ASSET_BYTES) -> None:
        if url.endswith("SHA256SUMS"):
            output.write_text(f"{hashlib.sha256(content).hexdigest()}  {asset}\n", encoding="utf-8")
        else:
            output.write_bytes(content)

    monkeypatch.setattr(launcher, "_download", download)
    binary = launcher._cached_native("0.12.2")
    assert binary.name == "r10n.exe"
    assert binary.read_bytes() == content
    assert launcher._cached_native("0.12.2") == binary


def test_symlinked_cache_installation_is_refused(release: dict[str, Any], tmp_path: Path) -> None:
    """A cache directory redirect cannot bypass inventory checks."""
    binary = launcher._cached_native("0.12.2")
    install = binary.parent.parent
    moved = install.with_name("other")
    install.rename(moved)
    install.symlink_to(moved, target_is_directory=True)
    with pytest.raises(RuntimeError, match="integrity check failed"):
        launcher._cached_native("0.12.2")


def test_missing_executable_is_never_published(release: dict[str, Any], tmp_path: Path) -> None:
    """Checksum-valid archives still need the agreed release executable layout."""
    release["content"] = make_archive([("r10n/library", b"library only")])
    with pytest.raises(RuntimeError, match="missing its executable"):
        launcher._cached_native("0.12.2")
    assert not any(path.is_dir() for path in (tmp_path / "cache/0.12.2").iterdir())


def test_bootstrap_interruption_returns_shell_cancellation_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ctrl+C before native handoff returns the standard 130 status."""
    monkeypatch.delenv("R10N_NATIVE", raising=False)
    monkeypatch.setattr(launcher, "_source_root", lambda: None)
    monkeypatch.setattr(launcher, "version", lambda _: "0.12.2")

    def interrupted(package_version: str) -> Path:
        raise KeyboardInterrupt

    monkeypatch.setattr(launcher, "_cached_native", interrupted)
    assert launcher.main([]) == 130
