# Publishing the Automation Toolkit as a Reusable CLI

This guide explains how to turn this repository into an installable command-line tool that others can add to their projects and use globally. It covers packaging, building, testing, publishing, and how consumers can install and extend it. No code changes are required by this guide.

---

## At a glance

- Package name (current): `automation-toolkit`
- CLI command (current): `automate` (entry point mapped in `pyproject.toml`)
- Build backend: `hatchling`
- Manager used here: `uv` (you can also use `pip`, `pipx`, or `hatch`)
- Python: 3.9+

You can publish as-is, but see “Recommended adjustments” for a future-proof layout and better import paths.

---

## Prerequisites

- A PyPI account and an API token for both TestPyPI and PyPI
- `uv` installed (or use `pip`/`pipx` equivalents)
- Clean git working tree and a tagged version in `pyproject.toml`

Optional but recommended:
- Enable 2FA on PyPI
- Set up a throwaway project on TestPyPI to dry-run releases

---

## Step 1 — Confirm or choose your public identifiers

- Distribution name (what users install): currently `automation-toolkit`
- CLI command (what users run): currently `automate`
- Import package name (what users import in Python): currently this repo ships code under a top-level module named `src` because of the packaging config.

Recommended for the next iteration (not required to publish now):
- Place sources in `src/automation_toolkit/` and expose imports like `import automation_toolkit`
- Map the entry point to `automation_toolkit.cli:main` instead of `src.cli:main`

Why: shipping a top-level package named `src` is non-idiomatic and makes imports awkward for library consumers.

---

## Step 2 — Package data you want to ship

If you want users to have default config/templates out-of-the-box, plan to include these directories in the wheel/sdist in a future update:
- `configs/` (defaults)
- `templates/` (starter templates)

With `hatchling`, this is done via include rules in `pyproject.toml`. Not required for the initial publish; you can also host templates in your repo and document how to copy them.

---

## Step 3 — Build artifacts

Using uv:

```zsh
# Build wheel and sdist
uv build

# Inspect artifacts
ls -lh dist/
```

Using Python build directly (alternative):

```zsh
uv pip install build
uv run python -m build
```

---

## Step 4 — Sanity-check the build

- Validate metadata:

```zsh
uv pip install twine
uv run twine check dist/*
```

- Test install in a clean virtual env and ensure the CLI runs:

```zsh
uv venv .dist-test
source .dist-test/bin/activate
pip install dist/*.whl

# Verify the command and help
automate --help
python -c 'import importlib; print(bool(importlib.util.find_spec("src")))'
```

Note: The import check above expects the top-level module to be `src` (current packaging). If you later migrate to a proper package name, change the probe accordingly.

---

## Step 5 — Publish to TestPyPI

Create a token on https://test.pypi.org/ and store it as an environment variable in your shell session:

```zsh
export TEST_PYPI_TOKEN="pypi-AgENdGVzdC5weXBpLm9yZwIk..."
```

Publish with uv (automatic repo selection based on URL):

```zsh
uv publish --repository-url https://test.pypi.org/legacy/ --token "$TEST_PYPI_TOKEN"
```

Alternatively with twine:

```zsh
uv run twine upload --repository-url https://test.pypi.org/legacy/ dist/* -u __token__ -p "$TEST_PYPI_TOKEN"
```

Verify install from TestPyPI in a clean env:

```zsh
uv venv .testpypi
source .testpypi/bin/activate
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple automation-toolkit
automate --version
```

---

## Step 6 — Publish to PyPI

When satisfied with TestPyPI:

```zsh
export PYPI_TOKEN="pypi-AgENd..."
uv publish --token "$PYPI_TOKEN"
# or with twine
uv run twine upload dist/* -u __token__ -p "$PYPI_TOKEN"
```

If you get “File already exists,” bump `version` in `pyproject.toml` and rebuild.

---

## Step 7 — How consumers can use it

### 1) Global CLI install (recommended for non-Python users)

- With pipx:

```zsh
pipx install automation-toolkit
# If pipx is missing:
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install automation-toolkit
```

- With uv tools (pipx alternative):

```zsh
uv tool install automation-toolkit
```

This provides the `automate` command in PATH.

### 2) Project dependency (use inside another repo)

Add to the project’s `pyproject.toml` dependencies, then call the CLI from Makefiles/CI:

