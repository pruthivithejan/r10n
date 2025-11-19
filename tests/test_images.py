import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import pytest
from PIL import Image

from src.automations.optimize_images import (
    ImageOptimizationConfig,
    ImageOptimizer,
    load_config,
    optimize_images,
)





class TestImageOptimizer:
    """Test ImageOptimizer class"""

    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return ImageOptimizationConfig(
            input_directory="/test/input",
            output_directory="/test/output",
            prefix="test",
            max_size_mb=1.0,
            quality=85
        )

    @pytest.fixture
    def optimizer(self, config):
        """Create ImageOptimizer instance"""
        return ImageOptimizer(config)



    def test_calculate_new_dimensions_preserve_aspect_ratio(self, optimizer):
        """Test dimension calculation with aspect ratio preservation"""
        # Test case where width is limiting factor
        new_width, new_height = optimizer.calculate_new_dimensions(2560, 1440)
        expected_width = 1920  # max_width
        expected_height = int(1440 * (1920 / 2560))  # preserve aspect ratio
        assert new_width == expected_width
        assert new_height == expected_height

        # Test case where height is limiting factor
        new_width, new_height = optimizer.calculate_new_dimensions(1600, 1200)
        expected_height = 1080  # max_height
        expected_width = int(1600 * (1080 / 1200))  # preserve aspect ratio
        assert new_width == expected_width
        assert new_height == expected_height

        # Test case where no scaling needed
        new_width, new_height = optimizer.calculate_new_dimensions(800, 600)
        assert new_width == 800
        assert new_height == 600

    def test_calculate_new_dimensions_no_aspect_ratio(self, config):
        """Test dimension calculation without aspect ratio preservation"""
        config.preserve_aspect_ratio = False
        optimizer = ImageOptimizer(config)
        
        new_width, new_height = optimizer.calculate_new_dimensions(2560, 1440)
        assert new_width == 1920  # min(2560, 1920)
        assert new_height == 1080  # min(1440, 1080)



    def test_generate_output_filename_with_prefix(self, optimizer):
        """Test output filename generation with prefix"""
        filename = optimizer.generate_output_filename(1, "original.jpg", ".jpg")
        assert filename == "test1.webp"  # convert_to_webp is True by default

        optimizer.config.convert_to_webp = False
        filename = optimizer.generate_output_filename(2, "original.png", ".png")
        assert filename == "test2.png"

    def test_generate_output_filename_preserve_original(self, optimizer):
        """Test output filename generation preserving original name"""
        optimizer.config.preserve_filename = True
        
        # With WebP conversion
        filename = optimizer.generate_output_filename(1, "vacation_photo.jpg", ".jpg")
        assert filename == "vacation_photo.webp"
        
        # Without WebP conversion
        optimizer.config.convert_to_webp = False
        filename = optimizer.generate_output_filename(1, "vacation_photo.jpg", ".jpg")
        assert filename == "vacation_photo.jpg"

    @patch('PIL.Image')
    @patch('PIL.ImageOps')
    @patch.object(ImageOptimizer, 'get_file_size_mb')
    def test_optimize_image_success(self, mock_get_size, mock_imageops, mock_image, optimizer):
        """Test successful image optimization"""
        # Mock PIL Image
        mock_img = Mock()
        mock_img.mode = "RGB"
        mock_img.width = 2000
        mock_img.height = 1500
        mock_img.resize.return_value = mock_img
        
        mock_image.open.return_value.__enter__.return_value = mock_img
        mock_imageops.exif_transpose.return_value = mock_img
        
        # Mock file sizes
        mock_get_size.side_effect = [2.5, 0.8]  # original: 2.5MB, final: 0.8MB
        
        input_path = Path("/test/input/image.jpg")
        output_path = Path("/test/output/test1.webp")
        
        result = optimizer.optimize_image(input_path, output_path)
        
        assert result["success"] is True
        assert result["original_file"] == str(input_path)
        assert result["output_file"] == str(output_path)
        assert result["original_size_mb"] == 2.5
        assert result["final_size_mb"] == 0.8
        assert result["compression_ratio"] == 68.0  # (1 - 0.8/2.5) * 100

    @patch('PIL.Image.open')
    def test_optimize_image_failure(self, mock_open, optimizer):
        """Test image optimization failure"""
        mock_open.side_effect = Exception("Cannot open image")
        
        input_path = Path("/test/input/corrupt.jpg")
        output_path = Path("/test/output/test1.webp")
        
        result = optimizer.optimize_image(input_path, output_path)
        
        assert result["success"] is False
        assert result["original_file"] == str(input_path)
        assert "Cannot open image" in result["error"]

    @patch.object(ImageOptimizer, 'get_image_files')
    @patch.object(ImageOptimizer, 'optimize_image')
    @patch('src.automations.optimize_images.Path')
    def test_process_directory_success(self, mock_path_class, mock_optimize, mock_get_files, optimizer):
        """Test successful directory processing"""
        # Mock paths
        mock_input_path = Mock()
        mock_input_path.exists.return_value = True
        mock_output_path = Mock()
        mock_path_class.return_value = mock_input_path
        mock_path_class.side_effect = [mock_input_path, mock_output_path]
        
        # Mock image files
        mock_files = [Path("/test/input/img1.jpg"), Path("/test/input/img2.png")]
        mock_get_files.return_value = mock_files
        
        # Mock optimization results
        mock_optimize.side_effect = [
            {
                "success": True,
                "original_size_mb": 2.0,
                "final_size_mb": 1.0,
            },
            {
                "success": True,
                "original_size_mb": 1.5,
                "final_size_mb": 0.8,
            }
        ]
        
        # Mock output file existence check
        # We need to ensure output_file_path.exists() returns False
        # mock_path_class is the Path class mock.
        # Path(config.output_directory) returns a mock.
        # That mock / filename returns another mock (output_file_path).
        # That mock .exists() must return False.
        
        mock_output_dir = mock_path_class.return_value
        mock_output_file = mock_output_dir.__truediv__.return_value
        mock_output_file.exists.return_value = False
        
        results = optimizer.process_directory()
        
        assert results["processed"] == 2
        assert results["failed"] == 0
        assert results["skipped"] == 0
        assert results["total_size_before"] == 3.5
        assert results["total_size_after"] == 1.8

    @patch('src.automations.optimize_images.Path')
    def test_process_directory_input_not_exists(self, mock_path, optimizer):
        """Test processing when input directory doesn't exist"""
        mock_input_path = Mock()
        mock_input_path.exists.return_value = False
        mock_path.return_value = mock_input_path
        
        results = optimizer.process_directory()
        
        assert "error" in results
        assert "does not exist" in results["error"]





