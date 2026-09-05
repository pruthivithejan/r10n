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
PAGE_EXTENSIONS = {"", ".html", ".htm", ".php", ".asp", ".aspx"}
IMAGE_URL_PATTERN = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.IGNORECASE)
DIMENSION_PATTERN = re.compile(r"[-_](?P<width>\d{2,5})x(?P<height>\d{2,5})(?=$|[-_.@])")
SCALE_PATTERN = re.compile(r"@(?P<scale>\d+(?:\.\d+)?)x(?=$|[-_.])", re.IGNORECASE)
RESPONSIVE_QUERY_PARAMETERS = {
    "auto",
    "dpr",
    "fm",
    "format",
    "h",
    "height",
    "q",
    "quality",
    "w",
    "width",
}
WIDTH_QUERY_PARAMETERS = {"w", "width"}
HEIGHT_QUERY_PARAMETERS = {"h", "height"}


@dataclass(frozen=True)
class ImageSourceCandidate:
    """Image URL candidate and optional srcset descriptor."""

    url: str
    descriptor: str | None = None


def is_fragment_reference(value: str) -> bool:
    """
    Report whether a URL value is a pure in-document fragment reference.

    SVG markup uses values such as ``url(#clip0_3705_6923)`` and ``href="#icon"``
    to point at internal definitions, not downloadable images. When joined to the
    page URL these collapse to the page itself, so they must be rejected before
    collection. A real path that merely carries a fragment (``/photo.jpg#a``) is
    not a fragment reference.

    Args:
        value: Raw, pre-resolution URL value.

    Returns:
        True when the value is an in-document fragment reference.
    """
    return urllib.parse.unquote(value).lstrip().startswith("#")


@dataclass
class WebsiteImageDownloadConfig:
    """Configuration for downloading and converting website images."""

    url: str
    output_directory: str = "local/outputs/website-images"
    output_format: str = "webp"
    quality: int = 85
    timeout: int = 20
    max_pages: int | None = 50
    user_agent: str = DEFAULT_USER_AGENT


