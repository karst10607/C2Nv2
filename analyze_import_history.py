#!/usr/bin/env python3
"""Analyze import history to understand duplicate entries"""
import sqlite3
from pathlib import Path
from collections import defaultdict

db_path = Path("out/import_history.db")
if not db_path.exists():
    print("No database found.")
    exit(1)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

print("\n" + "="*80)
print("IMPORT RUNS HISTORY")
print("="*80)

# Show all import runs
cursor = conn.execute('''
    SELECT id, timestamp, total_pages, total_images, successful_pages
    FROM import_runs
    ORDER BY timestamp DESC
    LIMIT 10
''')

runs = cursor.fetchall()
for run in runs:
    print(f"\nRun ID: {run['id']} - {run['timestamp']}")
    print(f"  Pages: {run['successful_pages']}/{run['total_pages']}")
    print(f"  Images: {run['total_images']}")

print("\n" + "="*80)
print("FAILED PAGES BY TITLE (showing duplicates)")
print("="*80)

# Group failed pages by title to see duplicates
cursor = conn.execute('''
    SELECT 
        title,
        page_id,
        run_id,
        retry_count,
        status,
        last_error
    FROM failed_pages
    ORDER BY title, run_id DESC
''')

pages_by_title = defaultdict(list)
for page in cursor.fetchall():
    pages_by_title[page['title']].append(dict(page))

# Show titles that appear multiple times (different page IDs)
for title, pages in pages_by_title.items():
    if len(pages) > 1:
        print(f"\n📄 {title}")
        print(f"   Found {len(pages)} entries:")
        for p in pages:
            print(f"   - Page ID: {p['page_id']}")
            print(f"     Run ID: {p['run_id']}, Retries: {p['retry_count']}, Status: {p['status']}")
            if p['last_error']:
                print(f"     Error: {p['last_error'][:60]}...")

print("\n" + "="*80)
print("UNDERSTANDING THE DATA")
print("="*80)
print("""
Why you see multiple entries with 0 retries:

1. **Each import creates NEW entries** - The database doesn't clear old records
2. **Different page IDs** - Each import to Notion creates new page IDs
3. **Retry count starts at 0** - Only increments when you click "Auto-Retry Failed"

So if you imported the same content 3 times:
- Run 1: Creates pages with IDs starting with 29360014-...
- Run 2: Creates NEW pages with IDs starting with 29460014-...  
- Run 3: Creates NEW pages with IDs starting with 29d60014-...

Each has retry_count=0 because they're separate import attempts, not retries!
""")

conn.close()








