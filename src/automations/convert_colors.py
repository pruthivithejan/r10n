"""
CSS Color to OKLCH Converter automation.

Converts CSS color values (hex, hsl/hsla, rgb/rgba, named colors) to oklch() notation.
Supports both single file and directory processing.
"""

import math
import os
import re
import shutil
from pathlib import Path
from typing import Any

# Regex patterns for color matching
HEX_RE = re.compile(r"#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
HSL_FUNC_RE = re.compile(r"hsla?\([^)]*\)", re.IGNORECASE)

# Named CSS colors mapped to hex
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

# Default directories to exclude
DEFAULT_EXCLUDES = ['.venv', 'venv', 'node_modules', '.git', 'dist', 'build', '__pycache__']


def expand_hex(s: str) -> tuple[float, float, float, float]:
    """Expand hex color to RGBA values (0..1)."""
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
    """Parse HSL/HSLA parameters and return RGBA values (0..1)."""
    s = inner.strip()
    s = s.replace(',', ' ')
    s = s.replace('/', ' / ')
    parts = [p for p in s.split() if p]
    if not parts:
        raise ValueError('empty hsl()')

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
        raise ValueError('invalid hsl params')

    hue_token = vals[0]
    sat_token = vals[1]
    light_token = vals[2]

    h = None
    if hue_token.endswith('deg'):
        h = float(hue_token[:-3])
    elif hue_token.endswith('rad'):
        h = float(hue_token[:-3]) * 180.0 / math.pi
    elif hue_token.endswith('turn'):
        h = float(hue_token[:-4]) * 360.0
    else:
        h = float(hue_token)

    if sat_token.endswith('%'):
        s_val = float(sat_token[:-1]) / 100.0
    else:
        s_val = float(sat_token)
    if light_token.endswith('%'):
        l_val = float(light_token[:-1]) / 100.0
    else:
        l_val = float(light_token)

    a = 1.0
    if alpha_token.endswith('%'):
        a = float(alpha_token[:-1]) / 100.0
    else:
        a = float(alpha_token)

    r, g, b = hsl_to_rgb(h % 360.0, s_val, l_val)
    return (r, g, b, a)


def parse_rgb_params(inner: str) -> tuple[float, float, float, float]:
    """Parse RGB/RGBA parameters and return RGBA values (0..1)."""
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

    if alpha_token.endswith('%'):
        a = float(alpha_token[:-1]) / 100.0
    else:
        a = float(alpha_token)
        if a > 1:
            a = max(0.0, min(1.0, a / 255.0))

    return (r, g, b, a)


def hsl_to_rgb(h: float, s: float, light: float) -> tuple[float, float, float]:
    """Convert HSL to RGB (0..1)."""
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
    """Convert sRGB to linear RGB."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def linear_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert linear RGB to Oklab."""
    l_lin = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_lin = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_lin = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    def cbrt(x: float) -> float:
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
    """Convert RGBA to OKLCH."""
    lr = srgb_to_linear(r)
    lg = srgb_to_linear(g)
    lb = srgb_to_linear(b)
    l_lab, a_, b_ = linear_to_oklab(lr, lg, lb)
    c_val = math.hypot(a_, b_)
    h = math.degrees(math.atan2(b_, a_)) % 360.0
    return (l_lab, c_val, h, alpha)


def format_oklch(l_val: float, c_val: float, h: float, alpha: float) -> str:
    """Format OKLCH color as CSS string."""
    l_pct = round(l_val * 100.0, 1)
    c_rounded = round(c_val, 3)
    h_rounded = round(h) % 360
    if alpha is None or alpha >= 0.9999:
        return f"oklch({l_pct}% {c_rounded} {h_rounded}deg)"
    a = round(alpha, 3)
    return f"oklch({l_pct}% {c_rounded} {h_rounded}deg / {a})"


def is_within_oklch(src: str, start: int, end: int) -> bool:
    """Check if a match is already inside an oklch() call."""
    idx = src.rfind('oklch(', 0, start)
    if idx == -1:
        return False
    close = src.find(')', idx)
    if close == -1:
        return False
    return end <= close


def make_replacement_for_match(token: str) -> str:
    """Convert a color token to OKLCH format."""
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


def process_css_content(src: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Process CSS content and convert colors to OKLCH.

    Args:
        src: CSS file content

    Returns:
        tuple: (new_content, list_of_changes)
    """
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
            start_line = src.count('\n', 0, s) + 1
            snippet = src[max(0, s - 30): min(len(src), e + 30)].replace('\n', ' ')
            changes.append({'orig': token, 'repl': repl, 'line': start_line, 'snippet': snippet})
            out_parts.append(src[last:s])
            out_parts.append(repl)
            last = e
    out_parts.append(src[last:])
    new = ''.join(out_parts)

    return (new, changes)


def process_file(file_path: str, dry_run: bool = False, no_backup: bool = False) -> dict[str, Any]:
    """
    Process a single CSS file.

    Args:
        file_path: Path to CSS file
        dry_run: If True, don't write changes
        no_backup: If True, don't create backup files

    Returns:
        dict: Results with changes made
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.suffix.lower() == '.css':
        raise ValueError(f"Not a CSS file: {file_path}")

    with open(path, encoding='utf-8') as f:
        src = f.read()

    new_content, changes = process_css_content(src)

    if changes and not dry_run:
        if not no_backup:
            shutil.copy2(path, str(path) + '.bak')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)

    return {
        'file': str(path),
        'changes': len(changes),
        'change_details': changes,
        'modified': bool(changes) and not dry_run,
    }


def find_css_files(root: str, excludes: list[str] | None = None) -> list[str]:
    """
    Find all CSS files in a directory.

    Args:
        root: Root directory to search
        excludes: List of directories/patterns to exclude

    Returns:
        list: Paths to CSS files
    """
    exclude_set = set(excludes or DEFAULT_EXCLUDES)
    css_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded directories
        dirnames[:] = [d for d in dirnames if d not in exclude_set]

        for fn in filenames:
            if fn.lower().endswith('.css'):
                full = os.path.join(dirpath, fn)
                if not any(ex in full for ex in exclude_set):
                    css_files.append(full)

    return css_files


def convert_colors(
    path: str,
    file: str | None = None,
    dry_run: bool = False,
    no_backup: bool = False,
    excludes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Convert CSS colors to OKLCH format.

    Args:
        path: Directory containing CSS files (used if file is None)
        file: Single CSS file to process (takes precedence over path)
        dry_run: Preview changes without writing
        no_backup: Don't create backup files
        excludes: Additional directories to exclude

    Returns:
        dict: Results with statistics

    Raises:
        FileNotFoundError: If path/file doesn't exist
        ValueError: If no CSS files found
    """
    results = {
        'files_found': 0,
        'files_modified': 0,
        'total_changes': 0,
        'dry_run': dry_run,
        'files': [],
    }

    if file:
        # Process single file
        file_path = Path(file)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file}")

        results['files_found'] = 1
        file_result = process_file(str(file_path), dry_run=dry_run, no_backup=no_backup)
        results['files'].append(file_result)
        results['total_changes'] = file_result['changes']
        if file_result['modified']:
            results['files_modified'] = 1
    else:
        # Process directory
        root_path = Path(path)
        if not root_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        all_excludes = list(DEFAULT_EXCLUDES)
        if excludes:
            all_excludes.extend(excludes)

        css_files = find_css_files(str(root_path), all_excludes)
        results['files_found'] = len(css_files)

        if not css_files:
            raise ValueError(f"No CSS files found in: {path}")

        for css_file in css_files:
            try:
                file_result = process_file(css_file, dry_run=dry_run, no_backup=no_backup)
                results['files'].append(file_result)
                results['total_changes'] += file_result['changes']
                if file_result['modified']:
                    results['files_modified'] += 1
            except Exception as e:
                results['files'].append({
                    'file': css_file,
                    'error': str(e),
                    'changes': 0,
                    'modified': False,
                })

    return results


if __name__ == "__main__":
    print("CSS Color to OKLCH Converter")
    print("Use the main CLI: uv run r10n colors")
