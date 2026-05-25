"""
Website image downloader automation.

This module downloads images referenced by a web page and converts them to a
requested raster format. It supports both CLI and programmatic usage.
"""

import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

DEFAULT_USER_AGENT = "r10n-website-images/1.0"
SUPPORTED_OUTPUT_FORMATS = {"jpg", "jpeg", "png", "webp"}
IMAGE_URL_PATTERN = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.IGNORECASE)


@dataclass
class WebsiteImageDownloadConfig:
    """Configuration for downloading and converting website images."""

    url: str
    output_directory: str = "local/outputs/website-images"
    output_format: str = "webp"
    quality: int = 85
    timeout: int = 20
    user_agent: str = DEFAULT_USER_AGENT


class WebsiteImageParser(HTMLParser):
    """Collect image URLs from HTML attributes and inline styles."""

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.image_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect image references from a start tag."""
        attr_map = {name.lower(): value for name, value in attrs if value}

        if tag.lower() == "img":
            self._add_url(attr_map.get("src"))
            self._add_srcset(attr_map.get("srcset"))
            for key, value in attr_map.items():
                if key.startswith("data-") and key in {
                    "data-src",
                    "data-original",
                    "data-lazy-src",
                }:
                    self._add_url(value)

        if tag.lower() == "source":
            self._add_srcset(attr_map.get("srcset"))

        if tag.lower() == "link":
            rel = attr_map.get("rel", "").lower()
            if "icon" in rel or "apple-touch-icon" in rel:
                self._add_url(attr_map.get("href"))

        self._add_style_urls(attr_map.get("style"))

    def handle_data(self, data: str) -> None:
        """Collect image URLs from style blocks."""
        self._add_style_urls(data)

    def _add_url(self, url: str | None) -> None:
        """Add a normalized image URL."""
        if not url:
            return

        cleaned = url.strip()
        if not cleaned or cleaned.startswith(("data:", "blob:", "javascript:")):
            return

        self.image_urls.append(urllib.parse.urljoin(self.base_url, cleaned))

    def _add_srcset(self, srcset: str | None) -> None:
        """Add all URLs from a srcset attribute."""
        if not srcset:
            return

        for candidate in srcset.split(","):
            url = candidate.strip().split()
            if url:
                self._add_url(url[0])

    def _add_style_urls(self, style_content: str | None) -> None:
        """Add image URLs from CSS url(...) declarations."""
        if not style_content:
            return

        for match in IMAGE_URL_PATTERN.finditer(style_content):
            self._add_url(match.group(1))


def normalize_output_format(output_format: str) -> str:
    """
    Normalize and validate an output image format.

    Args:
        output_format: Requested format, such as jpg, png, or webp.

    Returns:
        Normalized lowercase format.

    Raises:
        ValueError: If the format is unsupported.
    """
    normalized = output_format.lower().lstrip(".")
    if normalized not in SUPPORTED_OUTPUT_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_OUTPUT_FORMATS))
        raise ValueError(
            f"Unsupported output format: {output_format}. Supported formats: {supported}"
        )
    return normalized


def fetch_html(url: str, timeout: int = 20, user_agent: str = DEFAULT_USER_AGENT) -> str:
    """
    Fetch HTML content from a URL.

    Args:
        url: Web page URL.
        timeout: Request timeout in seconds.
        user_agent: User-Agent header value.

    Returns:
        Decoded HTML content.

    Raises:
        ValueError: If the URL is invalid.
        RuntimeError: If the page cannot be fetched.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Enter a valid website URL including http:// or https://: {url}")

    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not fetch website: {url}") from exc


def extract_image_urls(html: str, base_url: str) -> list[str]:
    """
    Extract unique image URLs from HTML content.

    Args:
        html: HTML content to parse.
        base_url: Base URL for resolving relative links.

    Returns:
        List of unique absolute image URLs in document order.
    """
    parser = WebsiteImageParser(base_url)
    parser.feed(html)

    seen: set[str] = set()
    unique_urls = []
    for image_url in parser.image_urls:
        normalized = image_url.split("#", 1)[0]
        if normalized not in seen:
            seen.add(normalized)
            unique_urls.append(normalized)

    return unique_urls


def build_output_filename(image_url: str, index: int, output_format: str) -> str:
    """
    Build a filesystem-safe output filename for a downloaded image.

    Args:
        image_url: Source image URL.
        index: One-based image index.
        output_format: Normalized output format.

    Returns:
        Safe output filename.
    """
    parsed = urllib.parse.urlparse(image_url)
    original_name = Path(urllib.parse.unquote(parsed.path)).stem
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", original_name).strip("-._")
    if not safe_name:
        safe_name = f"image-{index}"

    extension = "jpg" if output_format == "jpeg" else output_format
    return f"{index:03d}-{safe_name}.{extension}"


