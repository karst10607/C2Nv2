#!/usr/bin/env python3
"""Final test of Draw.io detection and matching"""
from pathlib import Path
from src.html_parser import parse_html_file

def test_drawio_matching():
    # Test the file with Draw.io content
    html_path = Path("EP/2753397032.html")
    
    print(f"\nParsing: {html_path}")
    print("=" * 60)
    
    # List available attachments
    attachments_dir = html_path.parent / 'attachments' / html_path.stem
    if attachments_dir.exists():
        print("\nAvailable attachments:")
        for f in sorted(attachments_dir.iterdir()):
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
    
    # Parse and find Draw.io blocks
    ast = parse_html_file(html_path)
    drawio_blocks = [b for b in ast['blocks'] if b.get('type') == 'drawio']
    
    print(f"\nFound {len(drawio_blocks)} Draw.io blocks:")
    for i, block in enumerate(drawio_blocks, 1):
        print(f"\n{i}. Diagram: {block.get('diagram_name', 'Unknown')}")
        print(f"   Container: {block.get('container_id', 'N/A')[:50]}...")
        print(f"   Matched file: {block.get('attachment_path', 'NOT FOUND')}")
        if block.get('aspect_hash'):
            print(f"   Aspect hash: {block.get('aspect_hash')}")
    
    # Show what would be rendered in Notion
    print("\n" + "=" * 60)
    print("How these will appear in Notion:")
    print("=" * 60)
    
    from src.transform import to_notion_blocks
    notion_blocks = to_notion_blocks(ast, image_base_url="https://example.com")
    
    # Find the Draw.io related blocks
    for i, block in enumerate(notion_blocks):
        if i > 0 and notion_blocks[i-1].get('type') == 'image':
            # Check if this is a caption for a Draw.io image
            if block.get('type') == 'paragraph' and block.get('paragraph'):
                text = block['paragraph'].get('rich_text', [{}])[0].get('text', {}).get('content', '')
                if '📊 Draw.io diagram:' in text:
                    img_block = notion_blocks[i-1]
                    url = img_block.get('image', {}).get('external', {}).get('url', '')
                    print(f"\nImage: {url}")
                    print(f"Caption: {text}")
        elif block.get('type') == 'callout' and '⚠️ Draw.io diagram placeholder' in str(block):
            text = block['callout'].get('rich_text', [{}])[0].get('text', {}).get('content', '')
            print(f"\nPlaceholder: {text}")

if __name__ == "__main__":
    test_drawio_matching()








