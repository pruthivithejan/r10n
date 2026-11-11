"""
Tests for the Markdown to PDF converter automation.

The automation should:
- Convert markdown files to styled PDF documents
- Support custom CSS styling
- Handle batch processing of directories
- Preserve markdown formatting (headers, lists, code blocks, etc.)
"""

import tempfile
from pathlib import Path

import pytest
from pypdf import PdfReader

from r10n_backend.automations.markdown_to_pdf import (
    MarkdownConverter,
    MarkdownToPdfConfig,
    apply_css_styling,
    convert_directory,
    convert_markdown_to_pdf,
    load_config,
    parse_markdown,
)


class TestMarkdownToPdfConfig:
    """Test MarkdownToPdfConfig dataclass."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = MarkdownToPdfConfig(input_path="input.md", output_path="output.pdf")
        assert config.input_path == "input.md"
        assert config.output_path == "output.pdf"
        assert config.css_file is None
        assert config.page_size == "A4"
        assert config.margin_top == 20
        assert config.margin_bottom == 20
        assert config.margin_left == 20
        assert config.margin_right == 20
        assert config.include_toc is False
        assert config.syntax_highlighting is True


class TestParseMarkdown:
    """Test markdown parsing functionality."""

    def test_parse_basic_text(self):
        """Test parsing basic text."""
        markdown = "Hello, World!"
        result = parse_markdown(markdown)
        assert "Hello, World!" in result

    def test_parse_headers(self):
        """Test parsing headers."""
        markdown = "# Header 1\n## Header 2\n### Header 3"
        result = parse_markdown(markdown)
        assert ">Header 1</h1>" in result
        assert ">Header 2</h2>" in result
        assert ">Header 3</h3>" in result

    def test_parse_bold_italic(self):
        """Test parsing bold and italic text."""
        markdown = "**bold** and *italic* text"
        result = parse_markdown(markdown)
        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result

    def test_parse_bullet_list(self):
        """Test parsing bullet lists."""
        markdown = "- Item 1\n- Item 2\n- Item 3"
        result = parse_markdown(markdown)
        assert "Item 1" in result
        assert "Item 2" in result

    def test_parse_numbered_list(self):
        """Test parsing numbered lists."""
        markdown = "1. First\n2. Second\n3. Third"
        result = parse_markdown(markdown)
        assert "First" in result
        assert "Second" in result

    def test_parse_code_block(self):
        """Test parsing code blocks."""
        markdown = "```python\nprint('hello')\n```"
        result = parse_markdown(markdown)
        assert "print" in result

    def test_parse_inline_code(self):
        """Test parsing inline code."""
        markdown = "Use `print()` to output"
        result = parse_markdown(markdown)
        assert "print()" in result

    def test_parse_links(self):
        """Test parsing links."""
        markdown = "[Google](https://google.com)"
        result = parse_markdown(markdown)
        assert "Google" in result
        assert 'href="https://google.com"' in result

    def test_parse_images(self):
        """Test parsing image references."""
        markdown = "![Alt text](image.png)"
        result = parse_markdown(markdown)
        assert 'src="image.png"' in result
        assert 'alt="Alt text"' in result

    def test_parse_blockquote(self):
        """Test parsing blockquotes."""
        markdown = "> This is a quote"
        result = parse_markdown(markdown)
        assert "<blockquote>" in result
        assert "This is a quote" in result

    def test_parse_horizontal_rule(self):
        """Test parsing horizontal rules."""
        markdown = "Text above\n\n---\n\nText below"
        result = parse_markdown(markdown)
        assert "above" in result.lower()
        assert "below" in result.lower()

    def test_parse_table(self):
        """Test parsing tables."""
        markdown = """
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
"""
        result = parse_markdown(markdown)
        assert "Header 1" in result
        assert "Cell 1" in result

    def test_parse_empty_content(self):
        """Test parsing empty content."""
        result = parse_markdown("")
        assert result == ""


class TestApplyCssStyling:
    """Test CSS styling application."""

    def test_apply_default_styling(self):
        """Test applying default CSS styling."""
        html = "<h1>Title</h1><p>Content</p>"
        result = apply_css_styling(html)
        assert "<style>" in result
        assert html in result

    def test_apply_custom_css(self):
        """Test applying custom CSS file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as f:
            f.write("body { font-family: Arial; color: blue; }")
            css_path = f.name

        try:
            html = "<p>Test content</p>"
            result = apply_css_styling(html, css_file=css_path)
            assert "body { font-family: Arial; color: blue; }" in result
        finally:
            Path(css_path).unlink()

    def test_apply_css_file_not_found(self):
        """Test error handling for missing CSS file."""
        html = "<p>Test</p>"
        with pytest.raises(FileNotFoundError):
            apply_css_styling(html, css_file="nonexistent.css")