class WebsiteImageParser(HTMLParser):
    """Collect image and same-page navigation URLs from HTML."""

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.image_urls: list[str] = []
        self.page_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect image references from a start tag."""
        attr_map = {name.lower(): value for name, value in attrs if value}

        if tag.lower() == "img":
            self._add_best_source(
                [
                    *self._build_url_candidates(attr_map.get("src")),
                    *self._parse_srcset(attr_map.get("srcset")),
                ]
            )
            for key, value in attr_map.items():
                if key.startswith("data-") and key in {
                    "data-src",
                    "data-original",
                    "data-lazy-src",
                }:
                    self._add_url(value)

        if tag.lower() == "source":
            self._add_best_source(self._parse_srcset(attr_map.get("srcset")))

        if tag.lower() == "link":
            rel = attr_map.get("rel", "").lower()
            if "icon" in rel or "apple-touch-icon" in rel:
                self._add_url(attr_map.get("href"))

        if tag.lower() == "a":
            self._add_page_url(attr_map.get("href"))

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
        if is_fragment_reference(cleaned):
            return

        self.image_urls.append(urllib.parse.urljoin(self.base_url, cleaned))

    def _add_page_url(self, url: str | None) -> None:
        """Add a normalized page URL."""
        if not url:
            return

        cleaned = url.strip()
        if not cleaned or cleaned.startswith(("mailto:", "tel:", "data:", "javascript:", "#")):
            return

        self.page_urls.append(urllib.parse.urljoin(self.base_url, cleaned))

    def _build_url_candidates(self, url: str | None) -> list[ImageSourceCandidate]:
        """Build a single image candidate from a URL."""
        if not url:
            return []

        cleaned = url.strip()
        if not cleaned or cleaned.startswith(("data:", "blob:", "javascript:")):
            return []
        if is_fragment_reference(cleaned):
            return []

        return [ImageSourceCandidate(urllib.parse.urljoin(self.base_url, cleaned))]

    def _parse_srcset(self, srcset: str | None) -> list[ImageSourceCandidate]:
        """Parse image candidates from a srcset attribute."""
        if not srcset:
            return []

        candidates = []
        for candidate in srcset.split(","):
            parts = candidate.strip().split()
            if not parts:
                continue
            built_candidates = self._build_url_candidates(parts[0])
            if not built_candidates:
                continue
            descriptor = parts[1] if len(parts) > 1 else None
            candidates.append(
                ImageSourceCandidate(
                    url=built_candidates[0].url,
                    descriptor=descriptor,
                )
            )

        return candidates

    def _add_best_source(self, candidates: list[ImageSourceCandidate]) -> None:
        """Add the highest-resolution candidate from one image source set."""
        if not candidates:
            return

        best_candidate = max(
            candidates,
            key=lambda candidate: image_resolution_score(candidate.url, candidate.descriptor),
        )
        self.image_urls.append(best_candidate.url)

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


def parse_positive_int(value: str | None) -> int | None:
    """
    Parse a positive integer from a URL value.

    Args:
        value: Raw string value.

    Returns:
        Parsed positive integer, or None when not present.
    """
    if not value:
        return None

    match = re.search(r"\d+", value)
    if not match:
        return None

    parsed = int(match.group(0))
    return parsed if parsed > 0 else None


def parse_positive_float(value: str | None) -> float | None:
    """
    Parse a positive float from a URL value.

    Args:
        value: Raw string value.

    Returns:
        Parsed positive float, or None when not present.
    """
    if not value:
        return None

    match = re.search(r"\d+(?:\.\d+)?", value)
    if not match:
        return None

    parsed = float(match.group(0))
    return parsed if parsed > 0 else None


def get_filename_dimensions(url_path: str) -> tuple[int, int] | None:
    """
    Extract dimensions from common image filename variants.

    Args:
        url_path: URL path, such as /photo-1200x800.jpg.

    Returns:
        Width and height when a dimension suffix is present.
    """
    decoded_path = urllib.parse.unquote(url_path)
    matches = list(DIMENSION_PATTERN.finditer(decoded_path))
    if not matches:
        return None

    match = matches[-1]
    return int(match.group("width")), int(match.group("height"))


def get_query_dimensions(parsed_url: urllib.parse.ParseResult) -> tuple[int | None, int | None]:
    """
    Extract requested dimensions from common resize query parameters.

    Args:
        parsed_url: Parsed image URL.

    Returns:
        Requested width and height values when present.
    """
    width = None
    height = None

    for key, value in urllib.parse.parse_qsl(parsed_url.query, keep_blank_values=True):
        normalized_key = key.lower()
        if normalized_key in WIDTH_QUERY_PARAMETERS and width is None:
            width = parse_positive_int(value)
        if normalized_key in HEIGHT_QUERY_PARAMETERS and height is None:
            height = parse_positive_int(value)

    return width, height


def get_device_pixel_ratio(parsed_url: urllib.parse.ParseResult) -> float:
    """
    Extract a device-pixel-ratio multiplier from an image URL.

    Args:
        parsed_url: Parsed image URL.

    Returns:
        DPR multiplier, defaulting to 1.
    """
    for key, value in urllib.parse.parse_qsl(parsed_url.query, keep_blank_values=True):
        if key.lower() == "dpr":
            return parse_positive_float(value) or 1.0

    return 1.0


def infer_image_dimensions(url: str) -> tuple[int, int] | None:
    """
    Infer image dimensions from URL path and query parameters.

    Args:
        url: Image URL.

    Returns:
        Width and height when dimensions are declared in the URL.
    """
    parsed = urllib.parse.urlparse(url)
    filename_dimensions = get_filename_dimensions(parsed.path)
    query_width, query_height = get_query_dimensions(parsed)

    if query_width and query_height:
        width, height = query_width, query_height
    elif query_width and filename_dimensions:
        filename_width, filename_height = filename_dimensions
        width = query_width
        height = max(1, round(query_width * filename_height / filename_width))
    elif query_height and filename_dimensions:
        filename_width, filename_height = filename_dimensions
        height = query_height
        width = max(1, round(query_height * filename_width / filename_height))
    elif query_width:
        width, height = query_width, query_width
    elif query_height:
        width, height = query_height, query_height
    elif filename_dimensions:
        width, height = filename_dimensions
    else:
        return None

    dpr = get_device_pixel_ratio(parsed)
    return max(1, round(width * dpr)), max(1, round(height * dpr))


def parse_srcset_descriptor_score(descriptor: str | None) -> tuple[float, float]:
    """
    Convert a srcset descriptor into a comparable resolution score.

    Args:
        descriptor: srcset descriptor, such as 1200w or 2x.

    Returns:
        Comparable score tuple.
    """
    if not descriptor:
        return 0, 0

    normalized = descriptor.strip().lower()
    if normalized.endswith("w"):
        width = parse_positive_int(normalized[:-1])
        if width:
            return float(width * width), float(width)

    if normalized.endswith("x"):
        scale = parse_positive_float(normalized[:-1])
        if scale:
            return scale * 1_000_000, scale

    return 0, 0


def image_resolution_score(url: str, descriptor: str | None = None) -> tuple[float, float]:
    """
    Estimate an image candidate's resolution from srcset and URL hints.

    Args:
        url: Image URL.
        descriptor: Optional srcset descriptor.

    Returns:
        Comparable score tuple where larger means higher resolution.
    """
    descriptor_score = parse_srcset_descriptor_score(descriptor)
    if descriptor_score != (0, 0):
        return descriptor_score

    dimensions = infer_image_dimensions(url)
    if dimensions:
        width, height = dimensions
        return float(width * height), float(max(width, height))

    scale_match = SCALE_PATTERN.search(urllib.parse.unquote(urllib.parse.urlparse(url).path))
    if scale_match:
        scale = parse_positive_float(scale_match.group("scale"))
        if scale:
            return scale * 1_000_000, scale

    return 0, 0


def strip_filename_variant_markers(url_path: str) -> str:
    """
    Remove common size markers from a URL path for variant grouping.

    Args:
        url_path: URL path.

    Returns:
        URL path without size suffixes such as -1200x800 or @2x.
    """
    decoded_path = urllib.parse.unquote(url_path)
    without_dimensions = DIMENSION_PATTERN.sub("", decoded_path)
    return SCALE_PATTERN.sub("", without_dimensions)


def image_variant_key(url: str) -> tuple[str, str, str, tuple[tuple[str, str], ...]]:
    """
    Build a stable key for grouping different sizes of the same image.

    Args:
        url: Image URL.

    Returns:
        Tuple key that ignores common responsive size, quality, and format parameters.
    """
    parsed = urllib.parse.urlparse(url)
    filtered_query = tuple(
        sorted(
            (key.lower(), value)
            for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in RESPONSIVE_QUERY_PARAMETERS
        )
    )
    return (
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        strip_filename_variant_markers(parsed.path),
        filtered_query,
    )


def select_highest_resolution_image_urls(image_urls: list[str]) -> list[str]:
    """
    Keep only the highest-resolution URL for repeated image variants.

    Args:
        image_urls: Extracted image URLs.

    Returns:
        Image URLs with responsive variants collapsed.
    """
    selected_by_key: dict[tuple[str, str, str, tuple[tuple[str, str], ...]], str] = {}
    scores_by_key: dict[tuple[str, str, str, tuple[tuple[str, str], ...]], tuple[float, float]] = {}
    key_order: list[tuple[str, str, str, tuple[tuple[str, str], ...]]] = []

    for image_url in image_urls:
        key = image_variant_key(image_url)
        score = image_resolution_score(image_url)

        if key not in selected_by_key:
            selected_by_key[key] = image_url
            scores_by_key[key] = score
            key_order.append(key)
            continue

        if score > scores_by_key[key]:
            selected_by_key[key] = image_url
            scores_by_key[key] = score

    return [selected_by_key[key] for key in key_order]


def extract_image_urls(html: str, base_url: str) -> list[str]:
    """
    Extract unique highest-resolution image URLs from HTML content.

    Args:
        html: HTML content to parse.
        base_url: Base URL for resolving relative links.

    Returns:
        List of unique absolute image URLs in document order, with responsive
        variants collapsed to the largest candidate.
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

    return select_highest_resolution_image_urls(unique_urls)


