"""
Tests for the CSS Color to OKLCH converter automation.

These tests verify the color conversion functionality for both
local usage and uvx distribution.
"""

import re
import tempfile
from pathlib import Path

import pytest

from src.automations.convert_colors import (
    convert_colors,
    expand_hex,
    find_css_files,
    format_oklch,
    hsl_to_rgb,
    is_within_oklch,
    linear_to_oklab,
    make_replacement_for_match,
    parse_hsl_params,
    parse_rgb_params,
    process_css_content,
    process_file,
    rgba_to_oklch,
    srgb_to_linear,
)


class TestExpandHex:
    """Test hex color expansion."""

    def test_3_digit_hex(self):
        """Test 3-digit hex expansion."""
        r, g, b, a = expand_hex("fff")
        assert r == 1.0
        assert g == 1.0
        assert b == 1.0
        assert a == 1.0

    def test_4_digit_hex_with_alpha(self):
        """Test 4-digit hex with alpha."""
        r, g, b, a = expand_hex("f008")
        assert r == 1.0
        assert g == 0.0
        assert b == 0.0
        assert a == pytest.approx(0.533, abs=0.01)

    def test_6_digit_hex(self):
        """Test 6-digit hex."""
        r, g, b, a = expand_hex("ff0000")
        assert r == 1.0
        assert g == 0.0
        assert b == 0.0
        assert a == 1.0

    def test_8_digit_hex_with_alpha(self):
        """Test 8-digit hex with alpha."""
        r, g, b, a = expand_hex("ff000080")
        assert r == 1.0
        assert g == 0.0
        assert b == 0.0
        assert a == pytest.approx(0.502, abs=0.01)

    def test_invalid_length(self):
        """Test invalid hex length."""
        with pytest.raises(ValueError, match="invalid hex length"):
            expand_hex("ff")


class TestParseHslParams:
    """Test HSL parameter parsing."""

    def test_hsl_with_commas(self):
        """Test HSL with comma syntax."""
        r, g, b, a = parse_hsl_params("240, 100%, 50%")
        assert r == pytest.approx(0.0, abs=0.01)
        assert g == pytest.approx(0.0, abs=0.01)
        assert b == pytest.approx(1.0, abs=0.01)
        assert a == 1.0

    def test_hsl_with_spaces(self):
        """Test HSL with space syntax."""
        r, g, b, a = parse_hsl_params("0 100% 50%")
        assert r == pytest.approx(1.0, abs=0.01)
        assert g == pytest.approx(0.0, abs=0.01)
        assert b == pytest.approx(0.0, abs=0.01)

    def test_hsla_with_alpha(self):
        """Test HSLA with alpha."""
        r, g, b, a = parse_hsl_params("120, 100%, 50%, 0.5")
        assert a == 0.5

    def test_hsl_with_slash_alpha(self):
        """Test HSL with slash alpha syntax."""
        r, g, b, a = parse_hsl_params("120 100% 50% / 50%")
        assert a == 0.5

    def test_hsl_with_deg_unit(self):
        """Test HSL with deg unit."""
        r, g, b, a = parse_hsl_params("180deg 100% 50%")
        # Cyan
        assert r == pytest.approx(0.0, abs=0.01)
        assert g == pytest.approx(1.0, abs=0.01)
        assert b == pytest.approx(1.0, abs=0.01)

    def test_hsl_with_turn_unit(self):
        """Test HSL with turn unit."""
        r, g, b, a = parse_hsl_params("0.5turn 100% 50%")
        # Cyan (180deg)
        assert r == pytest.approx(0.0, abs=0.01)
        assert g == pytest.approx(1.0, abs=0.01)

    def test_empty_params(self):
        """Test empty HSL params."""
        with pytest.raises(ValueError, match="empty hsl"):
            parse_hsl_params("")


class TestParseRgbParams:
    """Test RGB parameter parsing."""

    def test_rgb_with_commas(self):
        """Test RGB with comma syntax."""
        r, g, b, a = parse_rgb_params("255, 0, 0")
        assert r == 1.0
        assert g == 0.0
        assert b == 0.0
        assert a == 1.0

    def test_rgb_with_spaces(self):
        """Test RGB with space syntax."""
        r, g, b, a = parse_rgb_params("0 255 0")
        assert r == 0.0
        assert g == 1.0
        assert b == 0.0

    def test_rgba_with_alpha(self):
        """Test RGBA with alpha."""
        r, g, b, a = parse_rgb_params("255, 0, 0, 0.5")
        assert a == 0.5

    def test_rgb_with_percent(self):
        """Test RGB with percent values."""
        r, g, b, a = parse_rgb_params("100% 0% 0%")
        assert r == 1.0
        assert g == 0.0
        assert b == 0.0

    def test_rgb_with_slash_alpha(self):
        """Test RGB with slash alpha."""
        r, g, b, a = parse_rgb_params("255 0 0 / 50%")
        assert a == 0.5

    def test_empty_params(self):
        """Test empty RGB params."""
        with pytest.raises(ValueError, match="empty rgb"):
            parse_rgb_params("")


