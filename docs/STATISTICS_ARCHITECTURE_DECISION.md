# Statistics Feature Architecture Decision

## Question: Should Statistics be Separate from Import Parser?

**Answer: YES - Keep Statistics Completely Separate** ✅

---

## Architecture Comparison

### Option A: Separate Statistics Scanner (RECOMMENDED) ✅

```
src/
├── html_parser.py          # Full parser for conversion (creates AST blocks)
├── statistics.py           # Lightweight scanner (read-only analysis)
└── transform.py            # AST to Notion blocks conversion
```

**Statistics Scanner (`statistics.py`)**:
- **Purpose**: Read-only analysis of HTML structure
- **What it does**: 
  - Scans HTML files directly
  - Counts structural elements (tables, layouts)
  - No AST creation
  - No block conversion
  - No Notion API calls
- **Dependencies**: Only BeautifulSoup for HTML parsing
- **Output**: JSON statistics

**Benefits**:
- ✅ **Zero coupling** with conversion logic
- ✅ **Fast** - no need to create AST or blocks
- ✅ **Independent** - can add new statistics without touching parser
- ✅ **Simple** - just counts HTML elements
- ✅ **Testable** - easy to test in isolation
- ✅ **Maintainable** - changes to parser don't affect statistics

### Option B: Use Existing Parser (NOT RECOMMENDED) ❌

```
Statistics would call parse_html_file() for each file
→ Creates full AST
→ Processes all elements
→ Converts to blocks (unused)
→ Then counts things
```

**Problems**:
- ❌ **Overhead** - Full parsing for just counting
- ❌ **Coupling** - Statistics depends on parser implementation
- ❌ **Brittle** - Parser changes could break statistics
- ❌ **Slow** - Unnecessary AST/block creation
- ❌ **Complex** - Harder to add new statistics

---

## Implementation: Separate Statistics Scanner

### `src/statistics.py` Structure:

```python
"""
Lightweight HTML statistics scanner.
Completely separate from conversion parser.
"""

from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from collections import defaultdict


def scan_html_statistics(source_dir: Path) -> Dict[str, Any]:
    """
    Scan HTML files and collect statistics.
    
    This is a READ-ONLY operation - no conversion, no AST creation.
    Just counts structural elements in HTML.
    
    Args:
        source_dir: Directory containing HTML files
        
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
            'rowspan_count': 0,
            'details': []  # Per-table details
        },
        'layouts': {
            'total': 0,
            'by_type': defaultdict(int),
            'details': []  # Per-layout details
        }
    }
    
    html_files = list(source_dir.rglob('*.html'))
    stats['total_files'] = len(html_files)
    
    for html_file in html_files:
        file_stats = analyze_single_file(html_file)
        
        # Aggregate table statistics
        stats['tables']['total'] += file_stats['tables']['count']
        stats['tables']['with_merged_cells'] += file_stats['tables']['with_merged']
        stats['tables']['merged_cell_count'] += file_stats['tables']['merged_total']
        stats['tables']['colspan_count'] += file_stats['tables']['colspan_total']
        stats['tables']['rowspan_count'] += file_stats['tables']['rowspan_total']
        
        # Aggregate layout statistics
        stats['layouts']['total'] += file_stats['layouts']['count']
        for layout_type, count in file_stats['layouts']['by_type'].items():
            stats['layouts']['by_type'][layout_type] += count
    
    return stats


def analyze_single_file(html_file: Path) -> Dict[str, Any]:
    """
    Analyze a single HTML file for statistics.
    
    This function ONLY reads HTML structure - no conversion logic.
    """
    with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
        soup = BeautifulSoup(f.read(), 'lxml')
    
    file_stats = {
        'file': html_file.name,
        'tables': {
            'count': 0,
            'with_merged': 0,
            'merged_total': 0,
            'colspan_total': 0,
            'rowspan_total': 0
        },
        'layouts': {
            'count': 0,
            'by_type': defaultdict(int)
        }
    }
    
    # Count tables and merged cells
    tables = soup.find_all('table')
    file_stats['tables']['count'] = len(tables)
    
    for table in tables:
        has_merged = False
        colspan_count = 0
        rowspan_count = 0
        
        for td in table.find_all(['td', 'th']):
            colspan = int(td.get('colspan', 1))
            rowspan = int(td.get('rowspan', 1))
            
            if colspan > 1:
                has_merged = True
                colspan_count += 1
            if rowspan > 1:
                has_merged = True
                rowspan_count += 1
        
        if has_merged:
            file_stats['tables']['with_merged'] += 1
            file_stats['tables']['merged_total'] += colspan_count + rowspan_count
            file_stats['tables']['colspan_total'] += colspan_count
            file_stats['tables']['rowspan_total'] += rowspan_count
    
    # Count columnLayout divs
    layouts = soup.find_all('div', class_=lambda x: x and 'columnLayout' in x)
    file_stats['layouts']['count'] = len(layouts)
    
    for layout in layouts:
        layout_type = layout.get('data-layout', 'unknown')
        file_stats['layouts']['by_type'][layout_type] += 1
    
    return file_stats
```

