"""Generated docs and installer brand assets share one ASCII source."""

from pathlib import Path
from xml.etree import ElementTree

import pytest

from scripts import generate_brand_assets


def test_docs_logos_match_generated_wordmark_and_r_favicon() -> None:
    """Logos use only the primary foreground, with no background or shadow."""
    lines, color = generate_brand_assets.read_logo()
    wordmark = (generate_brand_assets.DOC_ASSETS / "r10n.svg").read_text(encoding="utf-8")
    favicon = (generate_brand_assets.DOC_ASSETS / "favicon.svg").read_text(encoding="utf-8")

    assert wordmark == generate_brand_assets.render_wordmark(lines, color)
    assert favicon == generate_brand_assets.render_favicon(lines, color)
    assert 'viewBox="0 0 16 16"' in favicon
    for forbidden in (
        "<filter",
        "<feDropShadow",
        "filter=",
        "box-shadow",
        "stroke=",
        "<text",
        "<linearGradient",
        "<radialGradient",
        "<stop",
    ):
        assert forbidden not in wordmark
        assert forbidden not in favicon
    for logo in (wordmark, favicon):
        tree = ElementTree.fromstring(logo)
        rects = tree.findall(".//{http://www.w3.org/2000/svg}rect")
        assert rects
        assert all(rect.attrib["height"] == "1" for rect in rects)
        fills = {element.attrib["fill"] for element in tree.iter() if "fill" in element.attrib}
        assert fills == {color}


def test_stripes_match_ascii_cells_and_favicon_contains_only_r() -> None:
    """SVG rows preserve every source cell and the first glyph's centered crop."""
    lines, color = generate_brand_assets.read_logo()
    assert set("".join(lines)) == {" ", "▀"}
    wordmark = ElementTree.fromstring(generate_brand_assets.render_wordmark(lines, color))
    favicon = ElementTree.fromstring(generate_brand_assets.render_favicon(lines, color))
    ns = "{http://www.w3.org/2000/svg}"
    for tree, source, x_offset, y_offset in (
        (wordmark, lines, 0, 0),
        (favicon, [line[:7] for line in lines], 4.5, 1.5),
    ):
        cells: set[tuple[int, int]] = set()
        for rect in tree.findall(f".//{ns}rect"):
            x = int(float(rect.attrib["x"]) - x_offset)
            y = int((float(rect.attrib["y"]) - y_offset) / 2)
            cells.update((y, x + dx) for dx in range(int(rect.attrib["width"])))
        expected = {
            (row, column)
            for row, line in enumerate(source)
            for column, cell in enumerate(line)
            if cell == "▀"
        }
        assert cells == expected


@pytest.mark.parametrize("invalid", ["█", "╔═╗", "▀x"])
def test_shadow_or_non_stripe_glyphs_are_rejected(invalid: str) -> None:
    """Old block/shadow geometry cannot silently return to the renderer."""
    with pytest.raises(ValueError, match="stripe blocks"):
        generate_brand_assets.render_glyphs([invalid])


def test_embedded_terminal_and_installer_logos_match_canonical_source() -> None:
    """The native CLI and shell installer cannot drift from the ASCII asset."""
    lines, _ = generate_brand_assets.read_logo()
    canonical = generate_brand_assets.ASCII_PATH.read_text(encoding="utf-8")
    assert (generate_brand_assets.RUNTIME_BRAND / "logo.txt").read_text(
        encoding="utf-8"
    ) == canonical
    installer = Path(generate_brand_assets.INSTALLER_PATH).read_text(encoding="utf-8")
    assert generate_brand_assets.render_installer_banner(lines) in installer


def test_installer_generation_preserves_surrounding_download_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regeneration changes only its marked block, including on a second run."""
    installer = tmp_path / "install.sh"
    prefix = "#!/bin/sh\n# existing download and theme code\n"
    suffix = "\n# existing checksum and installation code\n"
    installer.write_text(
        prefix
        + generate_brand_assets.INSTALLER_START
        + "\nold banner\n"
        + generate_brand_assets.INSTALLER_END
        + suffix,
        encoding="utf-8",
    )
    monkeypatch.setattr(generate_brand_assets, "INSTALLER_PATH", installer)
    lines, _ = generate_brand_assets.read_logo()
    for _ in range(2):
        generate_brand_assets.update_installer_banner(lines)
        assert installer.read_text(encoding="utf-8") == (
            prefix + generate_brand_assets.render_installer_banner(lines) + suffix
        )


def test_readme_starts_with_modest_logo_then_tagline() -> None:
    """The README has one small logo, no redundant word heading, and descriptive alt text."""
    readme = (generate_brand_assets.ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.startswith(
        '<img src="docs/assets/brand/r10n.svg" width="220" '
        'alt="r10n — striped routine automation wordmark">\n\n'
        "**Routine automation in an accessible, keyboard-first terminal.**"
    )
    assert "\n# r10n\n" not in "\n" + readme
    assert readme.count("docs/assets/brand/r10n.svg") == 1


def test_header_hides_only_duplicate_site_topic_visually() -> None:
    """Site-name accessibility and the normal second page-title topic are preserved."""
    css = (generate_brand_assets.ROOT / "docs/stylesheets/extra.css").read_text(encoding="utf-8")
    logo_rule = css.split(".md-header__button.md-logo {", 1)[1].split("}", 1)[0]
    assert "display: block" in logo_rule
    assert "background: transparent" in logo_rule
    assert "border-radius" not in logo_rule
    rule = css.split(".md-header__topic:first-child {", 1)[1].split("}", 1)[0]
    assert "clip-path: inset(50%)" in rule
    assert "display: none" not in rule
    assert "visibility: hidden" not in rule
    assert ".md-header__topic {" not in css.splitlines()
    assert ".md-header__title {" not in css
    page_rule = css.split(".md-header__title .md-header__topic + .md-header__topic {", 1)[1].split(
        "}", 1
    )[0]
    assert "opacity: 1;" in page_rule
    assert "transform: none;" in page_rule
