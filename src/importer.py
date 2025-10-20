import argparse
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich import print

from .config import AppConfig
from .image_server import StaticServer, Tunnel
from .html_parser import parse_html_file
from .transform import to_notion_blocks
from .notion_api import Notion


def count_images_in_blocks(blocks: List[Dict[str, Any]]) -> int:
    """Count total images in a list of blocks (including nested in column_list)"""
    count = 0
    for b in blocks:
        if b.get('type') == 'image':
            count += 1
        elif b.get('type') == 'column_list':
            for col in b.get('column_list', {}).get('children', []):
                for child in col.get('column', {}).get('children', []):
                    if child.get('type') == 'image':
                        count += 1
    return count


def verify_images_loaded(notion: Notion, page_id: str, expected_count: int, timeout: int = 60) -> bool:
    """
    Poll Notion API to verify that images have been fetched and cached.
    Returns True if all images are loaded, False if timeout.
    """
    if expected_count == 0:
        return True
    
    print(f"  [cyan]Verifying {expected_count} images...[/cyan]", end='', flush=True)
    start = time.time()
    last_count = 0
    
    while time.time() - start < timeout:
        try:
            # Fetch blocks from Notion
            page_blocks = notion.get_blocks(page_id)
            
            # Count images that have been cached (URL changed to Notion's CDN)
            loaded_count = 0
            for block in page_blocks:
                if block.get('type') == 'image':
                    image_data = block.get('image', {})
                    # Check if Notion has cached the image (external -> file)
                    if image_data.get('type') == 'file':
                        url = image_data.get('file', {}).get('url', '')
                        # Notion's cached images have notion.so or s3.us-west domains
                        if any(domain in url for domain in ['notion.so', 's3.us-west', 'prod-files-secure']):
                            loaded_count += 1
                    # External images that haven't been cached yet
                    elif image_data.get('type') == 'external':
                        # Still external, not cached yet
                        pass
                
                # Check column_list children
                if block.get('type') == 'column_list':
                    # Need to fetch column children separately
                    for col_block in notion.get_blocks(block['id']):
                        if col_block.get('type') == 'column':
                            for child in notion.get_blocks(col_block['id']):
                                if child.get('type') == 'image':
                                    image_data = child.get('image', {})
                                    if image_data.get('type') == 'file':
                                        url = image_data.get('file', {}).get('url', '')
                                        if any(domain in url for domain in ['notion.so', 's3.us-west', 'prod-files-secure']):
                                            loaded_count += 1
            
            # Show progress if changed
            if loaded_count != last_count:
                print(f"\r  [cyan]Verifying images: {loaded_count}/{expected_count}[/cyan]", end='', flush=True)
                last_count = loaded_count
            
            # Success if all loaded
            if loaded_count >= expected_count:
                elapsed = int(time.time() - start)
                print(f"\r  [green]✓ All {loaded_count} images verified ({elapsed}s)[/green]")
                return True
            
            # Wait before next poll
            time.sleep(3)
            
        except Exception as e:
            print(f"\r  [yellow]Warning during verification: {e}[/yellow]")
            time.sleep(5)
    
    # Timeout
    elapsed = int(time.time() - start)
    print(f"\r  [yellow]⚠ Timeout: {last_count}/{expected_count} images verified ({elapsed}s)[/yellow]")
    return False


def main(argv: Optional[list] = None):
    ap = argparse.ArgumentParser(description="Import Confluence HTML export into Notion")
    ap.add_argument('--source-dir', default=None)
    ap.add_argument('--run', action='store_true', help='Perform writes to Notion')
    ap.add_argument('--dry-run', action='store_true', help='Parse and plan only')
    ap.add_argument('--max-columns', type=int, default=6)
    ap.add_argument('--parent-id', default=None)
    args = ap.parse_args(argv)

    cfg = AppConfig.load()
    source_dir = args.source_dir or cfg.source_dir
    if not source_dir:
        print('[red]Source directory not set. Use GUI or --source-dir.[/red]')
        return 2

    # Start local static server and tunnel
    srv = StaticServer(Path(source_dir))
    srv.start()
    tunnel = Tunnel(srv.base_url())
    public = tunnel.start()
    print(f"[green]Serving images at:[/green] {public}")

    # Notion
    token = cfg.notion_token
    parent_id = args.parent_id or cfg.parent_id
    if args.run:
        if not token:
            print('[red]NOTION_TOKEN missing. Set via GUI or env.[/red]')
            return 2
        if not parent_id:
            print('[yellow]PARENT_ID missing. You can run --dry-run to preview or set it via GUI.[/yellow]')
            return 2
        notion = Notion(token)
    else:
        notion = None  # type: ignore

    # Walk HTML files
    mapping_path = Path(__file__).resolve().parents[1] / 'out' / 'mapping.jsonl'
    mapping_path.parent.mkdir(parents=True, exist_ok=True)

    html_files = sorted(Path(source_dir).rglob('*.html'))
    print(f"Found {len(html_files)} html files")
    
    # Track pages with failed images
    failed_pages = []

    for f in html_files:
        ast = parse_html_file(f)
        title = ast['title']
        blocks = to_notion_blocks(
            ast, 
            image_base_url=public, 
            max_cols=args.max_columns,
            preserve_table_layout=True,
            min_column_height=3
        )
        
        image_count = count_images_in_blocks(blocks)
        print(f"- {f.name} -> {title} ({len(blocks)} blocks, {image_count} images)")
        
        if args.run and notion:
            page_id = notion.create_page(parent_id, title)
            notion.append_blocks(page_id, blocks)
            
            # Verify images are loaded before moving to next page
            images_ok = True
            if image_count > 0:
                images_ok = verify_images_loaded(notion, page_id, image_count, timeout=60)
                if not images_ok:
                    failed_pages.append({
                        'file': str(f),
                        'page_id': page_id,
                        'title': title,
                        'expected_images': image_count
                    })
            
            line = f"{{\"source\":\"{str(f)}\",\"page_id\":\"{page_id}\"}}\n"
            with open(mapping_path, 'a', encoding='utf-8') as fp:
                fp.write(line)

    # Report failed pages
    if failed_pages:
        import json
        failed_path = Path(__file__).resolve().parents[1] / 'out' / 'failed_images.json'
        with open(failed_path, 'w', encoding='utf-8') as fp:
            json.dump(failed_pages, fp, indent=2, ensure_ascii=False)
        print(f"\n[yellow]⚠ {len(failed_pages)} page(s) with incomplete images saved to:[/yellow]")
        print(f"[yellow]  {failed_path}[/yellow]")
        for page in failed_pages:
            print(f"[yellow]  - {page['title']} (page_id: {page['page_id']})[/yellow]")
    
    # Keep tunnel alive briefly after all imports (images should already be cached)
    if not args.dry_run:
        import os
        keep_alive = int(os.environ.get('IMAGE_TUNNEL_KEEPALIVE_SEC', '30'))
        print(f"\n[green]Keeping tunnel alive for {keep_alive} seconds as safety buffer...[/green]")
        time.sleep(keep_alive)
    
    tunnel.stop()
    
    # Final summary
    if args.run:
        total = len(html_files)
        success = total - len(failed_pages)
        print(f"\n[green]✓ Import complete: {success}/{total} pages with all images verified[/green]")
        if failed_pages:
            print(f"[yellow]  {len(failed_pages)} page(s) need manual image check[/yellow]")

if __name__ == '__main__':
    sys.exit(main())
