#!/usr/bin/env python3
from PIL import Image, ImageDraw
import os

# Simple vector cat face on a colored background

def draw_cat(img_size):
    img = Image.new('RGBA', (img_size, img_size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded square
    radius = int(img_size * 0.18)
    bg = Image.new('RGBA', (img_size, img_size), (0,0,0,0))
    bg_draw = ImageDraw.Draw(bg)
    bg_color = (34, 34, 59, 255)  # dark indigo
    # rounded rect
    bg_draw.rounded_rectangle([0,0,img_size-1,img_size-1], radius=radius, fill=bg_color)

    # Cat head
    cx = cy = img_size // 2
    head_r = int(img_size * 0.28)
    head_bbox = [cx - head_r, cy - head_r, cx + head_r, cy + head_r]
    head_color = (246, 189, 96, 255)  # warm sand
    draw.ellipse(head_bbox, fill=head_color)

    # Ears
    ear_r = int(head_r * 0.8)
    ear_h = int(head_r * 0.9)
    left_ear = [
        (cx - int(head_r*0.5), cy - head_r),
        (cx - head_r, cy - int(head_r*0.1)),
        (cx - int(head_r*0.2), cy - int(head_r*0.1))
    ]
    right_ear = [
        (cx + int(head_r*0.5), cy - head_r),
        (cx + int(head_r), cy - int(head_r*0.1)),
        (cx + int(head_r*0.2), cy - int(head_r*0.1))
    ]
    draw.polygon(left_ear, fill=head_color)
    draw.polygon(right_ear, fill=head_color)

    # Eyes
    eye_r = max(2, int(img_size * 0.03))
    eye_dx = int(head_r * 0.45)
    eye_y = cy - int(head_r * 0.1)
    draw.ellipse([cx - eye_dx - eye_r, eye_y - eye_r, cx - eye_dx + eye_r, eye_y + eye_r], fill=(30,30,30,255))
    draw.ellipse([cx + eye_dx - eye_r, eye_y - eye_r, cx + eye_dx + eye_r, eye_y + eye_r], fill=(30,30,30,255))

    # Nose
    nose_r = max(2, int(img_size * 0.02))
    draw.ellipse([cx - nose_r, cy - nose_r, cx + nose_r, cy + nose_r], fill=(200,80,80,255))

    # Whiskers
    whisker_len = int(head_r * 0.9)
    whisker_y1 = cy
    whisker_y2 = cy + int(head_r * 0.2)
    for y in (whisker_y1, whisker_y2):
        draw.line([cx - nose_r, y, cx - whisker_len, y - int(head_r*0.05)], fill=(30,30,30,180), width=max(1,int(img_size*0.01)))
        draw.line([cx + nose_r, y, cx + whisker_len, y - int(head_r*0.05)], fill=(30,30,30,180), width=max(1,int(img_size*0.01)))

    # Composite head over bg
    out = Image.alpha_composite(bg, img)
    return out


def save_iconset(base_dir):
    os.makedirs(base_dir, exist_ok=True)
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for s in sizes:
        # @1x
        im = draw_cat(s)
        im.save(os.path.join(base_dir, f"icon_{s}x{s}.png"))
        # @2x
        im2 = draw_cat(s*2)
        im2.save(os.path.join(base_dir, f"icon_{s}x{s}@2x.png"))

if __name__ == '__main__':
    save_iconset('build/icon.iconset')
    # Also export a 512x512 for Electron window icon
    img512 = draw_cat(512)
    os.makedirs('electron', exist_ok=True)
    img512.save('electron/icon.png')
    print('Iconset generated at build/icon.iconset and window icon at electron/icon.png')
