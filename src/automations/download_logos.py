"""
Company logo downloader automation.

This module finds and downloads logos for requested company or brand names
from the SVGL API. If SVGL does not provide a usable logo, the logo is
reported as failed.
"""

import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

DEFAULT_USER_AGENT = "r10n-logo-downloader/1.0"
DEFAULT_OUTPUT_DIR = "local/outputs/logos"
DEFAULT_TIMEOUT_SECONDS = 5
SVGL_API_URL = "https://api.svgl.app"
MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024
SUPPORTED_DOWNLOAD_FORMATS = {"svg", "png", "webp", "jpg", "jpeg", "ico"}
RASTER_INPUT_FORMATS = {"png", "webp", "jpg", "jpeg", "ico"}
FORMAT_RANK = {
    "svg": 0,
    "png": 1,
    "webp": 2,
    "jpg": 3,
    "jpeg": 3,
    "ico": 4,
}
COMPANY_SUFFIX_WORDS = {
    "co",
    "company",
    "corp",
    "corporation",
    "gmbh",
    "group",
    "inc",
    "incorporated",
    "limited",
    "llc",
    "ltd",
    "plc",
}


def clean_url_text(url: str) -> str:
    """
    Normalize whitespace in URL text read from HTML or search results.

    Args:
        url: Raw URL text.

    Returns:
        URL text with leading/trailing whitespace removed and embedded control
        whitespace collapsed to one space.
    """
    return " ".join(url.strip().split())


@dataclass(frozen=True)
class LogoCandidate:
    """A possible logo source URL."""

    company_name: str
    url: str
    source: str
    format: str | None = None
    width: int | None = None
    height: int | None = None
    description: str = ""
    priority: int = 100


def parse_logo_names(names: str | Sequence[str]) -> list[str]:
    """
    Parse a comma-separated logo name list.

    Args:
        names: Comma-separated string or sequence of strings.

    Returns:
        Unique company/logo names in input order.

    Raises:
        ValueError: If no usable names are provided.
    """
    raw_items: list[str] = []
    if isinstance(names, str):
        raw_items = names.split(",")
    else:
        for name in names:
            raw_items.extend(str(name).split(","))

    parsed_names: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        cleaned = item.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            parsed_names.append(cleaned)
            seen.add(key)

    if not parsed_names:
        raise ValueError("Provide at least one company or logo name")

    return parsed_names


def normalize_ascii(value: str) -> str:
    """
    Normalize text to ASCII.

    Args:
        value: Text to normalize.

    Returns:
        ASCII-only normalized text.
    """
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def sanitize_filename(name: str) -> str:
    """
    Convert a company name to a safe output filename stem.

    Args:
        name: Company or logo name.

    Returns:
        Filesystem-safe lowercase filename stem.
    """
    normalized = normalize_ascii(name).lower()
    normalized = normalized.replace("&", " and ").replace("+", " plus ")
    safe = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return safe or "logo"


def score_svgl_title(query: str, title: str) -> int | None:
    """
    Score how closely an SVGL title matches a requested company name.

    Args:
        query: Requested company or logo name.
        title: SVGL title.

    Returns:
        Lower score for closer matches, or None when the result is unrelated.
    """
    query_slug = sanitize_filename(query)
    title_slug = sanitize_filename(title)
    if not query_slug or not title_slug:
        return None

    if title_slug == query_slug:
        return 0

    title_tokens = set(title_slug.split("-"))
    query_tokens = {
        token
        for token in query_slug.split("-")
        if len(token) >= 3 and token not in COMPANY_SUFFIX_WORDS
    }
    if query_tokens and query_tokens <= title_tokens:
        return 10

    if title_slug.startswith(f"{query_slug}-") or title_slug.endswith(f"-{query_slug}"):
        return 20

    return None