def extract_page_links(html: str, base_url: str, root_url: str) -> list[str]:
    """
    Extract unique same-site page URLs from HTML content.

    Args:
        html: HTML content to parse.
        base_url: URL for resolving relative links.
        root_url: Original website URL that defines the crawl host.

    Returns:
        Same-host HTTP(S) page URLs in document order.
    """
    parser = WebsiteImageParser(base_url)
    parser.feed(html)

    root_host = urllib.parse.urlparse(root_url).netloc.lower()
    seen: set[str] = set()
    page_links = []

    for page_url in parser.page_urls:
        parsed = urllib.parse.urlparse(page_url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != root_host:
            continue
        if Path(parsed.path).suffix.lower() not in PAGE_EXTENSIONS:
            continue

        normalized = urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, "")
        )
        if normalized not in seen:
            seen.add(normalized)
            page_links.append(normalized)

    return page_links


def sanitize_path_segment(segment: str) -> str:
    """
    Convert a URL path segment into a safe folder name.

    Args:
        segment: URL path segment.

    Returns:
        Filesystem-safe segment.
    """
    decoded = urllib.parse.unquote(segment)
    safe_segment = re.sub(r"[^A-Za-z0-9._-]+", "-", decoded).strip("-._")
    return safe_segment or "page"