class TestMarkdownConverter:
    """Test MarkdownConverter class."""

    @pytest.fixture
    def converter(self):
        """Create a MarkdownConverter instance for testing."""
        config = MarkdownToPdfConfig(input_path="input.md", output_path="output.pdf")
        return MarkdownConverter(config)

    def test_convert_basic_document(self, converter):
        """Test converting a basic markdown document."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "test.md"
            output_path = Path(temp_dir) / "test.pdf"

            input_path.write_text("# Hello World\n\nThis is a test document.")

            converter.config.input_path = str(input_path)
            converter.config.output_path = str(output_path)

            result = converter.convert()

            assert result["success"] is True
            assert output_path.exists()
            assert "Hello World" in PdfReader(output_path).pages[0].extract_text()
            assert "This is a test document." in PdfReader(output_path).pages[0].extract_text()

    def test_convert_with_code_blocks(self, converter):
        """Test converting document with code blocks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "code.md"
            output_path = Path(temp_dir) / "code.pdf"

            markdown_content = """
# Code Example

```python
def hello():
    print("Hello, World!")
```

Inline code: `variable = 42`
"""
            input_path.write_text(markdown_content)

            converter.config.input_path = str(input_path)
            converter.config.output_path = str(output_path)

            result = converter.convert()

            assert result["success"] is True
            assert output_path.exists()
            text = "\n".join(page.extract_text() for page in PdfReader(output_path).pages)
            assert "Hello, World!" in text
            assert "variable = 42" in text

    def test_convert_input_not_found(self, converter):
        """Test error when input file not found."""
        converter.config.input_path = "nonexistent.md"
        converter.config.output_path = "output.pdf"

        with pytest.raises(FileNotFoundError):
            converter.convert()

    def test_convert_creates_output_directory(self, converter):
        """Test that output directory is created if needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "test.md"
            output_path = Path(temp_dir) / "nested" / "output" / "test.pdf"

            input_path.write_text("# Test")

            converter.config.input_path = str(input_path)
            converter.config.output_path = str(output_path)

            result = converter.convert()

            assert result["success"] is True
            assert output_path.exists()


class TestConvertMarkdownToPdf:
    """Test the main convert_markdown_to_pdf function."""

    def test_convert_single_file(self):
        """Test converting a single markdown file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "document.md"
            output_path = Path(temp_dir) / "document.pdf"

            input_path.write_text("# My Document\n\nContent here.")

            result = convert_markdown_to_pdf(
                input_path=str(input_path), output_path=str(output_path)
            )

            assert result["success"] is True
            assert output_path.exists()

    def test_convert_accepts_css_file(self):
        """A valid CSS file can be supplied during conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "styled.md"
            output_path = Path(temp_dir) / "styled.pdf"
            css_path = Path(temp_dir) / "custom.css"

            input_path.write_text("# Styled Document")
            css_path.write_text("h1 { color: navy; }")

            result = convert_markdown_to_pdf(
                input_path=str(input_path), output_path=str(output_path), css_file=str(css_path)
            )

            assert result["success"] is True
            assert "Styled Document" in PdfReader(output_path).pages[0].extract_text()

    def test_convert_auto_output_path(self):
        """Test automatic output path generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "auto.md"
            input_path.write_text("# Auto Output")

            result = convert_markdown_to_pdf(input_path=str(input_path))

            assert result["success"] is True
            expected_output = Path(temp_dir) / "auto.pdf"
            assert expected_output.exists()


