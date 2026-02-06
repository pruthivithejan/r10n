"""
Tests for the Image Optimization automation.

These tests verify the image optimization functionality for both
local usage and uvx distribution.
"""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from PIL import Image

from src.automations.optimize_images import (
    ImageOptimizationConfig,
    ImageOptimizer,
    load_config,
    optimize_images,
)


class TestImageOptimizationConfig:
    """Test ImageOptimizationConfig dataclass."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = ImageOptimizationConfig(input_directory="input", output_directory="output")
        assert config.prefix == "img"
        assert config.max_size_mb == 1.0
        assert config.quality == 85
        assert config.max_width == 1920
        assert config.max_height == 1080
        assert config.convert_to_webp is True
        assert config.preserve_aspect_ratio is True
        assert config.auto_orient is True
        assert config.preserve_filename is False

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = ImageOptimizationConfig(
            input_directory="/path/to/input",
            output_directory="/path/to/output",
            prefix="photo",
            max_size_mb=2.0,
            quality=90,
            max_width=3840,
            max_height=2160,
            convert_to_webp=False,
            preserve_aspect_ratio=False,
            auto_orient=False,
            preserve_filename=True,
        )
        assert config.input_directory == "/path/to/input"
        assert config.prefix == "photo"
        assert config.max_size_mb == 2.0
        assert config.quality == 90
        assert config.convert_to_webp is False
        assert config.preserve_filename is True


class TestImageOptimizer:
    """Test ImageOptimizer class."""

    @pytest.fixture
    def optimizer(self):
        """Create an ImageOptimizer instance for testing."""
        config = ImageOptimizationConfig(input_directory="input", output_directory="output")
        return ImageOptimizer(config)

    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            img = Image.new("RGB", (800, 600), color="red")
            img.save(f.name, "JPEG")
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_supported_formats(self, optimizer):
        """Test supported image formats."""
        expected_formats = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
        assert optimizer.supported_formats == expected_formats

    def test_initial_results(self, optimizer):
        """Test initial results dictionary."""
        assert optimizer.results["processed"] == 0
        assert optimizer.results["skipped"] == 0
        assert optimizer.results["failed"] == 0
        assert optimizer.results["total_size_before"] == 0
        assert optimizer.results["total_size_after"] == 0
        assert optimizer.results["files"] == []

    def test_get_file_size_mb(self, optimizer, sample_image):
        """Test file size calculation in MB."""
        size_mb = optimizer.get_file_size_mb(Path(sample_image))
        assert isinstance(size_mb, float)
        assert size_mb > 0


class TestCalculateNewDimensions:
    """Test dimension calculation functionality."""

    @pytest.fixture
    def optimizer(self):
        """Create an ImageOptimizer with default config."""
        config = ImageOptimizationConfig(
            input_directory="input", output_directory="output", max_width=1920, max_height=1080
        )
        return ImageOptimizer(config)

    def test_smaller_than_max(self, optimizer):
        """Test image smaller than max dimensions."""
        new_width, new_height = optimizer.calculate_new_dimensions(800, 600)
        assert new_width == 800
        assert new_height == 600

    def test_width_exceeds_max(self, optimizer):
        """Test image with width exceeding max."""
        new_width, new_height = optimizer.calculate_new_dimensions(3840, 1080)
        assert new_width == 1920
        assert new_height == 540  # Maintains aspect ratio

    def test_height_exceeds_max(self, optimizer):
        """Test image with height exceeding max."""
        new_width, new_height = optimizer.calculate_new_dimensions(1920, 2160)
        assert new_height == 1080
        assert new_width == 960  # Maintains aspect ratio

    def test_both_exceed_max(self, optimizer):
        """Test image with both dimensions exceeding max."""
        new_width, new_height = optimizer.calculate_new_dimensions(3840, 2160)
        # Should scale down to fit within 1920x1080
        assert new_width <= 1920
        assert new_height <= 1080

    def test_no_upscaling(self, optimizer):
        """Test that small images are not upscaled."""
        new_width, new_height = optimizer.calculate_new_dimensions(640, 480)
        assert new_width == 640
        assert new_height == 480

    def test_preserve_aspect_ratio_disabled(self):
        """Test dimension calculation without aspect ratio preservation."""
        config = ImageOptimizationConfig(
            input_directory="input",
            output_directory="output",
            max_width=1920,
            max_height=1080,
            preserve_aspect_ratio=False,
        )
        optimizer = ImageOptimizer(config)

        new_width, new_height = optimizer.calculate_new_dimensions(3840, 2160)
        assert new_width == 1920
        assert new_height == 1080

    def test_exact_max_dimensions(self, optimizer):
        """Test image with exact max dimensions."""
        new_width, new_height = optimizer.calculate_new_dimensions(1920, 1080)
        assert new_width == 1920
        assert new_height == 1080


class TestOptimizeImage:
    """Test single image optimization functionality."""

    @pytest.fixture
    def optimizer(self):
        """Create an ImageOptimizer for testing."""
        with tempfile.TemporaryDirectory() as output_dir:
            config = ImageOptimizationConfig(
                input_directory="input", output_directory=output_dir, quality=85
            )
            yield ImageOptimizer(config)

    @pytest.fixture
    def create_test_image(self):
        """Factory fixture to create test images."""
        created_files = []

        def _create(width=800, height=600, mode="RGB", suffix=".jpg"):
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                img = Image.new(mode, (width, height), color="blue")
                format_map = {".jpg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
                img.save(f.name, format_map.get(suffix, "JPEG"))
                created_files.append(f.name)
                return f.name

        yield _create

        # Cleanup
        for f in created_files:
            Path(f).unlink(missing_ok=True)

    def test_optimize_image_basic(self, create_test_image):
        """Test basic image optimization."""
        with tempfile.TemporaryDirectory() as output_dir:
            config = ImageOptimizationConfig(input_directory="input", output_directory=output_dir)
            optimizer = ImageOptimizer(config)

            input_path = Path(create_test_image())
            output_path = Path(output_dir) / "output.webp"

            result = optimizer.optimize_image(input_path, output_path)

            assert result["success"] is True
            assert output_path.exists()
            assert "original_size_mb" in result
            assert "final_size_mb" in result
            assert "compression_ratio" in result

    def test_optimize_image_preserves_dimensions_for_small(self, create_test_image):
        """Test that small images keep their dimensions."""
        with tempfile.TemporaryDirectory() as output_dir:
            config = ImageOptimizationConfig(
                input_directory="input",
                output_directory=output_dir,
                max_width=1920,
                max_height=1080,
            )
            optimizer = ImageOptimizer(config)

            input_path = Path(create_test_image(width=640, height=480))
            output_path = Path(output_dir) / "output.webp"

            result = optimizer.optimize_image(input_path, output_path)

            assert result["success"] is True
            assert result["dimensions"] == "640x480"

    def test_optimize_image_resizes_large(self, create_test_image):
        """Test that large images are resized."""
        with tempfile.TemporaryDirectory() as output_dir:
            config = ImageOptimizationConfig(
                input_directory="input", output_directory=output_dir, max_width=800, max_height=600
            )
            optimizer = ImageOptimizer(config)

            input_path = Path(create_test_image(width=1600, height=1200))
            output_path = Path(output_dir) / "output.webp"

            result = optimizer.optimize_image(input_path, output_path)

            assert result["success"] is True
            # Should be scaled down
            dims = result["dimensions"].split("x")
            assert int(dims[0]) <= 800
            assert int(dims[1]) <= 600

    def test_optimize_image_converts_to_webp(self, create_test_image):
        """Test conversion to WebP format."""
        with tempfile.TemporaryDirectory() as output_dir:
            config = ImageOptimizationConfig(
                input_directory="input", output_directory=output_dir, convert_to_webp=True
            )
            optimizer = ImageOptimizer(config)

            input_path = Path(create_test_image(suffix=".jpg"))
            output_path = Path(output_dir) / "output.webp"

            result = optimizer.optimize_image(input_path, output_path)

            assert result["success"] is True
            assert output_path.suffix == ".webp"

    def test_optimize_image_rgba_to_rgb(self, create_test_image):
        """Test RGBA image is converted to RGB for WebP."""
        with tempfile.TemporaryDirectory() as output_dir:
            config = ImageOptimizationConfig(
                input_directory="input", output_directory=output_dir, convert_to_webp=True
            )
            optimizer = ImageOptimizer(config)

            # Create RGBA image
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
                img.save(f.name, "PNG")
                input_path = Path(f.name)

            try:
                output_path = Path(output_dir) / "output.webp"
                result = optimizer.optimize_image(input_path, output_path)
                assert result["success"] is True
            finally:
                input_path.unlink(missing_ok=True)

    def test_optimize_image_error_handling(self):
        """Test error handling for invalid image."""
        with tempfile.TemporaryDirectory() as output_dir:
            config = ImageOptimizationConfig(input_directory="input", output_directory=output_dir)
            optimizer = ImageOptimizer(config)

            # Create invalid file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, mode="w") as f:
                f.write("not an image")
                input_path = Path(f.name)

            try:
                output_path = Path(output_dir) / "output.webp"
                result = optimizer.optimize_image(input_path, output_path)
                assert result["success"] is False
                assert "error" in result
            finally:
                input_path.unlink(missing_ok=True)


class TestGenerateOutputFilename:
    """Test output filename generation."""

    def test_filename_with_prefix(self):
        """Test filename generation with prefix."""
        config = ImageOptimizationConfig(
            input_directory="input", output_directory="output", prefix="photo", convert_to_webp=True
        )
        optimizer = ImageOptimizer(config)

        filename = optimizer.generate_output_filename(1, "original.jpg")
        assert filename == "photo1.webp"

    def test_filename_sequential_numbering(self):
        """Test sequential numbering in filenames."""
        config = ImageOptimizationConfig(
            input_directory="input", output_directory="output", prefix="img"
        )
        optimizer = ImageOptimizer(config)

        assert optimizer.generate_output_filename(1, "a.jpg") == "img1.webp"
        assert optimizer.generate_output_filename(10, "b.jpg") == "img10.webp"
        assert optimizer.generate_output_filename(100, "c.jpg") == "img100.webp"

    def test_filename_preserve_original(self):
        """Test preserving original filename."""
        config = ImageOptimizationConfig(
            input_directory="input",
            output_directory="output",
            preserve_filename=True,
            convert_to_webp=True,
        )
        optimizer = ImageOptimizer(config)

        filename = optimizer.generate_output_filename(1, "my_photo.jpg")
        assert filename == "my_photo.webp"

    def test_filename_preserve_without_webp_conversion(self):
        """Test preserving filename without WebP conversion."""
        config = ImageOptimizationConfig(
            input_directory="input",
            output_directory="output",
            preserve_filename=True,
            convert_to_webp=False,
        )
        optimizer = ImageOptimizer(config)

        filename = optimizer.generate_output_filename(1, "my_photo.jpg")
        assert filename == "my_photo.jpg"

    def test_filename_without_webp(self):
        """Test filename without WebP conversion."""
        config = ImageOptimizationConfig(
            input_directory="input", output_directory="output", prefix="img", convert_to_webp=False
        )
        optimizer = ImageOptimizer(config)

        filename = optimizer.generate_output_filename(1, "original.jpg", ".jpg")
        assert filename == "img1.jpg"


class TestGetImageFiles:
    """Test image file discovery."""

    def test_get_image_files_basic(self):
        """Test finding image files in directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create various files
            (temp_path / "image1.jpg").write_bytes(b"fake jpg")
            (temp_path / "image2.png").write_bytes(b"fake png")
            (temp_path / "document.txt").write_text("not an image")
            (temp_path / "script.py").write_text("print('hello')")

            config = ImageOptimizationConfig(input_directory=temp_dir, output_directory="output")
            optimizer = ImageOptimizer(config)

            image_files = optimizer.get_image_files(temp_path)
            assert len(image_files) == 2
            extensions = {f.suffix.lower() for f in image_files}
            assert extensions == {".jpg", ".png"}

    def test_get_image_files_all_formats(self):
        """Test finding all supported image formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            formats = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]
            for i, ext in enumerate(formats):
                (temp_path / f"image{i}{ext}").write_bytes(b"fake")

            config = ImageOptimizationConfig(input_directory=temp_dir, output_directory="output")
            optimizer = ImageOptimizer(config)

            image_files = optimizer.get_image_files(temp_path)
            assert len(image_files) == len(formats)

    def test_get_image_files_sorted(self):
        """Test that image files are sorted by name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            (temp_path / "zebra.jpg").write_bytes(b"fake")
            (temp_path / "apple.jpg").write_bytes(b"fake")
            (temp_path / "mango.jpg").write_bytes(b"fake")

            config = ImageOptimizationConfig(input_directory=temp_dir, output_directory="output")
            optimizer = ImageOptimizer(config)

            image_files = optimizer.get_image_files(temp_path)
            names = [f.name for f in image_files]
            assert names == ["apple.jpg", "mango.jpg", "zebra.jpg"]

    def test_get_image_files_empty_directory(self):
        """Test empty directory returns empty list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ImageOptimizationConfig(input_directory=temp_dir, output_directory="output")
            optimizer = ImageOptimizer(config)

            image_files = optimizer.get_image_files(Path(temp_dir))
            assert image_files == []


class TestProcessDirectory:
    """Test batch directory processing."""

    @pytest.fixture
    def setup_test_images(self):
        """Set up a directory with test images."""
        with tempfile.TemporaryDirectory() as input_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                input_path = Path(input_dir)

                # Create test images
                for i in range(3):
                    img = Image.new("RGB", (800, 600), color=(i * 80, 0, 0))
                    img.save(input_path / f"image{i}.jpg", "JPEG")

                yield {
                    "input_dir": input_dir,
                    "output_dir": output_dir,
                }

    def test_process_directory_basic(self, setup_test_images):
        """Test basic directory processing."""
        dirs = setup_test_images

        config = ImageOptimizationConfig(
            input_directory=dirs["input_dir"], output_directory=dirs["output_dir"]
        )
        optimizer = ImageOptimizer(config)

        results = optimizer.process_directory()

        assert results["processed"] == 3
        assert results["failed"] == 0
        assert results["skipped"] == 0
        assert len(results["files"]) == 3

        # Check output files exist
        output_path = Path(dirs["output_dir"])
        webp_files = list(output_path.glob("*.webp"))
        assert len(webp_files) == 3

    def test_process_directory_skips_existing(self, setup_test_images):
        """Test that existing output files are skipped."""
        dirs = setup_test_images

        config = ImageOptimizationConfig(
            input_directory=dirs["input_dir"], output_directory=dirs["output_dir"]
        )
        optimizer = ImageOptimizer(config)

        # First run
        optimizer.process_directory()

        # Second run with fresh optimizer
        optimizer2 = ImageOptimizer(config)
        results = optimizer2.process_directory()

        assert results["processed"] == 0
        assert results["skipped"] == 3

    def test_process_directory_nonexistent_input(self):
        """Test error for nonexistent input directory."""
        config = ImageOptimizationConfig(
            input_directory="/nonexistent/path", output_directory="output"
        )
        optimizer = ImageOptimizer(config)

        results = optimizer.process_directory()
        assert "error" in results

    def test_process_directory_creates_output(self, setup_test_images):
        """Test that output directory is created."""
        dirs = setup_test_images
        new_output = Path(dirs["output_dir"]) / "nested" / "output"

        config = ImageOptimizationConfig(
            input_directory=dirs["input_dir"], output_directory=str(new_output)
        )
        optimizer = ImageOptimizer(config)

        optimizer.process_directory()

        assert new_output.exists()

    def test_process_directory_empty(self):
        """Test processing empty directory."""
        with tempfile.TemporaryDirectory() as input_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                config = ImageOptimizationConfig(
                    input_directory=input_dir, output_directory=output_dir
                )
                optimizer = ImageOptimizer(config)

                results = optimizer.process_directory()

                assert results["processed"] == 0
                assert len(results["files"]) == 0


class TestLoadConfig:
    """Test configuration loading from file."""

    def test_load_config_valid(self):
        """Test loading valid configuration file."""
        config_data = {
            "input_directory": "/path/to/input",
            "output_directory": "/path/to/output",
            "prefix": "photo",
            "max_size_mb": 2.0,
            "quality": 90,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            file_path = f.name

        try:
            config = load_config(file_path)
            assert isinstance(config, ImageOptimizationConfig)
            assert config.input_directory == "/path/to/input"
            assert config.prefix == "photo"
            assert config.quality == 90
        finally:
            Path(file_path).unlink()

    def test_load_config_file_not_found(self):
        """Test error for missing config file."""
        with pytest.raises(Exception):
            load_config("nonexistent_config.json")

    def test_load_config_invalid_json(self):
        """Test error for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            file_path = f.name

        try:
            with pytest.raises(Exception):
                load_config(file_path)
        finally:
            Path(file_path).unlink()


