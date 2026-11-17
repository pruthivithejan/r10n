"""Tests for the asset video automation."""

import subprocess
from pathlib import Path

import pytest
from PIL import Image
from reportlab.pdfgen import canvas

from r10n_backend import deps
from r10n_backend.automations import asset_video
from r10n_backend.deps import find_tool

requires_ffmpeg = pytest.mark.skipif(find_tool("ffmpeg") is None, reason="ffmpeg is not installed")


def make_pdf(path, pages=2):
    """Create a simple PDF with distinct page colors."""
    document = canvas.Canvas(str(path), pagesize=(200, 300))
    colors = [(0.8, 0.1, 0.1), (0.1, 0.4, 0.8), (0.2, 0.7, 0.3)]
    for index in range(pages):
        red, green, blue = colors[index % len(colors)]
        document.setFillColorRGB(red, green, blue)
        document.rect(0, 0, 200, 300, fill=1, stroke=0)
        document.showPage()
    document.save()


class TestDiscovery:
    """Verify asset discovery and ordering."""

    def test_discovers_images_and_pdf_pages(self, tmp_path):
        """Images and PDFs are found and PDFs report their page count."""
        Image.new("RGB", (40, 40), "red").save(tmp_path / "b.png")
        Image.new("RGB", (40, 40), "blue").save(tmp_path / "a.jpg")
        make_pdf(tmp_path / "brand.pdf", pages=3)

        assets = asset_video.discover_assets(tmp_path)

        assert [asset.relative_name for asset in assets] == [
            "a.jpg",
            "b.png",
            "brand.pdf",
        ]
        assert assets[-1].kind == "pdf"
        assert assets[-1].pages == 3

    def test_recursive_scan_includes_nested_assets(self, tmp_path):
        """Nested assets appear only when recursion is enabled."""
        Image.new("RGB", (20, 20), "red").save(tmp_path / "root.png")
        nested = tmp_path / "nested"
        nested.mkdir()
        Image.new("RGB", (20, 20), "blue").save(nested / "inside.png")

        assert len(asset_video.discover_assets(tmp_path)) == 1
        recursive = asset_video.discover_assets(tmp_path, recursive=True)
        assert [asset.relative_name for asset in recursive] == [
            "nested/inside.png",
            "root.png",
        ]

    def test_hidden_files_are_ignored(self, tmp_path):
        """Hidden files and folders do not become slides."""
        Image.new("RGB", (20, 20), "red").save(tmp_path / ".hidden.png")
        hidden_dir = tmp_path / ".cache"
        hidden_dir.mkdir()
        Image.new("RGB", (20, 20), "blue").save(hidden_dir / "asset.png")

        assert asset_video.discover_assets(tmp_path, recursive=True) == []

    def test_missing_folder_raises(self, tmp_path):
        """A missing input folder is reported clearly."""
        with pytest.raises(FileNotFoundError, match="Input folder not found"):
            asset_video.discover_assets(tmp_path / "missing")


