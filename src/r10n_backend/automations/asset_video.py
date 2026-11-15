"""Turn images and PDF pages into a short social-ready video.

The automation scans a folder for image assets and PDFs, lets the caller pick
an order and PDF pages, then renders each slide for a fixed duration. Frames
are streamed to ffmpeg as raw RGB data, so no intermediate image files are
written to disk.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pypdfium2 as pdfium
from PIL import Image, ImageColor, ImageOps

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
}
PDF_EXTENSIONS = {".pdf"}
FIT_MODES = {"contain", "cover"}
ASPECT_PRESETS = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "16:9": (1920, 1080),
}
ASPECT_ALIASES = {
    "vertical": "9:16",
    "square": "1:1",
    "portrait": "4:5",
    "landscape": "16:9",
}
DEFAULT_ASPECT = "16:9"
DEFAULT_DURATION = 0.5
DEFAULT_FPS = 30
DEFAULT_FIT = "contain"
DEFAULT_BACKGROUND = "#ffffff"
MAX_RENDER_PIXELS = 16_000_000

ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class Asset:
    """One discoverable source file in the input folder."""

    path: Path
    relative_name: str
    kind: Literal["image", "pdf"]
    pages: int = 1

    @property
    def label(self) -> str:
        """Human-readable asset name."""
        if self.kind == "pdf":
            return f"{self.relative_name} ({self.pages} pages)"
        return self.relative_name


@dataclass(frozen=True)
class SlideRef:
    """An asset reference with an optional page selection."""

    asset: Asset
    page_spec: str | None = None


@dataclass(frozen=True)
class Slide:
    """One rendered video slide."""

    path: Path
    page: int | None = None

    @property
    def label(self) -> str:
        """Human-readable slide name."""
        if self.page is None:
            return self.path.name
        return f"{self.path.name} (page {self.page})"


def _pdf_page_count(path: Path) -> int:
    """Return the number of pages in a PDF.

    Args:
        path: PDF file to inspect.

    Returns:
        Page count for the document.

    Raises:
        ValueError: If the PDF cannot be read.
    """
    try:
        document = pdfium.PdfDocument(str(path))
    except Exception as error:  # pragma: no cover - depends on PDFium internals
        raise ValueError(f"Could not read PDF {path.name}: {error}") from error

    try:
        return len(document)
    except Exception as error:  # pragma: no cover - depends on PDFium internals
        raise ValueError(f"Could not read PDF {path.name}: {error}") from error
    finally:
        document.close()


def discover_assets(
    directory: str | Path,
    *,
    recursive: bool = False,
) -> list[Asset]:
    """Find supported images and PDFs in a folder.

    Args:
        directory: Folder to scan.
        recursive: Include files in nested folders.

    Returns:
        Assets sorted by relative path.

    Raises:
        FileNotFoundError: If the folder does not exist.
        NotADirectoryError: If the path is not a folder.
        ValueError: If a PDF is unreadable.
    """
    root = Path(directory).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"Input folder not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Input path is not a folder: {root}")

    paths = root.rglob("*") if recursive else root.iterdir()
    assets: list[Asset] = []
    for path in paths:
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue

        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            assets.append(
                Asset(path=path, relative_name=relative.as_posix(), kind="image", pages=1)
            )
        elif suffix in PDF_EXTENSIONS:
            assets.append(
                Asset(
                    path=path,
                    relative_name=relative.as_posix(),
                    kind="pdf",
                    pages=_pdf_page_count(path),
                )
            )

    assets.sort(key=lambda asset: (asset.relative_name.casefold(), asset.relative_name))
    return assets


def split_order_spec(order: str | Sequence[str]) -> list[str]:
    """Split an order specification into slide reference tokens.

    Semicolons separate references. A single reference may use colons and
    commas for PDF pages, for example ``brand.pdf:1,3-5``. When page ranges
    are present, prefer semicolons between multiple references.

    Args:
        order: Order specification string or sequence of references.

    Returns:
        Trimmed reference tokens.
    """
    if not isinstance(order, str):
        tokens: list[str] = []
        for part in order:
            tokens.extend(split_order_spec(part))
        return tokens

    text = order.strip()
    if not text:
        return []

    if ";" in text:
        return [part.strip() for part in text.split(";") if part.strip()]

    parts = [part.strip() for part in text.split(",") if part.strip()]
    if len(parts) <= 1:
        return parts

    # Merge page fragments such as "brand.pdf:1, 3, 5-7" into one token.
    merged: list[str] = []
    for part in parts:
        if merged and _is_page_fragment(part) and ":" in merged[-1]:
            merged[-1] = f"{merged[-1]},{part}"
        else:
            merged.append(part)
    return merged


def _is_page_fragment(value: str) -> bool:
    """Return whether a token looks like a comma-separated PDF page fragment."""
    return bool(re.fullmatch(r"\d+(?:-\d+)?", value))


def split_slide_reference(token: str) -> tuple[str, str | None]:
    """Split a token into an asset reference and optional PDF pages.

    Args:
        token: Reference such as ``logo.png`` or ``brand.pdf:1-3``.

    Returns:
        Tuple of asset reference and page specification.
    """
    text = token.strip()
    if ":" in text:
        base, pages = text.rsplit(":", 1)
        if base.strip() and pages.strip():
            return base.strip(), pages.strip()
    return text, None


def resolve_asset(reference: str, assets: Sequence[Asset]) -> Asset:
    """Resolve a user reference to a discovered asset.

    References may be a 1-based index, a relative path, a filename, or a
    unique filename stem.

    Args:
        reference: User-provided asset reference.
        assets: Discovered assets in display order.

    Returns:
        Matching asset.

    Raises:
        ValueError: If the reference is missing, out of range, or ambiguous.
    """
    text = reference.strip()
    if not text:
        raise ValueError("Asset reference cannot be empty")

    if text.isdigit():
        index = int(text)
        if not 1 <= index <= len(assets):
            raise ValueError(f"Asset number {index} is out of range (1-{len(assets)})")
        return assets[index - 1]

    normalized = text.replace("\\", "/").casefold().removeprefix("./")
    candidates = [asset for asset in assets if asset.relative_name.casefold() == normalized]
    if not candidates:
        candidates = [asset for asset in assets if asset.path.name.casefold() == normalized]
    if not candidates:
        candidates = [asset for asset in assets if asset.path.stem.casefold() == normalized]

    if not candidates:
        raise ValueError(f"Asset not found: {reference}")
    if len(candidates) > 1:
        names = ", ".join(asset.relative_name for asset in candidates)
        raise ValueError(f"Asset name is ambiguous: {reference} ({names})")
    return candidates[0]


def resolve_order(order: str | Sequence[str] | None, assets: Sequence[Asset]) -> list[SlideRef]:
    """Resolve an order specification into ordered slide references.

    Args:
        order: Order specification, or ``None`` to include every asset.
        assets: Discovered assets in display order.

    Returns:
        Slide references in the requested order.

    Raises:
        ValueError: If no assets are selected or a reference is invalid.
    """
    tokens = split_order_spec(order) if order else [asset.relative_name for asset in assets]
    if not tokens:
        raise ValueError("Select at least one image or PDF")

    references: list[SlideRef] = []
    for token in tokens:
        base, page_spec = split_slide_reference(token)
        asset = resolve_asset(base, assets)
        if asset.kind == "image" and page_spec:
            raise ValueError(f"Page numbers only apply to PDFs: {asset.relative_name}")
        references.append(SlideRef(asset=asset, page_spec=page_spec))
    return references


def parse_page_selection(specification: str | None, total_pages: int) -> list[int]:
    """Parse a 1-based PDF page selection.

    Args:
        specification: Page list such as ``1,3-5``, or ``all``/``*``/empty.
        total_pages: Number of pages in the PDF.

    Returns:
        Selected page numbers in the requested order.

    Raises:
        ValueError: If the selection is invalid or out of range.
    """
    if total_pages < 1:
        raise ValueError("PDF has no pages")

    text = (specification or "").strip()
    if not text or text.lower() in {"all", "*"}:
        return list(range(1, total_pages + 1))

    pages: list[int] = []
    for token in re.split(r"[,\s]+", text):
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            try:
                start, end = int(start_text), int(end_text)
            except ValueError as error:
                raise ValueError(f"Invalid page range: {token}") from error
            if start > end:
                raise ValueError(f"Page range must ascend: {token}")
            candidates = range(start, end + 1)
        else:
            try:
                candidates = [int(token)]
            except ValueError as error:
                raise ValueError(f"Invalid page number: {token}") from error

        for page in candidates:
            if not 1 <= page <= total_pages:
                raise ValueError(f"Page {page} is outside 1-{total_pages}")
            pages.append(page)

    if not pages:
        raise ValueError("Select at least one PDF page")
    return pages


def expand_refs(
    references: Sequence[SlideRef],
    page_overrides: dict[str, str] | None = None,
) -> list[Slide]:
    """Expand slide references into individual slides.

    Args:
        references: Ordered asset references.
        page_overrides: Optional page specifications keyed by relative or
            plain filename.

    Returns:
        Slides in display order.

    Raises:
        ValueError: If a PDF page specification is invalid.
    """
    overrides = page_overrides or {}
    slides: list[Slide] = []
    for reference in references:
        asset = reference.asset
        if asset.kind == "pdf":
            page_spec = (
                reference.page_spec
                or overrides.get(asset.relative_name)
                or overrides.get(asset.path.name)
                or "all"
            )
            for page in parse_page_selection(page_spec, asset.pages):
                slides.append(Slide(path=asset.path, page=page))
        else:
            slides.append(Slide(path=asset.path))
    return slides


def build_slides(
    directory: str | Path,
    order: str | Sequence[str] | None = None,
    *,
    recursive: bool = False,
    page_overrides: dict[str, str] | None = None,
) -> list[Slide]:
    """Discover assets and build the ordered slide list.

    Args:
        directory: Folder containing images and PDFs.
        order: Optional order specification.
        recursive: Scan nested folders.
        page_overrides: Optional PDF page selections.

    Returns:
        Slides in display order.
    """
    assets = discover_assets(directory, recursive=recursive)
    return expand_refs(resolve_order(order, assets), page_overrides)


def resolve_canvas(aspect: str = DEFAULT_ASPECT, size: str | None = None) -> tuple[int, int]:
    """Resolve output dimensions from an aspect ratio or custom size.

    Args:
        aspect: Aspect ratio such as ``9:16`` or a preset alias.
        size: Optional ``WIDTHxHEIGHT`` override.

    Returns:
        Even output width and height.

    Raises:
        ValueError: If the value is invalid or the dimensions are odd.
    """
    if size:
        text = size.strip().lower().replace("*", "x").replace(" ", "")
        if "x" not in text:
            raise ValueError("Size must look like 1080x1920")
        width_text, height_text = text.split("x", 1)
        try:
            width, height = int(width_text), int(height_text)
        except ValueError as error:
            raise ValueError("Size must look like 1080x1920") from error
        if width <= 0 or height <= 0:
            raise ValueError("Video width and height must be positive")
        if width % 2 or height % 2:
            raise ValueError("Video width and height must be even for H.264 output")
        return width, height

    key = ASPECT_ALIASES.get(aspect.strip().lower(), aspect.strip().lower())
    if key in ASPECT_PRESETS:
        return ASPECT_PRESETS[key]

    if ":" not in key:
        raise ValueError(f"Unknown aspect ratio: {aspect}. Use 9:16, 1:1, 4:5, or 16:9")

    width_text, height_text = key.split(":", 1)
    try:
        ratio_width, ratio_height = int(width_text), int(height_text)
    except ValueError as error:
        raise ValueError(f"Unknown aspect ratio: {aspect}") from error
    if ratio_width <= 0 or ratio_height <= 0:
        raise ValueError(f"Unknown aspect ratio: {aspect}")

    width = 1080
    height = round(width * ratio_height / ratio_width)
    width -= width % 2
    height -= height % 2
    if height < 2:
        raise ValueError(f"Aspect ratio is too wide: {aspect}")
    return width, height


def find_ffmpeg() -> str:
    """Locate an ffmpeg executable.

    Returns:
        Path to a bundled or system ffmpeg binary.

    Raises:
        RuntimeError: If ffmpeg is unavailable.
    """
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    raise RuntimeError(
        "ffmpeg is required to create videos. Install it with "
        "`brew install ffmpeg`, `apt install ffmpeg`, or `pip install imageio-ffmpeg`."
    )


def _parse_background(color: str) -> tuple[int, int, int]:
    """Convert a color string into an RGB tuple."""
    try:
        rgb = ImageColor.getrgb(color)
    except ValueError as error:
        raise ValueError(f"Invalid background color: {color}") from error
    if len(rgb) == 3:
        return rgb
    return rgb[:3]


def _render_pdf_page(
    path: Path,
    page_number: int,
    canvas_size: tuple[int, int],
    fit: str,
) -> Image.Image:
    """Render one PDF page at a resolution suitable for the output canvas."""
    document = pdfium.PdfDocument(str(path))
    try:
        if not 1 <= page_number <= len(document):
            raise ValueError(f"Page {page_number} is outside {path.name} (1-{len(document)})")
        page = document[page_number - 1]
        page_width, page_height = page.get_size()
        if page_width <= 0 or page_height <= 0:
            raise ValueError(f"PDF page has no size: {path.name} page {page_number}")

        canvas_width, canvas_height = canvas_size
        width_scale = canvas_width / page_width
        height_scale = canvas_height / page_height
        scale = max(width_scale, height_scale) if fit == "cover" else min(width_scale, height_scale)

        rendered_pixels = (page_width * scale) * (page_height * scale)
        if rendered_pixels > MAX_RENDER_PIXELS:
            scale *= math.sqrt(MAX_RENDER_PIXELS / rendered_pixels)

        bitmap = page.render(scale=scale)
        return bitmap.to_pil()
    finally:
        document.close()


def _place_on_canvas(
    image: Image.Image,
    canvas_size: tuple[int, int],
    fit: str,
    background: tuple[int, int, int],
) -> Image.Image:
    """Fit an image onto a canvas and return a flat RGB frame."""
    canvas_width, canvas_height = canvas_size
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("Source image has no size")

    source = image.convert("RGBA")
    canvas = Image.new("RGB", canvas_size, background)

    if fit == "cover":
        scale = max(canvas_width / width, canvas_height / height)
        resized_width = max(1, round(width * scale))
        resized_height = max(1, round(height * scale))
        resized = source.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
        left = (resized_width - canvas_width) // 2
        top = (resized_height - canvas_height) // 2
        cropped = resized.crop((left, top, left + canvas_width, top + canvas_height))
        canvas.paste(cropped, (0, 0), cropped)
        return canvas

    scale = min(canvas_width / width, canvas_height / height)
    resized_width = max(1, round(width * scale))
    resized_height = max(1, round(height * scale))
    resized = source.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
    position = (
        (canvas_width - resized_width) // 2,
        (canvas_height - resized_height) // 2,
    )
    canvas.paste(resized, position, resized)
    return canvas


def render_slide(
    slide: Slide,
    canvas_size: tuple[int, int],
    *,
    fit: str = DEFAULT_FIT,
    background: str = DEFAULT_BACKGROUND,
) -> Image.Image:
    """Render a single slide as a flat RGB image.

    Args:
        slide: Asset and optional PDF page to render.
        canvas_size: Output frame dimensions.
        fit: ``contain`` or ``cover``.
        background: Background color used by contain mode.

    Returns:
        Rendered RGB frame.

    Raises:
        FileNotFoundError: If the source file is missing.
        ValueError: If the fit mode or background is invalid.
    """
    if fit not in FIT_MODES:
        raise ValueError(f"Fit must be one of: {', '.join(sorted(FIT_MODES))}")
    if not slide.path.exists():
        raise FileNotFoundError(f"Asset not found: {slide.path}")

    background_rgb = _parse_background(background)

    if slide.page is not None:
        image = _render_pdf_page(slide.path, slide.page, canvas_size, fit)
    else:
        with Image.open(slide.path) as opened:
            opened.seek(0)
            image = ImageOps.exif_transpose(opened)
            image.load()

    return _place_on_canvas(image, canvas_size, fit, background_rgb)


def _resolve_output_path(output_file: str | Path | None) -> Path:
    """Resolve the output file path and validate the MP4 extension."""
    if output_file is None:
        output = Path("r10n-output/video/asset-video.mp4")
    else:
        output = Path(output_file).expanduser()
        if output.is_dir():
            output = output / "asset-video.mp4"
        elif not output.suffix:
            output = output.with_suffix(".mp4")

    if output.suffix.lower() != ".mp4":
        raise ValueError("Video output must use the .mp4 extension")
    return output


def render_video(
    slides: Sequence[Slide],
    output_file: str | Path,
    *,
    duration: float = DEFAULT_DURATION,
    fps: int = DEFAULT_FPS,
    aspect: str = DEFAULT_ASPECT,
    size: str | None = None,
    fit: str = DEFAULT_FIT,
    background: str = DEFAULT_BACKGROUND,
    fade: float = 0.0,
    crf: int = 18,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Render ordered slides into an H.264 MP4 file.

    Args:
        slides: Ordered slides to show.
        output_file: Destination MP4 path.
        duration: Seconds each slide is visible.
        fps: Output frame rate.
        aspect: Aspect ratio when ``size`` is not provided.
        size: Optional custom output dimensions.
        fit: ``contain`` or ``cover``.
        background: Background color for contain mode.
        fade: Optional crossfade seconds between slides.
        crf: H.264 quality (lower is better, 0-51).
        progress_callback: Optional callback receiving slide progress events.

    Returns:
        Result summary with output path, duration, and encoding details.

    Raises:
        ValueError: If any input value is invalid.
        FileNotFoundError: If a source asset is missing.
        RuntimeError: If ffmpeg is unavailable or encoding fails.
    """
    if not slides:
        raise ValueError("Select at least one image or PDF page")
    if duration <= 0:
        raise ValueError("Seconds per slide must be greater than zero")
    if not 1 <= fps <= 60:
        raise ValueError("FPS must be between 1 and 60")
    if fit not in FIT_MODES:
        raise ValueError(f"Fit must be one of: {', '.join(sorted(FIT_MODES))}")
    if fade < 0:
        raise ValueError("Fade seconds cannot be negative")
    if not 0 <= crf <= 51:
        raise ValueError("CRF must be between 0 and 51")

    canvas_size = resolve_canvas(aspect, size)
    _parse_background(background)
    ffmpeg = find_ffmpeg()

    output_path = Path(output_file).expanduser()
    if output_path.suffix.lower() != ".mp4":
        raise ValueError("Video output must use the .mp4 extension")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frames_per_slide = max(1, round(duration * fps))
    fade_frames = min(frames_per_slide, round(fade * fps)) if fade > 0 else 0
    total_frames = frames_per_slide * len(slides)

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{canvas_size[0]}x{canvas_size[1]}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    assert process.stderr is not None

    previous: Image.Image | None = None
    frames_written = 0
    try:
        for index, slide in enumerate(slides, start=1):
            image = render_slide(
                slide,
                canvas_size,
                fit=fit,
                background=background,
            )
            raw_frame = image.tobytes()

            for frame_offset in range(frames_per_slide):
                if fade_frames and previous is not None and frame_offset < fade_frames:
                    alpha = (frame_offset + 1) / fade_frames
                    blended = Image.blend(previous, image, alpha)
                    frame_data = blended.tobytes()
                else:
                    frame_data = raw_frame
                process.stdin.write(frame_data)
                frames_written += 1

            previous = image
            if progress_callback:
                progress_callback(
                    {
                        "stage": "slide",
                        "current": index,
                        "total": len(slides),
                        "frames": frames_written,
                        "total_frames": total_frames,
                        "message": f"Rendering {slide.label}",
                    }
                )

        process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        return_code = process.wait()
    except BrokenPipeError as error:
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        process.wait()
        message = stderr.strip() or "ffmpeg stopped unexpectedly"
        raise RuntimeError(f"Video encoding failed: {message}") from error
    except BaseException:
        if process.poll() is None:
            process.kill()
        process.wait()
        raise

    if return_code != 0:
        message = stderr.strip() or "unknown ffmpeg error"
        raise RuntimeError(f"Video encoding failed: {message}")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    if progress_callback:
        progress_callback(
            {
                "stage": "complete",
                "current": len(slides),
                "total": len(slides),
                "frames": total_frames,
                "total_frames": total_frames,
                "message": "Video complete",
            }
        )

    return {
        "success": True,
        "output_file": str(output_path),
        "slides": len(slides),
        "frames": total_frames,
        "duration_seconds": round(total_frames / fps, 2),
        "resolution": f"{canvas_size[0]}x{canvas_size[1]}",
        "fps": fps,
        "seconds_per_slide": duration,
        "fit": fit,
        "background": background,
        "size_mb": round(size_mb, 2),
    }


