# CSS Color Conversion to OKLCH

This project includes a CLI automation to convert CSS color values (hex and
HSL) into the perceptually-uniform `oklch()` color function.

Why OKLCH
- OKLCH (derived from Oklab) is a perceptual color space that separates
  lightness, chroma and hue. Converting CSS colors to `oklch()` helps
  maintain visual consistency when adjusting color lightness or mixing
  colors.

Script
- Location: `scripts/convert_css_colors_to_oklch.py`
- What it does:
  - Searches recursively for `.css` files under a given path.
  - Replaces `#rgb`, `#rgba`, `#rrggbb`, `#rrggbbaa` and `hsl()`/`hsla()` tokens
    with `oklch()` equivalents. Alpha channel is preserved when present.
  - Creates a `.bak` backup for modified files by default.

Usage

1. Dry-run (no files modified):

```
python3 scripts/convert_css_colors_to_oklch.py . --dry-run
```

2. Apply changes (creates `.bak` files):

```
python3 scripts/convert_css_colors_to_oklch.py path/to/project
```

3. Apply changes without backups:

```
python3 scripts/convert_css_colors_to_oklch.py path/to/project --no-backup
```

Rounding and formatting
- Lightness is emitted as percentage with 1 decimal (e.g. `52.3%`).
- Chroma is rounded to 3 decimals.
- Hue is rounded to the nearest integer degree and printed with the `deg`
  unit.
- Alpha is included when present using the `/` alpha syntax.

Limitations
- `rgb()`/`rgba()` and named CSS colors are not converted yet.
- Running the script multiple times may re-convert already-converted tokens.

Next steps
1. Add `rgb()`/`rgba()` and named-color support.
2. Make replacements idempotent (skip `oklch()` tokens).
3. Add tests and a CI job to run the script in `--dry-run` mode on the repo.