```toml
[project]
dependencies = [
  "automation-toolkit>=2.0.0",
]
```

Example Make target in the consumer project:

```makefile
automate-contacts:
	automate contacts --input data/contacts.txt --output build/contacts.vcf --prefix "Customer"
```

### 3) Import as a library (Python API)

Current export path is bound to the `src` package. After a future package rename, it will look like this:

```python
# Recommended future shape
from automation_toolkit.automations.generate_contacts import generate_vcf_from_file

stats = generate_vcf_from_file(
    input_file="data/numbers.txt",
    output_file="build/contacts.vcf",
    prefix="Customer",
)
print(stats)
```

Until then, you can import via `src.automations...` (less ideal for public API).

---

## Step 8 — Extensibility (let others add their automations)

For a robust plugin story (future enhancement):

- Define an entry point group (e.g., `automation_toolkit.automations`) in `pyproject.toml`.
- Each plugin package exposes a callable or Click command factory registered under that group.
- In the main CLI, discover and load entry points dynamically, adding subcommands.

Contract for a plugin command (example):
- Inputs: Click context and options
- Output: result dict with simple metrics (`processed`, `failed`, etc.)
- Error handling: raise `click.ClickException` with user-friendly messages

This lets third-party packages add `automate my-tool ...` without changes to your core.

---

## Step 9 — Versioning, compatibility, and deprecations

- Use Semantic Versioning:
  - MAJOR: breaking CLI flags or API changes
  - MINOR: new commands/options (backward compatible)
  - PATCH: fixes and docs
- Maintain a `CHANGELOG.md` with “Added / Changed / Fixed / Deprecated / Removed” sections
- Deprecate flags with warnings before removal
- Keep Python support matrix (currently 3.9+)

---

## Step 10 — Release automation (CI)

Automate builds/tests/publish on tags. Example high-level flow:
- On push to main: run ruff + tests
- On tag `v*`: build dist, twine check, publish to PyPI using repository secrets
- Optionally publish to TestPyPI on pre-releases (tags with `-rc.*`)

Store tokens as CI secrets (never commit tokens):
- `TEST_PYPI_API_TOKEN`
- `PYPI_API_TOKEN`

---

## Troubleshooting

- Command not found after install
  - Ensure your installer wrote shims into PATH. For pipx: `python3 -m pipx ensurepath`. For uv tools: restart terminal.
- Import errors like `ModuleNotFoundError: No module named 'src'`
  - Caused by current package name layout. See “Recommended adjustments” below to migrate to a proper package name.
- Data files (templates/configs) missing after install
  - Include them in the wheel via `pyproject.toml` package data rules, or download them on first run.
- “File already exists” during upload
  - Version must be unique. Bump `version` in `pyproject.toml`.

---

## Recommended adjustments (future improvements)

These are optional and can be done after your first publish:

1) Adopt a conventional package name
- Move code to `src/automation_toolkit/` and update imports
- Change the script entry point to `automation_toolkit.cli:main`

2) Ship defaults with the wheel
- Add include rules for `configs/` and template samples
- Add lazy loading of templates via `importlib.resources`

3) Stable public API surface
- Re-export key functions under `automation_toolkit.api` for clean imports
- Document each function’s contract and error modes

4) Plugin system
- Define an entry point group and discover commands at runtime
- Provide a “create plugin” template in docs

---

## What’s already set up in this repo

- `pyproject.toml` with project metadata, dependencies, and CLI entry point:
  - `[project.scripts] automate = "src.cli:main"`
- Click-based CLI with rich TUI in `src/cli.py`
- Automations modules in `src/automations/`
- Make targets for local workflows using `uv`

You can publish with this as-is. Use this document as your checklist.

---

## Quick checklist before you hit publish

- [ ] `version` in `pyproject.toml` is updated and tagged in git
- [ ] `README.md` explains install and basic usage
- [ ] Build succeeds: `uv build`
- [ ] Twine check passes: `uv run twine check dist/*`
- [ ] Test install works in a fresh venv and `automate --help` runs
- [ ] Upload to TestPyPI, verify install/CLI
- [ ] Upload to PyPI
- [ ] Announce usage: `pipx install automation-toolkit` or `uv tool install automation-toolkit`

Happy releasing!