class TestOrderParsing:
    """Verify order and page-selection parsing."""

    def test_semicolon_separated_order(self):
        """Semicolons keep PDF page commas inside one reference."""
        tokens = asset_video.split_order_spec("cover.png;brand.pdf:1,3-5;logo.png")

        assert tokens == ["cover.png", "brand.pdf:1,3-5", "logo.png"]

    def test_comma_separated_indices(self):
        """A plain comma list is treated as separate indices."""
        assert asset_video.split_order_spec("3,1,2") == ["3", "1", "2"]

    def test_page_fragments_merge_into_pdf_reference(self):
        """Comma-separated pages stay attached to a PDF reference."""
        assert asset_video.split_order_spec("brand.pdf:1, 3, 5-7") == ["brand.pdf:1,3,5-7"]

    def test_split_slide_reference(self):
        """Page specifications are split from asset references."""
        assert asset_video.split_slide_reference("logo.png") == ("logo.png", None)
        assert asset_video.split_slide_reference("brand.pdf:2-4") == (
            "brand.pdf",
            "2-4",
        )

    def test_resolve_order_by_index_and_filename(self, tmp_path):
        """References resolve by index, filename, and filename stem."""
        Image.new("RGB", (20, 20), "red").save(tmp_path / "cover.png")
        make_pdf(tmp_path / "brand.pdf", pages=4)
        assets = asset_video.discover_assets(tmp_path)

        references = asset_video.resolve_order("brand.pdf:2-3;cover.png;1", assets)

        assert references[0].asset.relative_name == "brand.pdf"
        assert references[0].page_spec == "2-3"
        assert references[1].asset.relative_name == "cover.png"
        assert references[2].asset.relative_name == "brand.pdf"

    def test_image_page_spec_is_rejected(self, tmp_path):
        """Page numbers cannot be attached to images."""
        Image.new("RGB", (20, 20), "red").save(tmp_path / "cover.png")
        assets = asset_video.discover_assets(tmp_path)

        with pytest.raises(ValueError, match="Page numbers only apply to PDFs"):
            asset_video.resolve_order("cover.png:2", assets)

    def test_out_of_range_index_is_rejected(self, tmp_path):
        """Out-of-range asset indices report the valid range."""
        Image.new("RGB", (20, 20), "red").save(tmp_path / "cover.png")
        assets = asset_video.discover_assets(tmp_path)

        with pytest.raises(ValueError, match="out of range"):
            asset_video.resolve_order("2", assets)

    def test_sequence_order_is_supported(self):
        """Programmatic callers can pass a list of references."""
        assert asset_video.split_order_spec(["1,2", "brand.pdf:1,3"]) == [
            "1",
            "2",
            "brand.pdf:1,3",
        ]

    def test_ambiguous_filename_is_rejected(self, tmp_path):
        """Duplicate filenames require a relative path to disambiguate."""
        for folder in ("a", "b"):
            nested = tmp_path / folder
            nested.mkdir()
            Image.new("RGB", (20, 20), "red").save(nested / "logo.png")
        assets = asset_video.discover_assets(tmp_path, recursive=True)

        with pytest.raises(ValueError, match="ambiguous"):
            asset_video.resolve_asset("logo.png", assets)
        assert asset_video.resolve_asset("a/logo.png", assets).relative_name == "a/logo.png"

    def test_labels_are_readable(self, tmp_path):
        """Assets and slides expose readable labels."""
        make_pdf(tmp_path / "brand.pdf", pages=2)
        Image.new("RGB", (20, 20), "red").save(tmp_path / "logo.png")
        assets = asset_video.discover_assets(tmp_path)

        assert assets[0].label == "brand.pdf (2 pages)"
        assert assets[1].label == "logo.png"
        assert asset_video.Slide(tmp_path / "logo.png").label == "logo.png"
        assert asset_video.Slide(tmp_path / "brand.pdf", page=2).label == "brand.pdf (page 2)"


class TestPageSelection:
    """Verify PDF page selection."""

    def test_all_pages(self):
        """Empty, all, and wildcard selections return every page."""
        assert asset_video.parse_page_selection(None, 3) == [1, 2, 3]
        assert asset_video.parse_page_selection("", 3) == [1, 2, 3]
        assert asset_video.parse_page_selection("all", 3) == [1, 2, 3]
        assert asset_video.parse_page_selection("*", 3) == [1, 2, 3]

    def test_ranges_and_single_pages(self):
        """Pages and ascending ranges are expanded in order."""
        assert asset_video.parse_page_selection("1,3-4", 5) == [1, 3, 4]
        assert asset_video.parse_page_selection("4,2", 5) == [4, 2]

    def test_descending_range_is_rejected(self):
        """Descending ranges are invalid."""
        with pytest.raises(ValueError, match="ascend"):
            asset_video.parse_page_selection("4-2", 5)

    def test_out_of_range_page_is_rejected(self):
        """Pages beyond the document are rejected."""
        with pytest.raises(ValueError, match="outside"):
            asset_video.parse_page_selection("6", 5)

    def test_invalid_page_text_is_rejected(self):
        """Non-numeric page tokens are rejected."""
        with pytest.raises(ValueError, match="Invalid page"):
            asset_video.parse_page_selection("cover", 5)