def iter_svgl_asset_urls(svg_record: dict[str, Any]) -> list[tuple[str, str, int]]:
    """
    Extract downloadable SVG asset URLs from an SVGL API record.

    Args:
        svg_record: One SVGL API response item.

    Returns:
        Tuples of source label, URL, and relative priority.
    """
    assets: list[tuple[str, str, int]] = []
    route = svg_record.get("route")
    if isinstance(route, str):
        assets.append(("svgl", route, 0))
    elif isinstance(route, dict):
        for theme_name, priority in (("light", 0), ("dark", 1)):
            themed_url = route.get(theme_name)
            if isinstance(themed_url, str):
                assets.append((f"svgl-{theme_name}", themed_url, priority))

    wordmark = svg_record.get("wordmark")
    if isinstance(wordmark, str):
        assets.append(("svgl-wordmark", wordmark, 3))
    elif isinstance(wordmark, dict):
        for theme_name, priority in (("light", 3), ("dark", 4)):
            themed_url = wordmark.get(theme_name)
            if isinstance(themed_url, str):
                assets.append((f"svgl-wordmark-{theme_name}", themed_url, priority))

    return assets


def collect_svgl_candidates(
    company_name: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    user_agent: str = DEFAULT_USER_AGENT,
) -> list[LogoCandidate]:
    """
    Search SVGL for SVG logo candidates by title.

    Args:
        company_name: Company or brand name.
        timeout: Request timeout in seconds.
        user_agent: User-Agent header value.

    Returns:
        Ranked SVG logo candidates from SVGL.
    """
    query = urllib.parse.urlencode({"search": company_name})
    url = f"{SVGL_API_URL}?{query}"

    try:
        records = fetch_json(url, timeout=timeout, user_agent=user_agent)
    except RuntimeError:
        return []

    if not isinstance(records, list):
        return []

    candidates: list[LogoCandidate] = []
    for record in records:
        if not isinstance(record, dict):
            continue

        title = record.get("title")
        if not isinstance(title, str):
            continue

        match_score = score_svgl_title(company_name, title)
        if match_score is None:
            continue

        for source, asset_url, asset_priority in iter_svgl_asset_urls(record):
            candidates.append(
                LogoCandidate(
                    company_name=company_name,
                    url=asset_url,
                    source=source,
                    format="svg",
                    description=f"SVGL title: {title}",
                    priority=1 + match_score + asset_priority,
                )
            )

    return rank_logo_candidates(candidates)


def get_header(headers: Any, name: str) -> str | None:
    """
    Read a response header from urllib-compatible header objects.

    Args:
        headers: Response headers object.
        name: Header name.

    Returns:
        Header value, if available.
    """
    if not headers:
        return None
    if hasattr(headers, "get"):
        value = headers.get(name)
        if value is None:
            value = headers.get(name.lower())
        return value
    return None


def fetch_json(url: str, timeout: int = 20, user_agent: str = DEFAULT_USER_AGENT) -> dict[str, Any]:
    """
    Fetch JSON from a URL.

    Args:
        url: API URL.
        timeout: Request timeout in seconds.
        user_agent: User-Agent header value.

    Returns:
        Decoded JSON object.

    Raises:
        RuntimeError: If the request or JSON decoding fails.
    """
    normalized_url = clean_url_text(url)
    try:
        normalized_url = normalize_download_url(url)
        request = urllib.request.Request(normalized_url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(f"Could not fetch JSON: {normalized_url}") from exc

    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not decode JSON: {url}") from exc


def format_from_url(url: str) -> str | None:
    """
    Infer a logo format from a URL path.

    Args:
        url: Source URL.

    Returns:
        Normalized format, if known.
    """
    path = urllib.parse.urlparse(url).path.lower()
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix in SUPPORTED_DOWNLOAD_FORMATS:
        return suffix
    return None


def format_from_content_type(content_type: str | None) -> str | None:
    """
    Infer a logo format from a Content-Type header.

    Args:
        content_type: Content-Type header value.

    Returns:
        Normalized format, if known.
    """
    if not content_type:
        return None

    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type == "image/svg+xml":
        return "svg"
    if media_type == "image/png":
        return "png"
    if media_type == "image/webp":
        return "webp"
    if media_type == "image/jpeg":
        return "jpg"
    if media_type in {"image/x-icon", "image/vnd.microsoft.icon"}:
        return "ico"
    return None


def normalize_download_url(url: str) -> str:
    """
    Percent-encode a URL before passing it to urllib.

    Args:
        url: Raw candidate URL.

    Returns:
        HTTP(S) URL safe for urllib.request.

    Raises:
        ValueError: If the URL is not a valid HTTP(S) URL.
    """
    cleaned = clean_url_text(url)
    parsed = urllib.parse.urlsplit(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Unsupported logo URL: {url}")

    path = urllib.parse.quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
    query = urllib.parse.quote(parsed.query, safe="=&?/:@!$'()*+,;%-._~")
    fragment = urllib.parse.quote(parsed.fragment, safe="=&?/:@!$'()*+,;%-._~")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, query, fragment))


