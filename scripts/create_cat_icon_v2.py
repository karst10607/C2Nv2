#!/usr/bin/env python3
from PIL import Image, ImageDraw
import os

def draw_cute_cat(img_size):
    """Draw a cute cat face similar to the uploaded image"""
    img = Image.new('RGBA', (img_size, img_size), (240, 240, 240, 255))
    draw = ImageDraw.Draw(img)
    
    cx = cy = img_size // 2
    
    # Main head (yellow/orange)
    head_color = (255, 183, 77, 255)  # Orange-yellow
    head_r = int(img_size * 0.35)
    draw.ellipse([cx - head_r, cy - head_r + int(img_size*0.05), 
                  cx + head_r, cy + head_r + int(img_size*0.05)], 
                 fill=head_color)
    
    # Ears (darker orange)
    ear_color = (230, 140, 30, 255)
    ear_size = int(head_r * 0.6)
    # Left ear
    ear_points = [
        (cx - head_r + int(head_r*0.2), cy - head_r + int(img_size*0.05)),
        (cx - head_r - int(head_r*0.1), cy - head_r - int(head_r*0.4)),
        (cx - head_r + int(head_r*0.5), cy - head_r + int(head_r*0.3))
    ]
    draw.polygon(ear_points, fill=ear_color)
    # Right ear
    ear_points = [
        (cx + head_r - int(head_r*0.2), cy - head_r + int(img_size*0.05)),
        (cx + head_r + int(head_r*0.1), cy - head_r - int(head_r*0.4)),
        (cx + head_r - int(head_r*0.5), cy - head_r + int(head_r*0.3))
    ]
    draw.polygon(ear_points, fill=ear_color)
    
    # Inner ears (lighter)
    inner_ear_color = (255, 203, 107, 255)
    ear_inner = int(ear_size * 0.5)
    draw.polygon([
        (cx - head_r + int(head_r*0.25), cy - head_r + int(img_size*0.02)),
        (cx - head_r + int(head_r*0.05), cy - head_r - int(head_r*0.2)),
        (cx - head_r + int(head_r*0.4), cy - head_r + int(head_r*0.15))
    ], fill=inner_ear_color)
    draw.polygon([
        (cx + head_r - int(head_r*0.25), cy - head_r + int(img_size*0.02)),
        (cx + head_r - int(head_r*0.05), cy - head_r - int(head_r*0.2)),
        (cx + head_r - int(head_r*0.4), cy - head_r + int(head_r*0.15))
    ], fill=inner_ear_color)
    
    # Eyes (black circles)
    eye_r = max(3, int(img_size * 0.04))
    eye_dx = int(head_r * 0.35)
    eye_y = cy - int(head_r * 0.05)
    draw.ellipse([cx - eye_dx - eye_r, eye_y - eye_r, 
                  cx - eye_dx + eye_r, eye_y + eye_r], 
                 fill=(20, 20, 20, 255))
    draw.ellipse([cx + eye_dx - eye_r, eye_y - eye_r, 
                  cx + eye_dx + eye_r, eye_y + eye_r], 
                 fill=(20, 20, 20, 255))
    
    # Nose (pink/red)
    nose_color = (200, 80, 80, 255)
    nose_w = max(3, int(img_size * 0.04))
    nose_h = max(2, int(img_size * 0.025))
    draw.ellipse([cx - nose_w, cy + int(head_r*0.1) - nose_h, 
                  cx + nose_w, cy + int(head_r*0.1) + nose_h], 
                 fill=nose_color)
    
    # Mouth (curved lines forming a W shape)
    mouth_y = cy + int(head_r * 0.2)
    mouth_width = int(head_r * 0.25)
    # Left curve
    for i in range(-mouth_width, 0, 2):
        y_offset = abs(i / mouth_width) * int(head_r * 0.1)
        draw.ellipse([cx + i - 1, mouth_y + y_offset - 1,
                      cx + i + 1, mouth_y + y_offset + 1],
                     fill=(20, 20, 20, 255))
    # Right curve  
    for i in range(0, mouth_width, 2):
        y_offset = abs(i / mouth_width) * int(head_r * 0.1)
        draw.ellipse([cx + i - 1, mouth_y + y_offset - 1,
                      cx + i + 1, mouth_y + y_offset + 1],
                     fill=(20, 20, 20, 255))
    
    # Whiskers
    whisker_len = int(head_r * 0.7)
    whisker_y1 = cy + int(head_r * 0.05)
    whisker_y2 = cy + int(head_r * 0.2)
    whisker_width = max(1, int(img_size * 0.008))
    
    # Left whiskers
    draw.line([cx - int(head_r*0.2), whisker_y1, 
               cx - whisker_len, whisker_y1 - int(head_r*0.05)], 
              fill=(20, 20, 20, 255), width=whisker_width)
    draw.line([cx - int(head_r*0.2), whisker_y2, 
               cx - whisker_len, whisker_y2], 
              fill=(20, 20, 20, 255), width=whisker_width)
    
    # Right whiskers
    draw.line([cx + int(head_r*0.2), whisker_y1, 
               cx + whisker_len, whisker_y1 - int(head_r*0.05)], 
              fill=(20, 20, 20, 255), width=whisker_width)
    draw.line([cx + int(head_r*0.2), whisker_y2, 
               cx + whisker_len, whisker_y2], 
              fill=(20, 20, 20, 255), width=whisker_width)
    
    # Collar/bell area (optional red collar with orange bell)
    collar_y = cy + head_r - int(img_size * 0.05)
    collar_color = (200, 60, 60, 255)
    draw.arc([cx - head_r + int(head_r*0.3), collar_y - int(head_r*0.2),
              cx + head_r - int(head_r*0.3), collar_y + int(head_r*0.3)],
             start=0, end=180, fill=collar_color, width=max(3, int(img_size*0.02)))
    
    # Bell
    bell_color = (255, 140, 0, 255)
    bell_r = max(4, int(img_size * 0.05))
    draw.ellipse([cx - bell_r, collar_y - bell_r,
                  cx + bell_r, collar_y + bell_r],
                 fill=bell_color)
    
    return img

def save_iconset(base_dir):
    os.makedirs(base_dir, exist_ok=True)
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for s in sizes:
        # @1x
        im = draw_cute_cat(s)
        im.save(os.path.join(base_dir, f"icon_{s}x{s}.png"))
        # @2x
        im2 = draw_cute_cat(s*2)
        im2.save(os.path.join(base_dir, f"icon_{s}x{s}@2x.png"))

if __name__ == '__main__':
    save_iconset('build/icon.iconset')
    # Also export a 512x512 for Electron window icon
    img512 = draw_cute_cat(512)
    os.makedirs('electron', exist_ok=True)
    img512.save('electron/icon.png')
    print('Cute cat iconset generated at build/icon.iconset and window icon at electron/icon.png')