class TestConvertDirectory:
    """Test batch directory conversion."""

    def test_convert_directory_basic(self):
        """Test converting all markdown files in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            (temp_path / "doc1.md").write_text("# Document 1")
            (temp_path / "doc2.md").write_text("# Document 2")
            (temp_path / "doc3.md").write_text("# Document 3")
            (temp_path / "readme.txt").write_text("Not markdown")

            output_dir = temp_path / "output"

            result = convert_directory(input_dir=str(temp_path), output_dir=str(output_dir))

            assert result["total"] == 3
            assert result["converted"] == 3
            assert result["failed"] == 0
            assert output_dir.exists()
            assert len(list(output_dir.glob("*.pdf"))) == 3

    def test_convert_directory_recursive(self):
        """Test recursive directory conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            (temp_path / "root.md").write_text("# Root")
            sub_dir = temp_path / "subdir"
            sub_dir.mkdir()
            (sub_dir / "nested.md").write_text("# Nested")

            output_dir = temp_path / "output"

            result = convert_directory(
                input_dir=str(temp_path), output_dir=str(output_dir), recursive=True
            )

            assert result["total"] == 2
            assert result["converted"] == 2

    def test_convert_directory_empty(self):
        """Test converting empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = convert_directory(input_dir=temp_dir, output_dir=temp_dir + "/output")

            assert result["total"] == 0
            assert result["converted"] == 0

    def test_convert_directory_preserves_structure(self):
        """Test that directory structure is preserved."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            docs_dir = temp_path / "docs"
            docs_dir.mkdir()
            api_dir = docs_dir / "api"
            api_dir.mkdir()
            (api_dir / "reference.md").write_text("# API Reference")

            output_dir = temp_path / "output"

            result = convert_directory(
                input_dir=str(temp_path),
                output_dir=str(output_dir),
                recursive=True,
                preserve_structure=True,
            )

            expected_output = output_dir / "docs" / "api" / "reference.pdf"
            assert result["converted"] == 1
            assert "API Reference" in PdfReader(expected_output).pages[0].extract_text()

    def test_convert_directory_reports_failed_files(self):
        """Test per-file failures are surfaced in the batch summary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_dir = temp_path / "output"
            missing_css = temp_path / "missing.css"

            (temp_path / "doc1.md").write_text("# Document 1")

            result = convert_directory(
                input_dir=str(temp_path),
                output_dir=str(output_dir),
                css_file=str(missing_css),
            )

            assert result["total"] == 1
            assert result["converted"] == 0
            assert result["failed"] == 1
            assert result["files"][0]["success"] is False


class TestLoadConfig:
    """Test configuration loading from file."""

    def test_load_config_valid(self):
        """Test loading valid configuration."""
        config_data = {
            "input_path": "document.md",
            "output_path": "document.pdf",
            "css_file": "style.css",
            "page_size": "Letter",
            "include_toc": True,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json

            json.dump(config_data, f)
            file_path = f.name

        try:
            config = load_config(file_path)
            assert isinstance(config, MarkdownToPdfConfig)
            assert config.page_size == "Letter"
            assert config.include_toc is True
        finally:
            Path(file_path).unlink()

    def test_load_config_file_not_found(self):
        """Test error for missing config file."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_config.json")


class TestUvxCompatibility:
    """Test that the module works correctly when run via uvx."""

    def test_module_import(self):
        """Test module can be imported."""
        from r10n_backend.automations import markdown_to_pdf as mod

        assert hasattr(mod, "MarkdownToPdfConfig")
        assert hasattr(mod, "MarkdownConverter")
        assert hasattr(mod, "convert_markdown_to_pdf")
        assert hasattr(mod, "convert_directory")
        assert hasattr(mod, "parse_markdown")
        assert hasattr(mod, "apply_css_styling")


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_convert_unicode_content(self):
        """Test converting markdown with unicode characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "unicode.md"
            output_path = Path(temp_dir) / "unicode.pdf"

            input_path.write_text("# Unicode Test\n\nCafe, resume, naive", encoding="utf-8")

            result = convert_markdown_to_pdf(
                input_path=str(input_path), output_path=str(output_path)
            )

            assert result["success"] is True
            assert "Cafe, resume, naive" in PdfReader(output_path).pages[0].extract_text()

    def test_convert_large_document(self):
        """Test converting a large markdown document."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "large.md"
            output_path = Path(temp_dir) / "large.pdf"

            content = "# Large Document\n\n"
            for i in range(100):
                content += f"## Section {i}\n\nLorem ipsum dolor sit amet. " * 10 + "\n\n"

            input_path.write_text(content)

            result = convert_markdown_to_pdf(
                input_path=str(input_path), output_path=str(output_path)
            )

            assert result["success"] is True

    def test_convert_nested_lists(self):
        """Test converting nested lists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "lists.md"
            output_path = Path(temp_dir) / "lists.pdf"

            markdown = """
# Nested Lists

- Item 1
  - Sub-item 1.1
  - Sub-item 1.2
    - Sub-sub-item 1.2.1
- Item 2
  1. Numbered sub-item
  2. Another numbered
"""
            input_path.write_text(markdown)

            result = convert_markdown_to_pdf(
                input_path=str(input_path), output_path=str(output_path)
            )

            assert result["success"] is True

    def test_convert_math_expressions(self):
        """Test converting markdown with math expressions (if supported)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "math.md"
            output_path = Path(temp_dir) / "math.pdf"

            markdown = """
# Math Example

Inline math: $E = mc^2$

Block math:
$$
\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}
$$
"""
            input_path.write_text(markdown)

            result = convert_markdown_to_pdf(
                input_path=str(input_path), output_path=str(output_path)
            )

            assert result["success"] is True
            text = "\n".join(page.extract_text() for page in PdfReader(output_path).pages)
            assert "E = mc^2" in text