def prepare_image_for_format(image: Image.Image, output_format: str) -> Image.Image:
    """
    Convert a Pillow image to a mode suitable for the requested output format.

    Args:
        image: Source Pillow image.
        output_format: Normalized output format.

    Returns:
        Converted Pillow image.
    """
    image = ImageOps.exif_transpose(image)

    if output_format in {"jpg", "jpeg"}:
        if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
            rgba_image = image.convert("RGBA")
            background = Image.new("RGB", rgba_image.size, (255, 255, 255))
            background.paste(rgba_image, mask=rgba_image.getchannel("A"))
            return background
        return image.convert("RGB")

    if output_format == "webp" and image.mode == "P":
        return image.convert("RGBA")

    return image


def convert_image_bytes(
    image_data: bytes,
    output_path: Path,
    output_format: str,
    quality: int = 85,
) -> None:
    """
    Convert image bytes and write them to the requested output path.

    Args:
        image_data: Downloaded image bytes.
        output_path: Converted image destination.
        output_format: Normalized output format.
        quality: Quality for lossy image formats.

    Raises:
        UnidentifiedImageError: If bytes are not a supported raster image.
    """
    pil_format = "JPEG" if output_format in {"jpg", "jpeg"} else output_format.upper()
    save_kwargs: dict[str, Any] = {"format": pil_format}

    if output_format in {"jpg", "jpeg", "webp"}:
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
    if output_format == "webp":
        save_kwargs["method"] = 6

    from io import BytesIO

    with Image.open(BytesIO(image_data)) as image:
        converted = prepare_image_for_format(image, output_format)
        converted.save(output_path, **save_kwargs)


def download_image(
    image_url: str,
    output_path: Path,
    output_format: str,
    quality: int = 85,
    timeout: int = 20,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, Any]:
    """
    Download and convert a single image URL.

    Args:
        image_url: Source image URL.
        output_path: Converted output path.
        output_format: Normalized output format.
        quality: Quality for lossy formats.
        timeout: Request timeout in seconds.
        user_agent: User-Agent header value.

    Returns:
        Result dictionary for the image.
    """
    try:
        request = urllib.request.Request(image_url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            image_data = response.read()

        convert_image_bytes(image_data, output_path, output_format, quality)
        return {
            "success": True,
            "source_url": image_url,
            "output_file": str(output_path),
            "bytes_downloaded": len(image_data),
        }
    except (urllib.error.URLError, UnidentifiedImageError, OSError, ValueError) as exc:
        return {
            "success": False,
            "source_url": image_url,
            "output_file": str(output_path),
            "error": str(exc),
        }


def download_website_images(
    url: str,
    output_dir: str | None = None,
    output_format: str = "webp",
    quality: int = 85,
    timeout: int = 20,
) -> dict[str, Any]:
    """
    Download all image references from a web page and convert them.

    Args:
        url: Website URL to scan.
        output_dir: Directory for converted images.
        output_format: Output format: jpg, jpeg, png, or webp.
        quality: Quality for lossy formats.
        timeout: Request timeout in seconds.

    Returns:
        dict: Results with download statistics and per-file records.

    Raises:
        ValueError: If inputs are invalid.
        RuntimeError: If the website cannot be fetched.
    """
    normalized_format = normalize_output_format(output_format)
    if not 1 <= quality <= 100:
        raise ValueError("Quality must be between 1 and 100")

    destination = Path(output_dir or "local/outputs/website-images")
    destination.mkdir(parents=True, exist_ok=True)

    html = fetch_html(url, timeout=timeout)
    image_urls = extract_image_urls(html, url)

    results: dict[str, Any] = {
        "success": True,
        "url": url,
        "found": len(image_urls),
        "downloaded": 0,
        "failed": 0,
        "output_directory": str(destination),
        "format": normalized_format,
        "files": [],
    }

    for index, image_url in enumerate(image_urls, 1):
        output_path = destination / build_output_filename(image_url, index, normalized_format)
        file_result = download_image(
            image_url=image_url,
            output_path=output_path,
            output_format=normalized_format,
            quality=quality,
            timeout=timeout,
        )

        if file_result["success"]:
            results["downloaded"] += 1
        else:
            results["failed"] += 1
        results["files"].append(file_result)

    return results


if __name__ == "__main__":
    print("Website Image Downloader")
    print("Use the main CLI: uv run r10n website-images")
