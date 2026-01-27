# Markdown Export Design Decisions

## Overview

This document explains the design choices for the GitHub Markdown export feature.

## Problem Statement

When exporting Confluence HTML to Markdown for GitHub/Obsidian:
1. Confluence page filenames are long serial numbers (e.g., `123456789.html`)
2. Each page may have multiple images/attachments
3. Need to work in both GitHub and Obsidian
4. Repository should stay organized and not look bloated

## Options Considered

### Option A: Flat Structure with Shared Assets
```
docs/
├── 123456789.md
├── 234567890.md
└── assets/
    ├── image1.png
    └── image2.png
```

**Pros:**
- Simple structure
- Single assets folder

**Cons:**
- MD filenames are ugly serial numbers
- Hard to know which images belong to which page
- Potential filename collisions in shared assets folder

---

### Option B: Nested Folders with Page Titles ✅ CHOSEN
```
docs/
├── Database-Design/
│   ├── README.md
│   └── assets/
│       └── diagram.png
├── API-Reference/
│   ├── README.md
│   └── assets/
│       └── screenshot.png
```

**Pros:**
- Human-readable folder names (uses page title, not ID)
- Each page is self-contained
- GitHub auto-displays README.md when navigating to folder
- Easy to move/delete individual pages
- No asset filename collisions between pages
- Works in both Obsidian and GitHub

**Cons:**
- More folders in the directory
- Need to sanitize folder names for special characters

---

### Option C: Separate Assets Directory
```
docs/
├── page1.md
└── .assets/
    └── page1/
        └── image.png
```

**Pros:**
- Assets separated from content

**Cons:**
- Complex relative paths (`../.assets/page/image.png`)
- Paths break easily if files are moved
- Not self-contained

---

## Why We Chose Option B

1. **Human-Readable**: Folder names use the actual page title instead of Confluence IDs
2. **Self-Contained**: Each page folder has everything it needs
3. **GitHub-Friendly**: README.md is auto-displayed as folder homepage
4. **Obsidian-Compatible**: Standard markdown syntax works in Obsidian
5. **Maintainable**: Easy to add, remove, or reorganize pages
6. **No Collisions**: Assets are isolated per-page

## Folder Naming Rules

To ensure compatibility across operating systems:

| Rule | Example |
|------|---------|
| Replace `/\:*?"<>\|#` with `-` | `Q&A: Setup?` → `QA-Setup` |
| Replace spaces with `-` | `My Page` → `My-Page` |
| Truncate to 100 characters | Long titles are shortened |
| Handle duplicates | `Overview`, `Overview-2`, `Overview-3` |
| Preserve Unicode | `システム設計` → `システム設計` (kept as-is) |

## Image Syntax Trade-off

| Syntax | GitHub | Obsidian | Size Control |
|--------|--------|----------|--------------|
| `![alt](path)` | ✅ | ✅ | ❌ |
| `<img width="600">` | ✅ | ❌ | ✅ |

**Decision**: Use standard `![alt](path)` for maximum compatibility. Accept that images may appear at full size. For tables with complex content, use HTML (GitHub-only).

## File Structure

```
output/
├── Page-Title-1/
│   ├── README.md           # Page content with title as H1
│   └── assets/
│       ├── image1.png
│       └── diagram.png
├── Page-Title-2/
│   ├── README.md
│   └── assets/
│       └── screenshot.png
└── _index.md               # Optional: links to all pages
```

## Usage

```bash
# CLI
python -m src.markdown_exporter \
  --source-dir /path/to/confluence/export \
  --output-dir /path/to/output \
  --nested-folders

# Or use the GUI: "Export to Markdown" button
```

## Date

Decision made: January 2026
