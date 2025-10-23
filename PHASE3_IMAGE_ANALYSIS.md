# Phase 3: Current Image Processing Analysis

## 🔍 Current Image Processing Logic

### 1. **Image Detection** (`html_parser.py`)
- Finds `<img>` tags in HTML
- Handles inline images within paragraphs
- Processes images in table cells
- Creates AST nodes with type: 'image' and src

### 2. **Image Filtering** (`image_utils.py`)
Current filtering logic **SKIPS**:
- Images with class containing: 'icon', 'emoticon', 'bullet'
- URLs containing: '/universal_avatar/', '/icons/', 'emoticons/', 'attachments/thumbnails/'
- All GIF files (assumed to be UI animations)

### 3. **Image Source Extraction**
- Prefers `data-image-src` over `src` attribute
- Removes query parameters (e.g., ?width=760)
- Returns normalized URL

### 4. **Supported Formats** (`upload_strategies.py`)
Current MIME type mapping:
```python
'.png': 'image/png'
'.jpg': 'image/jpeg'
'.jpeg': 'image/jpeg'
'.gif': 'image/gif'
'.webp': 'image/webp'
'.svg': 'image/svg+xml'  # ✅ SVG is mapped but...
```

## ⚠️ Current Limitations

### 1. **Icon/Emoji Support**
- **Problem**: Currently FILTERS OUT icons and emojis
- **Impact**: Confluence custom emojis are lost
- **Solution Needed**: Selective filtering - keep content emojis, skip UI icons

### 2. **SVG Support**
- **Problem**: SVG MIME type is defined but:
  - SVGs might be filtered as 'icons'
  - Notion has limited SVG support (converts to raster)
- **Solution Needed**: Convert SVG to PNG before upload

### 3. **Hidden/Embedded Content**
- **Problem**: No extraction of:
  - Hidden drawio source in `data-*` attributes
  - Embedded diagrams in comments
  - Style="display:none" content
- **Current**: Only processes visible `<img>` tags

### 4. **Diagram Support (draw.io, PlantUML, etc.)**
- **Not Supported**: No detection of:
  - `<div data-drawio-diagram="...">`
  - PlantUML source blocks
  - Mermaid diagrams
  - Other diagram-as-code formats

### 5. **Image Processing Pipeline**
- **Current**: Pass-through only (no conversion)
- **Missing**: 
  - Format conversion (SVG→PNG)
  - Thumbnail generation
  - Image optimization
  - Diagram rendering

## 🎯 Phase 3 Refactoring Plan

### Core Image Processor Features

```python
class ImageProcessor:
    """Centralized image handling with conversion support"""
    
    def process_image(self, source: ImageSource) -> ProcessedImage:
        """Main processing pipeline"""
        
    def extract_hidden_content(self, element: Tag) -> List[HiddenImage]:
        """Extract drawio, plantUML from data attributes"""
        
    def convert_format(self, image: Image, target: Format) -> Image:
        """Convert between formats (SVG→PNG, etc.)"""
        
    def should_process(self, element: Tag) -> bool:
        """Smarter filtering - keep content emojis"""
        
    def render_diagram(self, source: str, type: DiagramType) -> Image:
        """Render diagram source to image"""
```

### Proposed Architecture

```
ImageProcessor/
├── extractors/
│   ├── visible_image.py    # Current <img> extraction
│   ├── hidden_content.py   # data-* attributes
│   ├── diagram_source.py   # Code block diagrams
│   └── emoji_handler.py    # Smart emoji handling
├── converters/
│   ├── svg_to_png.py      # SVG conversion
│   ├── diagram_renderer.py # drawio/plantuml/mermaid
│   └── format_converter.py # General conversions
├── filters/
│   ├── ui_filter.py       # Skip UI elements
│   └── content_filter.py  # Keep content images/emojis
└── models/
    ├── image_source.py    # Source types
    └── processed_image.py # Output model
```

### New Capabilities to Add

1. **Smart Filtering**
   - Differentiate UI icons vs content icons
   - Keep custom emojis used in content
   - Skip only navigation/UI elements

2. **Hidden Content Extraction**
   ```html
   <!-- Drawio diagram with hidden source -->
   <img src="diagram.png" data-drawio-source="{...}">
   
   <!-- PlantUML in comments -->
   <!-- @startuml
   Alice -> Bob: Hello
   @enduml -->
   ```

3. **Format Conversion**
   - SVG → PNG (for Notion compatibility)
   - WebP → PNG (if needed)
   - Diagram source → PNG rendering

4. **Diagram Support**
   - draw.io XML → rendered PNG
   - PlantUML text → rendered PNG
   - Mermaid → rendered PNG
   - GraphViz → rendered PNG

5. **Image Optimization**
   - Resize large images
   - Compress where beneficial
   - Generate appropriate thumbnails

### Dependencies Needed

For full image processing:
- `Pillow` - Image manipulation
- `cairosvg` - SVG to PNG conversion
- `plantuml` - PlantUML rendering (optional)
- `drawio-cli` - draw.io rendering (optional)

### Migration Path

1. **Phase 3a**: Extract image logic to processor (current functionality)
2. **Phase 3b**: Add smart filtering for emojis/icons
3. **Phase 3c**: Add SVG conversion support
4. **Phase 3d**: Add hidden content extraction
5. **Phase 3e**: Add diagram rendering (optional, plugin-based)

## 📊 Impact Analysis

### What Works Now
- Basic image import (PNG, JPG, WebP)
- Tunnel/S3/CDN upload strategies
- Image verification

### What's Missing
- Content emoji preservation
- SVG support (real conversion)
- Diagram extraction/rendering
- Hidden content discovery

### User Impact
- **Current**: Users lose emojis and diagrams
- **After Phase 3**: Full fidelity import with all visual content

