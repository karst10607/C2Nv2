#!/usr/bin/env python3
"""
Retry failed image imports from the database.
Can be called from CLI or Electron GUI.
"""
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.config import AppConfig
from src.database import ImportDatabase
from src.notion_api import Notion
from src.verification import ImageVerifier
from rich import print
from src.constants import MAX_RETRY_COUNT


def retry_failed_images(max_retry_count: int = MAX_RETRY_COUNT):
    """
    Retry pages with failed images.
    Re-checks Notion to see if images eventually loaded.
    """
    db = ImportDatabase()
    cfg = AppConfig.load()
    
    if not cfg.notion_token:
        print('[red]NOTION_TOKEN not set. Configure in GUI first.[/red]')
        return 1
    
    notion = Notion(cfg.notion_token)
    verifier = ImageVerifier(notion)
    
    # Get pages needing retry
    pending = db.get_pending_retries(max_retry_count=max_retry_count)
    
    if not pending:
        print('[green]No failed pages to retry! All images verified.[/green]')
        return 0
    
    print(f'[cyan]Found {len(pending)} page(s) to retry (retry_count < {max_retry_count})[/cyan]\n')
    
    resolved_count = 0
    still_failed = 0
    
    for page in pending:
        page_db_id = page['id']
        page_id = page['page_id']
        title = page['title']
        expected = page['expected_images']
        verified = page['verified_images']
        retry_count = page['retry_count']
        
        print(f"[cyan]Checking:[/cyan] {title}")
        print(f"  Page ID: {page_id}")
        print(f"  Expected: {expected}, Previously verified: {verified}, Retries: {retry_count}")
        
        try:
            # Fetch current state from Notion and count verified images
            page_blocks = notion.get_blocks(page_id)
            current_verified = verifier.count_verified_images_in_blocks(page_blocks)
            
            # Check if resolved
            if current_verified >= expected:
                print(f"  [green]✓ Resolved! {current_verified}/{expected} images now verified[/green]\n")
                db.update_retry_attempt(page_db_id, current_verified, success=True)
                resolved_count += 1
            else:
                print(f"  [yellow]⚠ Still incomplete: {current_verified}/{expected} verified[/yellow]\n")
                db.update_retry_attempt(page_db_id, current_verified, success=False, 
                                       error=f'Still missing {expected - current_verified} images')
                still_failed += 1
            
        except Exception as e:
            print(f"  [red]✗ Error checking page: {e}[/red]\n")
            db.update_retry_attempt(page_db_id, verified, success=False, error=str(e))
            still_failed += 1
    
    # Summary
    print(f"\n[green]{'═' * 40}[/green]")
    print(f"[green]Retry Summary[/green]")
    print(f"  Checked: {len(pending)} pages")
    print(f"  Resolved: {resolved_count} pages")
    print(f"  Still failing: {still_failed} pages")
    print(f"[green]{'═' * 40}[/green]")
    
    # Show persistent failures
    persistent = db.get_pending_retries(max_retry_count=99)
    max_retry = [p for p in persistent if p['retry_count'] >= max_retry_count]
    
    if max_retry:
        print(f"\n[yellow]Pages that reached max retries ({max_retry_count}):[/yellow]")
        for p in max_retry:
            print(f"[yellow]  - {p['title']} (retries: {p['retry_count']})[/yellow]")
    
    db.close()
    return 0


if __name__ == '__main__':
    sys.exit(retry_failed_images())

