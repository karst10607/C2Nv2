import argparse
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich import print

from .config import AppConfig
from .html_parser import parse_html_file
from .transform import to_notion_blocks
from .notion_api import Notion
from .database import ImportDatabase
from .verification import ImageVerifier
from .upload_strategies import create_strategy
from .constants import (
    DEFAULT_TUNNEL_KEEPALIVE,
    MAX_COLUMNS_PER_ROW,
    MIN_COLUMN_HEIGHT,
    SECONDS_PER_PAGE_ESTIMATE,
    SECONDS_PER_IMAGE_ESTIMATE,
    INITIAL_IMAGE_WAIT,
    MIN_IMAGE_TIMEOUT,
    MAX_IMAGE_TIMEOUT,
    IMAGE_TIMEOUT_BASE,
    IMAGE_TIMEOUT_PER_IMAGE,
    TUNNEL_KEEPALIVE_PER_FAILED_PAGE,
    MAX_FAILED_PAGES_DISPLAY,
    SECONDS_PER_MINUTE
)


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


def upload_images_in_blocks(blocks: List[Dict[str, Any]], strategy, source_dir: Path, context: Dict) -> List[Dict[str, Any]]:
    """
    Upload images using strategy and update URLs in blocks.
    For S3/CDN strategies only (tunnel doesn't need this).
    """
    context['source_dir'] = source_dir
    
    for block in blocks:
        if block.get('type') == 'image':
            # Get current URL (relative path)
            current_url = block['image']['external']['url']
            
            # If it's a local path, upload it
            if not current_url.startswith(('http://', 'https://')):
                local_path = source_dir / current_url
                if local_path.exists():
                    try:
                        # Upload and get CDN URL
                        cdn_url = strategy.upload_image(local_path, context)
                        # Update block with CDN URL
                        block['image']['external']['url'] = cdn_url
                    except Exception as e:
                        print(f"  [yellow]Warning: Failed to upload {local_path.name}: {e}[/yellow]")
        
        elif block.get('type') == 'column_list':
            # Handle images in column_list
            for col in block.get('column_list', {}).get('children', []):
                for child in col.get('column', {}).get('children', []):
                    if child.get('type') == 'image':
                        current_url = child['image']['external']['url']
                        if not current_url.startswith(('http://', 'https://')):
                            local_path = source_dir / current_url
                            if local_path.exists():
                                try:
                                    cdn_url = strategy.upload_image(local_path, context)
                                    child['image']['external']['url'] = cdn_url
                                except Exception as e:
                                    print(f"  [yellow]Warning: Failed to upload {local_path.name}: {e}[/yellow]")
    
    return blocks


# Removed: verify_images_loaded() - now in verification.py as ImageVerifier.verify_page_images()


