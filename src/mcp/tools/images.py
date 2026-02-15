"""MCP tool for image optimization."""

from src.automations.optimize_images import optimize_images as _optimize_images
from src.mcp.server import mcp


@mcp.tool()
def optimize_images(
    input_dir: str,
    output_dir: str | None = None,
    prefix: str = "img",
    max_size_mb: float = 1.0,
    quality: int = 85,
    max_width: int = 1920,
    max_height: int = 1080,
    preserve_filename: bool = False,
) -> dict:
    """Optimize and convert images to WebP format.

    Args:
        input_dir: Directory containing images to optimize.
        output_dir: Output directory (auto-generated if not provided).
        prefix: Filename prefix for renamed images.
        max_size_mb: Target maximum file size in MB.
        quality: Image quality (1-100).
        max_width: Maximum width in pixels.
        max_height: Maximum height in pixels.
        preserve_filename: Keep original filenames instead of renaming.
    """
    try:
        return _optimize_images(
            input_dir=input_dir,
            output_dir=output_dir,
            prefix=prefix,
            max_size_mb=max_size_mb,
            quality=quality,
            max_width=max_width,
            max_height=max_height,
            preserve_filename=preserve_filename,
        )
    except Exception as e:
        return {"error": str(e)}
