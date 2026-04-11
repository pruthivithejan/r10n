# r10n Agent Guidelines

> This document defines standards for AI agents and contributors creating, maintaining, and documenting automations in r10n. Following these guidelines ensures consistency, quality, and excellent user experience across all automations.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Automation Architecture](#automation-architecture)
3. [Code Standards](#code-standards)
4. [Documentation Standards](#documentation-standards)
5. [Testing Requirements](#testing-requirements)
6. [Git Workflow](#git-workflow)
7. [MCP Server Roadmap](#mcp-server-roadmap)
8. [Examples](#examples)

---

## Project Overview

**r10n** (routine automation) is a Python CLI toolkit for automating repetitive data and workflow tasks. It provides:

- Interactive terminal UI with step-by-step prompts
- Dual execution modes: `uvx` (instant, no install) and local installation
- Beautiful Rich-powered CLI output
- Comprehensive documentation with Zensical

### Project Structure

```
r10n/
├── src/
│   ├── cli.py                    # Main CLI entry point
│   └── automations/              # Automation modules
│       ├── __init__.py
│       ├── generate_contacts.py
│       ├── fill_pdfs.py
│       ├── optimize_images.py
│       ├── send_same_email.py
│       └── utils.py
├── scripts/                      # Standalone automation scripts
├── tests/                        # pytest test suite
├── docs/                         # Zensical documentation
│   ├── index.md
│   ├── get-started/
│   └── automations/
├── configs/                      # Default configuration templates
├── pyproject.toml                # Project configuration
├── zensical.toml                 # Documentation site config
├── lefthook.yml                  # Git hooks configuration
└── AGENTS.md                     # This file
```

---

## Automation Architecture

Every automation in r10n MUST support two execution modes:

### 1. Instant Execution (uvx/uv run)

Users can run automations without installing anything:

```bash
# Run directly from GitHub (no installation)
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n <command>

# Or with uv run after cloning
uv run r10n <command>
```

**Requirements:**
- Must work without a local folder structure
- Must accept all inputs via CLI flags OR interactive prompts
- Must handle missing files gracefully with helpful error messages

### 2. Local Installation

For repeated use, users clone and set up locally:

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n <command>
```

**Requirements:**
- Must support `local/` folder structure for inputs/outputs/configs
- Should create example files when missing
- Must work with configuration files

### Automation Module Structure

Each automation module in `src/automations/` MUST follow this pattern:

```python
"""
Module docstring explaining the automation purpose.

This module provides functionality for [description].
Supports both CLI and programmatic usage.
"""

from pathlib import Path
from typing import Any

# Type hints are required
def main_function(
    input_file: str,
    output_file: str = None,
    option: str = "default",
) -> dict[str, Any]:
    """
    Main automation function.

    Args:
        input_file: Path to input file
        output_file: Path to output file (optional)
        option: Description of option

    Returns:
        dict: Results dictionary with statistics

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If input data is invalid
    """
    # Implementation
    pass


def helper_function(data: str) -> str:
    """Helper functions should also have docstrings."""
    pass


if __name__ == "__main__":
    # Example usage when run directly
    print("Use the main CLI: uv run r10n <command>")
```

### CLI Command Structure

CLI commands in `src/cli.py` MUST:

1. Display a header with automation name and description
2. Use step-by-step prompts for interactive mode
3. Accept CLI flags to bypass prompts (for scripting)
4. Show a summary before executing
5. Confirm before destructive actions
6. Display results in a formatted table

Example pattern:

```python
@main.command()
@click.option("--input", "-i", "input_file", help="Input file path")
@click.option("--output", "-o", help="Output file path")
@click.option("--flag", "-f", is_flag=True, help="Enable feature")
def mycommand(input_file, output, flag):
    """Short description of the command.

    Detailed help text explaining what the command does.
    """
    display_header("Command Name", "Brief description")

    total_steps = 3

    # Step 1: Input
    display_step(1, total_steps, "Select input")
    if not input_file:
        input_file = Prompt.ask("Enter input file path", default="default/path")

    # Validate and provide helpful feedback
    if not Path(input_file).exists():
        console.print(f"[yellow]File not found: {input_file}[/]")
        if Confirm.ask("Create example file?"):
            # Create example
            pass
        return

    # Step 2-N: Additional configuration
    # ...

    # Show summary
    console.print("[bold]Summary:[/]")
    console.print(f"  Input: {input_file}")
    console.print(f"  Output: {output}")

    # Confirm
    if not Confirm.ask("Proceed?"):
        console.print("[yellow]Cancelled.[/]")
        return

    # Execute
    try:
        results = automation_module.main_function(input_file, output)

        # Display results
        console.print("[bold green]Done![/]")
        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        for key, value in results.items():
            table.add_row(key, str(value))
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)
```

---

## Code Standards

### Python Best Practices

1. **Type Hints**: All functions MUST have type hints
   ```python
   def process(data: list[str], config: dict[str, Any]) -> dict[str, int]:
   ```

2. **Docstrings**: All public functions MUST have Google-style docstrings
   ```python
   def function(arg: str) -> bool:
       """Short description.

       Longer description if needed.

       Args:
           arg: Description of argument

       Returns:
           Description of return value

       Raises:
           ValueError: When arg is invalid
       """
   ```

3. **Error Handling**: Use specific exceptions with helpful messages
   ```python
   if not path.exists():
       raise FileNotFoundError(f"Input file not found: {path}")
   ```

4. **Imports**: Standard library first, then third-party, then local
   ```python
   import json
   import os
   from pathlib import Path

   import click
   from rich.console import Console

   from src.automations import utils
   ```

5. **Constants**: Define at module level in UPPER_CASE
   ```python
   DEFAULT_QUALITY = 85
   SUPPORTED_FORMATS = {".jpg", ".png", ".webp"}
   ```

### Linting and Formatting

- **Ruff** for linting (configured in `pyproject.toml`)
- **Black** for formatting (line length 100)
- Run before committing:
  ```bash
  uv run ruff check src tests
  uv run black src tests
  ```

---

## Documentation Standards

Every automation MUST have comprehensive documentation following this template:

### Documentation Location

- Automation docs: `docs/automations/<name>.md`
- Update index: `docs/automations/index.md`
- Update navigation: `zensical.toml`

### Documentation Template

```markdown
---
icon: material/<icon-name>
---

# <Automation Name>

<One-line description of what the automation does.>

---

## Overview

<2-3 sentences explaining the automation's purpose and key features.>

**Key Features:**
- Feature 1
- Feature 2
- Feature 3

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n <command>
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n <command>
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n <command>
```

### Command Line Mode

Pass all options directly:

```bash
uv run r10n <command> --option1 value1 --option2 value2
```

---

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `--input` / `-i` | string | Yes | - | Path to input file |
| `--output` / `-o` | string | No | `local/outputs/<name>/` | Output path |
| `--option` | string | No | `default` | Description |
| `--flag` / `-f` | flag | No | `false` | Enable feature |

---

## Examples

### Example 1: Basic Usage

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n <command> \
  --input path/to/input.txt
```

### Example 2: With All Options

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n <command> \
  --input path/to/input.txt \
  --output path/to/output \
  --option value \
  --flag
```

### Example 3: Local Installation

```bash
uv run r10n <command> \
  --input local/inputs/<name>/data.txt \
  --output local/outputs/<name>/result
```

---

## Input Format

<Describe expected input format with examples>

```
# Example input file
line 1
line 2
```

---

## Output

<Describe what the automation produces>

- Output location: `local/outputs/<name>/`
- Output format: <description>

---

## Configuration

<If the automation uses config files>

Create `local/configs/<name>.json`:

```json
{
  "option1": "value1",
  "option2": 123
}
```

| Config Key | Type | Description |
|------------|------|-------------|
| `option1` | string | Description |
| `option2` | number | Description |

---

## Troubleshooting

### Common Issues

**Issue: Error message**
- Cause: Description
- Solution: Steps to fix

**Issue: Another error**
- Cause: Description
- Solution: Steps to fix

---

## See Also

- [Related Automation](./related.md)
- [Get Started Guide](../get-started/index.md)
```

### Index Card Format

Add a card to `docs/automations/index.md`:

```html
<a href="<name>/" style="text-decoration:none; border:1px solid var(--md-default-fg-color--lightest); border-radius:1rem; padding:1.15rem 1rem; display:flex; flex-direction:column; align-items:center; background:var(--md-accent-fg-color--lightest)">
  <span class="twemoji"><svg><!-- icon svg --></svg></span>
  <span style="font-weight:600; margin-top:.3em;"><Name></span>
  <span style="font-size:.95em; margin-top:3px; color:var(--md-default-fg-color--light)">Short description</span>
</a>
```

### Navigation Update

Add to `zensical.toml`:

```toml
{ "Automations" = [
    # ... existing
    "automations/<name>.md",
]}
```

---

## Testing Requirements

### Test File Location

Tests go in `tests/test_<module_name>.py`

### Test Structure

```python
"""
Tests for the <automation name> automation.

These tests verify the <functionality> both for local usage and uvx distribution.
"""

import tempfile
from pathlib import Path

import pytest

from src.automations.<module> import (
    main_function,
    helper_function,
)


class TestHelperFunction:
    """Test helper function functionality."""

    def test_valid_input(self):
        """Test with valid input."""
        result = helper_function("valid")
        assert result == "expected"

    def test_invalid_input(self):
        """Test with invalid input."""
        result = helper_function("invalid")
        assert result is None

    def test_edge_case(self):
        """Test edge case."""
        result = helper_function("")
        assert result is None


class TestMainFunction:
    """Test main automation function."""

    def test_basic_usage(self):
        """Test basic functionality."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test data\n")
            input_file = f.name

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "output.txt"
            result = main_function(input_file, str(output_file))

            assert result["success"] == True
            assert output_file.exists()

        Path(input_file).unlink()

    def test_file_not_found(self):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            main_function("nonexistent_file.txt")


class TestUvxCompatibility:
    """Test that the module works correctly when run via uvx."""

    def test_module_import(self):
        """Test module can be imported."""
        from src.automations import <module>
        assert hasattr(<module>, "main_function")

    def test_output_to_absolute_path(self):
        """Test output to absolute path works without local folder."""
        # Test implementation
        pass
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_<module>.py

# Run specific test
uv run pytest tests/test_<module>.py::TestClass::test_method
```

### Test Requirements

1. **Coverage**: Aim for >80% coverage on automation modules
2. **Edge Cases**: Test empty inputs, invalid data, missing files
3. **uvx Compatibility**: Test that module works with absolute paths
4. **Mocking**: Use tempfile for file operations, avoid touching real files

---

## Git Workflow

### Pre-commit Hooks (lefthook)

The project uses lefthook for git hooks. Hooks run automatically:

- **pre-commit**: Lint staged Python files, run tests if test files changed
- **pre-push**: Run full lint and test suite

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]
```

Types:
- `feat`: New feature or automation
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(automations): add PDF merger automation
fix(contacts): handle international phone formats
docs(automations): add colors automation documentation
test(images): add edge case tests for WebP conversion
```

### Adding a New Automation Checklist

1. [ ] Create automation module in `src/automations/<name>.py`
2. [ ] Add CLI command in `src/cli.py`
3. [ ] Write tests in `tests/test_<name>.py`
4. [ ] Create documentation in `docs/automations/<name>.md`
5. [ ] Add card to `docs/automations/index.md`
6. [ ] Update `zensical.toml` navigation
7. [ ] Add default config (if needed) to `configs/<name>.default.json`
8. [ ] Run tests: `uv run pytest`
9. [ ] Run linting: `uv run ruff check src tests`
10. [ ] Commit with appropriate message

---

## MCP Server Roadmap

### Overview

The Model Context Protocol (MCP) enables AI applications to connect to external tools. r10n automations are excellent candidates for MCP tools.

### Architecture Plan

```
r10n-mcp-server/
├── src/
│   └── mcp_server.py        # FastMCP server implementation
├── pyproject.toml           # Separate package or same package
└── README.md
```

### Implementation Approach

1. **Use FastMCP (Python SDK)**
   ```python
   from mcp.server.fastmcp import FastMCP

   mcp = FastMCP("r10n")

   @mcp.tool()
   async def generate_contacts(
       input_file: str,
       prefix: str = "Contact",
       output_file: str = None
   ) -> str:
       """Generate VCF contact cards from phone numbers.

       Args:
           input_file: Path to file with phone numbers (one per line)
           prefix: Prefix for contact names
           output_file: Output VCF file path
       """
       from src.automations.generate_contacts import generate_vcf_from_file
       result = generate_vcf_from_file(input_file, output_file, prefix)
       return f"Generated {result['valid']} contacts to {result['output_file']}"
   ```

2. **Tool Registration for Each Automation**
   - `generate_contacts`: Generate VCF from phone numbers
   - `optimize_images`: Optimize images to WebP
   - `fill_pdfs`: Fill PDF templates with data
   - `send_emails`: Send bulk emails (with confirmation)
   - `convert_colors`: Convert CSS colors to oklch

3. **Configuration**
   Claude Desktop config (`claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "r10n": {
         "command": "uv",
         "args": ["--directory", "/path/to/r10n", "run", "mcp-server"]
       }
     }
   }
   ```

4. **Safety Considerations**
   - Email automation requires explicit confirmation
   - File operations should be sandboxed to project directory
   - Sensitive data (SMTP credentials) handled via environment variables

### Next Steps

1. Create `src/mcp_server.py` with FastMCP implementation
2. Add `mcp` dependency to `pyproject.toml`
3. Create entry point: `r10n-mcp = "src.mcp_server:main"`
4. Write MCP-specific documentation
5. Test with Claude Desktop

---

## Examples

### Example: Creating a New Automation

Let's walk through creating a "PDF Merger" automation.

#### 1. Create the module (`src/automations/merge_pdfs.py`)

```python
"""
PDF Merger automation.

Combines multiple PDF files into a single document.
"""

from pathlib import Path
from typing import Any

from PyPDF2 import PdfMerger


def merge_pdfs(
    input_files: list[str],
    output_file: str = "merged.pdf",
) -> dict[str, Any]:
    """
    Merge multiple PDF files into one.

    Args:
        input_files: List of PDF file paths to merge
        output_file: Output file path

    Returns:
        dict: Results with file count and output path

    Raises:
        FileNotFoundError: If any input file doesn't exist
        ValueError: If no input files provided
    """
    if not input_files:
        raise ValueError("No input files provided")

    # Validate all files exist
    for file_path in input_files:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

    # Handle output path
    output_path = Path(output_file)
    if not output_path.is_absolute() and len(output_path.parts) == 1:
        output_path = Path("local/outputs/pdfs") / output_file

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Merge PDFs
    merger = PdfMerger()
    for pdf_file in input_files:
        merger.append(pdf_file)

    merger.write(str(output_path))
    merger.close()

    return {
        "files_merged": len(input_files),
        "output_file": str(output_path),
    }


if __name__ == "__main__":
    print("PDF Merger")
    print("Use the main CLI: uv run r10n pdfs")
```

#### 2. Add CLI command (`src/cli.py`)

```python
@main.command()
@click.option("--input", "-i", "input_files", multiple=True, help="Input PDF files")
@click.option("--output", "-o", help="Output PDF file path")
def pdfs(input_files, output):
    """Merge multiple PDF files into one

    Combine PDF documents in the order specified.
    """
    display_header("PDF Merger", "Combine multiple PDF files")
    # ... implementation
```

#### 3. Write tests (`tests/test_merge_pdfs.py`)

```python
"""Tests for PDF merger automation."""

import tempfile
from pathlib import Path

import pytest

from src.automations.merge_pdfs import merge_pdfs


class TestMergePdfs:
    def test_merge_two_files(self):
        """Test merging two PDF files."""
        # Create test PDFs and verify merge
        pass

    def test_empty_input(self):
        """Test error on empty input."""
        with pytest.raises(ValueError):
            merge_pdfs([])
```

#### 4. Create documentation (`docs/automations/pdfs.md`)

Following the template above.

#### 5. Update index and navigation

Add card to `docs/automations/index.md` and entry to `zensical.toml`.

---

## Summary

Following these guidelines ensures:

- Consistent, high-quality automations
- Excellent user experience with both instant and local execution
- Comprehensive documentation for easy copy-paste usage
- Reliable tests for maintainability
- Clear path for future MCP integration

For questions or clarifications, open an issue on GitHub.
