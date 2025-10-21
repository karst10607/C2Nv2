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
                    url = ''
                    
                    # Get URL from either 'file' or 'external' type
                    if image_data.get('type') == 'file':
                        url = image_data.get('file', {}).get('url', '')
                    elif image_data.get('type') == 'external':
                        url = image_data.get('external', {}).get('url', '')
                    
                    # Check if URL has been rewritten to Notion's CDN
                    # (excludes tunnel URLs like trycloudflare.com)
                    if url and any(domain in url for domain in ['notion.so', 's3.us-west', 'prod-files-secure', 's3.amazonaws.com']):
                        loaded_count += 1
                
                # Check column_list children
                if block.get('type') == 'column_list':
                    # Need to fetch column children separately
                    for col_block in notion.get_blocks(block['id']):
                        if col_block.get('type') == 'column':
                            for child in notion.get_blocks(col_block['id']):
                                if child.get('type') == 'image':
                                    image_data = child.get('image', {})
                                    url = ''
                                    
                                    # Get URL from either 'file' or 'external' type
                                    if image_data.get('type') == 'file':
                                        url = image_data.get('file', {}).get('url', '')
                                    elif image_data.get('type') == 'external':
                                        url = image_data.get('external', {}).get('url', '')
                                    
                                    # Check if URL has been rewritten to Notion's CDN
                                    if url and any(domain in url for domain in ['notion.so', 's3.us-west', 'prod-files-secure', 's3.amazonaws.com']):
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
            
            # Wait before next poll (longer to respect rate limits)
            time.sleep(5)
            
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
    print(f"[cyan]Scanning {len(html_files)} HTML files...[/cyan]")
    
    # Pre-scan to get totals
    total_blocks = 0
    total_images = 0
    page_stats = []
    
    for f in html_files:
        ast = parse_html_file(f)
        blocks = to_notion_blocks(
            ast, 
            image_base_url=public, 
            max_cols=args.max_columns,
            preserve_table_layout=True,
            min_column_height=3
        )
        image_count = count_images_in_blocks(blocks)
        total_blocks += len(blocks)
        total_images += image_count
        
        page_stats.append({
            'file': f,
            'title': ast['title'],
            'ast': ast,
            'blocks': blocks,
            'image_count': image_count
        })
    
    # Show summary before importing
    print(f"\n[green]═══ Import Summary ═══[/green]")
    print(f"  Pages:  {len(html_files)}")
    print(f"  Blocks: {total_blocks}")
    print(f"  Images: {total_images}")
    if args.run:
        est_time = len(html_files) * 15 + total_images * 8  # Rough estimate
        print(f"  Est. time: ~{est_time // 60}m {est_time % 60}s")
    print(f"[green]{'═' * 22}[/green]\n")
    
    # Track pages with failed images
    failed_pages = []

    for page_info in page_stats:
        f = page_info['file']
        title = page_info['title']
        blocks = page_info['blocks']
        image_count = page_info['image_count']
        
        print(f"- {f.name} -> {title} ({len(blocks)} blocks, {image_count} images)")
        
        if args.run and notion:
            page_id = notion.create_page(parent_id, title)
            notion.append_blocks(page_id, blocks)
            
            # Verify images are loaded before moving to next page
            images_ok = True
            if image_count > 0:
                # Give Notion's backend a head start before polling
                print(f"  [dim]Waiting 10s for Notion to start fetching images...[/dim]")
                time.sleep(10)
                
                # Timeout scales with image count: 10s base + 8s per image
                timeout = max(30, min(180, 10 + image_count * 8))  # 30s-180s range
                images_ok = verify_images_loaded(notion, page_id, image_count, timeout=timeout)
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
        total_pages = len(html_files)
        success_pages = total_pages - len(failed_pages)
        failed_image_count = sum(p['expected_images'] for p in failed_pages)
        success_images = total_images - failed_image_count
        
        print(f"\n[green]{'═' * 40}[/green]")
        print(f"[green]✓ Import Complete[/green]")
        print(f"  Pages:  {success_pages}/{total_pages} successful")
        print(f"  Images: {success_images}/{total_images} verified")
        if failed_pages:
            print(f"[yellow]  {len(failed_pages)} page(s) with {failed_image_count} unverified images[/yellow]")
        print(f"[green]{'═' * 40}[/green]")

if __name__ == '__main__':
    sys.exit(main())
