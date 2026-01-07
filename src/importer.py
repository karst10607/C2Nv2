import argparse
import sys
import time
import traceback
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
from .models import ImportConfig, ConfigurationError, UploadError, ErrorCode
from .processors import MediaProcessor
from .processors.drawio_scanner import DrawioScanner
from .constants import (
    SECONDS_PER_PAGE_ESTIMATE,
    SECONDS_PER_IMAGE_ESTIMATE,
    INITIAL_IMAGE_WAIT,
    MIN_IMAGE_TIMEOUT,
    MAX_IMAGE_TIMEOUT,
    IMAGE_TIMEOUT_BASE,
    IMAGE_TIMEOUT_PER_IMAGE,
    MAX_FAILED_PAGES_DISPLAY,
    SECONDS_PER_MINUTE
)


# Moved to MediaProcessor - keeping for backwards compatibility
def count_images_in_blocks(blocks: List[Dict[str, Any]]) -> int:
    """Count total images in a list of blocks (including nested in column_list)"""
    processor = MediaProcessor()
    return processor.count_images_in_blocks(blocks)


def upload_media_in_blocks(blocks: List[Dict[str, Any]], strategy, source_dir: Path, context: Dict) -> List[Dict[str, Any]]:
    """
    Upload all media (images, videos, documents, etc.) using strategy and update URLs in blocks.
    For S3/CDN strategies only (tunnel doesn't need this).
    """
    context['source_dir'] = source_dir
    failed_media = []
    
    for block in blocks:
        # Handle images, videos, and files
        if block.get('type') in ['image', 'video', 'file']:
            # Get current URL (relative path)
            media_type = block['type']
            if media_type == 'image':
                current_url = block['image']['external']['url']
            elif media_type == 'video':
                current_url = block['video']['external']['url']
            else:  # file
                current_url = block['file']['external']['url']
            
            # If it's a local path, upload it
            if not current_url.startswith(('http://', 'https://')):
                # Debug log the URL being processed
                print(f"  [dim]Processing {media_type}: {current_url}[/dim]")
                
                # Remove leading slash from relative paths
                relative_path = current_url.lstrip('/')
                local_path = source_dir / relative_path
                if local_path.exists():
                    try:
                        # Upload and get CDN URL
                        cdn_url = strategy.upload_image(local_path, context)
                        # Update block with CDN URL
                        if media_type == 'image':
                            block['image']['external']['url'] = cdn_url
                        elif media_type == 'video':
                            block['video']['external']['url'] = cdn_url
                        else:  # file
                            block['file']['external']['url'] = cdn_url
                    except Exception as e:
                        print(f"  [red]Error: Failed to upload {local_path.name}: {e}[/red]")
                        failed_media.append(str(local_path))
                        # Keep the invalid URL so we can see the issue
                else:
                    # Check if this is a placeholder or temporary file
                    from .image_utils import should_skip_image
                    from bs4 import BeautifulSoup
                    dummy_tag = BeautifulSoup().new_tag('img')
                    if should_skip_image(dummy_tag, current_url):
                        print(f"  [dim]Skipping temporary/placeholder: {current_url}[/dim]")
                    else:
                        print(f"  [red]Error: {media_type.capitalize()} not found: {local_path}[/red]")
                        failed_media.append(current_url)
        
        elif block.get('type') == 'column_list':
            # Handle images and videos in column_list
            for col in block.get('column_list', {}).get('children', []):
                for child in col.get('column', {}).get('children', []):
                    if child.get('type') in ['image', 'video', 'file']:
                        media_type = child['type']
                        if media_type == 'image':
                            current_url = child['image']['external']['url']
                        elif media_type == 'video':
                            current_url = child['video']['external']['url']
                        else:  # file
                            current_url = child['file']['external']['url']
                            
                        if not current_url.startswith(('http://', 'https://')):
                            # Remove leading slash from relative paths
                            relative_path = current_url.lstrip('/')
                            local_path = source_dir / relative_path
                            if local_path.exists():
                                try:
                                    cdn_url = strategy.upload_image(local_path, context)
                                    if media_type == 'image':
                                        child['image']['external']['url'] = cdn_url
                                    elif media_type == 'video':
                                        child['video']['external']['url'] = cdn_url
                                    else:  # file
                                        child['file']['external']['url'] = cdn_url
                                except Exception as e:
                                    print(f"  [red]Error: Failed to upload {local_path.name}: {e}[/red]")
                                    failed_media.append(str(local_path))
                            else:
                                # Check if this is a placeholder or temporary file
                                from .image_utils import should_skip_image
                                from bs4 import BeautifulSoup
                                dummy_tag = BeautifulSoup().new_tag('img')
                                if should_skip_image(dummy_tag, current_url):
                                    print(f"  [dim]Skipping temporary/placeholder: {current_url}[/dim]")
                                else:
                                    print(f"  [red]Error: {media_type.capitalize()} not found: {local_path}[/red]")
                                    failed_media.append(current_url)
    
    if failed_media:
        from .models.errors import UploadError, ErrorCode, get_error_message
        import logging
        
        # Count placeholder vs actual missing files
        placeholder_count = sum(1 for m in failed_media if 'placeholder' in m or 'unknown-attachment' in m)
        actual_missing = len(failed_media) - placeholder_count
        
        print(f"\n[yellow]Warning: Failed to process {len(failed_media)} media files:[/yellow]")
        for media in failed_media[:5]:  # Show first 5
            print(f"  - {media}")
        if len(failed_media) > 5:
            print(f"  ... and {len(failed_media) - 5} more")
        
        # Log appropriate warnings
        if placeholder_count > 0:
            logging.warning(get_error_message(
                ErrorCode.WARN_PLACEHOLDER_IMAGE_SKIPPED,
                f"{placeholder_count} placeholder images found and skipped"
            ))
        
        if actual_missing > 0:
            logging.warning(get_error_message(
                ErrorCode.WARN_MISSING_MEDIA_SKIPPED,
                f"{actual_missing} media files not found"
            ))
        
        # For now, continue with missing media files since we can't access the config
        # The proper fix would be to pass import_config as a parameter to this function
        print(f"\n[yellow]{get_error_message(ErrorCode.WARN_MISSING_MEDIA_SKIPPED)}[/yellow]")
        print(f"[dim]Continuing with {placeholder_count} placeholders and {actual_missing} missing files[/dim]")
    
    return blocks


