"""Generated docs and installer brand assets share one ASCII source."""

from pathlib import Path

from scripts import generate_brand_assets


def test_docs_logos_match_generated_wordmark_and_r_favicon() -> None:
    """The wordmark is shadow-free SVG and the favicon is its R-only crop."""
    lines, color, background = generate_brand_assets.read_logo()
    wordmark = (generate_brand_assets.DOC_ASSETS / "r10n.svg").read_text(encoding="utf-8")
    favicon = (generate_brand_assets.DOC_ASSETS / "favicon.svg").read_text(encoding="utf-8")

    assert wordmark == generate_brand_assets.render_wordmark(lines, color)
    assert favicon == generate_brand_assets.render_favicon(lines, color, background)
    assert 'viewBox="0 0 12 12"' in favicon
    for forbidden in ("<filter", "<feDropShadow", "filter=", "box-shadow"):
        assert forbidden not in wordmark
        assert forbidden not in favicon


def test_embedded_terminal_and_installer_logos_match_canonical_source() -> None:
    """The native CLI and shell installer cannot drift from the ASCII asset."""
    lines, _, _ = generate_brand_assets.read_logo()
    canonical = generate_brand_assets.ASCII_PATH.read_text(encoding="utf-8")
    assert (generate_brand_assets.RUNTIME_BRAND / "logo.txt").read_text(
        encoding="utf-8"
    ) == canonical
    installer = Path(generate_brand_assets.INSTALLER_PATH).read_text(encoding="utf-8")
    assert generate_brand_assets.render_installer_banner(lines) in installer
