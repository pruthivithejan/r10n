"""Shared read-only Go/Python developer checks, including safe staged paths."""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_PATHS = ["src", "tests", "scripts"]


def run(*command: str) -> None:
    """Run one check in the repository and propagate its failure."""
    subprocess.run(command, cwd=ROOT, check=True)


def go_files() -> list[str]:
    """Return repository Go sources without traversing generated build directories."""
    result = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.go"],
        cwd=ROOT,
    )
    return sorted(
        {
            os.fsdecode(path)
            for path in result.split(b"\0")
            if path and (ROOT / os.fsdecode(path)).is_file()
        }
    )


def check_gofmt(files: list[str]) -> None:
    """Check formatting without changing working or staged Go files."""
    if not files:
        return
    result = subprocess.check_output(["gofmt", "-l", *files], cwd=ROOT)
    if result:
        raise SystemExit("Run gofmt on these files before staging:\n" + os.fsdecode(result))


def check_go() -> None:
    """Check format, module tidiness, static analysis, and Go tests."""
    check_gofmt(go_files())
    run("go", "mod", "tidy", "-diff")
    run("go", "vet", "./...")
    run("go", "test", "./...")


def check_python() -> None:
    """Check the lockfile, versions, formatting, lint, types, and Python tests."""
    run("uv", "lock", "--check")
    run("uv", "run", "--locked", "python", "scripts/release_version.py", "--check")
    run("uv", "run", "--locked", "black", "--check", *PYTHON_PATHS)
    run("uv", "run", "--locked", "ruff", "check", *PYTHON_PATHS)
    run("uv", "run", "--locked", "ty", "check", *PYTHON_PATHS)
    run("uv", "run", "--locked", "pytest")


def check_staged() -> None:
    """Validate index contents safely and check changed Go/Python files.

    Partially staged code is rejected instead of checking a different version
    or silently formatting/restaging changes. Paths are always argument arrays.
    """
    run("git", "diff", "--cached", "--check")
    result = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"], cwd=ROOT
    )
    files = [os.fsdecode(path) for path in result.split(b"\0") if path]
    for name in files:
        parts = Path(name).parts
        if any(part in {"local", "htmlcov", ".coverage"} for part in parts) or any(
            part.startswith(".env") for part in parts
        ):
            raise SystemExit(f"Do not commit local/generated/secret files: {name}")
        blob = subprocess.check_output(["git", "show", f":{name}"], cwd=ROOT)
        if len(blob) > 2 * 1024 * 1024:
            raise SystemExit(f"Staged file exceeds 2 MB: {name}")
        if re.search(rb"(?m)^(<<<<<<<|=======|>>>>>>>)", blob):
            raise SystemExit(f"Conflict marker in staged file: {name}")
        if name.endswith((".py", ".go")) and (ROOT / name).read_bytes() != blob:
            raise SystemExit(f"Partially staged code: {name}. Stage or stash remaining changes.")
        if name.endswith(".py"):
            tree = ast.parse(blob, filename=name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and (
                    (isinstance(node.func, ast.Name) and node.func.id == "breakpoint")
                    or (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "set_trace"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id in {"pdb", "ipdb"}
                    )
                ):
                    raise SystemExit(f"Debugger call in staged file: {name}")
    check_gofmt([name for name in files if name.endswith(".go")])
    python = [name for name in files if name.endswith(".py")]
    if python:
        run("uv", "run", "--locked", "black", "--check", *python)
        run("uv", "run", "--locked", "ruff", "check", *python)
        run("uv", "run", "--locked", "ty", "check", *python)
    if {"pyproject.toml", "uv.lock"} & set(files):
        run("uv", "lock", "--check")
        run("uv", "run", "--locked", "python", "scripts/release_version.py", "--check")
    if any(name.startswith(("src/", "tests/")) for name in files):
        run("uv", "run", "--locked", "pytest")
    if any(name.startswith("docs/") or name == "zensical.toml" for name in files):
        run("uv", "run", "--locked", "zensical", "build", "--clean")


def main() -> None:
    """Dispatch the shared developer checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scope", choices=("staged", "go", "go-format", "python", "all"))
    scope = parser.parse_args().scope
    if scope == "staged":
        check_staged()
    elif scope == "go-format":
        files = go_files()
        if files:
            run("gofmt", "-w", *files)
    else:
        if scope in {"go", "all"}:
            check_go()
        if scope in {"python", "all"}:
            check_python()
        if scope == "all":
            run("uv", "run", "--locked", "zensical", "build", "--clean")


if __name__ == "__main__":
    main()
