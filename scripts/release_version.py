"""Prepare version metadata; publication belongs exclusively to release.yml."""

from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = ROOT / "pyproject.toml"
LOCK_PATH = ROOT / "uv.lock"
VERSION_KIND = Literal["patch", "minor", "major"]


@dataclass(frozen=True, order=True)
class Version:
    """A three-part semantic version."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> Version:
        """Parse a stable ``major.minor.patch`` version string.

        Args:
            value: Version string, optionally prefixed with ``v``.

        Returns:
            Parsed version.

        Raises:
            ValueError: If ``value`` is not a stable three-part version.
        """
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
        if not match:
            raise ValueError(f"Unsupported version: {value!r}")
        return cls(*(int(part) for part in match.groups()))

    def bump(self, kind: VERSION_KIND) -> Version:
        """Return the next version for a patch, minor, or major release."""
        if kind == "major":
            return Version(self.major + 1, 0, 0)
        if kind == "minor":
            return Version(self.major, self.minor + 1, 0)
        return Version(self.major, self.minor, self.patch + 1)

    def __str__(self) -> str:
        """Return the version without a ``v`` prefix."""
        return f"{self.major}.{self.minor}.{self.patch}"


def _replace_version(text: str, pattern: str, version: Version, label: str) -> str:
    """Replace one version declaration and reject unexpected file shapes."""
    replacement = rf"\g<prefix>{version}\g<suffix>"
    updated, count = re.subn(
        pattern,
        replacement,
        text,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError(f"Could not find exactly one {label} version declaration")
    return updated


def read_declared_versions(root: Path = ROOT) -> dict[str, Version]:
    """Read project metadata and the generated lockfile package version.

    Args:
        root: Repository root containing the version files.

    Returns:
        Mapping of version-file labels to parsed versions.

    Raises:
        ValueError: If a declaration is missing or the versions disagree.
    """
    pyproject = (root / PYPROJECT_PATH.relative_to(ROOT)).read_text(encoding="utf-8")
    lock = (root / LOCK_PATH.relative_to(ROOT)).read_text(encoding="utf-8")

    section = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)", pyproject)
    pyproject_match = re.search(
        r'(?m)^(?P<prefix>version\s*=\s*")(?P<version>[^"]+)(?P<suffix>")$',
        section[1] if section else "",
    )
    lock_match = re.search(
        r'(?m)^\[\[package\]\]\nname = "r10n"\nversion = "(?P<version>[^"]+)"$',
        lock,
    )
    if not pyproject_match or not lock_match:
        raise ValueError("Could not find all synchronized version declarations")

    versions = {
        "pyproject.toml": Version.parse(pyproject_match.group("version")),
        "uv.lock": Version.parse(lock_match.group("version")),
    }
    if len(set(versions.values())) != 1:
        details = ", ".join(f"{path}={version}" for path, version in versions.items())
        raise ValueError(f"Version mismatch: {details}")
    return versions


def list_release_tags(root: Path = ROOT) -> list[Version]:
    """Return stable semantic versions from local ``v*`` Git tags."""
    result = subprocess.run(
        ["git", "tag", "--list", "v*"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    versions = []
    for tag in result.stdout.splitlines():
        try:
            versions.append(Version.parse(tag))
        except ValueError:
            continue
    return versions


def next_release_version(kind: VERSION_KIND, root: Path = ROOT) -> Version:
    """Calculate the next release from declarations and existing Git tags.

    The declared version may be ahead of the latest tag when a prior release
    was pushed without tagging. In that case the declared version is the safe
    base, preventing the helper from moving backwards.
    """
    declared = next(iter(read_declared_versions(root).values()))
    tags = list_release_tags(root)
    latest_tag = max(tags, default=declared)
    if declared < latest_tag:
        raise ValueError(
            f"Declared version {declared} is behind the latest Git tag {latest_tag}; "
            "synchronize the files before releasing."
        )
    return declared.bump(kind)


def update_version_files(version: Version, root: Path = ROOT) -> None:
    """Update project metadata, then regenerate and validate ``uv.lock``.

    Args:
        version: New stable release version.
        root: Source checkout with uv available.
    """
    path = root / PYPROJECT_PATH.relative_to(ROOT)
    original = path.read_text(encoding="utf-8")
    updated = _replace_version(
        original,
        r'(?s)(?P<prefix>^\[project\]\s*\n(?:(?!^\[).)*?^version\s*=\s*")(?P<old>[^"]+)(?P<suffix>")',
        version,
        "pyproject.toml",
    )
    path.write_text(updated, encoding="utf-8")
    subprocess.run(["uv", "lock"], cwd=root, check=True)
    read_declared_versions(root)


def build_parser() -> argparse.ArgumentParser:
    """Build the release helper argument parser."""
    parser = argparse.ArgumentParser(
        description="Prepare project and lock metadata without committing or publishing."
    )
    parser.add_argument(
        "kind",
        nargs="?",
        choices=("patch", "minor", "major"),
        default="patch",
        help="Release component to bump (default: patch; major/minor must be explicit).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check metadata/lock agreement without changing files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the next version without changing files or Git state.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the release helper CLI."""
    args = build_parser().parse_args(argv)
    if args.check:
        print(read_declared_versions())
        return 0
    kind: VERSION_KIND = args.kind
    version = next_release_version(kind)
    tag = f"v{version}"
    if args.dry_run:
        print(f"Next {kind} release: {version} ({tag})")
        return 0

    update_version_files(version)
    print(f"Prepared {version}. Review and commit; a version bump on main triggers release.yml.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
