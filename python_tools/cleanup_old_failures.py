#!/usr/bin/env python3
"""
Clean up old failed page entries that no longer exist in Notion.
Called from CLI or Electron GUI.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.database import ImportDatabase
from rich import print


def cleanup_old_failures():
    """Clean up failed pages with 'Could not find block' errors"""
    db = ImportDatabase()
    
    # Count entries to be deleted
    cursor = db.conn.execute('''
        SELECT COUNT(*) as count
        FROM failed_pages
        WHERE last_error LIKE '%Could not find block%'
    ''')
    
    count = cursor.fetchone()['count']
    
    if count == 0:
        print('[green]No old entries to clean up![/green]')
        return 0
    
    print(f'[yellow]Found {count} old failed page entries (deleted/inaccessible pages)[/yellow]')
    
    # Delete old entries
    deleted = db.conn.execute('''
        DELETE FROM failed_pages
        WHERE last_error LIKE '%Could not find block%'
    ''').rowcount
    
    db.conn.commit()
    
    print(f'[green]✓ Cleaned up {deleted} old entries[/green]')
    
    # Show remaining failed pages summary
    cursor = db.conn.execute('''
        SELECT COUNT(*) as remaining,
               SUM(CASE WHEN retry_count >= 3 THEN 1 ELSE 0 END) as max_retries
        FROM failed_pages
        WHERE status = 'pending'
    ''')
    
    stats = cursor.fetchone()
    if stats['remaining'] > 0:
        print(f'\n[cyan]Remaining failed pages: {stats["remaining"]}[/cyan]')
        if stats['max_retries'] > 0:
            print(f'[yellow]  - {stats["max_retries"]} at max retry limit[/yellow]')
    
    db.close()
    return 0


if __name__ == '__main__':
    sys.exit(cleanup_old_failures())










