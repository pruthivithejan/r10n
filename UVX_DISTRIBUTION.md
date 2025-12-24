# Making r10n Accessible via `uvx`

A comprehensive guide to publishing r10n as a Python package so anyone with Python and uv installed can run it with a single command.

## Table of Contents

1. [Overview](#overview)
2. [Current Status](#current-status)
3. [Distribution Strategy](#distribution-strategy)
4. [Phase 1: Prepare Your Package](#phase-1-prepare-your-package)
5. [Phase 2: Publish to PyPI](#phase-2-publish-to-pypi)
6. [Phase 3: User Experience](#phase-3-user-experience)
7. [Testing & Verification](#testing--verification)
8. [Maintenance](#maintenance)

---

## Overview

With `uvx`, users can run r10n without cloning the repository or managing virtual environments:

```bash
# Simple, one-command interface
uvx r10n contacts --input numbers.csv --prefix "Customer"
```

This eliminates the need for:
- Cloning the repository
- Creating virtual environments
- Running setup scripts
- Managing dependencies locally

### What is `uvx`?

`uvx` is the uv package manager's tool execution command. It:
- Downloads your package from PyPI
- Creates an isolated, temporary environment
- Executes the specified command
- Cleans up after itself

**Perfect for**: One-off tools and utilities that users occasionally need.

---

## Current Status

✅ **Your package is already well-configured for distribution!**

### What's Already in Place

1. **Proper project structure** (`pyproject.toml`)
   ```toml
   [project]
   name = "r10n"
   version = "2.0.0"
   
   [project.scripts]
   r10n = "src.cli:main"
   ```

2. **Entry point defined** - Maps `r10n` command to `src.cli:main` function
3. **All dependencies listed** - Dependencies are clearly specified
4. **CLI interface** - Beautiful Click-based CLI is ready to go

### What Needs Enhancement

Minor improvements to make publishing production-ready:

1. Author information (currently placeholder)
2. Package metadata (keywords, classifiers)
3. License file reference
4. Repository/documentation URLs in metadata

---

## Distribution Strategy

### Architecture

```
┌─────────────────────────────────────────┐
│     User's Terminal (anywhere)          │
├─────────────────────────────────────────┤
│  $ uvx r10n contacts --input data.csv   │
│                                         │
│  ↓ uv installs from PyPI               │
│  ↓ Creates isolated environment        │
│  ↓ Runs command                        │
│  ↓ Cleans up                           │
│                                         │
│  Output: contacts.vcf ✅               │
└─────────────────────────────────────────┘
         │
         └──→ PyPI (Python Package Index)
               └──→ r10n v2.0.0
                   ├── Dependencies (pre-resolved)
                   └── Entry point: r10n
```

### How It Works

1. **User runs**: `uvx r10n contacts --input data.csv`
2. **uv downloads**: Latest `r10n` package from PyPI
3. **uv creates**: Isolated virtual environment with all dependencies
4. **uv executes**: `r10n contacts --input data.csv`
5. **uv cleans**: Removes temporary environment

---

## Phase 1: Prepare Your Package

### Step 1: Update Project Metadata

Edit `pyproject.toml` and improve the metadata:

```toml
[project]
name = "r10n"
version = "2.0.0"
description = "r10n (routine automation): Automates repetitive routines like emails, certificates, contacts, images, and more"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"
authors = [
    { name = "Your Name", email = "your-email@example.com" }
]
keywords = [
    "automation",
    "email",
    "certificates",
    "contacts",
    "vcf",
    "images",
    "blog",
    "routine"
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: End Users/Desktop",
    "Topic :: Utilities",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "pandas>=2.0.0",
    "pypdf2>=3.0.0",
    "reportlab>=4.0.0",
    "pillow>=10.0.0",
    "openai>=1.0.0",
    "click>=8.1.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "openpyxl>=3.0.0",
    "zensical>=0.0.8",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "ruff>=0.1.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
]

[project.urls]
Homepage = "https://github.com/pruthivithejan/r10n"
Documentation = "https://github.com/pruthivithejan/r10n#readme"
Repository = "https://github.com/pruthivithejan/r10n.git"
"Issue Tracker" = "https://github.com/pruthivithejan/r10n/issues"

[project.scripts]
r10n = "src.cli:main"
```

### Step 2: Ensure LICENSE File Exists

Create or verify `LICENSE` file exists in the root:

```bash
# Check if MIT license exists
ls -la LICENSE
```

If it doesn't exist, create one:

```bash
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2024 Pruthvi Thejan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
```

### Step 3: Verify Build System

Your `pyproject.toml` already has this, but verify:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

### Step 4: Test Local Build

Build your package locally to ensure everything works:

```bash
# Build the package
uv build

# You should see:
# Successfully built dist/r10n-2.0.0-py3-none-any.whl
# Successfully built dist/r10n-2.0.0.tar.gz
```

Verify the build artifacts:

```bash
ls -lh dist/
# Output should show:
# -rw-r--r-- r10n-2.0.0-py3-none-any.whl
# -rw-r--r-- r10n-2.0.0.tar.gz
```

### Step 5: Verify Entry Point

Ensure the CLI entry point works:

```bash
# Test the built package
uv run --no-project -i dist/r10n-2.0.0-py3-none-any.whl r10n --help

# You should see the banner and help text
```

---

## Phase 2: Publish to PyPI

### Step 1: Create PyPI Account

1. Go to [https://pypi.org/account/register/](https://pypi.org/account/register/)
2. Complete the registration process
3. Verify your email address

### Step 2: Generate PyPI API Token

1. Log in to [https://pypi.org/manage/account/](https://pypi.org/manage/account/)
2. Click **"Add API token"**
3. Set scope to **"Entire account"** (or specific project after first upload)
4. Copy the token (starts with `pypi-`)
5. **Keep this token secret!** - Store it securely

### Step 3: Configure uv for Publishing

Create or update your local uv configuration:

```bash
# On macOS/Linux
mkdir -p ~/.config/uv
cat > ~/.config/uv/uv.toml << 'EOF'
[publish]
index = "https://upload.pypi.org/legacy/"
EOF
```

Or set environment variable:

```bash
export UV_PUBLISH_TOKEN="pypi-your-token-here"
```

### Step 4: Publish to PyPI

```bash
# First time publishing (with token)
uv publish --token "pypi-your-token-here"

# You should see:
# Uploading r10n-2.0.0-py3-none-any.whl ... ✓
# Uploading r10n-2.0.0.tar.gz ... ✓
```

Or using environment variable:

```bash
export UV_PUBLISH_TOKEN="pypi-your-token-here"
uv publish
```

### Step 5: Verify on PyPI

1. Visit [https://pypi.org/project/r10n/](https://pypi.org/project/r10n/)
2. Verify your package information appears correctly
3. Check the README is formatted properly

---

## Phase 3: User Experience

### For End Users: The Simple Workflow

Once published to PyPI, users can do this:

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create a CSV file with phone numbers
cat > numbers.csv << EOF
0771234567
0712345678
+94771234567
EOF

# 3. Generate VCF contacts (one command!)
uvx r10n contacts \
  --input numbers.csv \
  --prefix "Customer" \
  --output contacts.vcf

# 4. Done! contacts.vcf is ready to import
```

### Available Commands

Users can discover all available commands:

```bash
# See all available automations
uvx r10n --help

# Specific command help
uvx r10n contacts --help
uvx r10n email --help
uvx r10n certificates --help
uvx r10n images --help
uvx r10n blog --help
```

### Version Pinning

Users can run specific versions:

```bash
# Run version 2.0.0 specifically
uvx r10n@2.0.0 contacts --input data.csv

# Run latest version explicitly
uvx r10n@latest contacts --input data.csv
```

### Installation (Optional)

For frequent users, they can install permanently:

```bash
# Install r10n as a persistent tool
uv tool install r10n

# Now available without uvx
r10n contacts --input data.csv
```

---

## Testing & Verification

### Test 1: Local Testing Before Publishing

```bash
# Build locally
uv build

# Test the built package
uv run --no-project -i dist/r10n-2.0.0-py3-none-any.whl \
  r10n contacts --help

# Should show the banner and help
```

### Test 2: Test with PyPI TestPyPI

Before publishing to main PyPI, test on TestPyPI:

```bash
# Create account at https://test.pypi.org/account/register/
# Generate API token at https://test.pypi.org/manage/account/

# Publish to TestPyPI
uv publish --index testpypi

# Test installation
uvx --from https://test.pypi.org/simple/ r10n@2.0.0 --help
```

### Test 3: After Publishing to PyPI

```bash
# Clean up local build
rm -rf dist/

# Test with fresh download from PyPI
uvx r10n --help

# Test with specific version
uvx r10n@2.0.0 --help

# Test a real use case
echo "0771234567" > test.csv
uvx r10n contacts --input test.csv --prefix "Test" --output test.vcf
ls -lh test.vcf  # Should exist
```

### Test 4: Cross-Platform Testing

If possible, test on:
- macOS
- Linux (Ubuntu)
- Windows PowerShell

Users on different platforms should all be able to run:

```bash
uvx r10n contacts --input data.csv
```

---

## Maintenance

### Updating Your Package

When you release a new version:

```bash
# 1. Update version in pyproject.toml
uv version 2.1.0

# 2. Commit changes
git add pyproject.toml uv.lock
git commit -m "Bump version to 2.1.0"
git tag v2.1.0

# 3. Build
uv build

# 4. Publish
uv publish --token "your-token"

# Users automatically get updates:
uvx r10n@latest contacts --input data.csv
```

### Deprecation & Breaking Changes

Document breaking changes clearly:

```bash
# In your release notes/changelog:
# v3.0.0 - BREAKING: Removed support for --legacy-format
#         - Use: uvx r10n@2.1.0 for legacy support
```

### Version Constraints

Users can specify version constraints:

```bash
# Run version 2.x.x only
uvx --from 'r10n>=2.0.0,<3.0.0' contacts --help

# Run within a specific range
uvx --from 'r10n>=2.0.0,<2.2.0' contacts --help
```

---

## Quick Reference: Command Cheat Sheet

### For Package Maintainers (You)

```bash
# Build locally
uv build

# Test locally
uv run --no-project -i dist/r10n-*.whl r10n --help

# Publish to PyPI
uv publish --token "your-token"

# Update version
uv version 2.1.0

# Upgrade package on PyPI (after making changes)
uv build
uv publish --token "your-token"
```

### For End Users

```bash
# Basic usage
uvx r10n contacts --input data.csv

# With version pinning
uvx r10n@2.0.0 contacts --input data.csv

# Install for repeated use
uv tool install r10n
r10n contacts --input data.csv

# Upgrade installed tool
uv tool upgrade r10n

# See all available commands
uvx r10n --help
```

---

## Troubleshooting

### Issue: "Package not found on PyPI"

**Solution**: Wait 5-10 minutes after publishing. PyPI caches may take time to update.

```bash
# Retry after a few minutes
uvx r10n --help
```

### Issue: "Permission denied when publishing"

**Solution**: Verify your API token is correct and has the right permissions.

```bash
# Re-generate token at https://pypi.org/manage/account/
# Ensure it has "Entire account" scope or project scope
uv publish --token "pypi-new-token"
```

### Issue: "Import errors when running uvx"

**Solution**: Verify all dependencies are listed in `pyproject.toml`:

```bash
# Check what's installed in the virtual environment
uvx --with pytest r10n --help  # Run with extra package

# If still broken, debug with:
uvx r10n --help  # See error messages
```

### Issue: "Entry point not found"

**Solution**: Verify `[project.scripts]` is correct in `pyproject.toml`:

```toml
[project.scripts]
r10n = "src.cli:main"  # Module path must be correct
```

And test locally:

```bash
uv build
uv run --no-project -i dist/r10n-*.whl r10n --help
```

---

## Next Steps

1. ✅ Update `pyproject.toml` with proper metadata
2. ✅ Ensure LICENSE file exists
3. ✅ Test locally with `uv build`
4. ✅ Create PyPI account and get API token
5. ✅ Publish to TestPyPI first (optional but recommended)
6. ✅ Publish to PyPI with `uv publish`
7. ✅ Test with `uvx r10n --help`
8. ✅ Update README with "Quick Start with uvx" section

---

## Example README Section

Add this to your README.md for users:

```markdown
## 🚀 Quick Start with uvx (No Installation Needed)

If you have Python 3.10+ and [uv](https://docs.astral.sh/uv/) installed:

```bash
# Run directly without cloning
uvx r10n contacts --input numbers.csv --prefix "Customer"
```

This downloads r10n, runs the command, and cleans up - no setup required!

### First-time setup (uv)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# That's it! You're ready to use r10n
```

### Common use cases

```bash
# Generate contact cards
uvx r10n contacts --input numbers.csv --prefix "Customer"

# Send emails
uvx r10n email --recipients emails.csv --body template.txt

# Generate certificates
uvx r10n certificates --recipients data.txt --template template.pdf

# See all available commands
uvx r10n --help
```

### For frequent users (optional installation)

If you use r10n often, install it permanently:

```bash
uv tool install r10n

# Now available anywhere
r10n contacts --input data.csv
```
```

---

## Summary

By following this guide, you'll have:

| ✅ | Feature |
|----|---------|
| ✅ | Package on PyPI accessible to 3M+ Python users |
| ✅ | One-command execution: `uvx r10n contacts --input data.csv` |
| ✅ | No installation/cloning required for end users |
| ✅ | Automatic dependency management |
| ✅ | Version control and easy upgrades |
| ✅ | Cross-platform compatibility |

Your tool will be truly accessible to anyone with Python and uv installed! 🎉