class TestValidation:
    """Verify render validation and ffmpeg discovery."""

    def test_render_slide_rejects_invalid_options(self, tmp_path):
        """Invalid fit and background values fail before rendering."""
        source = tmp_path / "cover.png"
        Image.new("RGB", (20, 20), "red").save(source)
        slide = asset_video.Slide(source)

        with pytest.raises(ValueError, match="Fit must be"):
            asset_video.render_slide(slide, (40, 40), fit="stretch")
        with pytest.raises(ValueError, match="Invalid background"):
            asset_video.render_slide(slide, (40, 40), background="not-a-color")
        with pytest.raises(FileNotFoundError, match="Asset not found"):
            asset_video.render_slide(asset_video.Slide(tmp_path / "missing.png"), (40, 40))

    def test_render_video_rejects_invalid_options(self, tmp_path):
        """Invalid timing and quality values fail fast."""
        source = tmp_path / "cover.png"
        Image.new("RGB", (20, 20), "red").save(source)
        slide = asset_video.Slide(source)

        with pytest.raises(ValueError, match="at least one"):
            asset_video.render_video([], tmp_path / "out.mp4")
        with pytest.raises(ValueError, match="greater than zero"):
            asset_video.render_video([slide], tmp_path / "out.mp4", duration=0)
        with pytest.raises(ValueError, match="FPS"):
            asset_video.render_video([slide], tmp_path / "out.mp4", fps=0)
        with pytest.raises(ValueError, match="Fade"):
            asset_video.render_video([slide], tmp_path / "out.mp4", fade=-1)
        with pytest.raises(ValueError, match="CRF"):
            asset_video.render_video([slide], tmp_path / "out.mp4", crf=99)

    @requires_ffmpeg
    def test_output_directory_gets_default_filename(self, tmp_path):
        """Passing an existing directory places the video inside it."""
        Image.new("RGB", (40, 40), "red").save(tmp_path / "cover.png")
        output_dir = tmp_path / "videos"
        output_dir.mkdir()

        result = asset_video.create_asset_video(
            tmp_path,
            output_file=output_dir,
            duration=0.1,
            fps=5,
            size="160x160",
        )

        assert result["output_file"] == str(output_dir / "asset-video.mp4")

    def test_find_ffmpeg_uses_the_dependency_resolver(self, monkeypatch):
        """The shared resolver supplies the ffmpeg path."""
        monkeypatch.setattr(asset_video, "ensure_tool", lambda name: "/opt/ffmpeg")
        assert asset_video.find_ffmpeg() == "/opt/ffmpeg"

    def test_find_ffmpeg_surfaces_install_failures(self, monkeypatch):
        """An unavailable tool raises the resolver error."""

        def missing(name):
            raise deps.ToolUnavailableError("ffmpeg is required")

        monkeypatch.setattr(asset_video, "ensure_tool", missing)
        with pytest.raises(RuntimeError, match="ffmpeg is required"):
            asset_video.find_ffmpeg()


class TestCanvas:
    """Verify output dimensions."""

    def test_aspect_presets(self):
        """Known aspect ratios use social-friendly resolutions."""
        assert asset_video.resolve_canvas() == (1920, 1080)
        assert asset_video.resolve_canvas("9:16") == (1080, 1920)
        assert asset_video.resolve_canvas("1:1") == (1080, 1080)
        assert asset_video.resolve_canvas("4:5") == (1080, 1350)
        assert asset_video.resolve_canvas("16:9") == (1920, 1080)

    def test_aliases_and_custom_ratio(self):
        """Aliases and arbitrary ratios produce even dimensions."""
        assert asset_video.resolve_canvas("vertical") == (1080, 1920)
        assert asset_video.resolve_canvas("2:1") == (1080, 540)

    def test_custom_size(self):
        """Custom size overrides the aspect ratio."""
        assert asset_video.resolve_canvas("9:16", "720x1280") == (720, 1280)

    def test_odd_size_is_rejected(self):
        """H.264 yuv420p requires even dimensions."""
        with pytest.raises(ValueError, match="even"):
            asset_video.resolve_canvas("9:16", "721x1281")

    def test_invalid_size_and_aspect_are_rejected(self):
        """Malformed dimensions and ratios fail with guidance."""
        with pytest.raises(ValueError, match="1080x1920"):
            asset_video.resolve_canvas(size="1080")
        with pytest.raises(ValueError, match="positive"):
            asset_video.resolve_canvas(size="0x1080")
        with pytest.raises(ValueError, match="Unknown aspect"):
            asset_video.resolve_canvas("banana")
        with pytest.raises(ValueError, match="Unknown aspect"):
            asset_video.resolve_canvas("wide:tall")


