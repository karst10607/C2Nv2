# Smart Table Rendering

## Overview

Smart Table Rendering is a feature that intelligently chooses between native Notion tables and column-based layouts based on table content. This provides a better user experience by using real tables for simple data while preserving the flexibility of column layouts for complex content.

## How It Works

### 1. Content Analysis

When processing a table, the system analyzes its content to determine:
- **Has images**: Whether any cells contain images
- **Has mixed content**: Whether cells contain both images and text
- **Has only text**: Pure text-based table
- **Has only icons**: Small images/GIFs that could be emojis
- **Total images/icons**: Count of media elements
- **Cell complexity**: Simple, moderate, or complex

### 2. Rendering Decision

Based on the analysis, the system chooses:

#### Native Notion Table
Used when:
- Table contains only text
- Table has only small icons (≤5 icons total)
- Table has ≤2 images with no mixed content in cells

Benefits:
- Clean, native table appearance
- Better performance
- Easier to edit in Notion
- Proper table semantics

#### Column-Based Layout
Used when:
- Table has images mixed with text in cells
- Table has more than 2 images
- Table complexity is high
- Smart rendering is disabled

Benefits:
- Full support for any content type
- Images display properly
- Complex formatting preserved

## Configuration

### Settings in BaseConfig

```python
# Enable/disable smart rendering (default: True)
smart_table_rendering: bool = True

# Maximum images before switching to columns (default: 2)
table_image_threshold: int = 2

# Prefer native tables when possible (default: True)
prefer_native_tables: bool = True

# Icon size threshold in pixels (default: 32)
icon_size_threshold: int = 32
```

### Command Line Usage

Smart table rendering is enabled by default. To disable:
```bash
# This would require adding CLI argument support
python -m src.importer --source-dir EP --no-smart-tables
```

## Examples

### Text-Only Table → Native Notion Table
```
┌─────────┬─────────┬─────────┐
│  Name   │  Role   │ Status  │
├─────────┼─────────┼─────────┤
│  Alice  │  Dev    │ Active  │
│  Bob    │  PM     │ Active  │
└─────────┴─────────┴─────────┘
```

### Table with Images → Column Layout
```
┌─────────────┬─────────────┬─────────────┐
│ Screenshot  │ Description │   Status    │
│  [Image]    │    Text     │   ✓ Done    │
│  [Image]    │    Text     │   ⚡ Active  │
└─────────────┴─────────────┴─────────────┘
```

### Table with Icons → Native Table
```
┌─────────┬─────────┬─────────┐
│  Task   │  Icon   │ Status  │
├─────────┼─────────┼─────────┤
│ Deploy  │   🚀    │  Done   │
│ Review  │   👀    │ Pending │
└─────────┴─────────┴─────────┘
```

## Technical Details

### Header Detection and Rendering

The system automatically detects and renders table headers:

1. **Primary Headers** (Native Notion styling):
   - First row with `<thead>` or all `<th>` cells → Column header (gray background)
   - First column with all `<th scope="row">` → Row header (gray background)
   
2. **Secondary Headers** (Bold text):
   - Additional `<th>` cells not in primary positions → Bold text
   - Cells with `confluenceTh` or `header` CSS classes → Bold text
   - Preserves visual hierarchy without breaking Notion's table structure

Example:
```
Original HTML:
<table>
  <thead>
    <tr><th>Main Header 1</th><th>Main Header 2</th></tr>
  </thead>
  <tbody>
    <tr><th>Sub Header</th><td>Data</td></tr>
    <tr><td>Value 1</td><td>Value 2</td></tr>
  </tbody>
</table>

Notion Result:
┌──────────────┬──────────────┐
│ Main Header 1│ Main Header 2│ ← Gray background (primary header)
├──────────────┼──────────────┤
│ **Sub Header**│     Data     │ ← Bold text (secondary header)
├──────────────┼──────────────┤
│   Value 1    │   Value 2    │
└──────────────┴──────────────┘
```

### Merged Cell Handling

When converting tables with merged cells (colspan/rowspan) to native Notion tables:
1. **Colspan**: Content is placed in the first cell, additional columns are filled with empty cells
2. **Rowspan**: Content is placed in the first row's cell, spanned rows get empty cells in that column
3. The visual structure is preserved even though Notion doesn't support true cell merging

Example:
```
HTML Table with colspan=2:
┌─────────────────┬─────────┐
│  Merged Header  │  Normal │
├────────┬────────┼─────────┤
│ Cell 1 │ Cell 2 │ Cell 3  │
└────────┴────────┴─────────┘

Notion Native Table:
┌─────────────────┬─────────┬─────────┐
│  Merged Header  │         │  Normal │
├─────────────────┼─────────┼─────────┤
│     Cell 1      │ Cell 2  │ Cell 3  │
└─────────────────┴─────────┴─────────┘
```

### Icon Detection

Icons are identified by:
1. Size attributes (≤32x32 pixels)
2. URL patterns (`/icon`, `/emoji`, `/16x16/`, etc.)
3. Filename patterns (`.gif`, `.ico`, status icons)
4. Common icon locations

### Text Extraction

For native tables, complex cell content is flattened:
- Paragraphs → Plain text
- Lists → Bullet points or numbered items
- Code → Inline code with backticks
- Multiple paragraphs → Joined with newlines

### Limitations

Native Notion tables have limitations:
- Maximum 100 rows per table (automatically split if larger)
- Maximum 100 characters per cell (truncated if longer)
- No images or complex formatting
- No nested blocks
- Simple text styling only

When a table exceeds 100 rows:
1. The table is split into multiple 100-row chunks
2. Each chunk becomes a separate table block
3. A note is added between chunks: "... table continues (rows 101-200)"

## Testing

Use the test script to verify smart table behavior:

```bash
python test_smart_tables.py
```

This will:
1. Scan HTML files for tables
2. Analyze each table's content
3. Show which rendering method would be used
4. Compare smart vs. regular rendering

## Future Improvements

1. **Hybrid Tables**: Mix native and column rows in same table
2. **Icon Mapping**: Convert common icons to Notion emojis
3. **Table Headers**: Detect and preserve header rows
4. **Cell Merging**: Handle colspan/rowspan
5. **Table Captions**: Preserve table titles/captions