def create_asset_video(
    input_dir: str | Path,
    output_file: str | Path | None = None,
    order: str | Sequence[str] | None = None,
    *,
    duration: float = DEFAULT_DURATION,
    fps: int = DEFAULT_FPS,
    aspect: str = DEFAULT_ASPECT,
    size: str | None = None,
    fit: str = DEFAULT_FIT,
    background: str = DEFAULT_BACKGROUND,
    fade: float = 0.0,
    crf: int = 18,
    recursive: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Create a short video from images and PDF pages in a folder.

    Args:
        input_dir: Folder containing images and PDFs.
        output_file: Destination MP4. Defaults to ``r10n-output/video/asset-video.mp4``.
        order: Ordered references such as ``cover.png;brand.pdf:1-3;logo.png``.
            Omit to use every asset in name order.
        duration: Seconds each slide is visible.
        fps: Output frame rate.
        aspect: ``9:16``, ``1:1``, ``4:5``, or ``16:9``.
        size: Optional custom ``WIDTHxHEIGHT`` override.
        fit: ``contain`` or ``cover``.
        background: Background color for contain mode.
        fade: Optional crossfade seconds between slides.
        crf: H.264 quality (lower is better, 0-51).
        recursive: Scan nested folders.
        progress_callback: Optional callback receiving slide progress events.

    Returns:
        Result summary with output path, duration, and encoding details.
    """
    root = Path(input_dir).expanduser()
    assets = discover_assets(root, recursive=recursive)
    if not assets:
        raise ValueError(f"No images or PDFs found in {root}")

    slides = expand_refs(resolve_order(order, assets))
    output_path = _resolve_output_path(output_file)

    return render_video(
        slides,
        output_path,
        duration=duration,
        fps=fps,
        aspect=aspect,
        size=size,
        fit=fit,
        background=background,
        fade=fade,
        crf=crf,
        progress_callback=progress_callback,
    )


if __name__ == "__main__":
    print("Asset Video")
    print("Use the main CLI: uv run r10n video --input path/to/assets")
