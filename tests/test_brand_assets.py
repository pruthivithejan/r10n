"""Generated docs and installer brand assets share one solid ASCII source."""

from pathlib import Path
from xml.etree import ElementTree

import pytest

from scripts import generate_brand_assets

NS = "{http://www.w3.org/2000/svg}"


def test_docs_logos_match_generated_wordmark_and_r_favicon() -> None:
    """Logos use the palette gradient, with no background or shadow."""
    lines, tokens = generate_brand_assets.read_logo()
    wordmark = (generate_brand_assets.DOC_ASSETS / "r10n.svg").read_text(encoding="utf-8")
    favicon = (generate_brand_assets.DOC_ASSETS / "favicon.svg").read_text(encoding="utf-8")

    assert wordmark == generate_brand_assets.render_wordmark(lines, tokens)
    assert favicon == generate_brand_assets.render_favicon(lines, tokens)
    assert 'viewBox="0 0 16 16"' in favicon
    for forbidden in (
        "<filter",
        "<feDropShadow",
        "filter=",
        "box-shadow",
        "stroke=",
        "<text",
        "<radialGradient",
    ):
        assert forbidden not in wordmark
        assert forbidden not in favicon
    for logo in (wordmark, favicon):
        tree = ElementTree.fromstring(logo)
        rects = tree.findall(f".//{NS}rect")
        assert rects
        assert all(float(rect.attrib["height"]) > 0 for rect in rects)
        fills = {element.attrib["fill"] for element in tree.iter() if "fill" in element.attrib}
        assert fills == {"url(#g)"}
        stops = {element.attrib["stop-color"] for element in tree.iter(f"{NS}stop")}
        assert stops == {tokens["light_blue"].lower(), tokens["frozen_water"].lower()}


def test_dark_logos_use_the_docs_ink() -> None:
    """Light-mode docs get a flat ink wordmark and R favicon."""
    lines, tokens = generate_brand_assets.read_logo()
    ink = tokens["doc_ink"]
    docs = generate_brand_assets.DOC_ASSETS
    assert (docs / "r10n-dark.svg").read_text(encoding="utf-8") == (
        generate_brand_assets.render_wordmark(lines, tokens, color=ink)
    )
    assert (docs / "favicon-dark.svg").read_text(encoding="utf-8") == (
        generate_brand_assets.render_favicon(lines, tokens, color=ink)
    )
    for name in ("r10n-dark.svg", "favicon-dark.svg"):
        logo = (docs / name).read_text(encoding="utf-8")
        assert f'fill="{ink}"' in logo
        assert "<linearGradient" not in logo


def test_cells_match_ascii_and_favicon_contains_only_r() -> None:
    """SVG rows preserve every source cell and the first glyph's centred crop."""
    lines, tokens = generate_brand_assets.read_logo()
    assert set("".join(lines)) == {" ", "█"}

    wordmark = ElementTree.fromstring(generate_brand_assets.render_wordmark(lines, tokens))
    cells: set[tuple[int, int]] = set()
    for rect in wordmark.findall(f".//{NS}rect"):
        x = round(float(rect.attrib["x"]))
        y = round(float(rect.attrib["y"]) / generate_brand_assets.ROW_PITCH)
        width = round(float(rect.attrib["width"]))
        cells.update((y, x + step) for step in range(width))
    expected = {
        (row, column)
        for row, line in enumerate(lines)
        for column, cell in enumerate(line)
        if cell == "█"
    }
    assert cells == expected

    from_column, to_column = generate_brand_assets.glyph_columns(lines)[0]
    assert to_column - from_column == 7
    r_cells = {
        (row, column - from_column) for row, column in expected if from_column <= column < to_column
    }

    favicon = ElementTree.fromstring(generate_brand_assets.render_favicon(lines, tokens))
    rects = favicon.findall(f".//{NS}rect")
    scale = float(rects[0].attrib["height"]) / generate_brand_assets.INK_HEIGHT
    left = min(float(rect.attrib["x"]) for rect in rects)
    top = min(float(rect.attrib["y"]) for rect in rects)
    favicon_cells: set[tuple[int, int]] = set()
    for rect in rects:
        row = round((float(rect.attrib["y"]) - top) / (generate_brand_assets.ROW_PITCH * scale))
        first = round((float(rect.attrib["x"]) - left) / (generate_brand_assets.CELL_WIDTH * scale))
        width = round(float(rect.attrib["width"]) / (generate_brand_assets.CELL_WIDTH * scale))
        favicon_cells.update((row, first + step) for step in range(width))
    assert favicon_cells == r_cells


@pytest.mark.parametrize("invalid", ["▀", "╔═╗", "█x"])
def test_shadow_or_non_block_glyphs_are_rejected(
    invalid: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Striped, shadow, and mixed geometry cannot silently return to the renderer."""
    logo = tmp_path / "r10n-wordmark.txt"
    logo.write_text(invalid, encoding="utf-8")
    monkeypatch.setattr(generate_brand_assets, "WORDMARK_PATH", logo)
    with pytest.raises(ValueError, match="full blocks"):
        generate_brand_assets.read_logo()


def test_embedded_terminal_and_installer_logos_match_canonical_source() -> None:
    """The native CLI and shell installer cannot drift from the ASCII asset."""
    lines, _ = generate_brand_assets.read_logo()
    canonical = generate_brand_assets.WORDMARK_PATH.read_text(encoding="utf-8")
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
        'alt="r10n — solid block wordmark">\n\n'
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
    assert 'content: url("../assets/brand/r10n-dark.svg")' in css