# Removed: verify_images_loaded() - now in verification.py as ImageVerifier.verify_page_images()


def main(argv: Optional[list] = None):
    ap = argparse.ArgumentParser(description="Import Confluence HTML export into Notion")
    ap.add_argument('--source-dir', default=None)
    ap.add_argument('--run', action='store_true', help='Perform writes to Notion')
    ap.add_argument('--max-columns', type=int, default=None)
    ap.add_argument('--parent-id', default=None)
    ap.add_argument('--skip-verification', action='store_true', help='Skip image verification after upload')
    args = ap.parse_args(argv)

    # Load configuration
    app_cfg = AppConfig.load()
    source_dir = args.source_dir or app_cfg.source_dir
    if not source_dir:
        print('[red]Source directory not set. Use GUI or --source-dir.[/red]')
        return 2
    
    # Convert to new config model
    import_config = app_cfg.to_import_config()
    import_config.base.source_dir = source_dir  # Override with CLI arg if provided
    
    # Override with CLI arguments
    if args.parent_id:
        import_config.base.parent_id = args.parent_id
    if args.max_columns:
        import_config.base.max_columns = args.max_columns
    
    # Validate configuration (always require Notion creds)
    try:
        import_config.validate(require_notion=True)
    except ConfigurationError as e:
        print(f'[red]{e}[/red]')
        return 2
    
    # Initialize upload strategy
    upload_strategy = create_strategy(import_config.strategy)
    public = upload_strategy.prepare(Path(source_dir))
    
    print(f"[green]Upload strategy:[/green] {upload_strategy.get_name()}")
    if public:
        print(f"[green]Base URL:[/green] {public}")
    
    # Initialize media processor and scan for media files
    media_processor = MediaProcessor()
    print(f"\n[cyan]Scanning for media files...[/cyan]")
    media_inventory = media_processor.scan_directory(Path(source_dir))
    if media_inventory.total_count > 0:
        print(media_inventory.get_summary())
    
    # Scan for Draw.io diagrams
    drawio_scanner = DrawioScanner()
    print(f"\n[cyan]Scanning for Draw.io diagrams...[/cyan]")
    drawio_diagrams = drawio_scanner.scan_export(Path(source_dir))
    
    total_drawio = sum(len(diagrams) for diagrams in drawio_diagrams.values())
    if total_drawio > 0:
        print(f"[yellow]Found {total_drawio} Draw.io diagram(s) in {len(drawio_diagrams)} file(s)[/yellow]")
        
        # Prepare diagrams for Notion (extract/convert)
        output_dir = Path(source_dir) / 'drawio_converted'
        output_dir.mkdir(exist_ok=True)
        
        prepared = drawio_scanner.prepare_for_notion(drawio_diagrams, output_dir)
        print(f"[green]Prepared {prepared} diagram(s) for import[/green]")
    else:
        print("[dim]No Draw.io diagrams found[/dim]")

    # Notion - always required now
    token = import_config.base.notion_token
    parent_id = import_config.base.parent_id
    
    if not token:
        print('[red]NOTION_TOKEN missing. Set via GUI or env.[/red]')
        return 2
    if not parent_id:
        print('[yellow]PARENT_ID missing. Set it via GUI or --parent-id argument.[/yellow]')
        return 2
    
    notion = Notion(token)
    verifier = ImageVerifier(notion)

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
    parsing_failures = []  # Track files that failed to parse/transform
    import_start_time = time.time()
    
    for f in html_files:
        try:
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
                max_cols=import_config.base.max_columns,
                preserve_table_layout=import_config.base.preserve_table_layout,
                min_column_height=import_config.base.min_column_height,
                smart_table_rendering=import_config.base.smart_table_rendering,
                table_image_threshold=import_config.base.table_image_threshold
            )
            
            # For S3/CDN strategies, upload media and update URLs in blocks
            if not public:
                blocks = upload_media_in_blocks(blocks, upload_strategy, Path(source_dir), {})
            
            image_count = count_images_in_blocks(blocks)
            total_blocks += len(blocks)
            total_images += image_count
            
            page_stats.append({
                'file': f,
                'title': ast['title'],
                'ast': ast,
                'blocks': blocks,
                'image_count': image_count,
                'metadata': ast.get('metadata', {})
            })
        except Exception as e:
            # Capture error details for later review
            error_detail = {
                'file': str(f),
                'filename': f.name,
                'stage': 'parsing',
                'error_type': type(e).__name__,
                'error_message': str(e),
                'traceback': traceback.format_exc()
            }
            parsing_failures.append(error_detail)
            print(f"[red]✗ Failed to parse {f.name}: {type(e).__name__}: {e}[/red]")
            continue  # Move to next file instead of crashing
    
    # Show summary before importing
    print(f"\n[green]═══ Import Summary ═══[/green]")
    print(f"  Pages:  {len(html_files)}")
    print(f"  Blocks: {total_blocks}")
    print(f"  Images: {total_images}")
    est_time = len(html_files) * SECONDS_PER_PAGE_ESTIMATE + total_images * SECONDS_PER_IMAGE_ESTIMATE
    print(f"  Est. time: ~{est_time // SECONDS_PER_MINUTE}m {est_time % SECONDS_PER_MINUTE}s")
    print(f"[green]{'═' * 22}[/green]\n")
    
    # Start database tracking for this import run
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
        metadata = page_info.get('metadata', {})
        
        print(f"- {f.name} -> {title} ({len(blocks)} blocks, {image_count} images)")
        
        if notion:
            page_id = None  # Track for error handling
            try:
                page_id = notion.create_page(parent_id, title)
                notion.append_blocks(page_id, blocks)
                
                # Save author/editor information to database
                if run_id and metadata:
                    db.add_page_authors(
                        run_id=run_id,
                        page_id=page_id,
                        created_by=metadata.get('created_by'),
                        last_modified_by=metadata.get('last_modified_by')
                    )
                
                # Verify images are loaded before moving to next page
                images_ok = True
                actual_verified = 0
                if image_count > 0 and not (import_config.base.skip_verification or args.skip_verification):
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
                elif image_count > 0 and (import_config.base.skip_verification or args.skip_verification):
                    # Skip verification - mark all images as verified
                    print(f"  [dim]Skipping verification for {image_count} images[/dim]")
                    actual_verified = image_count
                    verified_image_count += image_count
                    images_ok = True
                
                line = f"{{\"source\":\"{str(f)}\",\"page_id\":\"{page_id}\"}}\n"
                with open(mapping_path, 'a', encoding='utf-8') as fp:
                    fp.write(line)
            except Exception as e:
                # Capture Notion API error details
                error_detail = {
                    'file': str(f),
                    'filename': f.name,
                    'stage': 'notion_upload',
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'traceback': traceback.format_exc(),
                    'page_id': page_id  # May be None if create_page failed
                }
                parsing_failures.append(error_detail)
                print(f"[red]✗ Failed to upload {title}: {type(e).__name__}: {e}[/red]")
                continue  # Move to next page instead of crashing

    # Save parsing errors to database
    for err in parsing_failures:
        db.add_parsing_error(
            run_id=run_id,
            file_path=err['file'],
            filename=err['filename'],
            stage=err['stage'],
            error_type=err['error_type'],
            error_message=err['error_message'],
            traceback_str=err.get('traceback')
        )
    
    # Finalize database run
    duration = int(time.time() - import_start_time)
    # Subtract both failed pages (image verification) and parsing failures
    successful_pages = len(page_stats) - len(failed_pages)  # page_stats excludes parsing failures
    db.finish_import_run(run_id, successful_pages, verified_image_count, duration)
    
    # Export parsing errors to JSON (with run_id in filename for history)
    if parsing_failures:
        # Use run-specific filename so each import's errors are preserved
        parsing_errors_path = Path(__file__).resolve().parents[1] / 'out' / f'parsing_errors_run{run_id}.json'
        db.export_parsing_errors_to_json(parsing_errors_path, run_id)
        
        # Also save a "latest" copy for convenience
        latest_errors_path = Path(__file__).resolve().parents[1] / 'out' / 'parsing_errors_latest.json'
        db.export_parsing_errors_to_json(latest_errors_path, run_id)
        
        print(f"\n[red]═══ Parsing/Conversion Errors ═══[/red]")
        print(f"[red]{len(parsing_failures)} file(s) failed to process:[/red]")
        
        for err in parsing_failures[:MAX_FAILED_PAGES_DISPLAY]:
            print(f"  [red]✗ {err['filename']}[/red]")
            print(f"    Stage: {err['stage']}")
            print(f"    Error: {err['error_type']}: {err['error_message'][:100]}")
        if len(parsing_failures) > MAX_FAILED_PAGES_DISPLAY:
            print(f"  [red]... and {len(parsing_failures) - MAX_FAILED_PAGES_DISPLAY} more[/red]")
        
        print(f"\n[yellow]Detailed errors saved to:[/yellow]")
        print(f"[yellow]  - {parsing_errors_path} (this run)[/yellow]")
        print(f"[yellow]  - {latest_errors_path} (latest)[/yellow]")
        print(f"[yellow]Database: {db.db_path} (all runs, query by run_id={run_id})[/yellow]")
    
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
    upload_strategy.cleanup(failed_count=len(failed_pages))
    
    # Final summary
    if notion:
        total_pages = len(html_files)
        parsed_pages = len(page_stats)  # Successfully parsed pages
        success_pages = parsed_pages - len(failed_pages)
        failed_image_count = sum(p['expected_images'] for p in failed_pages)
        
        print(f"\n[green]{'═' * 40}[/green]")
        print(f"[green]✓ Import Complete[/green]")
        print(f"  Pages:  {success_pages}/{total_pages} successful")
        print(f"  Images: {verified_image_count}/{total_images} verified")
        if parsing_failures:
            print(f"[red]  {len(parsing_failures)} page(s) failed to parse/convert[/red]")
        if failed_pages:
            print(f"[yellow]  {len(failed_pages)} page(s) with {failed_image_count} unverified images[/yellow]")
            print(f"[cyan]  Run 'Auto-Retry Failed' in GUI to retry failed pages[/cyan]")
        
        # Display author statistics
        author_stats = db.get_author_statistics()
        if author_stats:
            print(f"\n[cyan]📊 Author Statistics (sorted by total contributions):[/cyan]")
            print(f"  {'Name':<40} {'Total':<8} {'Created':<8} {'Edited':<8}")
            print(f"  {'-' * 40} {'-' * 8} {'-' * 8} {'-' * 8}")
            for stat in author_stats[:20]:  # Show top 20
                name = stat['author_name']
                total = stat['total_count']
                created = stat['creator_count']
                edited = stat['editor_count']
                print(f"  {name:<40} {total:<8} {created:<8} {edited:<8}")
            if len(author_stats) > 20:
                print(f"  ... and {len(author_stats) - 20} more authors")
        
        print(f"[green]{'═' * 40}[/green]")
    
    # Close database connection
    db.close()

if __name__ == '__main__':
    sys.exit(main())
