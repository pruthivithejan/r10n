"""Keep color-conversion coverage on the canonical backend implementation."""

import re
from pathlib import Path

from r10n_backend.automations import convert_colors as mod


def test_hex_and_alpha() -> None:
    """Hex colors preserve opaque and alpha channel formatting."""
    out = mod.make_replacement_for_match("#fff")
    assert out.startswith("oklch(")
    assert "/" not in out

    out2 = mod.make_replacement_for_match("#ff000080")
    assert out2.startswith("oklch(")
    assert " / " in out2


def test_rgb_and_rgba() -> None:
    """RGB and RGBA tokens use the same canonical conversion."""
    o1 = mod.make_replacement_for_match("rgb(255,0,0)")
    assert o1.startswith("oklch(")
    assert "/" not in o1

    o2 = mod.make_replacement_for_match("rgba(255,0,0,0.5)")
    assert o2.startswith("oklch(")
    assert " / 0.5" in o2


def test_rgb_percent_and_slash_alpha() -> None:
    """Modern percentage RGB syntax retains alpha."""
    o = mod.make_replacement_for_match("rgb(100% 0% 0% / 50%)")
    assert o.startswith("oklch(")
    assert " / " in o


def test_hsl_variants() -> None:
    """Both modern and comma-separated HSL syntax are supported."""
    o = mod.make_replacement_for_match("hsl(240 100% 50%)")
    assert o.startswith("oklch(")
    o2 = mod.make_replacement_for_match("hsla(240,100%,50%,0.25)")
    assert " / 0.25" in o2


def test_named_and_transparent() -> None:
    """Named and transparent colors share the canonical parser."""
    o = mod.make_replacement_for_match("rebeccapurple")
    assert o.startswith("oklch(")
    t = mod.make_replacement_for_match("transparent")
    assert " / 0.0" in t


def test_output_format_regex() -> None:
    """Generated OKLCH tokens match the documented CSS syntax."""
    sample = mod.make_replacement_for_match("#123456")
    pat = re.compile(r"^oklch\(\d{1,3}(?:\.\d+)?% \d+(?:\.\d+)? \d+deg(?: / \d+(?:\.\d+)?)?\)$")
    assert pat.match(sample)


def test_process_file_fixture(tmp_path: Path) -> None:
    """The canonical file processor converts a fixture and preserves a backup."""
    source = (Path(__file__).parent / "fixtures" / "colors_fixture.css").read_text()
    fixture = tmp_path / "colors.css"
    fixture.write_text(source, encoding="utf-8")
    result = mod.process_file(str(fixture))
    assert result["modified"] is True
    assert result["changes"] > 0
    new = fixture.read_text(encoding="utf-8")
    assert "oklch(" in new
    assert (tmp_path / "colors.css.bak").read_text(encoding="utf-8") == source
