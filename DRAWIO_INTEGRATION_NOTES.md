# Draw.io Integration for Confluence → Notion Import

## What We've Implemented

### 1. Draw.io Detection
- **DrawioConverter** with Confluence-specific patterns:
  - Detects `.drawio`, `.drawio.png`, `.drawio.svg` files
  - Finds embedded diagrams in HTML with `mxfile` or `mxGraphModel` tags
  - Recognizes Confluence-specific `ac:structured-macro` tags
  - Scans attachment references with `ri:attachment` tags

### 2. Export Scanning
- **DrawioScanner** that:
  - Scans entire Confluence export directory
  - Finds all HTML files and their Draw.io references
  - Maps diagrams to their source HTML files
  - Attempts to locate actual attachment files

### 3. Notion Integration
- Automatically inserts Draw.io diagrams into imported pages:
  - Adds a "📊 Draw.io Diagrams" section
  - Creates image blocks for converted diagrams
  - Adds placeholder callouts for unconverted diagrams
  - Preserves original filenames as captions

### 4. Import Flow Updates
- Integrated into main import process:
  1. Scans for Draw.io content after media inventory
  2. Prepares diagrams (extracts XML for now)
  3. Associates diagrams with their HTML pages
  4. Inserts diagram blocks during page import

## How It Works

1. **During Import Initialization**:
   ```
   Scanning for Draw.io diagrams...
   Found 3 Draw.io diagram(s) in 2 file(s)
   Prepared 3 diagram(s) for import
   ```

2. **During Page Import**:
   ```
   - page1.html -> Page Title (45 blocks, 5 images)
     + 2 Draw.io diagram(s)
   ```

3. **In Notion Page**:
   - Regular content
   - ---
   - ## 📊 Draw.io Diagrams
   - [Diagram placeholder or image]
   - Caption: "Draw.io diagram: architecture.drawio"

## What's Not Implemented Yet

### Actual PNG Conversion
The current implementation:
- Extracts Draw.io XML data
- Saves it as `.xml` file
- Returns `success=False` for conversion

To complete this, you would need one of:
1. **Draw.io Export API** (recommended)
2. **Headless Browser** with draw.io
3. **drawio-cli** tool
4. **External conversion service**

## Testing

Use the test script:
```bash
python test_drawio_detection.py /path/to/confluence/export
```

This will:
- Show all detected Draw.io content
- Indicate if attachment files exist
- Test the preparation process
- Show created files

## File Structure

```
src/processors/
├── converters.py          # Base converter infrastructure
├── drawio_converter.py    # Draw.io specific converter
├── drawio_scanner.py      # Confluence export scanner
└── media_processor.py     # Updated with conversion support
```

## Next Steps

1. **Implement PNG Conversion**:
   - Choose conversion method (API, CLI, etc.)
   - Update `_convert_diagram_to_image()` method
   - Handle conversion errors gracefully

2. **Enhance Detection**:
   - Support more Confluence macro variations
   - Handle inline SVG diagrams
   - Detect Gliffy and other diagram types

3. **Upload Integration**:
   - Upload converted PNGs using existing upload strategies
   - Update image URLs in blocks before Notion import

## Configuration

No additional configuration needed currently. Future options could include:
- `convert_drawio`: Enable/disable conversion (default: true)
- `drawio_api_url`: Custom Draw.io export API endpoint
- `drawio_output_format`: PNG, SVG, or PDF
- `drawio_max_size`: Maximum output dimensions








