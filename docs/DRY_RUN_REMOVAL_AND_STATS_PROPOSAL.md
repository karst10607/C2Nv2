# Proposal: Remove Dry Run & Add Statistics Feature

## Part 1: Removing Dry Run

### Analysis: Is it safe to remove?

**Answer: YES, it's relatively safe** ✅

### Current Dry Run Usage:

1. **CLI Argument** (`src/importer.py`):
   - `--dry-run` flag (line 174)
   - Used to skip Notion API calls (sets `notion = None` when not `args.run`)
   - Used to skip Notion credential validation (`require_notion=args.run`)

2. **GUI Components**:
   - Button in `electron/index.html` (line 163)
   - Handler in `electron/renderer.js` (line 19, 261, 295, 308)
   - IPC handler in `electron/main.js` (lines 152, 165)

3. **What Dry Run Actually Does**:
   - ✅ Still parses HTML files
   - ✅ Still scans media files
   - ✅ Still uploads to S3/CDN (if configured)
   - ✅ Still processes Draw.io diagrams
   - ❌ Skips creating Notion pages
   - ❌ Skips appending blocks to Notion
   - ❌ Skips image verification

### Impact Assessment:

**Low Risk** - Dry run is mostly a flag that prevents Notion API calls. Removing it won't break:
- HTML parsing
- Media scanning
- File processing
- Transform logic

**What needs to change:**
1. Remove `--dry-run` CLI argument
2. Remove dry run button from GUI
3. Remove dry run logic from importer (always run)
4. Update validation to always require Notion credentials

### Proposed Changes:

1. **Remove from `src/importer.py`**:
   - Remove `--dry-run` argument
   - Remove `args.dry_run` checks
   - Always require Notion credentials
   - Always create pages and append blocks

2. **Remove from GUI** (`electron/index.html`, `electron/renderer.js`, `electron/main.js`):
   - Remove dry run button
   - Remove dry run parameter from `startImport` calls
   - Simplify import flow

3. **Update documentation**:
   - Remove dry run references from README

---

## Part 2: Add Statistics Feature

### Feature: Show Merged Cells & Side-by-Side Layout Statistics

### What to Count:

1. **Merged Cells**:
   - Tables with `colspan > 1` (horizontal merge)
   - Tables with `rowspan > 1` (vertical merge)
   - Count per table and total

2. **Side-by-Side Layouts**:
   - Confluence `columnLayout` divs
   - Patterns: `two-equal`, `three-equal`, `fixed-width`, etc.
   - Count layouts and their types

### Implementation Plan:

#### Step 1: Create Statistics Scanner (`src/statistics.py`)

```python
def scan_html_statistics(source_dir: Path) -> Dict[str, Any]:
    """
    Scan HTML files and collect statistics about:
    - Merged cells (colspan/rowspan)
    - Side-by-side layouts (columnLayout)
    
    Returns:
        Dictionary with statistics
    """
    stats = {
        'total_files': 0,
        'tables': {
            'total': 0,
            'with_merged_cells': 0,
            'merged_cell_count': 0,
            'colspan_count': 0,
            'rowspan_count': 0
        },
        'layouts': {
            'total': 0,
            'by_type': {}
        }
    }
    
    # Scan HTML files
    for html_file in source_dir.rglob('*.html'):
        stats['total_files'] += 1
        # Parse and analyze
        # Count merged cells
        # Count layouts
    
    return stats
```

#### Step 2: Add IPC Handler (`electron/main.js`)

```javascript
ipcMain.handle('get-statistics', async (event, sourceDir) => {
  // Call Python script to get statistics
  // Return JSON result
});
```

#### Step 3: Add GUI Button (`electron/index.html`)

```html
<button id="statistics-btn" class="btn-secondary">
  📊 Show Statistics
</button>
```

#### Step 4: Add Handler (`electron/renderer.js`)

```javascript
statisticsBtn.addEventListener('click', async () => {
  const sourceDir = sourceDirInput.value.trim();
  if (!sourceDir) {
    alert('Please select a source directory first');
    return;
  }
  
  const stats = await electronAPI.getStatistics(sourceDir);
  // Display in modal or log area
});
```

### Statistics Output Format:

```json
{
  "total_files": 147,
  "tables": {
    "total": 45,
    "with_merged_cells": 12,
    "merged_cell_count": 38,
    "colspan_count": 25,
    "rowspan_count": 13
  },
  "layouts": {
    "total": 89,
    "by_type": {
      "two-equal": 45,
      "three-equal": 20,
      "fixed-width": 24
    }
  }
}
```

### Display Format:

```
📊 Statistics for Selected Folder

Files Scanned: 147

Tables:
  • Total tables: 45
  • Tables with merged cells: 12
  • Total merged cells: 38
    - Horizontal merges (colspan): 25
    - Vertical merges (rowspan): 13

Side-by-Side Layouts:
  • Total layouts: 89
  • Two-column layouts: 45
  • Three-column layouts: 20
  • Fixed-width layouts: 24
```

---

## Implementation Order:

1. ✅ **First**: Add statistics feature (doesn't affect existing code)
2. ✅ **Then**: Remove dry run (simpler after stats are working)

---

## Risk Assessment:

### Dry Run Removal: **LOW RISK** ✅
- Only affects import flow
- No breaking changes to parsing/transformation
- Can be tested easily

### Statistics Feature: **NO RISK** ✅
- New feature, doesn't modify existing code
- Read-only operation
- Can be added incrementally

---

## Files to Modify:

### Dry Run Removal:
1. `src/importer.py` - Remove dry-run logic
2. `electron/index.html` - Remove button
3. `electron/renderer.js` - Remove handler
4. `electron/main.js` - Remove dry-run parameter
5. `README.md` - Update documentation

### Statistics Feature:
1. `src/statistics.py` - **NEW FILE** - Scanner logic
2. `electron/main.js` - Add IPC handler
3. `electron/index.html` - Add button
4. `electron/renderer.js` - Add click handler
5. `electron/styles.css` - Style statistics display (if modal)

---

## Testing Strategy:

1. **Statistics Feature**:
   - Test with various HTML files
   - Verify counts are accurate
   - Test with empty folder
   - Test with folder containing no tables/layouts

2. **Dry Run Removal**:
   - Test import still works
   - Verify Notion pages are created
   - Verify no dry-run references remain

---

## Summary:

- **Dry Run Removal**: Safe, low risk, straightforward
- **Statistics Feature**: New feature, zero risk to existing code
- **Recommendation**: Implement statistics first, then remove dry run