class TestOptimizeImages:
    """Test main optimize_images function"""

    @patch('src.automations.optimize_images.ImageOptimizer')
    def test_optimize_images_without_config_file(self, mock_optimizer_class):
        """Test optimize_images function without config file"""
        # Mock optimizer instance and results
        mock_optimizer = Mock()
        mock_optimizer.process_directory.return_value = {
            "processed": 5,
            "failed": 0,
            "skipped": 1
        }
        mock_optimizer_class.return_value = mock_optimizer
        
        results = optimize_images(
            input_dir="/test/input",
            output_dir="/test/output",
            prefix="photo",
            max_size_mb=2.0,
            quality=90
        )
        
        # Verify optimizer was created with correct config
        assert mock_optimizer_class.called
        config_arg = mock_optimizer_class.call_args[0][0]
        assert config_arg.input_directory == "/test/input"
        assert config_arg.output_directory == "/test/output"
        assert config_arg.prefix == "photo"
        assert config_arg.max_size_mb == 2.0
        assert config_arg.quality == 90
        
        # Verify results
        assert results["processed"] == 5
        assert results["failed"] == 0
        assert results["skipped"] == 1

    @patch('src.automations.optimize_images.load_config')
    @patch('src.automations.optimize_images.ImageOptimizer')
    def test_optimize_images_with_config_file(self, mock_optimizer_class, mock_load_config):
        """Test optimize_images function with config file"""
        # Mock config loading
        mock_config = ImageOptimizationConfig(
            input_directory="/config/input",
            output_directory="/config/output",
            prefix="cfg"
        )
        mock_load_config.return_value = mock_config
        
        # Mock optimizer
        mock_optimizer = Mock()
        mock_optimizer.process_directory.return_value = {"processed": 3}
        mock_optimizer_class.return_value = mock_optimizer
        
        results = optimize_images(
            input_dir="/test/input",
            config_file="/test/config.json"
        )
        
        # Verify config was loaded
        mock_load_config.assert_called_once_with("/test/config.json")
        
        # Verify optimizer was created with loaded config
        mock_optimizer_class.assert_called_once_with(mock_config)
        assert results["processed"] == 3

    @patch('src.automations.optimize_images.load_config')
    def test_optimize_images_config_override(self, mock_load_config):
        """Test config file parameters can be overridden by command line args"""
        # Mock config loading
        mock_config = ImageOptimizationConfig(
            input_directory="/config/input",
            output_directory="/config/output",
            prefix="cfg"
        )
        mock_load_config.return_value = mock_config
        
        with patch('src.automations.optimize_images.ImageOptimizer') as mock_optimizer_class:
            mock_optimizer = Mock()
            mock_optimizer.process_directory.return_value = {"processed": 1}
            mock_optimizer_class.return_value = mock_optimizer
            
            optimize_images(
                input_dir="/test/input",
                output_dir="/override/output",
                prefix="override",
                config_file="/test/config.json"
            )
            
            # Check that config was modified with overrides
            config_arg = mock_optimizer_class.call_args[0][0]
            assert config_arg.output_directory == "/override/output"
            assert config_arg.prefix == "override"

    def test_optimize_images_default_output_dir(self):
        """Test default output directory creation"""
        with patch('src.automations.optimize_images.ImageOptimizer') as mock_optimizer_class:
            mock_optimizer = Mock()
            mock_optimizer.process_directory.return_value = {"processed": 1}
            mock_optimizer_class.return_value = mock_optimizer
            
            optimize_images(input_dir="/test/input")
            
            # Check that default output directory is input_dir/optimized
            config_arg = mock_optimizer_class.call_args[0][0]
            assert config_arg.output_directory == "/test/input/optimized"

    @patch('src.automations.optimize_images.ImageOptimizer')
    def test_optimize_images_exception_handling(self, mock_optimizer_class):
        """Test exception handling in optimize_images"""
        # Mock optimizer to raise exception
        mock_optimizer_class.side_effect = Exception("Optimizer failed")
        
        results = optimize_images(input_dir="/test/input")
        
        assert results["success"] is False
        assert "Optimizer failed" in results["error"]
        assert results["processed"] == 0
        assert results["failed"] == 0
        assert results["skipped"] == 0