class TestHslToRgb:
    """Test HSL to RGB conversion."""

    def test_red(self):
        """Test red color."""
        r, g, b = hsl_to_rgb(0, 1.0, 0.5)
        assert r == pytest.approx(1.0, abs=0.01)
        assert g == pytest.approx(0.0, abs=0.01)
        assert b == pytest.approx(0.0, abs=0.01)

    def test_green(self):
        """Test green color."""
        r, g, b = hsl_to_rgb(120, 1.0, 0.5)
        assert r == pytest.approx(0.0, abs=0.01)
        assert g == pytest.approx(1.0, abs=0.01)
        assert b == pytest.approx(0.0, abs=0.01)

    def test_blue(self):
        """Test blue color."""
        r, g, b = hsl_to_rgb(240, 1.0, 0.5)
        assert r == pytest.approx(0.0, abs=0.01)
        assert g == pytest.approx(0.0, abs=0.01)
        assert b == pytest.approx(1.0, abs=0.01)

    def test_white(self):
        """Test white color."""
        r, g, b = hsl_to_rgb(0, 0.0, 1.0)
        assert r == pytest.approx(1.0, abs=0.01)
        assert g == pytest.approx(1.0, abs=0.01)
        assert b == pytest.approx(1.0, abs=0.01)

    def test_black(self):
        """Test black color."""
        r, g, b = hsl_to_rgb(0, 0.0, 0.0)
        assert r == pytest.approx(0.0, abs=0.01)
        assert g == pytest.approx(0.0, abs=0.01)
        assert b == pytest.approx(0.0, abs=0.01)


class TestColorConversion:
    """Test color space conversions."""

    def test_srgb_to_linear_dark(self):
        """Test sRGB to linear for dark values."""
        result = srgb_to_linear(0.01)
        assert result == pytest.approx(0.000773, abs=0.0001)

    def test_srgb_to_linear_light(self):
        """Test sRGB to linear for light values."""
        result = srgb_to_linear(0.5)
        assert result == pytest.approx(0.214, abs=0.01)

    def test_rgba_to_oklch_red(self):
        """Test RGBA to OKLCH for red."""
        l, c, h, a = rgba_to_oklch(1.0, 0.0, 0.0, 1.0)
        assert l == pytest.approx(0.628, abs=0.01)
        assert c > 0.2  # Red has high chroma
        assert a == 1.0

    def test_rgba_to_oklch_white(self):
        """Test RGBA to OKLCH for white."""
        l, c, h, a = rgba_to_oklch(1.0, 1.0, 1.0, 1.0)
        assert l == pytest.approx(1.0, abs=0.01)
        assert c == pytest.approx(0.0, abs=0.01)  # White has no chroma

    def test_rgba_to_oklch_with_alpha(self):
        """Test RGBA to OKLCH preserves alpha."""
        l, c, h, a = rgba_to_oklch(1.0, 0.0, 0.0, 0.5)
        assert a == 0.5


class TestFormatOklch:
    """Test OKLCH formatting."""

    def test_format_without_alpha(self):
        """Test formatting without alpha."""
        result = format_oklch(0.628, 0.258, 29.2, 1.0)
        assert result == "oklch(62.8% 0.258 29deg)"

    def test_format_with_alpha(self):
        """Test formatting with alpha."""
        result = format_oklch(0.628, 0.258, 29.2, 0.5)
        assert result == "oklch(62.8% 0.258 29deg / 0.5)"

    def test_format_rounding(self):
        """Test proper rounding."""
        result = format_oklch(0.5556, 0.1234, 45.6789, 1.0)
        assert result == "oklch(55.6% 0.123 46deg)"


class TestIsWithinOklch:
    """Test oklch detection."""

    def test_inside_oklch(self):
        """Test detection inside oklch()."""
        src = "color: oklch(50% 0.1 180deg);"
        assert is_within_oklch(src, 13, 16) is True

    def test_outside_oklch(self):
        """Test detection outside oklch()."""
        src = "color: #ff0000;"
        assert is_within_oklch(src, 7, 14) is False


