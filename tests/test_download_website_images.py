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
    normalize_output_format,
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
        """Extract images from img, srcset, source, link icons, and style URLs."""
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
            "https://example.com/hero.jpg",
            "https://example.com/hero-small.jpg",
            "https://example.com/hero-large.jpg",
            "https://cdn.example.com/photo.webp",
            "https://example.com/background.png",
        ]

    def test_deduplicates_urls(self):
        """Deduplicate repeated URLs while preserving order."""
        html = '<img src="/same.jpg"><img src="/same.jpg#section">'

        result = extract_image_urls(html, "https://example.com")

        assert result == ["https://example.com/same.jpg"]


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
        """Download images from mocked HTML and write converted files."""
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

    def test_invalid_url_raises_value_error(self, tmp_path):
        """Reject invalid website URLs."""
        with pytest.raises(ValueError, match="valid website URL"):
            download_website_images("example.com", output_dir=str(tmp_path))
