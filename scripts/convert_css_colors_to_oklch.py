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
import math
import os
import re
import shutil
import sys


def debug(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


HEX_RE = re.compile(r"#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
HSL_FUNC_RE = re.compile(r"hsla?\(([^)]*)\)", re.IGNORECASE)

# Partial list of standard CSS color keywords mapped to hex. Used to parse
# named colors like 'rebeccapurple', 'transparent' is handled separately.
NAMED_COLORS = {
    'aliceblue': '#f0f8ff', 'antiquewhite': '#faebd7', 'aqua': '#00ffff',
    'aquamarine': '#7fffd4', 'azure': '#f0ffff', 'beige': '#f5f5dc',
    'bisque': '#ffe4c4', 'black': '#000000', 'blanchedalmond': '#ffebcd',
    'blue': '#0000ff', 'blueviolet': '#8a2be2', 'brown': '#a52a2a',
    'burlywood': '#deb887', 'cadetblue': '#5f9ea0', 'chartreuse': '#7fff00',
    'chocolate': '#d2691e', 'coral': '#ff7f50', 'cornflowerblue': '#6495ed',
    'cornsilk': '#fff8dc', 'crimson': '#dc143c', 'cyan': '#00ffff',
    'darkblue': '#00008b', 'darkcyan': '#008b8b', 'darkgoldenrod': '#b8860b',
    'darkgray': '#a9a9a9', 'darkgreen': '#006400', 'darkgrey': '#a9a9a9',
    'darkkhaki': '#bdb76b', 'darkmagenta': '#8b008b', 'darkolivegreen': '#556b2f',
    'darkorange': '#ff8c00', 'darkorchid': '#9932cc', 'darkred': '#8b0000',
    'darksalmon': '#e9967a', 'darkseagreen': '#8fbc8f', 'darkslateblue': '#483d8b',
    'darkslategray': '#2f4f4f', 'darkslategrey': '#2f4f4f', 'darkturquoise': '#00ced1',
    'darkviolet': '#9400d3', 'deeppink': '#ff1493', 'deepskyblue': '#00bfff',
    'dimgray': '#696969', 'dimgrey': '#696969', 'dodgerblue': '#1e90ff',
    'firebrick': '#b22222', 'floralwhite': '#fffaf0', 'forestgreen': '#228b22',
    'fuchsia': '#ff00ff', 'gainsboro': '#dcdcdc', 'ghostwhite': '#f8f8ff',
    'gold': '#ffd700', 'goldenrod': '#daa520', 'gray': '#808080', 'green': '#008000',
    'greenyellow': '#adff2f', 'grey': '#808080', 'honeydew': '#f0fff0',
    'hotpink': '#ff69b4', 'indianred': '#cd5c5c', 'indigo': '#4b0082',
    'ivory': '#fffff0', 'khaki': '#f0e68c', 'lavender': '#e6e6fa',
    'lavenderblush': '#fff0f5', 'lawngreen': '#7cfc00', 'lemonchiffon': '#fffacd',
    'lightblue': '#add8e6', 'lightcoral': '#f08080', 'lightcyan': '#e0ffff',
    'lightgoldenrodyellow': '#fafad2', 'lightgray': '#d3d3d3', 'lightgreen': '#90ee90',
    'lightgrey': '#d3d3d3', 'lightpink': '#ffb6c1', 'lightsalmon': '#ffa07a',
    'lightseagreen': '#20b2aa', 'lightskyblue': '#87cefa', 'lightslategray': '#778899',
    'lightslategrey': '#778899', 'lightsteelblue': '#b0c4de', 'lightyellow': '#ffffe0',
    'lime': '#00ff00', 'limegreen': '#32cd32', 'linen': '#faf0e6', 'magenta': '#ff00ff',
    'maroon': '#800000', 'mediumaquamarine': '#66cdaa', 'mediumblue': '#0000cd',
    'mediumorchid': '#ba55d3', 'mediumpurple': '#9370db', 'mediumseagreen': '#3cb371',
    'mediumslateblue': '#7b68ee', 'mediumspringgreen': '#00fa9a', 'mediumturquoise': '#48d1cc',
    'mediumvioletred': '#c71585', 'midnightblue': '#191970', 'mintcream': '#f5fffa',
    'mistyrose': '#ffe4e1', 'moccasin': '#ffe4b5', 'navajowhite': '#ffdead', 'navy': '#000080',
    'oldlace': '#fdf5e6', 'olive': '#808000', 'olivedrab': '#6b8e23', 'orange': '#ffa500',
    'orangered': '#ff4500', 'orchid': '#da70d6', 'palegoldenrod': '#eee8aa',
    'palegreen': '#98fb98', 'paleturquoise': '#afeeee', 'palevioletred': '#db7093',
    'papayawhip': '#ffefd5', 'peachpuff': '#ffdab9', 'peru': '#cd853f', 'pink': '#ffc0cb',
    'plum': '#dda0dd', 'powderblue': '#b0e0e6', 'purple': '#800080', 'rebeccapurple': '#663399',
    'red': '#ff0000', 'rosybrown': '#bc8f8f', 'royalblue': '#4169e1', 'saddlebrown': '#8b4513',
    'salmon': '#fa8072', 'sandybrown': '#f4a460', 'seagreen': '#2e8b57', 'seashell': '#fff5ee',
    'sienna': '#a0522d', 'silver': '#c0c0c0', 'skyblue': '#87ceeb', 'slateblue': '#6a5acd',
    'slategray': '#708090', 'slategrey': '#708090', 'snow': '#fffafa', 'springgreen': '#00ff7f',
    'steelblue': '#4682b4', 'tan': '#d2b48c', 'teal': '#008080', 'thistle': '#d8bfd8',
    'tomato': '#ff6347', 'turquoise': '#40e0d0', 'violet': '#ee82ee', 'wheat': '#f5deb3',
    'white': '#ffffff', 'whitesmoke': '#f5f5f5', 'yellow': '#ffff00', 'yellowgreen': '#9acd32'
}

NAMED_PATTERN = r"\b(?:" + "|".join(re.escape(n) for n in NAMED_COLORS.keys()) + r")\b"


def expand_hex(s: str) -> tuple[float, float, float, float]:
    # Return r,g,b,a in 0..1
    length = len(s)
    if length == 3:
        r = int(s[0] * 2, 16)
        g = int(s[1] * 2, 16)
        b = int(s[2] * 2, 16)
        a = 255
    elif length == 4:
        r = int(s[0] * 2, 16)
        g = int(s[1] * 2, 16)
        b = int(s[2] * 2, 16)
        a = int(s[3] * 2, 16)
    elif length == 6:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        a = 255
    elif length == 8:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        a = int(s[6:8], 16)
    else:
        raise ValueError("invalid hex length")
    return (r / 255.0, g / 255.0, b / 255.0, a / 255.0)


def parse_hsl_params(inner: str) -> tuple[float, float, float, float]:
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


def parse_rgb_params(inner: str) -> tuple[float, float, float, float]:
    # Parse rgb()/rgba() CSS function parameters. Accepts comma or space syntax
    # and optional alpha (with '/' or as fourth parameter). Returns r,g,b,a in 0..1
    s = inner.strip()
    s = s.replace(',', ' ')
    s = s.replace('/', ' / ')
    parts = [p for p in s.split() if p]
    if not parts:
        raise ValueError('empty rgb()')

    if '/' in parts:
        idx = parts.index('/')
        vals = parts[:idx]
        alpha_token = parts[idx + 1] if idx + 1 < len(parts) else '1'
    else:
        if len(parts) == 4:
            vals = parts[:3]
            alpha_token = parts[3]
        else:
            vals = parts[:3]
            alpha_token = '1'

    if len(vals) < 3:
        raise ValueError('invalid rgb params')

    def parse_channel(tok: str) -> float:
        if tok.endswith('%'):
            return float(tok[:-1]) / 100.0
        return float(tok) / 255.0

    r = parse_channel(vals[0])
    g = parse_channel(vals[1])
    b = parse_channel(vals[2])

    # alpha
    if alpha_token.endswith('%'):
        a = float(alpha_token[:-1]) / 100.0
    else:
        a = float(alpha_token)
        if a > 1:
            # maybe specified 0-255 range, clamp
            a = max(0.0, min(1.0, a / 255.0))

    return (r, g, b, a)


def hsl_to_rgb(h: float, s: float, light: float) -> tuple[float, float, float]:
    # h in degrees, s and light in 0..1
    c = (1 - abs(2 * light - 1)) * s
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
    m = light - c / 2
    return (rp + m, gp + m, bp + m)


def srgb_to_linear(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def linear_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    # matrices/constants from Oklab reference implementation
    l_lin = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_lin = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_lin = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    def cbrt(x):
        if x >= 0:
            return x ** (1.0 / 3.0)
        return -((-x) ** (1.0 / 3.0))

    l_ = cbrt(l_lin)
    m_ = cbrt(m_lin)
    s_ = cbrt(s_lin)

    l_val = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return (l_val, a, b)


def rgba_to_oklch(r: float, g: float, b: float, alpha: float) -> tuple[float, float, float, float]:
    # r,g,b are sRGB 0..1; convert to linear, then to Oklab then to OKLCH
    lr = srgb_to_linear(r)
    lg = srgb_to_linear(g)
    lb = srgb_to_linear(b)
    l_lab, a_, b_ = linear_to_oklab(lr, lg, lb)
    c_val = math.hypot(a_, b_)
    h = math.degrees(math.atan2(b_, a_)) % 360.0
    return (l_lab, c_val, h, alpha)


def format_oklch(l_val: float, c_val: float, h: float, alpha: float) -> str:
    # CSS expects L as percentage. We'll round: L 1 decimal, C 3 decimals, h int, alpha 3 decimals
    l_pct = round(l_val * 100.0, 1)
    c_rounded = round(c_val, 3)
    h_rounded = round(h) % 360
    if alpha is None or alpha >= 0.9999:
        return f"oklch({l_pct}% {c_rounded} {h_rounded}deg)"
    a = round(alpha, 3)
    return f"oklch({l_pct}% {c_rounded} {h_rounded}deg / {a})"




def is_within_oklch(src: str, start: int, end: int) -> bool:
    # Determine if the match at [start:end] is inside an oklch(...) call
    # by searching backwards for 'oklch(' and seeing if a closing ')' occurs after end.
    idx = src.rfind('oklch(', 0, start)
    if idx == -1:
        return False
    # find the next ')' after idx
    close = src.find(')', idx)
    if close == -1:
        return False
    return end <= close


def make_replacement_for_match(token: str) -> str:
    # Decide if token is hex or hsl and produce replacement, or return original on failure
    tl = token.strip().lower()
    if tl.startswith('hsl'):
        inner = token[token.find('(') + 1: token.rfind(')')]
        try:
            r, g, b, a = parse_hsl_params(inner)
        except Exception:
            return token
        l_val, c_val, h, alpha = rgba_to_oklch(r, g, b, a)
        return format_oklch(l_val, c_val, h, alpha)
    if tl.startswith('rgb'):
        inner = token[token.find('(') + 1: token.rfind(')')]
        try:
            r, g, b, a = parse_rgb_params(inner)
        except Exception:
            return token
        l_val, c_val, h, alpha = rgba_to_oklch(r, g, b, a)
        return format_oklch(l_val, c_val, h, alpha)
    # named color (including 'transparent')
    if tl == 'transparent':
        r, g, b, a = 0.0, 0.0, 0.0, 0.0
        l_val, c_val, h, alpha = rgba_to_oklch(r, g, b, a)
        return format_oklch(l_val, c_val, h, alpha)
    if tl in NAMED_COLORS:
        hexpart = NAMED_COLORS[tl].lstrip('#')
        try:
            r, g, b, a = expand_hex(hexpart)
        except Exception:
            return token
        l_val, c_val, h, alpha = rgba_to_oklch(r, g, b, a)
        return format_oklch(l_val, c_val, h, alpha)
    else:
        # hex
        m = re.match(r"#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b", token)
        if not m:
            return token
        hexpart = m.group(1)
        try:
            r, g, b, a = expand_hex(hexpart)
        except Exception:
            return token
        l_val, c_val, h, alpha = rgba_to_oklch(r, g, b, a)
        return format_oklch(l_val, c_val, h, alpha)


def process_file(path: str) -> tuple[int, int, str, list]:
    with open(path, encoding='utf-8') as f:
        src = f.read()

    pattern = re.compile(
        r"(#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b|hsla?\([^)]*\)|rgba?\([^)]*\)|" + NAMED_PATTERN + r")",
        re.IGNORECASE,
    )

    out_parts = []
    last = 0
    changes = []
    for m in pattern.finditer(src):
        s, e = m.span()
        token = m.group(0)
        if is_within_oklch(src, s, e):
            continue
        repl = make_replacement_for_match(token)
        if repl != token:
            # record change
            # capture a small snippet around the token for preview
            start_line = src.count('\n', 0, s) + 1
            snippet = src[max(0, s - 30): min(len(src), e + 30)].replace('\n', ' ')
            changes.append({'orig': token, 'repl': repl, 'line': start_line, 'snippet': snippet})
            out_parts.append(src[last:s])
            out_parts.append(repl)
            last = e
    out_parts.append(src[last:])
    new = ''.join(out_parts)

    changed = 1 if changes else 0
    return (changed, 1, new, changes)


def find_css_files(root: str):
    # kept for backward compatibility; prefer find_css_files_with_excludes
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith('.css'):
                yield os.path.join(dirpath, fn)


def find_css_files_with_excludes(root: str, excludes: list[str]):
    # Walk the tree but prune directories in 'excludes'. Excludes may be
    # file/directory names (e.g. '.venv', 'node_modules') or path fragments.
    exclude_set = set(excludes or [])
    for dirpath, dirnames, filenames in os.walk(root):
        # prune dirnames in-place so os.walk won't traverse them
        pruned = []
        for d in list(dirnames):
            if d in exclude_set:
                dirnames.remove(d)
            else:
                # also prune common virtual env dirs by prefix
                if any(d == ex or d.startswith(ex) for ex in exclude_set):
                    try:
                        dirnames.remove(d)
                    except ValueError:
                        pass
        for fn in filenames:
            if fn.lower().endswith('.css'):
                full = os.path.join(dirpath, fn)
                # skip if any exclude fragment is in the full path
                if any(ex in full for ex in exclude_set):
                    continue
                yield full


def main():
    p = argparse.ArgumentParser(description='Convert colors in CSS to oklch()')
    p.add_argument('path', nargs='?', default='.', help='path to search (default: .)')
    p.add_argument('--dry-run', action='store_true', help='show changes but do not write')
    p.add_argument('--no-backup', action='store_true', help='do not create .bak files')
    p.add_argument('--all', action='store_true', help='process all found .css files without prompting')
    p.add_argument('--exclude', action='append', help='glob or path fragment to exclude (can be passed multiple times)')
    args = p.parse_args()

    # default excludes for common generated or third-party folders
    default_excludes = ['.venv', 'venv', 'node_modules', '.git', 'dist', 'build']
    if args.exclude:
        default_excludes.extend(args.exclude)
    css_files = list(find_css_files_with_excludes(args.path, default_excludes))
    if not css_files:
        print('No .css files found under', args.path)
        return

    # Interactive selection when multiple files found and --all not passed
    selected = css_files
    if not args.all and sys.stdin.isatty() and len(css_files) > 1:
        print(f"Found {len(css_files)} .css files under {args.path}:")
        for i, pth in enumerate(css_files, start=1):
            print(f"  {i}. {pth}")
        print("\nEnter a number to process a single file, a comma-separated list (e.g. 1,3), 'a' for all, or 'q' to cancel:")
        resp = input('> ').strip()
        if not resp:
            print('No selection, aborting.')
            return
        if resp.lower() == 'q':
            print('Cancelled')
            return
        if resp.lower() == 'a':
            selected = css_files
        else:
            parts = [s.strip() for s in resp.split(',') if s.strip()]
            picks = []
            try:
                for p in parts:
                    idx = int(p)
                    if 1 <= idx <= len(css_files):
                        picks.append(css_files[idx - 1])
                if not picks:
                    print('No valid selections made, aborting.')
                    return
                selected = picks
            except ValueError:
                print('Invalid selection, aborting.')
                return

    results = []
    for fpath in selected:
        ch, _tot, new, changes = process_file(fpath)
        results.append({'path': fpath, 'changed': ch, 'new': new, 'changes': changes})

    files_with_changes = [r for r in results if r['changed']]
    if not files_with_changes:
        print('No color tokens to convert in the selected files.')
        return

    if args.dry_run:
        print('Dry run — the following changes would be made:')
        for r in files_with_changes:
            print(f"\nFile: {r['path']}")
            for c in r['changes']:
                print(f"  Line {c['line']}: {c['orig']} -> {c['repl']}")
                print(f"    ...{c['snippet']}...")
        print('\nNo files were modified (dry-run).')
        return

    # Confirm before applying if multiple files and interactive
    if not args.all and sys.stdin.isatty() and len(files_with_changes) > 1:
        print('The following files will be updated:')
        for r in files_with_changes:
            print(f"  {r['path']} ({len(r['changes'])} change(s))")
        resp = input('\nProceed to apply these changes? [y/N]: ').strip().lower()
        if resp != 'y':
            print('Aborted — no files changed.')
            return

    total_changed = 0
    total_files = 0
    for r in results:
        total_files += 1
        if not r['changed']:
            continue
        if not args.no_backup:
            bak = r['path'] + '.bak'
            shutil.copy2(r['path'], bak)
        with open(r['path'], 'w', encoding='utf-8') as f:
            f.write(r['new'])
        print(f"updated: {r['path']} ({len(r['changes'])} change(s))")
        total_changed += 1

    print(f"Processed {total_files} files, modified {total_changed} files")


if __name__ == '__main__':
    main()
