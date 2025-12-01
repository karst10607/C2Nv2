#!/usr/bin/env python3
"""Check the status of retry attempts in the database"""
from pathlib import Path
import sqlite3
from datetime import datetime

db_path = Path("out/import_history.db")

if not db_path.exists():
    print("No database found. Have you run any imports yet?")
    exit(1)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

print("\n" + "="*80)
print("FAILED PAGES RETRY STATUS")
print("="*80)

# Get all failed pages with their current status
cursor = conn.execute('''
    SELECT 
        page_id,
        title,
        expected_images,
        verified_images,
        retry_count,
        status,
        last_retry_timestamp,
        last_error
    FROM failed_pages
    ORDER BY status DESC, retry_count DESC
''')

failed_pages = cursor.fetchall()

if not failed_pages:
    print("\n✅ No failed pages found! All imports were successful.")
else:
    # Group by status
    pending = []
    resolved = []
    
    for page in failed_pages:
        if page['status'] == 'resolved':
            resolved.append(page)
        else:
            pending.append(page)
    
    # Show resolved pages
    if resolved:
        print(f"\n✅ RESOLVED PAGES ({len(resolved)} total)")
        print("-" * 80)
        for page in resolved:
            print(f"\nTitle: {page['title']}")
            print(f"  Page ID: {page['page_id']}")
            print(f"  Images: {page['verified_images']}/{page['expected_images']} verified")
            print(f"  Retry attempts: {page['retry_count']}")
            if page['last_retry_timestamp']:
                print(f"  Resolved at: {page['last_retry_timestamp']}")
    
    # Show pending pages
    if pending:
        print(f"\n⚠️  PENDING/FAILED PAGES ({len(pending)} total)")
        print("-" * 80)
        for page in pending:
            print(f"\nTitle: {page['title']}")
            print(f"  Page ID: {page['page_id']}")
            print(f"  Images: {page['verified_images']}/{page['expected_images']} verified")
            print(f"  Retry attempts: {page['retry_count']}")
            
            if page['retry_count'] >= 3:
                print(f"  ❌ MAX RETRIES REACHED")
            else:
                print(f"  🔄 Can retry ({3 - page['retry_count']} attempts left)")
                
            if page['last_retry_timestamp']:
                print(f"  Last retry: {page['last_retry_timestamp']}")
            if page['last_error']:
                print(f"  Last error: {page['last_error']}")

# Show summary statistics
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

cursor = conn.execute('''
    SELECT 
        COUNT(*) as total_failed,
        SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
        SUM(CASE WHEN retry_count >= 3 AND status = 'pending' THEN 1 ELSE 0 END) as max_retries
    FROM failed_pages
''')

stats = cursor.fetchone()
if stats and stats['total_failed'] > 0:
    print(f"Total failed pages: {stats['total_failed']}")
    print(f"  ✅ Resolved: {stats['resolved']}")
    print(f"  ⚠️  Still pending: {stats['pending']}")
    print(f"  ❌ Hit max retries: {stats['max_retries']}")

conn.close()