class TestRendering:
    """Verify slide rendering and video output."""

    def test_contain_preserves_background(self, tmp_path):
        """Contain mode letterboxes the asset over the background."""
        source = tmp_path / "wide.png"
        Image.new("RGB", (100, 50), "red").save(source)

        frame = asset_video.render_slide(
            asset_video.Slide(source),
            (200, 200),
            fit="contain",
            background="#000000",
        )

        assert frame.size == (200, 200)
        assert frame.getpixel((100, 100)) == (255, 0, 0)
        assert frame.getpixel((5, 5)) == (0, 0, 0)

    def test_cover_fills_canvas(self, tmp_path):
        """Cover mode crops the asset to fill the frame."""
        source = tmp_path / "wide.png"
        Image.new("RGB", (200, 100), "red").save(source)

        frame = asset_video.render_slide(
            asset_video.Slide(source),
            (100, 100),
            fit="cover",
            background="#000000",
        )

        assert frame.size == (100, 100)
        assert frame.getpixel((0, 0)) == (255, 0, 0)
        assert frame.getpixel((99, 99)) == (255, 0, 0)

    def test_pdf_page_renders(self, tmp_path):
        """PDF pages render to a flat frame."""
        pdf_path = tmp_path / "brand.pdf"
        make_pdf(pdf_path, pages=2)

        frame = asset_video.render_slide(
            asset_video.Slide(pdf_path, page=2),
            (100, 150),
            fit="contain",
            background="#ffffff",
        )

        assert frame.size == (100, 150)

    @requires_ffmpeg
    def test_end_to_end_video(self, tmp_path):
        """Images and PDF pages encode into a decodable MP4."""
        Image.new("RGB", (120, 80), "red").save(tmp_path / "cover.png")
        Image.new("RGB", (80, 120), "blue").save(tmp_path / "logo.png")
        make_pdf(tmp_path / "brand.pdf", pages=2)
        output = tmp_path / "reel.mp4"
        events = []

        result = asset_video.create_asset_video(
            tmp_path,
            output_file=output,
            order="cover.png;brand.pdf:2",
            duration=0.25,
            fps=8,
            size="320x320",
            fade=0.05,
            progress_callback=events.append,
        )

        assert output.exists()
        assert output.stat().st_size > 0
        assert result["slides"] == 2
        assert result["frames"] == 4
        assert result["resolution"] == "320x320"
        assert [event["stage"] for event in events] == ["slide", "slide", "complete"]

        ffmpeg = asset_video.find_ffmpeg()
        decoded = subprocess.run(
            [ffmpeg, "-v", "error", "-i", str(output), "-f", "null", "-"],
            capture_output=True,
            text=True,
        )
        assert decoded.returncode == 0, decoded.stderr

    @requires_ffmpeg
    def test_default_output_path(self, tmp_path, monkeypatch):
        """The default output uses the caller's output root."""
        monkeypatch.chdir(tmp_path)
        Image.new("RGB", (40, 40), "red").save(tmp_path / "cover.png")

        result = asset_video.create_asset_video(
            tmp_path,
            duration=0.1,
            fps=5,
            size="160x160",
        )

        assert result["output_file"] == "r10n-output/video/asset-video.mp4"
        assert Path("r10n-output/video/asset-video.mp4").exists()

    def test_empty_folder_is_rejected(self, tmp_path):
        """A folder without supported assets cannot produce a video."""
        with pytest.raises(ValueError, match="No images or PDFs found"):
            asset_video.create_asset_video(tmp_path)

    def test_non_mp4_output_is_rejected(self, tmp_path):
        """The automation only writes MP4 files."""
        Image.new("RGB", (40, 40), "red").save(tmp_path / "cover.png")

        with pytest.raises(ValueError, match=r"\.mp4"):
            asset_video.create_asset_video(tmp_path, output_file=tmp_path / "reel.mov")
