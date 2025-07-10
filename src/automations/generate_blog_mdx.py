import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import openai
from openai import OpenAI


@dataclass
class BlogConfig:
    """Configuration for blog generation"""
    openai_api_key: str
    model: str = "gpt-4"
    temperature: float = 0.3
    max_tokens: int = 4000
    output_directory: str = "output"
    author: str = "Anonymous"
    default_tags: list = None
    
    def __post_init__(self):
        if self.default_tags is None:
            self.default_tags = ["blog", "article"]


class BlogMDXGenerator:
    """Generate well-structured MDX blog files with OpenAI proofreading"""
    
    def __init__(self, config: BlogConfig):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
    
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from content"""
        lines = content.split('\n')
        title = None
        description = None
        
        # Try to find title (first heading or first line)
        for line in lines:
            if line.strip():
                if line.startswith('#'):
                    title = line.strip('#').strip()
                elif not title:
                    title = line.strip()
                break
        
        # Try to find description (first paragraph after title)
        found_title = False
        for line in lines:
            if line.strip():
                if found_title and not line.startswith('#'):
                    description = line.strip()[:150] + "..."
                    break
                elif line.strip() == title or line.strip().endswith(title):
                    found_title = True
        
        return {
            "title": title or "Untitled Blog Post",
            "description": description or "A blog post generated with AI assistance",
            "author": self.config.author,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "tags": self.config.default_tags.copy(),
            "published": True
        }
    
    def proofread_content(self, content: str) -> str:
        """Proofread content using OpenAI API"""
        try:
            print("🔍 Proofreading content with OpenAI...")
            
            prompt = f"""Please proofread the following blog post content. 

IMPORTANT INSTRUCTIONS:
1. Fix ONLY grammar, spelling, and punctuation errors
2. Do NOT change the writing style, tone, or voice
3. Do NOT alter the main ideas or arguments
4. Do NOT add new content or remove existing content
5. Maintain the original structure and formatting
6. Keep all headings, lists, and formatting intact
7. Preserve the author's unique writing style and personality

Content to proofread:

{content}

Return only the corrected content without any additional comments or explanations."""

            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are a professional proofreader. Your job is to fix grammar, spelling, and punctuation errors while preserving the original writing style and content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            proofread_content = response.choices[0].message.content.strip()
            print("✅ Content proofread successfully")
            return proofread_content
            
        except Exception as e:
            print(f"❌ Error proofreading content: {str(e)}")
            return content  # Return original content if proofreading fails
    
    def structure_content(self, content: str) -> str:
        """Structure content for better readability"""
        lines = content.split('\n')
        structured_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                structured_lines.append("")
                continue
            
            # Ensure proper heading format
            if stripped.startswith('#'):
                # Add space after # if missing
                if not stripped.startswith('# ') and not stripped.startswith('## '):
                    stripped = re.sub(r'^(#{1,6})([^#\s])', r'\1 \2', stripped)
                structured_lines.append(stripped)
            else:
                structured_lines.append(stripped)
        
        return '\n'.join(structured_lines)
    
    def generate_mdx_frontmatter(self, metadata: Dict[str, Any]) -> str:
        """Generate MDX frontmatter"""
        frontmatter = "---\n"
        frontmatter += f"title: \"{metadata['title']}\"\n"
        frontmatter += f"description: \"{metadata['description']}\"\n"
        frontmatter += f"author: \"{metadata['author']}\"\n"
        frontmatter += f"date: \"{metadata['date']}\"\n"
        frontmatter += f"published: {str(metadata['published']).lower()}\n"
        
        if metadata['tags']:
            tags_str = ', '.join([f'"{tag}"' for tag in metadata['tags']])
            frontmatter += f"tags: [{tags_str}]\n"
        
        frontmatter += "---\n\n"
        return frontmatter
    
    def generate_filename(self, title: str) -> str:
        """Generate filename from title"""
        # Convert to lowercase and replace spaces with hyphens
        filename = re.sub(r'[^\w\s-]', '', title).strip().lower()
        filename = re.sub(r'[-\s]+', '-', filename)
        return f"{filename}.mdx"
    
    def process_blog_post(self, content: str, custom_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a blog post from content to MDX"""
        try:
            print(f"📝 Processing blog post...")
            
            # Extract metadata
            metadata = self.extract_metadata(content)
            
            # Update with custom metadata if provided
            if custom_metadata:
                metadata.update(custom_metadata)
            
            # Proofread content
            proofread_content = self.proofread_content(content)
            
            # Structure content
            structured_content = self.structure_content(proofread_content)
            
            # Generate MDX frontmatter
            frontmatter = self.generate_mdx_frontmatter(metadata)
            
            # Combine frontmatter and content
            mdx_content = frontmatter + structured_content
            
            # Generate filename
            filename = self.generate_filename(metadata['title'])
            
            return {
                "filename": filename,
                "content": mdx_content,
                "metadata": metadata,
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Error processing blog post: {str(e)}")
            return {
                "filename": None,
                "content": None,
                "metadata": None,
                "success": False,
                "error": str(e)
            }
    
    def save_mdx_file(self, filename: str, content: str) -> bool:
        """Save MDX content to file"""
        try:
            output_path = Path(self.config.output_directory)
            output_path.mkdir(parents=True, exist_ok=True)
            
            file_path = output_path / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ MDX file saved: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving MDX file: {str(e)}")
            return False
    
    def process_from_file(self, input_file: str, custom_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process blog post from input file"""
        try:
            print(f"📄 Reading content from: {input_file}")
            
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process the content
            result = self.process_blog_post(content, custom_metadata)
            
            if result['success']:
                # Save the MDX file
                if self.save_mdx_file(result['filename'], result['content']):
                    result['output_path'] = str(Path(self.config.output_directory) / result['filename'])
                    print(f"🎉 Blog post processed successfully!")
                    print(f"📄 Output: {result['output_path']}")
                else:
                    result['success'] = False
                    result['error'] = "Failed to save MDX file"
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing file: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


def load_config(config_path: str) -> BlogConfig:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return BlogConfig(**config_data)
        
    except Exception as e:
        print(f"❌ Error loading configuration: {str(e)}")
        raise


def generate_blog_mdx(
    input_file: str,
    config_file: str = "data/blog_config.json",
    title: str = None,
    author: str = None,
    tags: list = None,
    description: str = None
) -> Dict[str, Any]:
    """Main function to generate blog MDX"""
    try:
        # Load configuration
        config = load_config(config_file)
        
        # Create generator
        generator = BlogMDXGenerator(config)
        
        # Prepare custom metadata
        custom_metadata = {}
        if title:
            custom_metadata['title'] = title
        if author:
            custom_metadata['author'] = author
        if tags:
            custom_metadata['tags'] = tags
        if description:
            custom_metadata['description'] = description
        
        # Process the blog post
        result = generator.process_from_file(input_file, custom_metadata)
        
        return result
        
    except Exception as e:
        print(f"❌ Error in blog generation: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    print("Blog MDX Generator")
    print("Use the main CLI to run this automation:")
    print("python src/main.py generate_blog_mdx --input 'path/to/blog.txt' --title 'My Blog Post'")