class TestMakeReplacementForMatch:
    """Test color token replacement."""

    def test_hex_3_digit(self):
        """Test 3-digit hex replacement."""
        result = make_replacement_for_match("#fff")
        assert result.startswith("oklch(")
        assert "/" not in result  # Full alpha, no slash

    def test_hex_6_digit(self):
        """Test 6-digit hex replacement."""
        result = make_replacement_for_match("#ff0000")
        assert result.startswith("oklch(")

    def test_hex_8_digit_with_alpha(self):
        """Test 8-digit hex with alpha."""
        result = make_replacement_for_match("#ff000080")
        assert result.startswith("oklch(")
        assert " / " in result

    def test_rgb(self):
        """Test RGB replacement."""
        result = make_replacement_for_match("rgb(255,0,0)")
        assert result.startswith("oklch(")

    def test_rgba(self):
        """Test RGBA replacement."""
        result = make_replacement_for_match("rgba(255,0,0,0.5)")
        assert result.startswith("oklch(")
        assert " / 0.5" in result

    def test_hsl(self):
        """Test HSL replacement."""
        result = make_replacement_for_match("hsl(240 100% 50%)")
        assert result.startswith("oklch(")

    def test_hsla(self):
        """Test HSLA replacement."""
        result = make_replacement_for_match("hsla(240,100%,50%,0.25)")
        assert result.startswith("oklch(")
        assert " / 0.25" in result

    def test_named_color(self):
        """Test named color replacement."""
        result = make_replacement_for_match("rebeccapurple")
        assert result.startswith("oklch(")

    def test_transparent(self):
        """Test transparent keyword."""
        result = make_replacement_for_match("transparent")
        assert result.startswith("oklch(")
        assert " / 0.0" in result

    def test_output_format(self):
        """Test output format regex."""
        result = make_replacement_for_match("#123456")
        pat = re.compile(
            r"^oklch\(\d{1,3}(?:\.\d+)?% \d+(?:\.\d+)? \d+deg(?: / \d+(?:\.\d+)?)?\)$"
        )
        assert pat.match(result)


class TestProcessCssContent:
    """Test CSS content processing."""

    def test_single_color(self):
        """Test processing single color."""
        content = ".class { color: #ff0000; }"
        new_content, changes = process_css_content(content)
        assert "oklch(" in new_content
        assert len(changes) == 1

    def test_multiple_colors(self):
        """Test processing multiple colors."""
        content = """
        .a { color: #ff0000; }
        .b { background: rgb(0, 255, 0); }
        .c { border-color: blue; }
        """
        new_content, changes = process_css_content(content)
        assert new_content.count("oklch(") == 3
        assert len(changes) == 3

    def test_skip_existing_oklch(self):
        """Test that existing oklch is not double-converted."""
        content = ".class { color: oklch(50% 0.1 180deg); }"
        new_content, changes = process_css_content(content)
        assert len(changes) == 0
        assert new_content == content

    def test_preserves_structure(self):
        """Test CSS structure is preserved."""
        content = ".class {\n  color: #ff0000;\n  margin: 10px;\n}"
        new_content, changes = process_css_content(content)
        assert "margin: 10px" in new_content
        assert new_content.count("{") == 1
        assert new_content.count("}") == 1


class TestProcessFile:
    """Test file processing."""

    def test_process_css_file(self):
        """Test processing a CSS file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".css", delete=False
        ) as f:
            f.write(".class { color: #ff0000; }")
            file_path = f.name

        try:
            result = process_file(file_path, dry_run=True)
            assert result["file"] == file_path
            assert result["changes"] == 1
            assert result["modified"] is False  # dry_run=True
        finally:
            Path(file_path).unlink()

    def test_process_file_writes_backup(self):
        """Test backup file is created."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".css", delete=False
        ) as f:
            f.write(".class { color: #ff0000; }")
            file_path = f.name

        try:
            result = process_file(file_path, dry_run=False, no_backup=False)
            backup_path = Path(file_path + ".bak")
            assert backup_path.exists()
            assert result["modified"] is True
            backup_path.unlink()
        finally:
            Path(file_path).unlink()

    def test_process_file_no_backup(self):
        """Test no backup with flag."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".css", delete=False
        ) as f:
            f.write(".class { color: #ff0000; }")
            file_path = f.name

        try:
            process_file(file_path, dry_run=False, no_backup=True)
            backup_path = Path(file_path + ".bak")
            assert not backup_path.exists()
        finally:
            Path(file_path).unlink()

    def test_process_file_not_found(self):
        """Test file not found error."""
        with pytest.raises(FileNotFoundError):
            process_file("nonexistent.css")

    def test_process_file_not_css(self):
        """Test non-CSS file error."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("not css")
            file_path = f.name

        try:
            with pytest.raises(ValueError, match="Not a CSS file"):
                process_file(file_path)
        finally:
            Path(file_path).unlink()


