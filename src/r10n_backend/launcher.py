"""Thin native frontend launcher for source checkouts, wheels, and uvx.

The package version selects an exact release, never ``latest``. Downloads are
checksum-verified before extraction; a private cache records every installed
file and relative symlink and verifies that inventory before each handoff.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from collections.abc import Generator, Sequence
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import Any

RELEASES = "https://github.com/pruthivithejan/r10n/releases/download"
ASSETS = {
    ("Linux", "x86_64"): "r10n-linux-x86_64.tar.gz",
    ("Darwin", "arm64"): "r10n-macos-arm64.tar.gz",
    ("Windows", "x86_64"): "r10n-windows-x86_64.exe",
}
MAX_ASSET_BYTES = 1024 * 1024 * 1024


def _source_root() -> Path | None:
    root = Path(__file__).resolve().parents[2]
    if (root / "go.mod").is_file() and (root / "cmd" / "r10n").is_dir():
        return root
    return None


def _private_directory(path: Path) -> None:
    """Create a user-private directory, refusing symlinked cache boundaries."""
    if path.is_symlink():
        raise RuntimeError(f"Refusing symlinked native cache directory: {path}")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir():
        raise RuntimeError(f"Native cache path is not a directory: {path}")
    if os.name != "nt":
        if path.stat().st_uid != os.getuid():
            raise RuntimeError(f"Native cache is owned by another user: {path}")
        path.chmod(0o700)


@contextlib.contextmanager
def _lock(path: Path) -> Generator[None]:
    """Serialize installation/builds using an OS lock released on interruption."""
    if path.is_symlink():
        raise RuntimeError(f"Refusing symlinked launcher lock: {path}")
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            # Nonblocking attempts permit Ctrl+C even during a concurrent install.
            import time

            while True:
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, output: Path, limit: int = MAX_ASSET_BYTES) -> None:
    """Download over verified TLS, with certifi fallback for missing OS roots."""
    request = urllib.request.Request(url, headers={"User-Agent": "r10n-python-launcher"})
    try:
        response = urllib.request.urlopen(request, timeout=60)
    except urllib.error.URLError as error:
        if not isinstance(error.reason, ssl.SSLCertVerificationError):
            raise
        import certifi

        response = urllib.request.urlopen(
            request, timeout=60, context=ssl.create_default_context(cafile=certifi.where())
        )
    with response, output.open("wb") as stream:
        count = 0
        while block := response.read(1024 * 1024):
            count += len(block)
            if count > limit:
                raise RuntimeError("Native release download exceeds the allowed size")
            stream.write(block)


def _expected_checksum(checksums: Path, asset: str) -> str:
    matches = []
    for line in checksums.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].lstrip("*") == asset:
            matches.append(fields[0].lower())
    if len(matches) != 1 or not re.fullmatch(r"[a-f0-9]{64}", matches[0]):
        raise RuntimeError(f"Missing or ambiguous SHA256SUMS entry for {asset}")
    return matches[0]


def _archive_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or ":" in name
        or not path.parts
    ):
        raise RuntimeError(f"Unsafe native archive path: {name}")
    return path


def _extract(archive_path: Path, destination: Path) -> None:
    """Extract ordinary files/directories and safe relative symlinks only."""
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        paths: dict[PurePosixPath, tarfile.TarInfo] = {}
        total = 0
        for member in members:
            path = _archive_path(member.name)
            if path in paths:
                raise RuntimeError(f"Duplicate native archive path: {member.name}")
            if not (member.isfile() or member.isdir() or member.issym()):
                raise RuntimeError(f"Unsupported native archive entry: {member.name}")
            paths[path] = member
            total += member.size
            if total > MAX_ASSET_BYTES:
                raise RuntimeError("Expanded native release exceeds the allowed size")
        for path, member in paths.items():
            if any(parent in paths and not paths[parent].isdir() for parent in path.parents):
                raise RuntimeError(f"Native archive entry has a non-directory parent: {path}")
            if member.issym():
                target = member.linkname
                if not target or "\\" in target or ":" in target or target.startswith("/"):
                    raise RuntimeError(f"Unsafe native archive symlink: {path}")
                resolved = (destination / path.parent / target).resolve()
                if not resolved.is_relative_to(destination.resolve()):
                    raise RuntimeError(f"Escaping native archive symlink: {path}")
        # Create links last: ordinary file writes can never follow archive links.
        for path, member in paths.items():
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.isdir():
                target.mkdir(exist_ok=True)
            elif member.isfile():
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError(f"Unreadable native archive entry: {path}")
                with source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(member.mode & 0o777)
        for path, member in paths.items():
            if member.issym():
                destination.joinpath(*path.parts).symlink_to(member.linkname)
        # Resolve again with the complete link graph, rejecting chained escapes.
        for path, member in paths.items():
            if member.issym() and not (destination / path).resolve().is_relative_to(
                destination.resolve()
            ):
                raise RuntimeError(f"Escaping native archive symlink chain: {path}")


def _inventory(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for directory, directories, files in os.walk(root, followlinks=False):
        for name in sorted([*directories, *files]):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if relative == "manifest.json":
                continue
            if path.is_symlink():
                target = os.readlink(path)
                if not path.resolve().is_relative_to(root.resolve()):
                    raise RuntimeError(f"Native cache contains an unsafe symlink: {relative}")
                result[relative] = {"link": target}
            elif path.is_file():
                result[relative] = {"sha256": _sha256(path), "mode": path.stat().st_mode & 0o777}
            elif path.is_dir():
                result[relative] = {"directory": True}
            else:
                raise RuntimeError(f"Native cache contains an unsupported entry: {relative}")
    return result


def _asset() -> str:
    system, machine = platform.system(), platform.machine().lower()
    machine = {"amd64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    try:
        return ASSETS[system, machine]
    except KeyError as error:
        raise RuntimeError(
            f"No native release for {system}/{machine}; build from source or set R10N_NATIVE"
        ) from error


def _cache_root() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return base.expanduser().resolve() / "r10n" / "native"


def _cached_native(package_version: str) -> Path:
    if not re.fullmatch(r"[0-9][0-9A-Za-z.+_-]*", package_version):
        raise RuntimeError("Invalid package version for native release selection")
    asset = _asset()
    cache = _cache_root()
    _private_directory(cache.parent)
    _private_directory(cache)
    release = cache / package_version
    _private_directory(release)
    install = release / asset.removesuffix(".tar.gz").removesuffix(".exe")
    executable_relative = "r10n.exe" if asset.endswith(".exe") else "r10n/r10n"
    executable = install / executable_relative
    with _lock(release / f".{install.name}.lock"):
        if install.exists() or install.is_symlink():
            try:
                if install.is_symlink() or (install / "manifest.json").is_symlink():
                    raise ValueError("symlinked installation or manifest")
                manifest = json.loads((install / "manifest.json").read_text(encoding="utf-8"))
                if (
                    manifest["version"] != package_version
                    or manifest["asset"] != asset
                    or manifest["files"] != _inventory(install)
                    or not re.fullmatch(r"[a-f0-9]{64}", manifest["checksum"])
                    or not executable.is_file()
                    or executable.is_symlink()
                ):
                    raise ValueError("inventory mismatch")
            except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
                raise RuntimeError(
                    f"Native cache integrity check failed: {install}. "
                    "Remove this cache directory and retry."
                ) from error
            return executable

        with tempfile.TemporaryDirectory(prefix=f".{install.name}-", dir=release) as temporary:
            staging = Path(temporary)
            archive_path = staging / asset
            checksums = staging / "SHA256SUMS"
            url = f"{RELEASES}/v{package_version}"
            _download(f"{url}/SHA256SUMS", checksums, limit=1024 * 1024)
            expected = _expected_checksum(checksums, asset)
            _download(f"{url}/{asset}", archive_path)
            if _sha256(archive_path) != expected:
                raise RuntimeError(f"SHA256 checksum mismatch for {asset}; refusing to execute")
            payload = staging / "payload"
            payload.mkdir(mode=0o700)
            if asset.endswith(".exe"):
                shutil.copyfile(archive_path, payload / executable_relative)
            else:
                _extract(archive_path, payload)
            binary = payload / executable_relative
            if not binary.is_file() or binary.is_symlink():
                raise RuntimeError("Native release is missing its executable")
            binary.chmod(0o755)
            manifest = {
                "version": package_version,
                "asset": asset,
                "checksum": expected,
                "files": _inventory(payload),
            }
            (payload / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            os.replace(payload, install)
        return executable


def _build_source(root: Path, go: str) -> Path:
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    executable = dist / ("r10n-dev.exe" if os.name == "nt" else "r10n-dev")
    with _lock(dist / ".r10n-dev.lock"):
        with tempfile.TemporaryDirectory(prefix=".r10n-dev-", dir=dist) as temporary:
            output = Path(temporary) / executable.name
            # Always ask Go to build current sources; Go owns incremental caching.
            subprocess.run(
                [go, "build", "-trimpath", "-o", str(output), "./cmd/r10n"],
                cwd=root,
                check=True,
            )
            if not executable.is_file() or _sha256(output) != _sha256(executable):
                os.replace(output, executable)
    return executable


def main(argv: Sequence[str] | None = None) -> int:
    """Forward all public arguments to the native frontend without parsing them.

    Args:
        argv: Arguments excluding executable name, or process arguments.

    Returns:
        Native process exit status on Windows, or bootstrap failure status.
        Unix success replaces this process, preserving native signal handling.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    environment = os.environ.copy()
    try:
        root = _source_root()
        override = os.environ.get("R10N_NATIVE")
        if override:
            candidate = shutil.which(override)
            if candidate is None:
                raise RuntimeError("R10N_NATIVE must name an existing executable")
            executable = Path(candidate).resolve()
            if executable == Path(sys.argv[0]).resolve():
                raise RuntimeError("R10N_NATIVE cannot point to the Python launcher itself")
        elif root is not None and (go := shutil.which("go")) is not None:
            executable = _build_source(root, go)
            environment.pop("R10N_MANAGED", None)
        else:
            executable = _cached_native(version("r10n"))
            environment["R10N_MANAGED"] = "python"
            environment.pop("R10N_PROJECT", None)
        if root is not None and not environment.get("R10N_MANAGED"):
            environment["R10N_PROJECT"] = str(root)
        command = [str(executable), *arguments]
        if os.name == "nt":
            return subprocess.call(command, env=environment)
        os.execve(str(executable), command, environment)
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"r10n: native launcher failed: {error}", file=sys.stderr)
        return 1