def main(argv: Optional[list] = None):
    ap = argparse.ArgumentParser(description="Import Confluence HTML export into Notion")
    ap.add_argument('--source-dir', default=None)
    ap.add_argument('--run', action='store_true', help='Perform writes to Notion')
    ap.add_argument('--dry-run', action='store_true', help='Parse and plan only')
    ap.add_argument('--max-columns', type=int, default=MAX_COLUMNS_PER_ROW)
    ap.add_argument('--parent-id', default=None)
    args = ap.parse_args(argv)

    cfg = AppConfig.load()
    source_dir = args.source_dir or cfg.source_dir
    if not source_dir:
        print('[red]Source directory not set. Use GUI or --source-dir.[/red]')
        return 2
    
    # Create upload strategy based on config
    # Create a minimal config object for strategy
    class StrategyConfig:
        pass
    
    strategy_config = StrategyConfig()
    strategy_config.upload_mode = getattr(cfg, 'upload_mode', 'tunnel')
    strategy_config.s3_bucket = getattr(cfg, 's3_bucket', '')
    strategy_config.s3_region = getattr(cfg, 's3_region', 'us-west-2')
    strategy_config.s3_access_key = getattr(cfg, 's3_access_key', '')
    strategy_config.s3_secret_key = getattr(cfg, 's3_secret_key', '')
    strategy_config.s3_lifecycle_days = getattr(cfg, 's3_lifecycle_days', 1)
    strategy_config.s3_use_presigned = getattr(cfg, 's3_use_presigned', True)
    strategy_config.cf_bucket = getattr(cfg, 'cf_bucket', '')
    strategy_config.cf_account_id = getattr(cfg, 'cf_account_id', '')
    strategy_config.cf_access_key = getattr(cfg, 'cf_access_key', '')
    strategy_config.cf_secret_key = getattr(cfg, 'cf_secret_key', '')
    strategy_config.cf_public_domain = getattr(cfg, 'cf_public_domain', '')
    strategy_config.tunnel_keepalive_sec = getattr(cfg, 'tunnel_keepalive_sec', DEFAULT_TUNNEL_KEEPALIVE)
    
    # Initialize upload strategy
    upload_strategy = create_strategy(strategy_config)
    public = upload_strategy.prepare(Path(source_dir))
    
    print(f"[green]Upload strategy:[/green] {upload_strategy.get_name()}")
    if public:
        print(f"[green]Base URL:[/green] {public}")

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
        verifier = ImageVerifier(notion)
    else:
        notion = None  # type: ignore
        verifier = None  # type: ignore

    # Walk HTML files
    mapping_path = Path(__file__).resolve().parents[1] / 'out' / 'mapping.jsonl'
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize database
    db = ImportDatabase()

    html_files = sorted(Path(source_dir).rglob('*.html'))
    print(f"[cyan]Scanning {len(html_files)} HTML files...[/cyan]")
    
    # Pre-scan to get totals
    total_blocks = 0
    total_images = 0
    page_stats = []
    import_start_time = time.time()
    
    for f in html_files:
        ast = parse_html_file(f)
        
        # For S3/CDN strategies, upload images now and get URLs
        # For tunnel, public URL is already set
        if public:
            # Tunnel strategy - use base URL
            image_base_url = public
        else:
            # S3/CDN strategy - will upload per-image
            image_base_url = ""  # Will be replaced during transform
        
        blocks = to_notion_blocks(
            ast, 
            image_base_url=image_base_url, 
            max_cols=args.max_columns,
            preserve_table_layout=True,
            min_column_height=MIN_COLUMN_HEIGHT
        )
        
        # For S3/CDN strategies, upload images and update URLs in blocks
        if not public:
            blocks = upload_images_in_blocks(blocks, upload_strategy, Path(source_dir), {})
        
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
        est_time = len(html_files) * SECONDS_PER_PAGE_ESTIMATE + total_images * SECONDS_PER_IMAGE_ESTIMATE
        print(f"  Est. time: ~{est_time // SECONDS_PER_MINUTE}m {est_time % SECONDS_PER_MINUTE}s")
    print(f"[green]{'═' * 22}[/green]\n")
    
    # Start database tracking for this import run
    run_id = None
    if args.run:
        from importlib.metadata import version as get_version
        try:
            app_version = get_version('notion-importer')
        except:
            app_version = '2.6.0'
        run_id = db.start_import_run(app_version, len(html_files), total_images)
    
    # Track pages with failed images
    failed_pages = []
    verified_image_count = 0

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
            actual_verified = 0
            if image_count > 0:
                # Give Notion's backend a head start before polling
                print(f"  [dim]Waiting {INITIAL_IMAGE_WAIT}s for Notion to start fetching images...[/dim]")
                time.sleep(INITIAL_IMAGE_WAIT)
                
                # Timeout scales with image count: 10s base + 8s per image
                timeout = max(MIN_IMAGE_TIMEOUT, min(MAX_IMAGE_TIMEOUT, IMAGE_TIMEOUT_BASE + image_count * IMAGE_TIMEOUT_PER_IMAGE))
                
                # Verify using ImageVerifier
                images_ok, actual_verified = verifier.verify_page_images(
                    page_id, image_count, timeout=timeout
                )
                
                # Record failures in database
                if not images_ok:
                    db.add_failed_page(
                        run_id=run_id,
                        file_path=str(f),
                        page_id=page_id,
                        title=title,
                        expected_images=image_count,
                        verified_images=actual_verified,
                        error=f'Verification timeout after {timeout}s'
                    )
                    
                    failed_pages.append({
                        'file': str(f),
                        'page_id': page_id,
                        'title': title,
                        'expected_images': image_count
                    })
                else:
                    actual_verified = image_count
                    verified_image_count += image_count
            
            line = f"{{\"source\":\"{str(f)}\",\"page_id\":\"{page_id}\"}}\n"
            with open(mapping_path, 'a', encoding='utf-8') as fp:
                fp.write(line)

    # Finalize database run
    if args.run and run_id:
        duration = int(time.time() - import_start_time)
        successful_pages = len(html_files) - len(failed_pages)
        db.finish_import_run(run_id, successful_pages, verified_image_count, duration)
    
    # Export failed pages to JSON for compatibility
    if failed_pages:
        import json
        failed_path = Path(__file__).resolve().parents[1] / 'out' / 'failed_images.json'
        db.export_failed_to_json(failed_path)
        
        print(f"\n[yellow]⚠ {len(failed_pages)} page(s) with incomplete images:[/yellow]")
        print(f"[yellow]  Database: {db.db_path}[/yellow]")
        print(f"[yellow]  JSON export: {failed_path}[/yellow]")
        for page in failed_pages[:MAX_FAILED_PAGES_DISPLAY]:
            print(f"[yellow]  - {page['title']}[/yellow]")
        if len(failed_pages) > MAX_FAILED_PAGES_DISPLAY:
            print(f"[yellow]  ... and {len(failed_pages) - MAX_FAILED_PAGES_DISPLAY} more[/yellow]")
    
    # Cleanup upload strategy (keepalive if needed, or just cleanup)
    if not args.dry_run:
        upload_strategy.cleanup(failed_count=len(failed_pages))
    
    db.close()
    
    # Final summary
    if args.run:
        total_pages = len(html_files)
        success_pages = total_pages - len(failed_pages)
        failed_image_count = sum(p['expected_images'] for p in failed_pages)
        
        print(f"\n[green]{'═' * 40}[/green]")
        print(f"[green]✓ Import Complete[/green]")
        print(f"  Pages:  {success_pages}/{total_pages} successful")
        print(f"  Images: {verified_image_count}/{total_images} verified")
        if failed_pages:
            print(f"[yellow]  {len(failed_pages)} page(s) with {failed_image_count} unverified images[/yellow]")
            print(f"[cyan]  Run 'Auto-Retry Failed' in GUI to retry failed pages[/cyan]")
        print(f"[green]{'═' * 40}[/green]")

if __name__ == '__main__':
    sys.exit(main())
