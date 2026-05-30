"""
Tests for the company logo downloader automation.

These tests verify comma-separated input parsing, SVGL candidate handling,
download behavior, and offline uvx-compatible usage with absolute paths.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from src.automations.download_logos import (
    LogoCandidate,
    collect_svgl_candidates,
    download_logo_candidate,
    download_logos,
    fetch_json,
    normalize_download_url,
    parse_logo_names,
    rank_logo_candidates,
    sanitize_filename,
)


class FakeResponse:
    """Minimal context-manager response for urlopen tests."""

    def __init__(self, body: bytes, content_type: str):
        self.body = body
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size=-1):
        """Return response body bytes."""
        if size == -1:
            return self.body
        return self.body[:size]


def make_image_bytes(image_format: str = "PNG") -> bytes:
    """Create a small in-memory image."""
    buffer = BytesIO()
    Image.new("RGB", (24, 12), color="blue").save(buffer, image_format)
    return buffer.getvalue()


class TestLogoNameParsing:
    """Test logo name parsing and filename helpers."""

    def test_parse_logo_names_deduplicates_comma_separated_input(self):
        """Parse comma-separated names and drop duplicates."""
        result = parse_logo_names("Apple, Google, apple, , OpenAI")

        assert result == ["Apple", "Google", "OpenAI"]

    def test_parse_logo_names_rejects_empty_input(self):
        """Reject input with no usable names."""
        with pytest.raises(ValueError, match="at least one"):
            parse_logo_names(" , ")

    def test_sanitize_filename(self):
        """Create a safe lowercase filename stem."""
        assert sanitize_filename("AT&T Inc.") == "at-and-t-inc"


class TestCandidateRanking:
    """Test logo candidate ranking."""

    def test_rank_logo_candidates_prefers_svg_then_png(self):
        """SVG candidates sort before PNG candidates even when PNG dimensions are known."""
        png_candidate = LogoCandidate(
            company_name="Example",
            url="https://example.com/logo.png",
            source="official",
            format="png",
            width=2000,
            height=1000,
            priority=1,
        )
        svg_candidate = LogoCandidate(
            company_name="Example",
            url="https://example.com/logo.svg",
            source="simple-icons",
            format="svg",
            priority=50,
        )

        ranked = rank_logo_candidates([png_candidate, svg_candidate])

        assert ranked[0] == svg_candidate


class TestLogoCandidateFiltering:
    """Test URL normalization."""

    def test_normalize_download_url_encodes_spaces(self):
        """Encode spaces and collapsed newlines in candidate URLs."""
        result = normalize_download_url(
            "https://example.com/images/doTERRA\nEssential Oil-small.svg"
        )

        assert result == "https://example.com/images/doTERRA%20Essential%20Oil-small.svg"


class TestNetworkHelpers:
    """Test network helper failure handling."""

    def test_fetch_json_wraps_timeout(self):
        """Timeouts while fetching JSON become RuntimeError."""
        with (
            patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")),
            pytest.raises(RuntimeError, match="Could not fetch JSON"),
        ):
            fetch_json("https://example.com/api.json", timeout=1)


class TestSvglHelpers:
    """Test SVGL lookup helpers."""

    def test_collect_svgl_candidates_uses_matching_titles(self):
        """Build SVG candidates from matching SVGL records."""
        records = [
            {
                "title": "OpenAI",
                "route": {
                    "light": "https://svgl.app/openai-light.svg",
                    "dark": "https://svgl.app/openai-dark.svg",
                },
            },
            {
                "title": "OpenSearch",
                "route": "https://svgl.app/opensearch.svg",
            },
        ]

        with patch("src.automations.download_logos.fetch_json", return_value=records):
            candidates = collect_svgl_candidates("OpenAI")

        assert [candidate.url for candidate in candidates] == [
            "https://svgl.app/openai-light.svg",
            "https://svgl.app/openai-dark.svg",
        ]
        assert candidates[0].source == "svgl-light"

    def test_download_logos_uses_svgl_api(self, tmp_path):
        """Logo downloads should use SVGL as the only search source."""
        svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'

        with (
            patch(
                "src.automations.download_logos.fetch_json",
                return_value=[{"title": "OpenAI", "route": "https://svgl.app/openai.svg"}],
            ),
            patch("urllib.request.urlopen", return_value=FakeResponse(svg_bytes, "image/svg+xml")),
        ):
            result = download_logos(
                "OpenAI",
                output_dir=str(tmp_path),
                write_manifest=False,
            )

        assert result["downloaded"] == 1
        assert result["logos"][0]["source"] == "svgl"

    def test_download_logos_errors_when_svgl_has_no_match(self, tmp_path):
        """Missing SVGL records should produce a failed logo result."""
        with patch("src.automations.download_logos.fetch_json", return_value=[]):
            result = download_logos(
                "Unknown Brand",
                output_dir=str(tmp_path),
                write_manifest=False,
            )

        assert result["success"] is False
        assert result["downloaded"] == 0
        assert result["failed"] == 1
        assert result["logos"][0]["error"] == "No working SVG logo found in SVGL"


class TestDownloadLogoCandidate:
    """Test downloading and writing one logo candidate."""

    def test_downloads_svg_logo(self, tmp_path):
        """Download valid SVG data as an SVG file."""
        svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'
        candidate = LogoCandidate(
            company_name="Example",
            url="https://example.com/logo.svg",
            source="test",
            format="svg",
        )

        def fake_urlopen(request, timeout=20):
            return FakeResponse(svg_bytes, "image/svg+xml")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_logo_candidate(candidate, tmp_path / "example")

        output_file = Path(result["output_file"])
        assert result["success"] is True
        assert result["format"] == "svg"
        assert output_file == tmp_path / "example.svg"
        assert output_file.read_bytes() == svg_bytes

    def test_converts_raster_logo_to_png(self, tmp_path):
        """Download JPEG data and save it as PNG."""
        jpg_bytes = make_image_bytes("JPEG")
        candidate = LogoCandidate(
            company_name="Example",
            url="https://example.com/logo.jpg",
            source="test",
            format="jpg",
        )

        def fake_urlopen(request, timeout=20):
            return FakeResponse(jpg_bytes, "image/jpeg")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_logo_candidate(candidate, tmp_path / "example")

        output_file = Path(result["output_file"])
        assert result["success"] is True
        assert result["format"] == "png"
        assert output_file == tmp_path / "example.png"
        with Image.open(output_file) as image:
            assert image.format == "PNG"

    def test_downloads_url_with_spaces(self, tmp_path):
        """Percent-encode whitespace-containing logo URLs before requesting."""
        svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'
        candidate = LogoCandidate(
            company_name="Example",
            url="https://example.com/doTERRA Essential Oil.svg",
            source="test",
            format="svg",
        )
        requested_urls = []

        def fake_urlopen(request, timeout=20):
            requested_urls.append(request.full_url)
            return FakeResponse(svg_bytes, "image/svg+xml")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = download_logo_candidate(candidate, tmp_path / "example")

        assert result["success"] is True
        assert requested_urls == ["https://example.com/doTERRA%20Essential%20Oil.svg"]


class TestDownloadLogos:
    """Test end-to-end logo downloading with mocked network calls."""

    def test_downloads_logos_to_absolute_output_path_and_writes_manifest(self, tmp_path):
        """Download two logos with mocked candidates and write a manifest."""
        svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'

        def fake_collect(company_name, timeout=20, user_agent=""):
            return [
                LogoCandidate(
                    company_name=company_name,
                    url=f"https://example.com/{sanitize_filename(company_name)}.svg",
                    source="test",
                    format="svg",
                )
            ]

        def fake_urlopen(request, timeout=20):
            return FakeResponse(svg_bytes, "image/svg+xml")

        progress_results = []
        with (
            patch(
                "src.automations.download_logos.collect_logo_candidates", side_effect=fake_collect
            ),
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
        ):
            result = download_logos(
                "Apple, OpenAI",
                output_dir=str(tmp_path),
                write_manifest=True,
                progress_callback=progress_results.append,
            )

        assert result["requested"] == 2
        assert result["downloaded"] == 2
        assert result["failed"] == 0
        assert [item["company_name"] for item in progress_results] == ["Apple", "OpenAI"]
        assert (tmp_path / "apple.svg").exists()
        assert (tmp_path / "openai.svg").exists()
        assert (tmp_path / "logos_manifest.json").exists()

    def test_skips_existing_logo_without_network_search(self, tmp_path):
        """Existing logos are skipped unless overwrite is enabled."""
        existing_logo = tmp_path / "apple.svg"
        existing_logo.write_text("<svg></svg>", encoding="utf-8")

        with patch(
            "src.automations.download_logos.collect_logo_candidates",
            side_effect=AssertionError("network search should not run"),
        ):
            result = download_logos(
                "Apple",
                output_dir=str(tmp_path),
                overwrite=False,
                write_manifest=False,
            )

        assert result["downloaded"] == 0
        assert result["skipped"] == 1
        assert result["failed"] == 0
        assert result["logos"][0]["output_file"] == str(existing_logo)

    def test_overwrite_removes_stale_alternate_extension(self, tmp_path):
        """Overwrite removes an old PNG when a fresh SVG is downloaded."""
        stale_logo = tmp_path / "apple.png"
        stale_logo.write_bytes(make_image_bytes("PNG"))
        svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'

        def fake_collect(company_name, timeout=20, user_agent=""):
            return [
                LogoCandidate(
                    company_name=company_name,
                    url="https://example.com/apple.svg",
                    source="test",
                    format="svg",
                )
            ]

        def fake_urlopen(request, timeout=20):
            return FakeResponse(svg_bytes, "image/svg+xml")

        with (
            patch(
                "src.automations.download_logos.collect_logo_candidates", side_effect=fake_collect
            ),
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
        ):
            result = download_logos(
                "Apple",
                output_dir=str(tmp_path),
                overwrite=True,
                write_manifest=False,
            )

        assert result["downloaded"] == 1
        assert (tmp_path / "apple.svg").exists()
        assert not stale_logo.exists()
