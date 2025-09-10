import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageOps


@dataclass
class ImageOptimizationConfig:
    """Configuration for image optimization"""

    input_directory: str
    output_directory: str
    prefix: str = "img"
    max_size_mb: float = 1.0
    quality: int = 85
    max_width: int = 1920
    max_height: int = 1080
    convert_to_webp: bool = True
    preserve_aspect_ratio: bool = True
    auto_orient: bool = True
    preserve_filename: bool = False


class ImageOptimizer:
    """Optimize and rename images for web use"""

    def __init__(self, config: ImageOptimizationConfig):
        self.config = config
        self.supported_formats = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
        self.results = {
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "total_size_before": 0,
            "total_size_after": 0,
            "files": [],
        }

    def get_file_size_mb(self, file_path: Path) -> float:
        """Get file size in MB"""
        return file_path.stat().st_size / (1024 * 1024)

    def calculate_new_dimensions(self, width: int, height: int) -> tuple:
        """Calculate new dimensions while preserving aspect ratio"""
        if not self.config.preserve_aspect_ratio:
            return min(width, self.config.max_width), min(height, self.config.max_height)

        # Calculate scaling factor
        width_ratio = self.config.max_width / width
        height_ratio = self.config.max_height / height
        scale_ratio = min(width_ratio, height_ratio, 1.0)  # Don't upscale

        new_width = int(width * scale_ratio)
        new_height = int(height * scale_ratio)

        return new_width, new_height

    def optimize_image(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Optimize a single image"""
        try:
            print(f"🖼️  Processing: {input_path.name}")

            # Record original size
            original_size_mb = self.get_file_size_mb(input_path)

            # Open and process image
            with Image.open(input_path) as img:
                # Auto-orient if enabled
                if self.config.auto_orient:
                    img = ImageOps.exif_transpose(img)

                # Convert to RGB if necessary (for WEBP)
                if img.mode in ("RGBA", "LA", "P") and self.config.convert_to_webp:
                    # Create white background for transparency
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = background
                elif img.mode != "RGB" and not self.config.convert_to_webp:
                    img = img.convert("RGB")

                # Calculate new dimensions
                new_width, new_height = self.calculate_new_dimensions(img.width, img.height)

                # Resize if necessary
                if new_width != img.width or new_height != img.height:
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    print(f"  📏 Resized from {input_path.stem}: {img.width}x{img.height}")

                # Determine output format and extension
                output_format = "WEBP" if self.config.convert_to_webp else "JPEG"

                # Save with initial quality
                current_quality = self.config.quality
                temp_output = output_path

                while current_quality >= 10:
                    # Save with current quality
                    save_kwargs = {
                        "format": output_format,
                        "optimize": True,
                        "quality": current_quality,
                    }

                    if output_format == "WEBP":
                        save_kwargs["method"] = 6  # Better compression

                    img.save(temp_output, **save_kwargs)

                    # Check file size
                    new_size_mb = self.get_file_size_mb(temp_output)

                    if new_size_mb <= self.config.max_size_mb or current_quality <= 10:
                        break

                    # Reduce quality and try again
                    current_quality -= 5
                    print(
                        f"  🔄 Reducing quality to {current_quality}% (size: {new_size_mb:.2f}MB)"
                    )

                final_size_mb = self.get_file_size_mb(output_path)

                # Create result info
                result = {
                    "success": True,
                    "original_file": str(input_path),
                    "output_file": str(output_path),
                    "original_size_mb": original_size_mb,
                    "final_size_mb": final_size_mb,
                    "compression_ratio": (1 - final_size_mb / original_size_mb) * 100,
                    "final_quality": current_quality,
                    "dimensions": f"{new_width}x{new_height}",
                }

                print(f"  ✅ Saved: {output_path.name}")
                print(
                    f"  📊 Size: {original_size_mb:.2f}MB → {final_size_mb:.2f}MB ({result['compression_ratio']:.1f}% reduction)"
                )

                return result

        except Exception as e:
            error_result = {"success": False, "original_file": str(input_path), "error": str(e)}
            print(f"  ❌ Error: {e!s}")
            return error_result

    def get_image_files(self, directory: Path) -> List[Path]:
        """Get all supported image files from directory"""
        image_files = []

        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                image_files.append(file_path)

        # Sort for consistent numbering
        image_files.sort(key=lambda x: x.name.lower())
        return image_files

    def generate_output_filename(
        self, index: int, original_name: str, original_extension: str = None
    ) -> str:
        """Generate output filename with prefix and number or preserve original name"""
        if self.config.preserve_filename:
            # Preserve original filename but change extension if converting to WebP
            if self.config.convert_to_webp:
                # Remove original extension and add .webp
                name_without_ext = Path(original_name).stem
                return f"{name_without_ext}.webp"
            else:
                # Keep original extension
                return original_name
        else:
            # Use prefix + index naming
            if self.config.convert_to_webp:
                extension = ".webp"
            else:
                extension = original_extension or ".jpg"

            return f"{self.config.prefix}{index}{extension}"

    def process_directory(self) -> Dict[str, Any]:
        """Process all images in the input directory"""
        try:
            input_path = Path(self.config.input_directory)
            output_path = Path(self.config.output_directory)

            # Validate input directory
            if not input_path.exists():
                raise Exception(f"Input directory does not exist: {input_path}")

            # Create output directory
            output_path.mkdir(parents=True, exist_ok=True)

            # Get all image files
            image_files = self.get_image_files(input_path)

            if not image_files:
                print(f"⚠️  No supported image files found in {input_path}")
                return self.results

            print("🚀 Starting image optimization...")
            print(f"📁 Input: {input_path}")
            print(f"📁 Output: {output_path}")
            print(f"🖼️  Found {len(image_files)} images to process")
            print(
                f"🎯 Target: WebP format, max {self.config.max_size_mb}MB, quality {self.config.quality}%"
            )
            print()

            # Process each image
            for index, image_file in enumerate(image_files, 1):
                output_filename = self.generate_output_filename(
                    index, image_file.name, image_file.suffix
                )
                output_file_path = output_path / output_filename

                # Skip if output file already exists
                if output_file_path.exists():
                    print(f"⏭️  Skipping {image_file.name} (output exists)")
                    self.results["skipped"] += 1
                    continue

                # Process the image
                result = self.optimize_image(image_file, output_file_path)

                if result["success"]:
                    self.results["processed"] += 1
                    self.results["total_size_before"] += result["original_size_mb"]
                    self.results["total_size_after"] += result["final_size_mb"]
                else:
                    self.results["failed"] += 1

                self.results["files"].append(result)
                print()

            # Print summary
            self.print_summary()

            return self.results

        except Exception as e:
            print(f"❌ Error processing directory: {e!s}")
            self.results["error"] = str(e)
            return self.results

    def print_summary(self):
        """Print processing summary"""
        total_files = len(self.results["files"])

        print("📊 Image Optimization Summary:")
        print(f"📁 Total files found: {total_files}")
        print(f"✅ Successfully processed: {self.results['processed']}")
        print(f"⏭️  Skipped (already exists): {self.results['skipped']}")
        print(f"❌ Failed: {self.results['failed']}")

        if self.results["processed"] > 0:
            total_reduction = self.results["total_size_before"] - self.results["total_size_after"]
            reduction_percentage = (total_reduction / self.results["total_size_before"]) * 100

            print(f"📊 Size before: {self.results['total_size_before']:.2f}MB")
            print(f"📊 Size after: {self.results['total_size_after']:.2f}MB")
            print(
                f"💾 Total saved: {total_reduction:.2f}MB ({reduction_percentage:.1f}% reduction)"
            )

        print(f"📁 Output directory: {self.config.output_directory}")


def load_config(config_path: str) -> ImageOptimizationConfig:
    """Load configuration from JSON file"""
    try:
        with open(config_path) as f:
            config_data = json.load(f)

        return ImageOptimizationConfig(**config_data)

    except Exception as e:
        print(f"❌ Error loading configuration: {e!s}")
        raise


def optimize_images(
    input_dir: str,
    output_dir: str = None,
    prefix: str = "img",
    max_size_mb: float = 1.0,
    quality: int = 85,
    max_width: int = 1920,
    max_height: int = 1080,
    preserve_filename: bool = False,
    config_file: str = None,
) -> Dict[str, Any]:
    """Main function to optimize images"""
    try:
        if config_file:
            # Load from config file
            config = load_config(config_file)
            # Override with command line arguments if provided
            if output_dir:
                config.output_directory = output_dir
            if prefix != "img":
                config.prefix = prefix
        else:
            # Create config from parameters
            if not output_dir:
                output_dir = str(Path(input_dir) / "optimized")

            config = ImageOptimizationConfig(
                input_directory=input_dir,
                output_directory=output_dir,
                prefix=prefix,
                max_size_mb=max_size_mb,
                quality=quality,
                max_width=max_width,
                max_height=max_height,
                preserve_filename=preserve_filename,
            )

        # Create optimizer and process
        optimizer = ImageOptimizer(config)
        results = optimizer.process_directory()

        return results

    except Exception as e:
        print(f"❌ Error in image optimization: {e!s}")
        return {"success": False, "error": str(e), "processed": 0, "failed": 0, "skipped": 0}


if __name__ == "__main__":
    print("Image Optimizer for Web")
    print("Use the main CLI to run this automation:")
    print("python src/main.py optimize_images --input 'path/to/images' --prefix 'photo'")
