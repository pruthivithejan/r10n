"""
Tests for the website image downloader automation.

These tests verify page image extraction, conversion, and offline uvx-compatible
usage with absolute output paths.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from src.automations.download_website_images import (
    build_output_filename,
    convert_image_bytes,
    download_website_images,
    extract_image_urls,
    extract_page_links,
    get_page_output_directory,
    image_variant_key,
    normalize_output_format,
    select_highest_resolution_image_urls,
)


class FakeHeaders:
    """Minimal headers object for urlopen response tests."""

    def get_content_charset(self):
        """Return no explicit charset."""
        return None


class FakeResponse:
    """Minimal context-manager response for urlopen tests."""

    def __init__(self, body: bytes):
        self.body = body
        self.headers = FakeHeaders()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        """Return response body bytes."""
        return self.body


def make_image_bytes(image_format: str = "PNG") -> bytes:
    """Create a small in-memory image."""
    buffer = BytesIO()
    Image.new("RGB", (20, 10), color="red").save(buffer, image_format)
    return buffer.getvalue()


class TestExtractImageUrls:
    """Test HTML image URL extraction."""

    def test_extracts_common_image_sources(self):
        """Extract images and keep the largest candidate from responsive sources."""
        html = """
        <html>
          <head><link rel="icon" href="/favicon.png"></head>
          <body>
            <img src="/hero.jpg" srcset="/hero-small.jpg 1x, /hero-large.jpg 2x">
            <picture><source srcset="https://cdn.example.com/photo.webp 800w"></picture>
            <div style="background-image: url('/background.png')"></div>
            <img src="data:image/png;base64,ignored">
          </body>
        </html>
        """

        result = extract_image_urls(html, "https://example.com/page/")

        assert result == [
            "https://example.com/favicon.png",
            "https://example.com/hero-large.jpg",
            "https://cdn.example.com/photo.webp",
            "https://example.com/background.png",
        ]

    def test_deduplicates_urls(self):
        """Deduplicate repeated URLs while preserving order."""
        html = '<img src="/same.jpg"><img src="/same.jpg#section">'

        result = extract_image_urls(html, "https://example.com")

        assert result == ["https://example.com/same.jpg"]

    def test_ignores_fragment_only_references(self):
        """Ignore SVG-internal and placeholder fragment references, not real paths."""
        html = """
        <img src="#b">
        <img src="%23b">
        <div style="clip-path: url(#clip0_3705_6923)"></div>
        <img src="/real.jpg#anchor">
        """

        result = extract_image_urls(html, "https://example.com/stays")

        assert result == ["https://example.com/real.jpg"]

    def test_deduplicates_query_resized_variants_to_largest(self):
        """Keep only the largest query-resized variant of the same image."""
        html = """
        <img
          src="/photo-1200x800.jpg?w=2048&q=75&auto=format"
          srcset="/photo-1200x800.jpg?w=256&q=75&auto=format 256w,
                  /photo-1200x800.jpg?w=640&q=75&auto=format 640w,
                  /photo-1200x800.jpg?w=2048&q=75&auto=format 2048w">
        """

        result = extract_image_urls(html, "https://example.com")

        assert result == ["https://example.com/photo-1200x800.jpg?w=2048&q=75&auto=format"]


class TestSelectHighestResolutionImageUrls:
    """Test responsive image variant selection."""

    def test_groups_urls_without_responsive_query_parameters(self):
        """Build the same variant key for different widths of one image."""
        first = image_variant_key("https://example.com/photo.jpg?w=256&q=75&auto=format")
        second = image_variant_key("https://example.com/photo.jpg?w=2048&q=90&auto=format")

        assert first == second

    def test_keeps_largest_query_width_variant(self):
        """Keep the URL with the largest requested width."""
        result = select_highest_resolution_image_urls(
            [
                "https://example.com/photo.jpg?w=256&q=75",
                "https://example.com/photo.jpg?w=2048&q=75",
                "https://example.com/photo.jpg?w=640&q=75",
            ]
        )

        assert result == ["https://example.com/photo.jpg?w=2048&q=75"]

    def test_keeps_largest_filename_dimension_variant(self):
        """Keep the URL with the largest filename dimensions."""
        result = select_highest_resolution_image_urls(
            [
                "https://example.com/photo-320x180.jpg",
                "https://example.com/photo-1920x1080.jpg",
                "https://example.com/photo-800x450.jpg",
            ]
        )

        assert result == ["https://example.com/photo-1920x1080.jpg"]


class TestExtractPageLinks:
    """Test same-site page link extraction."""

    def test_extracts_same_site_links(self):
        """Extract same-host page links and ignore external or non-page protocols."""
        html = """
        <a href="/about">About</a>
        <a href="https://example.com/tours/rafting?ref=nav">Rafting</a>
        <a href="https://other.example.com/external">External</a>
        <a href="/files/brochure.pdf">PDF</a>
        <a href="mailto:hello@example.com">Email</a>
        <a href="#section">Section</a>
        """

        result = extract_page_links(html, "https://example.com", "https://example.com")

        assert result == [
            "https://example.com/about",
            "https://example.com/tours/rafting?ref=nav",
        ]


class TestFormatAndFilenames:
    """Test output format and filename helpers."""

    def test_normalize_output_format_accepts_supported_formats(self):
        """Normalize supported output formats."""
        assert normalize_output_format(".WEBP") == "webp"
        assert normalize_output_format("jpeg") == "jpeg"

    def test_normalize_output_format_rejects_unsupported_formats(self):
        """Reject unsupported output formats."""
        with pytest.raises(ValueError, match="Unsupported output format"):
            normalize_output_format("svg")

    def test_build_output_filename_sanitizes_url_path(self):
        """Create safe filenames from URL paths."""
        result = build_output_filename(
            "https://example.com/images/My Photo!.png?size=large", 2, "jpg"
        )

        assert result == "002-My-Photo.jpg"

    def test_build_output_filename_uses_index_when_name_missing(self):
        """Use image index when URL path has no filename."""
        result = build_output_filename("https://example.com/", 3, "webp")

        assert result == "003-image-3.webp"


class TestPageOutputDirectories:
    """Test page URL to folder mapping."""

    def test_homepage_images_go_to_root(self, tmp_path):
        """Map homepage URL to the output root."""
        result = get_page_output_directory(tmp_path, "https://example.com/", "https://example.com")

        assert result == tmp_path

    def test_subpage_images_go_to_matching_folder(self, tmp_path):
        """Map nested page paths to nested output folders."""
        result = get_page_output_directory(
            tmp_path,
            "https://example.com/tours/white-water-rafting/",
            "https://example.com",
        )

        assert result == tmp_path / "tours" / "white-water-rafting"

    def test_html_page_uses_stem_folder(self, tmp_path):
        """Use page stem instead of .html filename extension."""
        result = get_page_output_directory(
            tmp_path,
            "https://example.com/about.html",
            "https://example.com",
        )

        assert result == tmp_path / "about"


class TestConvertImageBytes:
    """Test image conversion."""

    def test_convert_png_to_webp(self, tmp_path):
        """Convert image bytes to WebP."""
        output_file = tmp_path / "image.webp"

        convert_image_bytes(make_image_bytes("PNG"), output_file, "webp", quality=80)

        assert output_file.exists()
        with Image.open(output_file) as image:
            assert image.format == "WEBP"

    def test_convert_png_to_jpg(self, tmp_path):
        """Convert image bytes to JPEG."""
        output_file = tmp_path / "image.jpg"

        convert_image_bytes(make_image_bytes("PNG"), output_file, "jpg", quality=80)

        assert output_file.exists()
        with Image.open(output_file) as image:
            assert image.format == "JPEG"


class TestDownloadWebsiteImages:
    """Test end-to-end website image downloading with mocked network calls."""

    def test_downloads_and_converts_images_to_absolute_output_path(self, tmp_path):
        """Download homepage images from mocked HTML and write converted files."""
        html = b"""
        <html>
          <body>
            <img src="/one.png">
            <img src="https://example.com/two.jpg">
          </body>
        </html>
        """
        image_bytes = make_image_bytes("PNG")

        def fake_urlopen(request, timeout=20):
            url = request.full_url
            if url == "https://example.com/page":
                return FakeResponse(html)
            if url in {"https://example.com/one.png", "https://example.com/two.jpg"}:
                return FakeResponse(image_bytes)
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_website_images(
                "https://example.com/page",
                output_dir=str(tmp_path),
                output_format="png",
            )

        assert result["found"] == 2
        assert result["downloaded"] == 2
        assert result["failed"] == 0
        assert Path(result["files"][0]["output_file"]).exists()
        assert (tmp_path / "001-one.png").exists()
        assert (tmp_path / "002-two.png").exists()

    def test_downloads_only_largest_responsive_variant(self, tmp_path):
        """Download only the highest-resolution URL from responsive image variants."""
        html = b"""
        <html>
          <body>
            <img
              src="/photo-1200x800.jpg?w=2048&q=75&auto=format"
              srcset="/photo-1200x800.jpg?w=256&q=75&auto=format 256w,
                      /photo-1200x800.jpg?w=640&q=75&auto=format 640w,
                      /photo-1200x800.jpg?w=2048&q=75&auto=format 2048w">
          </body>
        </html>
        """
        image_bytes = make_image_bytes("PNG")
        downloaded_urls = []

        def fake_urlopen(request, timeout=20):
            url = request.full_url
            if url == "https://example.com/page":
                return FakeResponse(html)
            if url == "https://example.com/photo-1200x800.jpg?w=2048&q=75&auto=format":
                downloaded_urls.append(url)
                return FakeResponse(image_bytes)
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_website_images(
                "https://example.com/page",
                output_dir=str(tmp_path),
                output_format="jpg",
            )

        assert result["found"] == 1
        assert result["downloaded"] == 1
        assert result["failed"] == 0
        assert downloaded_urls == ["https://example.com/photo-1200x800.jpg?w=2048&q=75&auto=format"]
        assert (tmp_path / "001-photo-1200x800.jpg").exists()

    def test_crawls_pages_and_places_images_in_page_folders(self, tmp_path):
        """Crawl same-site pages and mirror page paths in output folders."""
        homepage_html = b"""
        <html>
          <body>
            <img src="/home.png">
            <a href="/about">About</a>
            <a href="https://example.com/tours/rafting/">Rafting</a>
            <a href="https://other.example.com/ignored">Ignored</a>
          </body>
        </html>
        """
        about_html = b'<html><body><img src="/about.png"></body></html>'
        rafting_html = b'<html><body><img src="/rafting.png"></body></html>'
        image_bytes = make_image_bytes("PNG")

        def fake_urlopen(request, timeout=20):
            url = request.full_url
            if url == "https://example.com/":
                return FakeResponse(homepage_html)
            if url == "https://example.com/about":
                return FakeResponse(about_html)
            if url == "https://example.com/tours/rafting/":
                return FakeResponse(rafting_html)
            if url in {
                "https://example.com/home.png",
                "https://example.com/about.png",
                "https://example.com/rafting.png",
            }:
                return FakeResponse(image_bytes)
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_website_images(
                "https://example.com/",
                output_dir=str(tmp_path),
                output_format="png",
            )

        assert result["pages_scanned"] == 3
        assert result["found"] == 3
        assert result["downloaded"] == 3
        assert (tmp_path / "001-home.png").exists()
        assert (tmp_path / "about" / "001-about.png").exists()
        assert (tmp_path / "tours" / "rafting" / "001-rafting.png").exists()

    def test_respects_max_pages(self, tmp_path):
        """Stop crawling after the requested page limit."""
        html = b"""
        <html>
          <body>
            <img src="/home.png">
            <a href="/about">About</a>
          </body>
        </html>
        """
        image_bytes = make_image_bytes("PNG")

        def fake_urlopen(request, timeout=20):
            url = request.full_url
            if url == "https://example.com/":
                return FakeResponse(html)
            if url == "https://example.com/home.png":
                return FakeResponse(image_bytes)
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_website_images(
                "https://example.com/",
                output_dir=str(tmp_path),
                output_format="png",
                max_pages=1,
            )

        assert result["pages_scanned"] == 1
        assert result["found"] == 1
        assert (tmp_path / "001-home.png").exists()
        assert not (tmp_path / "about").exists()

    def test_invalid_url_raises_value_error(self, tmp_path):
        """Reject invalid website URLs."""
        with pytest.raises(ValueError, match="valid website URL"):
            download_website_images("example.com", output_dir=str(tmp_path))
