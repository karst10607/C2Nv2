#!/usr/bin/env python3
import os
import sys
from PIL import Image

def create_iconset_from_image(input_path, output_dir):
    """Convert uploaded image to macOS iconset"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Open the uploaded image
    img = Image.open(input_path)
    
    # Convert to RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Required sizes for macOS iconset
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    for size in sizes:
        # @1x version
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(os.path.join(output_dir, f"icon_{size}x{size}.png"))
        
        # @2x version
        resized_2x = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
        resized_2x.save(os.path.join(output_dir, f"icon_{size}x{size}@2x.png"))
    
    # Also save a 512x512 version for the Electron window icon
    img_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    img_512.save('electron/icon.png')
    
    print(f"Iconset created at {output_dir}")
    print("Window icon saved at electron/icon.png")

if __name__ == '__main__':
    # Use the uploaded image path
    input_image = sys.argv[1] if len(sys.argv) > 1 else 'uploaded_icon.png'
    create_iconset_from_image(input_image, 'build/icon.iconset')
