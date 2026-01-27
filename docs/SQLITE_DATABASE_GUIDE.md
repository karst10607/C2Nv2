# SQLite Database Usage Guide

## Overview

The Notion Importer uses SQLite (`import_history.db`) to track import history, failed pages, and retry attempts. The database persists across import sessions and helps manage image verification failures.

## Database Location

```
/out/import_history.db
```

## Database Schema

### 1. `import_runs` Table
Tracks each import session:

```sql
CREATE TABLE import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    version TEXT,
    total_pages INTEGER,
    total_images INTEGER,
    successful_pages INTEGER,
    verified_images INTEGER,
    duration_seconds INTEGER
)
```

### 2. `failed_pages` Table
Records pages with unverified images:

```sql
CREATE TABLE failed_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,              -- Links to import_runs.id
    file_path TEXT NOT NULL,     -- Source HTML file path
    page_id TEXT NOT NULL,       -- Notion page ID (UUID)
    title TEXT NOT NULL,         -- Page title
    expected_images INTEGER,     -- Total images in page
    verified_images INTEGER,     -- Successfully verified images
    retry_count INTEGER DEFAULT 0,
    last_retry_timestamp TEXT,   -- ISO format timestamp
    last_error TEXT,            -- Last error message
    status TEXT DEFAULT 'pending' -- 'pending' or 'resolved'
)
```

## Programs Using SQLite

### 1. Main Import Process (`src/importer.py`)
- Creates new `import_runs` entry when starting
- Records `failed_pages` when image verification fails
- Updates run statistics on completion

### 2. Database Module (`src/database.py`)
- Core database interface
- Handles schema initialization
- Provides query methods

### 3. Retry Tool (`python_tools/retry_failed.py`)
- Reads pending failed pages
- Reverifies images via Notion API
- Updates retry count and status
- Records last error message

### 4. Cleanup Tool (`python_tools/cleanup_old_failures.py`)
- Removes old entries where Notion pages no longer exist
- Helps maintain a clean retry list
- Called via GUI button

### 5. Analysis Scripts
- `check_retry_status.py` - Shows current retry status
- `analyze_import_history.py` - Analyzes import patterns

## Key Concepts

### 1. Each Import Creates New Records
- Every import run creates new Notion pages with new IDs
- Old failed page records persist in database
- This creates "duplicates" with different page IDs

### 2. Retry Count Behavior
- `retry_count = 0`: Never retried
- `retry_count = 1-2`: Retried but still failing
- `retry_count >= 3`: Max retries reached (default limit)

### 3. Error Types
- **"Still missing X images"**: Some images not verified
- **"Could not find block"**: Page deleted or inaccessible
- **API errors**: Rate limits, network issues

## Using the Database

### View Failed Pages
```python
from src.database import ImportDatabase

db = ImportDatabase()
failed = db.get_all_failed_pages()
for page in failed:
    print(f"{page['title']}: {page['retry_count']} retries, {page['status']}")
```

### Get Retry Candidates
```python
pending = db.get_pending_retries(max_retry_count=3)
print(f"Found {len(pending)} pages to retry")
```

### Clean Old Entries
```python
# Remove entries with "Could not find block" errors
deleted = db.conn.execute('''
    DELETE FROM failed_pages
    WHERE last_error LIKE '%Could not find block%'
''').rowcount
db.conn.commit()
```

## GUI Integration

### Retry Button
- Calls `python_tools/retry_failed.py`
- Re-verifies all pending failed pages
- Updates retry counts and timestamps

### Cleanup Button (New)
- Calls `python_tools/cleanup_old_failures.py`
- Removes old entries for deleted pages
- Helps focus on current failures

## Best Practices

1. **Regular Cleanup**: Use cleanup button after deleting test imports
2. **Monitor Retry Counts**: Pages at max retries may have persistent issues
3. **Check Error Messages**: Different errors require different solutions
4. **Backup Database**: Before major operations, backup `import_history.db`

## Troubleshooting

### Q: Why do I see multiple entries for the same page title?
A: Each import creates new Notion pages. Old entries persist from previous imports.

### Q: How do I reset retry counts?
A: Update the database directly:
```sql
UPDATE failed_pages SET retry_count = 0 WHERE status = 'pending';
```

### Q: Can I manually mark pages as resolved?
A: Yes:
```sql
UPDATE failed_pages SET status = 'resolved' WHERE page_id = 'YOUR_PAGE_ID';
```

## Future Enhancements

1. **Auto-cleanup**: Option to auto-remove old entries after N days
2. **Retry strategies**: Different retry logic based on error type
3. **Export reports**: Generate CSV reports of failed pages
4. **Batch operations**: Select specific pages to retry via GUI