def candidate_area(candidate: LogoCandidate) -> int:
    """
    Calculate candidate pixel area.

    Args:
        candidate: Logo candidate.

    Returns:
        Pixel area, or 0 when unknown.
    """
    if not candidate.width or not candidate.height:
        return 0
    return candidate.width * candidate.height


def rank_logo_candidates(candidates: Sequence[LogoCandidate]) -> list[LogoCandidate]:
    """
    Rank and deduplicate logo candidates.

    Args:
        candidates: Candidate list.

    Returns:
        Ranked candidates. SVG is preferred, then PNG, then lower-quality
        raster formats.
    """
    best_by_url: dict[str, LogoCandidate] = {}
    for candidate in candidates:
        normalized_url = candidate.url.split("#", 1)[0]
        existing = best_by_url.get(normalized_url)
        if existing is None or candidate.priority < existing.priority:
            best_by_url[normalized_url] = candidate

    return sorted(
        best_by_url.values(),
        key=lambda candidate: (
            FORMAT_RANK.get(candidate.format or format_from_url(candidate.url) or "", 99),
            candidate.priority,
            -candidate_area(candidate),
            candidate.source,
            candidate.url,
        ),
    )


def collect_logo_candidates(
    company_name: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    user_agent: str = DEFAULT_USER_AGENT,
    search_limit: int = 5,
) -> list[LogoCandidate]:
    """
    Collect ranked logo candidates from SVGL.

    Args:
        company_name: Company or logo name.
        timeout: Request timeout in seconds.
        user_agent: User-Agent header value.
        search_limit: Ignored. Kept for backward-compatible function calls.

    Returns:
        Ranked logo candidates.
    """
    _ = search_limit
    return collect_svgl_candidates(
        company_name=company_name,
        timeout=timeout,
        user_agent=user_agent,
    )


def detect_logo_format(
    data: bytes,
    content_type: str | None = None,
    fallback_format: str | None = None,
) -> str | None:
    """
    Detect the downloaded logo format.

    Args:
        data: Downloaded bytes.
        content_type: Response Content-Type header.
        fallback_format: Candidate-provided or URL-inferred format.

    Returns:
        Normalized detected format, if supported.
    """
    header_format = format_from_content_type(content_type)
    if header_format:
        return header_format

    prefix = data[:4096].lower()
    if b"<svg" in prefix:
        return "svg"

    try:
        with Image.open(BytesIO(data)) as image:
            image_format = (image.format or "").lower()
    except UnidentifiedImageError:
        image_format = ""

    if image_format == "jpeg":
        return "jpg"
    if image_format in SUPPORTED_DOWNLOAD_FORMATS:
        return image_format

    return fallback_format if fallback_format in SUPPORTED_DOWNLOAD_FORMATS else None


