---
icon: material/palette
---

# Colors

Convert CSS color codes to the perceptual `oklch()` format. Makes color editing and mixing more predictable across lightness and hue.

---

## Overview

The Colors automation finds CSS files and converts hex colors and HSL/HSLA values to the modern `oklch()` color function.

**Key Features:**

- Convert `#rgb`, `#rgba`, `#rrggbb`, `#rrggbbaa` formats
- Convert `hsl()` and `hsla()` functions
- Preserves alpha transparency
- Interactive file selection
- Dry-run preview before changes

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors path/to/project --dry-run
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n colors path/to/project --dry-run
```

---

## Usage

### Dry Run (Preview Only)

Preview changes without modifying files:

```bash
python3 scripts/convert_css_colors_to_oklch.py path/to/project --dry-run
```

### Process All CSS Files

Convert all CSS files non-interactively:

```bash
python3 scripts/convert_css_colors_to_oklch.py path/to/project --all
```

### Interactive Mode

Select files to process one by one:

```bash
python3 scripts/convert_css_colors_to_oklch.py path/to/project
```

---

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | - | Directory containing CSS files |
| `--dry-run` | flag | No | `false` | Preview changes without writing |
| `--all` | flag | No | `false` | Process all files without prompting |

---

## Examples

### Example 1: Preview Changes

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors ./src/styles --dry-run
```

### Example 2: Convert All Files

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors ./src/styles --all
```

### Example 3: Interactive Selection

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors ./my-project
```

### Example 4: Using the Script Directly

```bash
python3 scripts/convert_css_colors_to_oklch.py ./website/css --dry-run
```

---

## Color Conversions

### Input Formats

| Format | Example | Description |
|--------|---------|-------------|
| Hex 3-digit | `#f00` | Short hex |
| Hex 4-digit | `#f00a` | Short hex with alpha |
| Hex 6-digit | `#ff0000` | Full hex |
| Hex 8-digit | `#ff0000aa` | Full hex with alpha |
| HSL | `hsl(0, 100%, 50%)` | Hue, saturation, lightness |
| HSLA | `hsla(0, 100%, 50%, 0.5)` | HSL with alpha |

### Output Format

All colors are converted to `oklch()`:

```css
/* Input */
.button {
  color: #ff0000;
  background: hsl(240, 100%, 50%);
  border-color: #00ff0080;
}

/* Output */
.button {
  color: oklch(62.8% 0.258 29.23);
  background: oklch(45.2% 0.313 264.05);
  border-color: oklch(86.6% 0.295 142.5 / 0.502);
}
```

---

## Why OKLCH?

OKLCH is a perceptually uniform color space that offers:

1. **Predictable lightness**: Equal steps in L produce equal perceived brightness changes
2. **Consistent chroma**: Colors with the same C value appear equally vivid
3. **Intuitive hue**: H rotates through the color wheel (0-360)
4. **Better gradients**: Smooth transitions without muddy midpoints

### OKLCH Format

```
oklch(L C H / A)
```

| Component | Range | Description |
|-----------|-------|-------------|
| L (Lightness) | 0% - 100% | Perceived brightness |
| C (Chroma) | 0 - 0.4+ | Color intensity/saturation |
| H (Hue) | 0 - 360 | Color angle on the wheel |
| A (Alpha) | 0 - 1 | Transparency (optional) |

---

## Output

The automation modifies CSS files in place (unless using `--dry-run`):

**Before:**
```css
:root {
  --primary: #3b82f6;
  --secondary: hsl(270, 60%, 50%);
  --accent: #22c55e;
}

.card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px #00000026;
}
```

**After:**
```css
:root {
  --primary: oklch(63.3% 0.213 255.1);
  --secondary: oklch(48.4% 0.187 303.4);
  --accent: oklch(72.3% 0.195 142.5);
}

.card {
  background: oklch(100% 0 0);
  border: 1px solid oklch(91.5% 0.006 264.5);
  box-shadow: 0 1px 3px oklch(0% 0 0 / 0.149);
}
```

---

## Troubleshooting

### "No CSS files found"

Ensure your path contains `.css` files:

```bash
find ./src -name "*.css"
```

### Colors Not Converting

Currently, these formats are **not** converted:

- `rgb()` and `rgba()` functions
- Named CSS colors (e.g., `red`, `blue`)
- CSS variables referencing colors

### Running Twice Produces Different Results

The script may re-convert already converted tokens. This will be fixed in a future update to make the operation idempotent.

### File Permissions

Ensure you have write access to the CSS files:

```bash
chmod 644 ./styles/*.css
```

---

## Limitations

1. **Not converted:** `rgb()`, `rgba()`, named colors
2. **Not idempotent:** Running twice may alter values slightly
3. **No CSS-in-JS:** Only works with `.css` files

---

## See Also

- [Images Automation](images.md) — Optimize images for web
- [Get Started Guide](../get-started/index.md) — Setup instructions
- [OKLCH Color Picker](https://oklch.com/) — Interactive OKLCH tool
