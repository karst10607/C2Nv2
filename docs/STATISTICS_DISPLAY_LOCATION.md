# Statistics Display Location

## Where Statistics Are Shown

### **Modal Dialog** 📊

Statistics are displayed in a **modal dialog** that appears when you click the **"📊 Show Statistics"** button.

### Location in UI:

1. **Button Location**: 
   - In the main configuration section
   - Between "Save Configuration" and "Start Import" buttons
   - Label: **"📊 Show Statistics"**

2. **Modal Appearance**:
   - **Overlay**: Full-screen overlay with blur effect
   - **Position**: Centered on screen
   - **Size**: 80% width, max 700px, max 80% height
   - **Style**: White background with gradient header

### Modal Structure:

```
┌─────────────────────────────────────┐
│  📊 HTML Statistics          [×]    │ ← Header (gradient purple)
├─────────────────────────────────────┤
│                                     │
│  📁 Files                          │
│    Total HTML files scanned: 147   │
│                                     │
│  📊 Tables                         │
│    Total tables: 124                │
│    Files with tables: 42            │
│    Tables with merged cells: 24     │
│    Total merged cells: 121          │
│      • Horizontal merges: 27       │
│      • Vertical merges: 94           │
│                                     │
│  📐 Side-by-Side Layouts            │
│    Total layouts: 28                │
│    Files with layouts: 10           │
│    ┌─────────┬─────────┐            │
│    │two-equal│fixed-w  │            │
│    │   11    │   17    │            │
│    └─────────┴─────────┘            │
│                                     │
└─────────────────────────────────────┘
```

### How to Access:

1. **Select Source Directory**: Choose the folder containing HTML files
2. **Click "📊 Show Statistics"**: Button in the main action area
3. **Modal Opens**: Shows loading message while scanning
4. **Results Display**: Statistics appear in formatted sections
5. **Close Modal**: Click × button or click outside modal

### Statistics Shown:

#### Files Section:
- Total HTML files scanned

#### Tables Section:
- Total tables found
- Files containing tables
- Tables with merged cells
- Total merged cells count
- Breakdown: Horizontal (colspan) vs Vertical (rowspan)

#### Side-by-Side Layouts Section:
- Total layouts found
- Files containing layouts
- Grid display of layout types:
  - `two-equal` - Two equal columns
  - `three-equal` - Three equal columns
  - `fixed-width` - Fixed width layout
  - `two-left-sidebar` - Two columns with left sidebar
  - `two-right-sidebar` - Two columns with right sidebar
  - And any other layout types found

### Visual Design:

- **Header**: Purple gradient matching app theme
- **Sections**: Clear headings with icons
- **Values**: Large, bold numbers for easy reading
- **Cards**: Layout types shown in card grid
- **Colors**: Professional gray/blue color scheme
- **Responsive**: Adapts to content, scrollable if needed

### User Experience:

- ✅ **Non-blocking**: Modal doesn't prevent other actions
- ✅ **Fast**: Statistics scan is quick (read-only)
- ✅ **Clear**: Well-organized, easy to read
- ✅ **Informative**: Shows exactly what you need to know
- ✅ **Dismissible**: Easy to close and reopen

---

## Technical Implementation

### Files Involved:

1. **`src/statistics.py`** - Statistics scanner (separate from parser)
2. **`electron/main.js`** - IPC handler for statistics
3. **`electron/preload.js`** - Exposes `getStatistics` API
4. **`electron/renderer.js`** - Button handler and display function
5. **`electron/index.html`** - Modal HTML structure
6. **`electron/styles.css`** - Modal styling

### Flow:

```
User clicks "Show Statistics"
    ↓
renderer.js: statisticsBtn click handler
    ↓
electronAPI.getStatistics(sourceDir)
    ↓
IPC: 'get-statistics' → main.js
    ↓
Spawn Python: python -m src.statistics --source-dir <dir>
    ↓
statistics.py: scan_html_statistics()
    ↓
Returns JSON statistics
    ↓
main.js: Parse JSON, return to renderer
    ↓
renderer.js: displayStatistics(stats)
    ↓
Modal displays formatted statistics
```

---

## Summary

**Statistics are displayed in a modal dialog** that:
- Opens when clicking "📊 Show Statistics" button
- Shows comprehensive statistics about tables and layouts
- Is easy to read and dismiss
- Doesn't interfere with other app functionality

The modal provides a clean, professional way to view statistics without cluttering the main interface.

