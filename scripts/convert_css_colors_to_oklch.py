#!/usr/bin/env python3
"""
Find .css files and convert color values (hex, hsl/hsla) to oklch() notation.

Usage: python3 scripts/convert_css_colors_to_oklch.py [path] [--dry-run]

This script searches recursively for .css files under `path` (or current
directory) and replaces color tokens with `oklch(...)` equivalents. It
creates a .bak file for each modified file unless --no-backup is passed.

Conversion notes:
- Supports hex: #rgb, #rgba, #rrggbb, #rrggbbaa (alpha preserved)
- Supports hsl() and hsla() in both comma- and space-separated forms,
  including new CSS syntax with `/` for alpha.
- Rounds L to 1 decimal percent, C to 3 decimals, hue to integer degrees.

Implementation follows Oklab/OKLCH conversion from linear sRGB using the
matrices and equations from Björn Ottosson's Oklab specification.
"""

import argparse
import glob
import math
import os
import re
import shutil
import sys
from typing import Tuple


def debug(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


HEX_RE = re.compile(r"#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
HSL_FUNC_RE = re.compile(r"hsla?\(([^)]*)\)", re.IGNORECASE)


def expand_hex(s: str) -> Tuple[float, float, float, float]:
    # Return r,g,b,a in 0..1
    l = len(s)
    if l == 3:
        r = int(s[0] * 2, 16)
        g = int(s[1] * 2, 16)
        b = int(s[2] * 2, 16)
        a = 255
    elif l == 4:
        r = int(s[0] * 2, 16)
        g = int(s[1] * 2, 16)
        b = int(s[2] * 2, 16)
        a = int(s[3] * 2, 16)
    elif l == 6:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        a = 255
    elif l == 8:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        a = int(s[6:8], 16)
    else:
        raise ValueError("invalid hex length")
    return (r / 255.0, g / 255.0, b / 255.0, a / 255.0)


def parse_hsl_params(inner: str) -> Tuple[float, float, float, float]:
    # Returns r,g,b,a in 0..1. Accepts both comma and space syntax; alpha
    # may be a trailing value separated by comma or `/`.
    s = inner.strip()
    # Normalize commas and slashes for simple splitting
    s = s.replace(',', ' ')
    s = s.replace('/', ' / ')
    parts = [p for p in s.split() if p]
    if not parts:
        raise ValueError('empty hsl()')

    # find slash if present
    if '/' in parts:
        idx = parts.index('/')
        vals = parts[:idx]
        alpha_token = parts[idx + 1] if idx + 1 < len(parts) else '1'
    else:
        # if there are 4 tokens assume last is alpha
        if len(parts) == 4:
            vals = parts[:3]
            alpha_token = parts[3]
        else:
            vals = parts[:3]
            alpha_token = '1'

    if len(vals) < 3:
        raise ValueError('invalid hsl params')

    hue_token = vals[0]
    sat_token = vals[1]
    light_token = vals[2]

    # Hue with units
    h = None
    if hue_token.endswith('deg'):
        h = float(hue_token[:-3])
    elif hue_token.endswith('rad'):
        h = float(hue_token[:-3]) * 180.0 / math.pi
    elif hue_token.endswith('turn'):
        h = float(hue_token[:-4]) * 360.0
    else:
        h = float(hue_token)
    # saturation and lightness are percentages in CSS
    if sat_token.endswith('%'):
        s_val = float(sat_token[:-1]) / 100.0
    else:
        s_val = float(sat_token)
    if light_token.endswith('%'):
        l_val = float(light_token[:-1]) / 100.0
    else:
        l_val = float(light_token)

    # alpha parse
    a = 1.0
    if alpha_token.endswith('%'):
        a = float(alpha_token[:-1]) / 100.0
    else:
        a = float(alpha_token)

    # convert HSL to sRGB (0..1)
    r, g, b = hsl_to_rgb(h % 360.0, s_val, l_val)
    return (r, g, b, a)


def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[float, float, float]:
    # h in degrees, s,l in 0..1
    c = (1 - abs(2 * l - 1)) * s
    h_ = h / 60.0
    x = c * (1 - abs((h_ % 2) - 1))
    if 0 <= h_ < 1:
        rp, gp, bp = c, x, 0
    elif 1 <= h_ < 2:
        rp, gp, bp = x, c, 0
    elif 2 <= h_ < 3:
        rp, gp, bp = 0, c, x
    elif 3 <= h_ < 4:
        rp, gp, bp = 0, x, c
    elif 4 <= h_ < 5:
        rp, gp, bp = x, 0, c
    else:
        rp, gp, bp = c, 0, x
    m = l - c / 2
    return (rp + m, gp + m, bp + m)


def srgb_to_linear(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def linear_to_oklab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    # matrices/constants from Oklab reference implementation
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    def cbrt(x):
        if x >= 0:
            return x ** (1.0 / 3.0)
        return -((-x) ** (1.0 / 3.0))

    l_ = cbrt(l)
    m_ = cbrt(m)
    s_ = cbrt(s)

    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return (L, a, b)


def rgba_to_oklch(r: float, g: float, b: float, alpha: float) -> Tuple[float, float, float, float]:
    # r,g,b are sRGB 0..1; convert to linear, then to Oklab then to OKLCH
    lr = srgb_to_linear(r)
    lg = srgb_to_linear(g)
    lb = srgb_to_linear(b)
    L, a_, b_ = linear_to_oklab(lr, lg, lb)
    C = math.hypot(a_, b_)
    h = math.degrees(math.atan2(b_, a_)) % 360.0
    return (L, C, h, alpha)


def format_oklch(L: float, C: float, h: float, alpha: float) -> str:
    # CSS expects L as percentage. We'll round: L 1 decimal, C 3 decimals, h int, alpha 3 decimals
    Lp = round(L * 100.0, 1)
    Cp = round(C, 3)
    hp = int(round(h)) % 360
    if alpha is None or alpha >= 0.9999:
        return f"oklch({Lp}% {Cp} {hp}deg)"
    a = round(alpha, 3)
    return f"oklch({Lp}% {Cp} {hp}deg / {a})"


def replace_hex_match(m: re.Match) -> str:
    token = m.group(0)
    hexpart = m.group(1)
    try:
        r, g, b, a = expand_hex(hexpart)
    except Exception:
        return token
    L, C, h, alpha = rgba_to_oklch(r, g, b, a)
    return format_oklch(L, C, h, alpha)


def replace_hsl_match(m: re.Match) -> str:
    whole = m.group(0)
    inner = m.group(1)
    try:
        r, g, b, a = parse_hsl_params(inner)
    except Exception:
        return whole
    L, C, h, alpha = rgba_to_oklch(r, g, b, a)
    return format_oklch(L, C, h, alpha)


def process_file(path: str, dry_run: bool = False, backup: bool = True) -> Tuple[int, int]:
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    new = HEX_RE.sub(replace_hex_match, src)
    new = HSL_FUNC_RE.sub(replace_hsl_match, new)

    changed = 0
    if new != src:
        changed = 1
        if dry_run:
            debug(f"[dry-run] would change: {path}")
        else:
            if backup:
                bak = path + '.bak'
                shutil.copy2(path, bak)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new)
            debug(f"updated: {path}")
    return (changed, 1)


def find_css_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith('.css'):
                yield os.path.join(dirpath, fn)


def main():
    p = argparse.ArgumentParser(description='Convert colors in CSS to oklch()')
    p.add_argument('path', nargs='?', default='.', help='path to search (default: .)')
    p.add_argument('--dry-run', action='store_true', help='show changes but do not write')
    p.add_argument('--no-backup', action='store_true', help='do not create .bak files')
    args = p.parse_args()

    css_files = list(find_css_files(args.path))
    if not css_files:
        print('No .css files found under', args.path)
        return

    total_changed = 0
    total_files = 0
    for fpath in css_files:
        ch, tot = process_file(fpath, dry_run=args.dry_run, backup=not args.no_backup)
        total_changed += ch
        total_files += tot

    print(f"Processed {total_files} files, modified {total_changed} files")


if __name__ == '__main__':
    main()