class TestOptimizeImagesFunction:
    """Test the main optimize_images function."""

    @pytest.fixture
    def setup_images(self):
        """Set up test images."""
        with tempfile.TemporaryDirectory() as input_dir:
            input_path = Path(input_dir)

            # Create test images
            for i in range(2):
                img = Image.new("RGB", (800, 600), color="green")
                img.save(input_path / f"test{i}.jpg", "JPEG")

            yield input_dir

    def test_optimize_images_basic(self, setup_images):
        """Test basic image optimization function."""
        with tempfile.TemporaryDirectory() as output_dir:
            results = optimize_images(input_dir=setup_images, output_dir=output_dir)

            assert results["processed"] == 2
            assert results["failed"] == 0

    def test_optimize_images_with_config_file(self, setup_images):
        """Test optimization with config file."""
        with tempfile.TemporaryDirectory() as output_dir:
            config_data = {
                "input_directory": setup_images,
                "output_directory": output_dir,
                "quality": 70,
                "prefix": "optimized",
            }
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(config_data, f)
                config_path = f.name

            try:
                results = optimize_images(input_dir=setup_images, config_file=config_path)
                assert results["processed"] == 2
            finally:
                Path(config_path).unlink()

    def test_optimize_images_default_output_dir(self, setup_images):
        """Test default output directory creation."""
        results = optimize_images(input_dir=setup_images)

        expected_output = Path(setup_images) / "optimized"
        assert expected_output.exists()

    def test_optimize_images_custom_prefix(self, setup_images):
        """Test custom prefix in output filenames."""
        with tempfile.TemporaryDirectory() as output_dir:
            results = optimize_images(input_dir=setup_images, output_dir=output_dir, prefix="photo")

            output_path = Path(output_dir)
            files = list(output_path.glob("photo*.webp"))
            assert len(files) == 2