def get_page_output_directory(base_output_dir: Path, page_url: str, root_url: str) -> Path:
    """
    Resolve the output directory for a crawled page URL.

    Homepage images are written directly to base_output_dir. Subpage images are
    written to folders that mirror the page path.

    Args:
        base_output_dir: Root output directory.
        page_url: Page URL being processed.
        root_url: Original website URL.

    Returns:
        Output directory for the page.
    """
    root_path = urllib.parse.urlparse(root_url).path.strip("/")
    page_path = urllib.parse.urlparse(page_url).path.strip("/")

    if not page_path or page_path in {"index.html", "index.htm"} or page_path == root_path:
        return base_output_dir

    path = base_output_dir
    for segment in page_path.split("/"):
        if not segment:
            continue
        parsed_segment = Path(segment)
        folder_segment = parsed_segment.stem if parsed_segment.suffix else segment
        path = path / sanitize_path_segment(folder_segment)

    return path


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
    max_pages: int | None = 50,
) -> dict[str, Any]:
    """
    Download images from a website and convert them.

    Args:
        url: Website URL to scan and crawl.
        output_dir: Directory for converted images.
        output_format: Output format: jpg, jpeg, png, or webp.
        quality: Quality for lossy formats.
        timeout: Request timeout in seconds.
        max_pages: Maximum same-site pages to crawl. Use None for no limit.

    Returns:
        dict: Results with download statistics and per-file records.

    Raises:
        ValueError: If inputs are invalid.
        RuntimeError: If the website cannot be fetched.
    """
    normalized_format = normalize_output_format(output_format)
    if not 1 <= quality <= 100:
        raise ValueError("Quality must be between 1 and 100")
    if max_pages is not None and max_pages < 1:
        raise ValueError("Max pages must be at least 1, or None for no limit")

    destination = Path(output_dir or "local/outputs/website-images")
    destination.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {
        "success": True,
        "url": url,
        "pages_scanned": 0,
        "found": 0,
        "downloaded": 0,
        "failed": 0,
        "output_directory": str(destination),
        "format": normalized_format,
        "pages": [],
        "files": [],
    }

    normalized_start_url = urllib.parse.urlunparse(urllib.parse.urlparse(url)._replace(fragment=""))
    pending_urls = [normalized_start_url]
    seen_pages: set[str] = set()

    while pending_urls and (max_pages is None or len(seen_pages) < max_pages):
        page_url = pending_urls.pop(0)
        if page_url in seen_pages:
            continue

        seen_pages.add(page_url)
        page_output_dir = get_page_output_directory(destination, page_url, normalized_start_url)
        page_output_dir.mkdir(parents=True, exist_ok=True)

        try:
            html = fetch_html(page_url, timeout=timeout)
        except RuntimeError as exc:
            results["pages"].append(
                {
                    "success": False,
                    "url": page_url,
                    "output_directory": str(page_output_dir),
                    "error": str(exc),
                }
            )
            continue

        image_urls = extract_image_urls(html, page_url)
        page_links = extract_page_links(html, page_url, normalized_start_url)
        for linked_page in page_links:
            if linked_page not in seen_pages and linked_page not in pending_urls:
                pending_urls.append(linked_page)

        results["pages_scanned"] += 1
        results["found"] += len(image_urls)
        page_result = {
            "success": True,
            "url": page_url,
            "images_found": len(image_urls),
            "output_directory": str(page_output_dir),
        }
        results["pages"].append(page_result)

        for index, image_url in enumerate(image_urls, 1):
            output_path = page_output_dir / build_output_filename(
                image_url, index, normalized_format
            )
            file_result = download_image(
                image_url=image_url,
                output_path=output_path,
                output_format=normalized_format,
                quality=quality,
                timeout=timeout,
            )
            file_result["page_url"] = page_url

            if file_result["success"]:
                results["downloaded"] += 1
            else:
                results["failed"] += 1
            results["files"].append(file_result)

    return results


if __name__ == "__main__":
    print("Website Image Downloader")
    print("Use the main CLI: uv run r10n website-images")