class TestFindCssFiles:
    """Test CSS file discovery."""

    def test_find_css_files(self):
        """Test finding CSS files in directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create CSS files
            (Path(temp_dir) / "style.css").write_text(".a { color: red; }")
            (Path(temp_dir) / "theme.css").write_text(".b { color: blue; }")
            (Path(temp_dir) / "not-css.txt").write_text("text file")

            css_files = find_css_files(temp_dir)
            assert len(css_files) == 2
            assert all(f.endswith(".css") for f in css_files)

    def test_find_css_files_recursive(self):
        """Test recursive CSS file search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            sub_dir = Path(temp_dir) / "sub"
            sub_dir.mkdir()
            (Path(temp_dir) / "root.css").write_text(".a { color: red; }")
            (sub_dir / "nested.css").write_text(".b { color: blue; }")

            css_files = find_css_files(temp_dir)
            assert len(css_files) == 2

    def test_find_css_files_excludes_node_modules(self):
        """Test node_modules is excluded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create node_modules directory
            node_dir = Path(temp_dir) / "node_modules"
            node_dir.mkdir()
            (Path(temp_dir) / "style.css").write_text(".a { color: red; }")
            (node_dir / "vendor.css").write_text(".b { color: blue; }")

            css_files = find_css_files(temp_dir)
            assert len(css_files) == 1
            assert "node_modules" not in css_files[0]


class TestConvertColors:
    """Test main convert_colors function."""

    def test_convert_single_file(self):
        """Test converting a single file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".css", delete=False
        ) as f:
            f.write(".class { color: #ff0000; background: blue; }")
            file_path = f.name

        try:
            result = convert_colors(
                path=".", file=file_path, dry_run=True
            )
            assert result["files_found"] == 1
            assert result["total_changes"] == 2
        finally:
            Path(file_path).unlink()

    def test_convert_directory(self):
        """Test converting a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create CSS files
            (Path(temp_dir) / "a.css").write_text(".a { color: #ff0000; }")
            (Path(temp_dir) / "b.css").write_text(".b { color: rgb(0,255,0); }")

            result = convert_colors(path=temp_dir, dry_run=True)
            assert result["files_found"] == 2
            assert result["total_changes"] == 2
            assert result["files_modified"] == 0  # dry_run

    def test_convert_directory_writes(self):
        """Test converting directory actually writes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            css_path = Path(temp_dir) / "style.css"
            css_path.write_text(".a { color: #ff0000; }")

            result = convert_colors(path=temp_dir, dry_run=False, no_backup=True)
            assert result["files_modified"] == 1

            # Verify file was modified
            content = css_path.read_text()
            assert "oklch(" in content
            assert "#ff0000" not in content

    def test_convert_file_not_found(self):
        """Test error for missing file."""
        with pytest.raises(FileNotFoundError):
            convert_colors(path=".", file="nonexistent.css")

    def test_convert_directory_not_found(self):
        """Test error for missing directory."""
        with pytest.raises(FileNotFoundError):
            convert_colors(path="/nonexistent/path")

    def test_convert_no_css_files(self):
        """Test error when no CSS files found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Empty directory
            with pytest.raises(ValueError, match="No CSS files found"):
                convert_colors(path=temp_dir)


class TestUvxCompatibility:
    """Test that the module works correctly when run via uvx."""

    def test_module_import(self):
        """Test module can be imported."""
        from src.automations import convert_colors as mod

        assert hasattr(mod, "convert_colors")
        assert hasattr(mod, "process_file")
        assert hasattr(mod, "process_css_content")
        assert hasattr(mod, "make_replacement_for_match")

    def test_output_with_absolute_path(self):
        """Test processing with absolute paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            css_path = Path(temp_dir) / "test.css"
            css_path.write_text(".a { color: red; }")

            # Use absolute path
            result = convert_colors(
                path=temp_dir,
                file=str(css_path.absolute()),
                dry_run=True,
            )
            assert result["files_found"] == 1


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_css_file(self):
        """Test processing empty CSS file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".css", delete=False
        ) as f:
            f.write("")
            file_path = f.name

        try:
            result = process_file(file_path, dry_run=True)
            assert result["changes"] == 0
        finally:
            Path(file_path).unlink()

    def test_css_with_comments(self):
        """Test CSS with comments."""
        content = """
        /* Color: #ff0000 */
        .class {
            color: #ff0000;
        }
        """
        new_content, changes = process_css_content(content)
        # Comment color should also be converted
        assert "oklch(" in new_content

    def test_css_variables(self):
        """Test CSS custom properties."""
        content = ":root { --primary: #ff0000; }"
        new_content, changes = process_css_content(content)
        assert "oklch(" in new_content
        assert "--primary:" in new_content

    def test_mixed_converted_and_unconverted(self):
        """Test file with both oklch and old colors."""
        content = """
        .a { color: oklch(50% 0.1 180deg); }
        .b { color: #ff0000; }
        """
        new_content, changes = process_css_content(content)
        assert len(changes) == 1  # Only #ff0000 converted
        assert new_content.count("oklch(") == 2
