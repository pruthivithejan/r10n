"""Create tag-backed r10n releases without hand-editing version files.

Patch releases are the default. Use the explicit ``minor`` or ``major`` command
when you want to advance either of those version components. ``--publish``
updates the synchronized version files, commits the release, creates an
annotated Git tag, and pushes both the branch and tag.
"""

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
CLI_PATH = ROOT / "src" / "cli.py"
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
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError(f"Could not find exactly one {label} version declaration")
    return updated


def read_declared_versions(root: Path = ROOT) -> dict[str, Version]:
    """Read the synchronized versions from project metadata and the CLI.

    Args:
        root: Repository root containing the version files.

    Returns:
        Mapping of version-file labels to parsed versions.

    Raises:
        ValueError: If a declaration is missing or the versions disagree.
    """
    pyproject = (root / PYPROJECT_PATH.relative_to(ROOT)).read_text(encoding="utf-8")
    cli = (root / CLI_PATH.relative_to(ROOT)).read_text(encoding="utf-8")
    lock = (root / LOCK_PATH.relative_to(ROOT)).read_text(encoding="utf-8")

    pyproject_match = re.search(
        r'(?m)^(?P<prefix>version\s*=\s*")(?P<version>[^"]+)(?P<suffix>")$',
        pyproject,
    )
    cli_match = re.search(
        r'(?m)^(?P<prefix>VERSION\s*=\s*")(?P<version>[^"]+)(?P<suffix>")$',
        cli,
    )
    lock_match = re.search(
        r'(?m)^\[\[package\]\]\nname = "r10n"\nversion = "(?P<version>[^"]+)"$',
        lock,
    )
    if not pyproject_match or not cli_match or not lock_match:
        raise ValueError("Could not find all synchronized version declarations")

    versions = {
        "pyproject.toml": Version.parse(pyproject_match.group("version")),
        "src/cli.py": Version.parse(cli_match.group("version")),
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
    """Write one version to ``pyproject.toml``, ``src/cli.py``, and ``uv.lock``."""
    paths_and_patterns = (
        (
            root / PYPROJECT_PATH.relative_to(ROOT),
            r'^(?P<prefix>version\s*=\s*")(?P<old>[^"]+)(?P<suffix>")$',
            "pyproject.toml",
        ),
        (
            root / CLI_PATH.relative_to(ROOT),
            r'^(?P<prefix>VERSION\s*=\s*")(?P<old>[^"]+)(?P<suffix>")$',
            "src/cli.py",
        ),
        (
            root / LOCK_PATH.relative_to(ROOT),
            r'^(?P<prefix>\[\[package\]\]\nname = "r10n"\nversion = ")(?P<old>[^"]+)(?P<suffix>")$',
            "uv.lock",
        ),
    )
    for path, pattern, label in paths_and_patterns:
        original = path.read_text(encoding="utf-8")
        updated = _replace_version(original, pattern, version, label)
        path.write_text(updated, encoding="utf-8")


def _run_git(args: Sequence[str], root: Path = ROOT) -> None:
    """Run a Git command in the repository."""
    subprocess.run(["git", *args], cwd=root, check=True)


def publish_release(version: Version, root: Path = ROOT) -> str:
    """Commit the version update, create an annotated tag, and push both.

    Args:
        version: Version to publish.
        root: Repository root.

    Returns:
        Created tag name.
    """
    tag = f"v{version}"
    if tag in {f"v{item}" for item in list_release_tags(root)}:
        raise ValueError(f"Git tag already exists: {tag}")

    _run_git(["add", "-A"], root)
    _run_git(["commit", "-m", f"chore(release): {tag}"], root)
    _run_git(["tag", "-a", tag, "-m", f"Release {tag}"], root)
    branch = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _run_git(["push", "origin", branch], root)
    _run_git(["push", "origin", tag], root)
    return tag


def build_parser() -> argparse.ArgumentParser:
    """Build the release helper argument parser."""
    parser = argparse.ArgumentParser(
        description="Bump r10n versions from Git tags and optionally publish a release."
    )
    parser.add_argument(
        "kind",
        nargs="?",
        choices=("patch", "minor", "major"),
        default="patch",
        help="Release component to bump (default: patch; major/minor must be explicit).",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Update files, commit, create an annotated tag, and push to origin.",
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
    kind: VERSION_KIND = args.kind
    version = next_release_version(kind)
    tag = f"v{version}"
    if args.dry_run:
        print(f"Next {kind} release: {version} ({tag})")
        return 0

    update_version_files(version)
    if args.publish:
        created_tag = publish_release(version)
        print(f"Published {version} as {created_tag}")
    else:
        print(f"Updated version files to {version}. Run again with --publish to commit, tag, and push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