def read_remote_bytes(
    url: str,
    timeout: int = 20,
    user_agent: str = DEFAULT_USER_AGENT,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> tuple[bytes, str | None]:
    """
    Download bytes from a URL with a size limit.

    Args:
        url: Source URL.
        timeout: Request timeout in seconds.
        user_agent: User-Agent header value.
        max_bytes: Maximum bytes to read.

    Returns:
        Tuple of downloaded bytes and Content-Type header.

    Raises:
        RuntimeError: If the file cannot be downloaded or is too large.
    """
    normalized_url = clean_url_text(url)
    try:
        normalized_url = normalize_download_url(url)
        request = urllib.request.Request(normalized_url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_length = get_header(response.headers, "Content-Length")
            if content_length:
                try:
                    if int(content_length) > max_bytes:
                        raise RuntimeError(f"File is too large: {content_length} bytes")
                except ValueError:
                    pass
            data = response.read(max_bytes + 1)
            content_type = get_header(response.headers, "Content-Type")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(f"Could not download: {normalized_url}") from exc

    if len(data) > max_bytes:
        raise RuntimeError(f"File is too large: more than {max_bytes} bytes")
    if not data:
        raise RuntimeError("Downloaded file is empty")

    return data, content_type


def write_logo_file(
    data: bytes,
    output_stem: Path,
    detected_format: str,
) -> tuple[Path, str, int | None, int | None]:
    """
    Validate and write logo data.

    Args:
        data: Downloaded bytes.
        output_stem: Output path without extension.
        detected_format: Detected source format.

    Returns:
        Tuple of output path, saved format, width, and height.

    Raises:
        ValueError: If the logo data is invalid or unsupported.
    """
    output_stem.parent.mkdir(parents=True, exist_ok=True)

    if detected_format == "svg":
        prefix = data[:4096].lower()
        if b"<svg" not in prefix:
            raise ValueError("Downloaded file is not valid SVG")
        output_path = output_stem.with_suffix(".svg")
        output_path.write_bytes(data)
        return output_path, "svg", None, None

    if detected_format not in RASTER_INPUT_FORMATS:
        raise ValueError(f"Unsupported logo format: {detected_format}")

    try:
        with Image.open(BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)
            width, height = image.size
            if image.mode == "P":
                image = image.convert("RGBA")
            elif image.mode not in {"RGB", "RGBA", "LA", "L"}:
                image = image.convert("RGBA")

            output_path = output_stem.with_suffix(".png")
            image.save(output_path, "PNG", optimize=True)
            return output_path, "png", width, height
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Downloaded file is not a supported raster logo") from exc


def download_logo_candidate(
    candidate: LogoCandidate,
    output_stem: Path,
    timeout: int = 20,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, Any]:
    """
    Download one logo candidate.

    Args:
        candidate: Logo candidate.
        output_stem: Output path without extension.
        timeout: Request timeout in seconds.
        user_agent: User-Agent header value.

    Returns:
        Result dictionary for this candidate.
    """
    try:
        data, content_type = read_remote_bytes(
            candidate.url,
            timeout=timeout,
            user_agent=user_agent,
        )
        detected_format = detect_logo_format(
            data,
            content_type=content_type,
            fallback_format=candidate.format or format_from_url(candidate.url),
        )
        if not detected_format:
            raise ValueError("Could not detect a supported logo format")

        output_path, saved_format, width, height = write_logo_file(
            data=data,
            output_stem=output_stem,
            detected_format=detected_format,
        )
        return {
            "success": True,
            "company_name": candidate.company_name,
            "source": candidate.source,
            "source_url": candidate.url,
            "output_file": str(output_path),
            "format": saved_format,
            "source_format": detected_format,
            "width": width or candidate.width,
            "height": height or candidate.height,
            "bytes_downloaded": len(data),
        }
    except (RuntimeError, ValueError) as exc:
        return {
            "success": False,
            "company_name": candidate.company_name,
            "source": candidate.source,
            "source_url": candidate.url,
            "error": str(exc),
        }


def find_existing_logo(output_dir: Path, filename_stem: str) -> Path | None:
    """
    Find an existing saved logo.

    Args:
        output_dir: Output directory.
        filename_stem: Filename stem to check.

    Returns:
        Existing SVG or PNG path, if found.
    """
    for extension in ("svg", "png"):
        path = output_dir / f"{filename_stem}.{extension}"
        if path.exists():
            return path
    return None


def remove_alternate_logo_files(output_dir: Path, filename_stem: str, keep_path: Path) -> None:
    """
    Remove stale alternate logo files after a successful overwrite.

    Args:
        output_dir: Output directory.
        filename_stem: Filename stem to check.
        keep_path: Newly written file that should remain.
    """
    for extension in ("svg", "png"):
        path = output_dir / f"{filename_stem}.{extension}"
        if path != keep_path and path.exists():
            path.unlink()


def download_logo_for_name(
    company_name: str,
    output_dir: Path,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_candidates: int = 20,
    overwrite: bool = False,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, Any]:
    """
    Download the best working logo for one company name.

    Args:
        company_name: Company or logo name.
        output_dir: Output directory.
        timeout: Request timeout in seconds.
        max_candidates: Maximum ranked candidates to try.
        overwrite: Replace existing SVG/PNG output files.
        user_agent: User-Agent header value.

    Returns:
        Result dictionary for the company.
    """
    filename_stem = sanitize_filename(company_name)
    if not overwrite:
        existing = find_existing_logo(output_dir, filename_stem)
        if existing:
            return {
                "success": True,
                "skipped": True,
                "company_name": company_name,
                "output_file": str(existing),
                "format": existing.suffix.lstrip("."),
                "message": "Logo already exists",
            }

    candidates = collect_logo_candidates(
        company_name=company_name,
        timeout=timeout,
        user_agent=user_agent,
    )
    if max_candidates > 0:
        candidates = candidates[:max_candidates]

    output_stem = output_dir / filename_stem
    failures: list[dict[str, Any]] = []
    for candidate in candidates:
        result = download_logo_candidate(
            candidate=candidate,
            output_stem=output_stem,
            timeout=timeout,
            user_agent=user_agent,
        )
        if result.get("success"):
            if overwrite:
                remove_alternate_logo_files(
                    output_dir=output_dir,
                    filename_stem=filename_stem,
                    keep_path=Path(str(result["output_file"])),
                )
            result["skipped"] = False
            result["candidates_tried"] = len(failures) + 1
            return result
        failures.append(result)

    return {
        "success": False,
        "skipped": False,
        "company_name": company_name,
        "candidates_tried": len(candidates),
        "errors": failures[:5],
        "error": "No working SVG logo found in SVGL",
    }


def download_logos(
    names: str | Sequence[str],
    output_dir: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_candidates: int = 20,
    overwrite: bool = False,
    write_manifest: bool = True,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """
    Download logos for a comma-separated list of company names.

    Args:
        names: Comma-separated names or sequence of names.
        output_dir: Directory for downloaded logos.
        timeout: Request timeout in seconds.
        max_candidates: Maximum ranked candidates to try per company.
        overwrite: Replace existing SVG/PNG output files.
        write_manifest: Write a JSON manifest with download results.
        progress_callback: Optional callback called after each company result.

    Returns:
        dict: Results with download statistics and per-logo records.

    Raises:
        ValueError: If inputs are invalid.
    """
    company_names = parse_logo_names(names)
    if timeout < 1:
        raise ValueError("Timeout must be at least 1 second")
    if max_candidates < 1:
        raise ValueError("Max candidates must be at least 1")

    destination = Path(output_dir or DEFAULT_OUTPUT_DIR)
    destination.mkdir(parents=True, exist_ok=True)

    logo_results = []
    for company_name in company_names:
        logo_result = download_logo_for_name(
            company_name=company_name,
            output_dir=destination,
            timeout=timeout,
            max_candidates=max_candidates,
            overwrite=overwrite,
        )
        logo_results.append(logo_result)
        if progress_callback:
            progress_callback(logo_result)

    downloaded = sum(
        1 for result in logo_results if result.get("success") and not result.get("skipped")
    )
    skipped = sum(1 for result in logo_results if result.get("skipped"))
    failed = sum(
        1 for result in logo_results if not result.get("success") and not result.get("skipped")
    )

    results: dict[str, Any] = {
        "success": failed == 0,
        "requested": len(company_names),
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "output_directory": str(destination),
        "logos": logo_results,
    }

    if write_manifest:
        manifest_path = destination / "logos_manifest.json"
        manifest_payload = {
            **results,
            "logos": list(logo_results),
        }
        manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
        results["manifest_file"] = str(manifest_path)

    return results


def candidates_to_dicts(candidates: Sequence[LogoCandidate]) -> list[dict[str, Any]]:
    """
    Convert logo candidates to dictionaries.

    Args:
        candidates: Candidate list.

    Returns:
        Serializable candidate dictionaries.
    """
    return [asdict(candidate) for candidate in candidates]


if __name__ == "__main__":
    print("Logo Downloader")
    print("Use the main CLI: uv run r10n logos")
