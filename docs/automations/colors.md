---
icon: material/robot
---

# Colors — CSS to OKLCH

This automation finds `.css` files and converts CSS color tokens (hex and
HSL/HSLA) to the perceptual `oklch()` function. Use it to make color edits
and mixing behave more predictably across lightness and hue.

Script location: `scripts/convert_css_colors_to_oklch.py`

Features
- Convert `#rgb`, `#rgba`, `#rrggbb`, `#rrggbbaa` and `hsl()`/`hsla()` into
  `oklch()` (alpha preserved).
- Interactive selection of files, dry-run preview, and confirmation before
  writing changes.

Usage

Dry run (preview only):

```
python3 scripts/convert_css_colors_to_oklch.py path/to/project --dry-run
```

Process all CSS files non-interactively:

```
python3 scripts/convert_css_colors_to_oklch.py path/to/project --all
```

Notes and limitations
- `rgb()`/`rgba()` and named CSS colors are not converted yet.
- Running the script twice may re-convert tokens — future improvements will
  make the operation idempotent.

See `scripts/convert_css_colors_to_oklch.py` for implementation details.