class TestUvxCompatibility:
    """Test that the module works correctly when run via uvx."""

    def test_module_import(self):
        """Test module can be imported."""
        from src.automations import optimize_images as mod

        assert hasattr(mod, "ImageOptimizationConfig")
        assert hasattr(mod, "ImageOptimizer")
        assert hasattr(mod, "optimize_images")
        assert hasattr(mod, "load_config")

    def test_dataclass_fields(self):
        """Test ImageOptimizationConfig has all expected fields."""
        from dataclasses import fields

        field_names = {f.name for f in fields(ImageOptimizationConfig)}
        expected_fields = {
            "input_directory",
            "output_directory",
            "prefix",
            "max_size_mb",
            "quality",
            "max_width",
            "max_height",
            "convert_to_webp",
            "preserve_aspect_ratio",
            "auto_orient",
            "preserve_filename",
        }
        assert field_names == expected_fields


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_optimize_very_small_image(self):
        """Test optimizing a very small image."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "tiny.jpg"
            output_path = Path(temp_dir) / "output.webp"

            # Create tiny image
            img = Image.new("RGB", (10, 10), color="white")
            img.save(input_path, "JPEG")

            config = ImageOptimizationConfig(input_directory=temp_dir, output_directory=temp_dir)
            optimizer = ImageOptimizer(config)

            result = optimizer.optimize_image(input_path, output_path)
            assert result["success"] is True
            assert result["dimensions"] == "10x10"

    def test_optimize_grayscale_image(self):
        """Test optimizing a grayscale image."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "gray.jpg"
            output_path = Path(temp_dir) / "output.webp"

            # Create grayscale image
            img = Image.new("L", (100, 100), color=128)
            img.save(input_path, "JPEG")

            config = ImageOptimizationConfig(input_directory=temp_dir, output_directory=temp_dir)
            optimizer = ImageOptimizer(config)

            result = optimizer.optimize_image(input_path, output_path)
            assert result["success"] is True

    def test_quality_reduction_loop(self):
        """Test that quality is reduced when file exceeds size limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "large.jpg"
            output_path = Path(temp_dir) / "output.webp"

            # Create a larger image that might need quality reduction
            img = Image.new("RGB", (2000, 2000), color="red")
            img.save(input_path, "JPEG", quality=100)

            config = ImageOptimizationConfig(
                input_directory=temp_dir,
                output_directory=temp_dir,
                max_size_mb=0.01,  # Very small limit to trigger reduction
                quality=90,
            )
            optimizer = ImageOptimizer(config)

            result = optimizer.optimize_image(input_path, output_path)
            # Should succeed but may have reduced quality
            assert result["success"] is True
            assert result["final_quality"] <= 90

    def test_case_insensitive_extension(self):
        """Test that file extensions are case-insensitive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create images with various case extensions
            for ext in [".JPG", ".Png", ".WEBP"]:
                img = Image.new("RGB", (100, 100), color="blue")
                img.save(temp_path / f"image{ext}")

            config = ImageOptimizationConfig(input_directory=temp_dir, output_directory="output")
            optimizer = ImageOptimizer(config)

            image_files = optimizer.get_image_files(temp_path)
            assert len(image_files) == 3
