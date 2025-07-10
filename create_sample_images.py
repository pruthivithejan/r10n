#!/usr/bin/env python3
"""
Create sample images for testing the image optimization automation
"""

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

def create_sample_images():
    """Create sample images for testing"""
    output_dir = Path("data/images/input")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create different sized images
    images_to_create = [
        {"name": "large_photo.jpg", "size": (3000, 2000), "color": (255, 100, 100)},
        {"name": "medium_image.png", "size": (1600, 900), "color": (100, 255, 100)},
        {"name": "small_pic.jpg", "size": (800, 600), "color": (100, 100, 255)},
        {"name": "square_image.png", "size": (1000, 1000), "color": (255, 255, 100)},
        {"name": "wide_banner.jpg", "size": (2400, 600), "color": (255, 100, 255)},
    ]
    
    for img_info in images_to_create:
        # Create image
        img = Image.new('RGB', img_info["size"], img_info["color"])
        draw = ImageDraw.Draw(img)
        
        # Add some text
        try:
            # Try to use a default font
            font = ImageFont.load_default()
        except:
            font = None
        
        text = f'{img_info["name"]}\n{img_info["size"][0]}x{img_info["size"][1]}'
        
        # Calculate text position (center)
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = 100, 20
        
        x = (img_info["size"][0] - text_width) // 2
        y = (img_info["size"][1] - text_height) // 2
        
        draw.text((x, y), text, fill=(0, 0, 0), font=font)
        
        # Save image
        img_path = output_dir / img_info["name"]
        img.save(img_path, quality=95)
        print(f"Created: {img_path}")
    
    print(f"\n✅ Created {len(images_to_create)} sample images in {output_dir}")
    print("You can now test the image optimization with:")
    print(f"python src/main.py optimize_images --input {output_dir} --prefix test")

if __name__ == "__main__":
    create_sample_images()
