#!/usr/bin/env python3
"""Test inline Draw.io detection in HTML parsing"""
from pathlib import Path
from src.html_parser import parse_html_file
import json

def test_file(html_file):
    """Test parsing a single HTML file"""
    print(f"\nTesting: {html_file}")
    print("=" * 60)
    
    ast = parse_html_file(Path(html_file))
    
    # Count Draw.io blocks
    drawio_blocks = [b for b in ast['blocks'] if b.get('type') == 'drawio']
    
    print(f"Title: {ast['title']}")
    print(f"Total blocks: {len(ast['blocks'])}")
    print(f"Draw.io blocks found: {len(drawio_blocks)}")
    
    if drawio_blocks:
        print("\nDraw.io blocks details:")
        for i, block in enumerate(drawio_blocks, 1):
            print(f"\n{i}. Container ID: {block.get('container_id', 'N/A')}")
            print(f"   Diagram name: {block.get('diagram_name', 'N/A')}")
            print(f"   Attachment: {block.get('attachment_path', 'Not found')}")
            print(f"   Attachment ID: {block.get('attachment_id', 'N/A')}")
    
    # Show a sample of blocks around Draw.io blocks
    for i, block in enumerate(ast['blocks']):
        if block.get('type') == 'drawio':
            print(f"\nContext around Draw.io block at index {i}:")
            # Show previous block
            if i > 0:
                prev = ast['blocks'][i-1]
                print(f"  [{i-1}] {prev.get('type')}: {prev.get('text', '')[:50]}")
            # Show Draw.io block
            print(f"  [{i}] >>> DRAW.IO: {block.get('diagram_name', 'Unknown')} <<<")
            # Show next block
            if i < len(ast['blocks']) - 1:
                next_block = ast['blocks'][i+1]
                print(f"  [{i+1}] {next_block.get('type')}: {next_block.get('text', '')[:50]}")

if __name__ == "__main__":
    # Test the file with Draw.io content
    test_file("EP/2753397032.html")
    
    # Also test the other file
    test_file("EP/Duplicate-of-Logi-Accounts-System_4073750733.html")








