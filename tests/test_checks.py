"""Regression tests for read-only, index-aware developer checks."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import check


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use an isolated Git index without installing hooks or making commits."""
    # Git hooks export repository-local overrides. Without clearing them, git -C
    # and git init may operate on the parent repository instead of this fixture.
    local_variables = subprocess.check_output(
        ["git", "rev-parse", "--local-env-vars"], text=True
    ).splitlines()
    for name in local_variables:
        monkeypatch.delenv(name, raising=False)
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "core.autocrlf", "false"], check=True)
    monkeypatch.setattr(check, "ROOT", tmp_path)
    # Language suites are unrelated to index/format regression fixtures.
    monkeypatch.setattr(check, "run", lambda *arguments: None)
    return tmp_path


def stage(root: Path, path: str, contents: str) -> Path:
    """Stage a fixture using an argument array that preserves spaces."""
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(contents, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "--force", "--", path], check=True)
    return file


def test_go_paths_with_spaces_and_deleted_files(repository: Path) -> None:
    """The Go inventory preserves filenames and skips deleted tracked sources."""
    stage(repository, "a folder/a file.go", "package fixture\n")
    removed = stage(repository, "removed.go", "package fixture\n")
    removed.unlink()
    assert check.go_files() == ["a folder/a file.go"]


def test_gofmt_check_never_rewrites_or_restages(repository: Path) -> None:
    """A failing formatting check leaves both worktree and index untouched."""
    if shutil.which("gofmt") is None:
        pytest.skip("Go is required to exercise gofmt")
    original = "package fixture\nfunc   example( ) { }\n"
    file = stage(repository, "a folder/a file.go", original)
    with pytest.raises(SystemExit, match="gofmt"):
        check.check_staged()
    assert file.read_text(encoding="utf-8") == original
    indexed = subprocess.check_output(
        ["git", "-C", str(repository), "show", ":a folder/a file.go"], text=True
    )
    assert indexed == original


@pytest.mark.parametrize("extension", ["go", "py"])
def test_partial_staging_is_rejected(repository: Path, extension: str) -> None:
    """Do not validate working bytes that differ from the committed candidate."""
    original = "package fixture\n" if extension == "go" else 'value = "staged"\n'
    file = stage(repository, f"a file.{extension}", original)
    file.write_text(original + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="Partially staged code"):
        check.check_staged()


@pytest.mark.parametrize("name", [".env", "local/inputs/example.txt", "htmlcov/index.html"])
def test_local_or_secret_paths_are_rejected(repository: Path, name: str) -> None:
    """Only synthetic fixtures are used; actual user files are never inspected."""
    stage(repository, name, "fixture\n")
    with pytest.raises(SystemExit, match="Do not commit"):
        check.check_staged()


def test_env_example_remains_allowed(repository: Path) -> None:
    """The public template is distinct from an actual credential file."""
    stage(repository, ".env.example", "# No credentials\n")
    check.check_staged()