---

## Key Differences: Statistics vs Parser

| Aspect | Statistics Scanner | HTML Parser |
|--------|-------------------|-------------|
| **Purpose** | Read-only analysis | Full conversion |
| **Output** | JSON statistics | AST blocks |
| **Dependencies** | BeautifulSoup only | BeautifulSoup + all parsers |
| **Speed** | Fast (just counting) | Slower (full processing) |
| **Complexity** | Simple | Complex |
| **Coupling** | None | High (depends on many modules) |
| **Extensibility** | Easy to add new stats | Harder (affects conversion) |

---

## Adding New Statistics Attributes

### With Separate Scanner (Easy) ✅:

```python
# Just add new counting logic in statistics.py
def analyze_single_file(html_file: Path) -> Dict[str, Any]:
    # ... existing code ...
    
    # NEW: Count code blocks
    code_blocks = soup.find_all(['pre', 'code'])
    file_stats['code_blocks'] = len(code_blocks)
    
    # NEW: Count images
    images = soup.find_all('img')
    file_stats['images'] = len(images)
    
    # NEW: Count links
    links = soup.find_all('a', href=True)
    file_stats['links'] = len(links)
    
    return file_stats
```

**No impact on**:
- HTML parser
- Transform logic
- Conversion flow
- Existing statistics

### With Coupled Parser (Hard) ❌:

```python
# Would need to modify parse_html_file()
# → Risk breaking conversion
# → Need to understand full parser logic
# → Slower (full parsing)
# → Harder to test
```

---

## Example: Adding "Code Block Count" Statistics

### Separate Scanner Approach:

```python
# src/statistics.py - Just add this:
code_blocks = soup.find_all(['pre', 'code'])
stats['code_blocks'] = len(code_blocks)
```

**Impact**: None on other code ✅

### Coupled Approach:

```python
# Would need to:
# 1. Modify parse_html_file() to track code blocks
# 2. Ensure it doesn't break conversion
# 3. Test full import flow
# 4. Risk introducing bugs
```

**Impact**: High risk, affects conversion ❌

---

## Conclusion

**Keep Statistics Completely Separate** because:

1. ✅ **Zero Coupling** - No dependencies on conversion logic
2. ✅ **Easy to Extend** - Add new statistics without touching parser
3. ✅ **Fast** - No unnecessary AST/block creation
4. ✅ **Simple** - Just HTML structure analysis
5. ✅ **Maintainable** - Changes isolated to one file
6. ✅ **Testable** - Easy to test independently

**Architecture**:
```
Statistics Scanner (statistics.py)
    ↓ (reads HTML)
    ↓ (counts elements)
    ↓ (returns JSON)
Statistics Display

HTML Parser (html_parser.py)
    ↓ (reads HTML)
    ↓ (creates AST)
    ↓ (converts to blocks)
Notion Import
```

**No shared code, no coupling, clean separation!** ✅



