import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import pytest

from src.automations.generate_blog_mdx import (
    BlogConfig,
    BlogMDXGenerator,
    load_config,
    generate_blog_mdx,
)





class TestBlogMDXGenerator:
    """Test BlogMDXGenerator class"""

    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return BlogConfig(
            openai_api_key="test-key",
            model="gpt-4",
            output_directory="/test/output",
            author="Test Author",
            default_tags=["test", "blog"]
        )

    @pytest.fixture
    def generator(self, config):
        """Create BlogMDXGenerator instance"""
        with patch('src.automations.generate_blog_mdx.OpenAI'):
            return BlogMDXGenerator(config)



    def test_extract_metadata_with_heading(self, generator):
        """Test metadata extraction with markdown heading"""
        content = """# My Blog Post Title

This is the first paragraph that should become the description.
This is a second paragraph that should not be included in description.

## Another heading
More content here."""
        
        metadata = generator.extract_metadata(content)
        
        assert metadata["title"] == "My Blog Post Title"
        assert metadata["description"].startswith("This is the first paragraph")
        assert metadata["author"] == "Test Author"
        assert metadata["tags"] == ["test", "blog"]
        assert metadata["published"] is True
        assert "date" in metadata

    def test_extract_metadata_without_heading(self, generator):
        """Test metadata extraction without markdown heading"""
        content = """First line becomes title

This is the description paragraph.
Another paragraph."""
        
        metadata = generator.extract_metadata(content)
        
        assert metadata["title"] == "First line becomes title"
        assert metadata["description"].startswith("This is the description")

    def test_extract_metadata_empty_content(self, generator):
        """Test metadata extraction with empty content"""
        metadata = generator.extract_metadata("")
        
        assert metadata["title"] == "Untitled Blog Post"
        assert metadata["description"] == "A blog post generated with AI assistance"

    @patch('src.automations.generate_blog_mdx.OpenAI')
    def test_proofread_content_success(self, mock_openai, config):
        """Test successful content proofreading"""
        # Mock OpenAI client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Proofread content here"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        generator = BlogMDXGenerator(config)
        result = generator.proofread_content("Original content here")
        
        assert result == "Proofread content here"
        mock_client.chat.completions.create.assert_called_once()
        
        # Check the call arguments
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["temperature"] == 0.3
        assert call_args[1]["max_tokens"] == 4000

    @patch('src.automations.generate_blog_mdx.OpenAI')
    def test_proofread_content_failure(self, mock_openai, config):
        """Test content proofreading failure"""
        # Mock OpenAI client to raise exception
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        generator = BlogMDXGenerator(config)
        original_content = "Original content here"
        result = generator.proofread_content(original_content)
        
        # Should return original content on failure
        assert result == original_content

    def test_structure_content(self, generator):
        """Test content structuring"""
        content = """#Title without space
## Subtitle with space

Some paragraph text.

###Another heading without space
More content."""
        
        structured = generator.structure_content(content)
        lines = structured.split("\n")
        
        # Check that headings are properly formatted
        assert "# Title without space" in lines
        assert "## Subtitle with space" in lines
        assert "### Another heading without space" in lines

    def test_generate_mdx_frontmatter(self, generator):
        """Test MDX frontmatter generation"""
        metadata = {
            "title": "Test Blog Post",
            "description": "This is a test description",
            "author": "Test Author",
            "date": "2023-01-01",
            "published": True,
            "tags": ["test", "blog"]
        }
        
        frontmatter = generator.generate_mdx_frontmatter(metadata)
        
        assert 'title: "Test Blog Post"' in frontmatter
        assert 'description: "This is a test description"' in frontmatter
        assert 'author: "Test Author"' in frontmatter
        assert 'date: "2023-01-01"' in frontmatter
        assert "published: true" in frontmatter
        assert 'tags: ["test", "blog"]' in frontmatter
        assert frontmatter.startswith("---\n")
        assert frontmatter.endswith("---\n\n")

    def test_generate_mdx_frontmatter_no_tags(self, generator):
        """Test MDX frontmatter generation without tags"""
        metadata = {
            "title": "Test Post",
            "description": "Test description",
            "author": "Author",
            "date": "2023-01-01",
            "published": False,
            "tags": []
        }
        
        frontmatter = generator.generate_mdx_frontmatter(metadata)
        
        assert "tags:" not in frontmatter
        assert "published: false" in frontmatter

    def test_generate_filename(self, generator):
        """Test filename generation from title"""
        # Test normal title
        filename = generator.generate_filename("My Great Blog Post")
        assert filename == "my-great-blog-post.mdx"
        
        # Test title with special characters
        filename = generator.generate_filename("My Blog Post: A Guide (2023)!")
        assert filename == "my-blog-post-a-guide-2023.mdx"
        
        # Test title with multiple spaces and hyphens
        filename = generator.generate_filename("Multiple   Spaces -- And Hyphens")
        assert filename == "multiple-spaces-and-hyphens.mdx"

    @patch.object(BlogMDXGenerator, 'proofread_content')
    @patch.object(BlogMDXGenerator, 'extract_metadata')
    def test_process_blog_post_success(self, mock_extract, mock_proofread, generator):
        """Test successful blog post processing"""
        # Mock methods
        mock_extract.return_value = {
            "title": "Test Post",
            "description": "Test description",
            "author": "Test Author",
            "date": "2023-01-01",
            "published": True,
            "tags": ["test"]
        }
        mock_proofread.return_value = "# Test Post\n\nProofread content"
        
        result = generator.process_blog_post("Original content")
        
        assert result["success"] is True
        assert result["filename"] == "test-post.mdx"
        assert "---\n" in result["content"]  # Has frontmatter
        assert "# Test Post" in result["content"]
        assert result["metadata"]["title"] == "Test Post"

    @patch.object(BlogMDXGenerator, 'extract_metadata')
    def test_process_blog_post_with_custom_metadata(self, mock_extract, generator):
        """Test blog post processing with custom metadata"""
        mock_extract.return_value = {
            "title": "Original Title",
            "description": "Original description",
            "author": "Original Author",
            "date": "2024-01-01",
            "tags": ["original"],
            "published": True
        }
        
        custom_metadata = {
            "title": "Custom Title",
            "tags": ["custom", "test"]
        }
        
        with patch.object(generator, 'proofread_content', return_value="content"):
            result = generator.process_blog_post("content", custom_metadata)
        
        assert result["success"] is True
        assert result["metadata"]["title"] == "Custom Title"
        assert result["metadata"]["tags"] == ["custom", "test"]

    @patch.object(BlogMDXGenerator, 'extract_metadata')
    def test_process_blog_post_failure(self, mock_extract, generator):
        """Test blog post processing failure"""
        mock_extract.side_effect = Exception("Processing error")
        
        result = generator.process_blog_post("content")
        
        assert result["success"] is False
        assert "Processing error" in result["error"]
        assert result["filename"] is None
        assert result["content"] is None



    @patch('builtins.open', new_callable=mock_open, read_data="file content")
    @patch.object(BlogMDXGenerator, 'process_blog_post')
    @patch.object(BlogMDXGenerator, 'save_mdx_file')
    def test_process_from_file_success(self, mock_save, mock_process, mock_file, generator):
        """Test successful file processing"""
        # Mock process_blog_post return
        mock_process.return_value = {
            "success": True,
            "filename": "test.mdx",
            "content": "mdx content"
        }
        mock_save.return_value = True
        
        result = generator.process_from_file("/test/input.txt")
        
        assert result["success"] is True
        assert "output_path" in result
        mock_file.assert_called_once_with("/test/input.txt", encoding="utf-8")
        mock_process.assert_called_once_with("file content", None)
        mock_save.assert_called_once_with("test.mdx", "mdx content")

    @patch('builtins.open', new_callable=mock_open)
    @patch.object(BlogMDXGenerator, 'process_blog_post')
    @patch.object(BlogMDXGenerator, 'save_mdx_file')
    def test_process_from_file_save_failure(self, mock_save, mock_process, mock_file, generator):
        """Test file processing with save failure"""
        mock_process.return_value = {
            "success": True,
            "filename": "test.mdx",
            "content": "content"
        }
        mock_save.return_value = False
        
        result = generator.process_from_file("/test/input.txt")
        
        assert result["success"] is False
        assert "Failed to save MDX file" in result["error"]

    @patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    def test_process_from_file_read_failure(self, mock_file, generator):
        """Test file processing with read failure"""
        result = generator.process_from_file("/nonexistent.txt")
        
        assert result["success"] is False
        assert "File not found" in result["error"]





