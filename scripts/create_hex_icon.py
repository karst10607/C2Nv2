#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import os
import math

def draw_hex_icon(img_size):
    """Draw a clean white hexagon in a blue circle"""
    img = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    cx = cy = img_size // 2
    
    # Blue circle background
    circle_r = int(img_size * 0.45)
    blue_color = (59, 130, 246, 255)  # Nice blue
    draw.ellipse([cx - circle_r, cy - circle_r, 
                  cx + circle_r, cy + circle_r], 
                 fill=blue_color)
    
    # White hexagon
    hex_r = int(circle_r * 0.55)
    white_color = (255, 255, 255, 255)
    
    # Calculate hexagon vertices
    vertices = []
    for i in range(6):
        angle = math.pi / 3 * i - math.pi / 6  # Start from top
        x = cx + hex_r * math.cos(angle)
        y = cy + hex_r * math.sin(angle)
        vertices.append((x, y))
    
    # Draw hexagon
    draw.polygon(vertices, fill=white_color)
    
    # Optional: Add subtle shadow/depth to hex
    if img_size >= 128:
        # Draw a slightly smaller hex with slight transparency for depth
        inner_hex_r = int(hex_r * 0.92)
        inner_vertices = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 6
            x = cx + inner_hex_r * math.cos(angle)
            y = cy + inner_hex_r * math.sin(angle)
            inner_vertices.append((x, y))
        draw.polygon(inner_vertices, fill=(245, 245, 245, 255))
    
    return img

def save_iconset(base_dir):
    os.makedirs(base_dir, exist_ok=True)
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for s in sizes:
        # @1x
        im = draw_hex_icon(s)
        im.save(os.path.join(base_dir, f"icon_{s}x{s}.png"))
        # @2x
        im2 = draw_hex_icon(s*2)
        im2.save(os.path.join(base_dir, f"icon_{s}x{s}@2x.png"))

if __name__ == '__main__':
    save_iconset('build/icon.iconset')
    # Also export a 512x512 for Electron window icon
    img512 = draw_hex_icon(512)
    os.makedirs('electron', exist_ok=True)
    img512.save('electron/icon.png')
    print('Hex icon generated at build/icon.iconset and window icon at electron/icon.png')
