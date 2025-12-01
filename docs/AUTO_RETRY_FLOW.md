# Auto-Retry Failed Images: How It Works

## Overview

The auto-retry mechanism **DOES NOT re-upload images**. Instead, it **re-checks** if Notion has successfully cached images that were previously uploaded.

## The Complete Flow

### 1. Initial Import Process
```
HTML Files → Parse → Transform → Create Notion Pages → Upload Images → Verify
                                                                          ↓
                                                                    If Failed → Store in DB
```

### 2. What Gets Stored in Database
When images fail verification, the database stores:
- `page_id`: The Notion page UUID
- `expected_images`: Total image count in the page
- `verified_images`: How many were successfully cached by Notion
- `file_path`: Original HTML source (for reference only)

### 3. Auto-Retry Process

```
Click "Auto-Retry Failed" Button
        ↓
1. Query Database
   - Get all failed pages where retry_count < 3
   - Each page has: page_id, expected_images, verified_images
        ↓
2. For Each Failed Page:
   a. Call Notion API: get_blocks(page_id)
      - Fetches current page content from Notion
      - Gets ALL blocks including nested column_list blocks
        ↓
   b. Count Verified Images
      - Extract all image blocks from the response
      - Check each image URL
      - Count URLs that point to Notion's CDN
        ↓
   c. Compare Results
      - If verified_count >= expected_count → Mark as resolved
      - If still missing images → Update retry_count, record error
        ↓
3. Update Database
   - Increment retry_count
   - Update last_retry_timestamp
   - Record success/failure status
```

## Key Points

### What Auto-Retry DOES:
1. **Queries Notion API** to get current page state
2. **Counts cached images** by checking if URLs point to Notion's CDN
3. **Updates database** with current verification status
4. **Tracks retry attempts** to avoid infinite loops

### What Auto-Retry DOES NOT:
1. **Does NOT re-upload** images from attachment folders
2. **Does NOT modify** the Notion page content
3. **Does NOT access** local HTML or attachment files
4. **Does NOT create** new image blocks

## Why Images Might Eventually Verify

1. **Notion Processing Delay**: Large images take time to process
2. **CDN Propagation**: Images need to propagate to Notion's CDN
3. **Rate Limiting**: Notion might delay processing during high load
4. **Network Issues**: Temporary failures that resolve later

## Understanding Image URLs

### Original Upload (External URL)
```
https://your-tunnel.com/attachments/2753397032/image.png
https://your-s3-bucket.com/attachments/2753397032/image.png
```

### After Notion Caches (CDN URL)
```
https://prod-files-secure.s3.us-west-2.amazonaws.com/workspace-id/block-id/image.png
https://notion.so/image/https%3A%2F%2Fs3.us-west...
```

The retry process checks if this transformation has occurred.

## Database Queries Used

### Get Pending Retries
```sql
SELECT * FROM failed_pages 
WHERE status = 'pending' AND retry_count < 3
ORDER BY retry_count ASC
```

### Update After Retry
```sql
UPDATE failed_pages
SET retry_count = retry_count + 1,
    verified_images = ?,
    last_retry_timestamp = ?,
    last_error = ?,
    status = ?
WHERE id = ?
```

## When to Use Auto-Retry

### Good Cases:
- After waiting 5-10 minutes for Notion to process
- When you see "Still missing X images" errors
- After fixing network/tunnel issues

### Won't Help:
- If source images were deleted
- If Notion page was deleted ("Could not find block")
- If images exceed Notion's size limits
- If upload strategy failed initially

## Manual Verification

To manually check if an image is cached:
1. Open the Notion page
2. Right-click an image → "Copy Image Address"
3. Check if URL contains Notion CDN domains
4. Or refresh the page - cached images load instantly

## Summary

Auto-retry is a **verification re-check**, not a re-upload. It's useful when:
- Notion needs more time to process images
- You want to verify current state without re-importing
- You need to track which pages still have issues

For actual re-uploads, you would need to:
1. Delete the Notion page
2. Run a fresh import
3. Or manually update image URLs in Notion