class TestGenerateBlogMdx:
    """Test main generate_blog_mdx function"""

    @patch('src.automations.generate_blog_mdx.load_config')
    @patch('src.automations.generate_blog_mdx.BlogMDXGenerator')
    def test_generate_blog_mdx_success(self, mock_generator_class, mock_load_config):
        """Test successful blog MDX generation"""
        # Mock config loading
        mock_config = BlogConfig(openai_api_key="test-key")
        mock_load_config.return_value = mock_config
        
        # Mock generator
        mock_generator = Mock()
        mock_generator.process_from_file.return_value = {
            "success": True,
            "filename": "test.mdx"
        }
        mock_generator_class.return_value = mock_generator
        
        result = generate_blog_mdx(
            input_file="/test/input.txt",
            config_file="/test/config.json",
            title="Custom Title",
            author="Custom Author",
            tags=["custom", "tags"],
            description="Custom description"
        )
        
        # Verify config was loaded
        mock_load_config.assert_called_once_with("/test/config.json")
        
        # Verify generator was created and called
        mock_generator_class.assert_called_once_with(mock_config)
        
        # Verify custom metadata was passed
        call_args = mock_generator.process_from_file.call_args
        assert call_args[0][0] == "/test/input.txt"
        custom_metadata = call_args[0][1]
        assert custom_metadata["title"] == "Custom Title"
        assert custom_metadata["author"] == "Custom Author"
        assert custom_metadata["tags"] == ["custom", "tags"]
        assert custom_metadata["description"] == "Custom description"
        
        assert result["success"] is True

    @patch('src.automations.generate_blog_mdx.load_config')
    @patch('src.automations.generate_blog_mdx.BlogMDXGenerator')
    def test_generate_blog_mdx_minimal_params(self, mock_generator_class, mock_load_config):
        """Test blog MDX generation with minimal parameters"""
        mock_config = BlogConfig(openai_api_key="test-key")
        mock_load_config.return_value = mock_config
        
        mock_generator = Mock()
        mock_generator.process_from_file.return_value = {"success": True}
        mock_generator_class.return_value = mock_generator
        
        result = generate_blog_mdx(input_file="/test/input.txt")
        
        # Verify empty custom metadata was passed
        call_args = mock_generator.process_from_file.call_args
        custom_metadata = call_args[0][1]
        assert custom_metadata == {}

    @patch('src.automations.generate_blog_mdx.load_config')
    def test_generate_blog_mdx_config_load_failure(self, mock_load_config):
        """Test blog MDX generation with config loading failure"""
        mock_load_config.side_effect = Exception("Config load error")
        
        result = generate_blog_mdx(input_file="/test/input.txt")
        
        assert result["success"] is False
        assert "Config load error" in result["error"]

    @patch('src.automations.generate_blog_mdx.load_config')
    @patch('src.automations.generate_blog_mdx.BlogMDXGenerator')
    def test_generate_blog_mdx_generation_failure(self, mock_generator_class, mock_load_config):
        """Test blog MDX generation with processing failure"""
        mock_config = BlogConfig(openai_api_key="test-key")
        mock_load_config.return_value = mock_config
        
        mock_generator_class.side_effect = Exception("Generator error")
        
        result = generate_blog_mdx(input_file="/test/input.txt")
        
        assert result["success"] is False
        assert "Generator error" in result["error"]