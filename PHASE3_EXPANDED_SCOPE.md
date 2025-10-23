# Phase 3 Expanded Scope: Media & Attachment Processor

## 🚨 Scope Expansion Analysis

You're right - limiting Phase 3 to just images is too narrow. Confluence exports contain many file types that need different handling strategies.

## 📁 File Types in Confluence Exports

### 1. **Images** (Current Focus)
- `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`
- `.ico` (icons), `.bmp`, `.tiff`

### 2. **Documents** (Not Currently Handled)
- `.pdf` - Can be embedded or linked
- `.doc`, `.docx` - Word documents
- `.xls`, `.xlsx` - Excel spreadsheets
- `.ppt`, `.pptx` - PowerPoint presentations
- `.txt`, `.rtf` - Text files

### 3. **Archives** (Not Currently Handled)
- `.zip`, `.tar`, `.gz`, `.7z`
- `.rar` (if supported)

### 4. **Code/Data Files** (Not Currently Handled)
- `.json`, `.xml`, `.yaml`, `.csv`
- `.sql`, `.py`, `.js`, `.java`, etc.
- `.log` files

### 5. **Media Files** (Not Currently Handled)
- `.mp4`, `.avi`, `.mov` - Videos
- `.mp3`, `.wav`, `.ogg` - Audio
- `.webm` - Web media

### 6. **Diagrams/Special** (Not Currently Handled)
- `.drawio`, `.dio` - draw.io files
- `.vsd`, `.vsdx` - Visio files
- `.graffle` - OmniGraffle
- `.puml` - PlantUML source

## 🎯 Revised Phase 3: Media & Attachment Processor

### Core Architecture

```python
@dataclass
class MediaItem:
    """Represents any media/attachment"""
    source_path: Path
    media_type: MediaType
    mime_type: str
    size: int
    metadata: Dict[str, Any]
    
@dataclass 
class ProcessedMedia:
    """Result of processing"""
    notion_block_type: str  # 'image', 'file', 'embed', 'video', 'audio'
    upload_url: Optional[str]
    thumbnail_url: Optional[str]
    converted_items: List[ConvertedItem]  # e.g., PDF pages as images
    metadata: Dict[str, Any]

class MediaProcessor:
    """Central processor for all media types"""
    
    def scan_directory(self, path: Path) -> MediaInventory:
        """Scan and categorize all files"""
        
    def process_item(self, item: MediaItem) -> ProcessedMedia:
        """Process based on type"""
        
    def get_notion_block(self, item: ProcessedMedia) -> Dict:
        """Generate appropriate Notion block"""
```

### Processing Strategies by Type

```python
# 1. Images
ImageStrategy:
    - Current image processing
    - SVG → PNG conversion
    - Thumbnail generation
    - EXIF data extraction

# 2. PDFs
PDFStrategy:
    - Option 1: Upload as file attachment
    - Option 2: Convert to images (first page preview)
    - Option 3: Extract text for searchability
    - Extract metadata (title, author)

# 3. Office Documents
OfficeStrategy:
    - Upload as file attachment
    - Generate preview thumbnail
    - Extract metadata
    - Optional: Convert to PDF

# 4. Archives
ArchiveStrategy:
    - Upload as file attachment
    - List contents in description
    - Calculate compressed/uncompressed size

# 5. Code/Data
CodeStrategy:
    - Small files: Embed as code blocks
    - Large files: Upload as attachment
    - Syntax highlighting for code blocks

# 6. Media
MediaStrategy:
    - Video: Upload with thumbnail
    - Audio: Upload with metadata
    - Streaming considerations

# 7. Diagrams
DiagramStrategy:
    - .drawio → Render to PNG + keep source
    - .puml → Render to PNG + embed source
    - .vsd → Convert if possible or upload raw
```

### Notion Block Mapping

```python
MEDIA_TO_NOTION_BLOCK = {
    MediaType.IMAGE: 'image',
    MediaType.PDF: 'file',  # or 'embed' if Notion supports
    MediaType.DOCUMENT: 'file',
    MediaType.ARCHIVE: 'file',
    MediaType.VIDEO: 'video',  # if supported, else 'file'
    MediaType.AUDIO: 'audio',  # if supported, else 'file'
    MediaType.CODE: 'code',  # if small, else 'file'
    MediaType.DIAGRAM: 'image',  # rendered version
}
```

### Statistics & Reporting

```python
@dataclass
class MediaInventory:
    """Complete inventory of found media"""
    total_count: int
    total_size: int
    by_type: Dict[MediaType, List[MediaItem]]
    
    def get_summary(self) -> str:
        """
        Media Inventory Summary:
        - Images: 45 files (23.5 MB)
          - PNG: 30 (15 MB)
          - SVG: 10 (500 KB) [needs conversion]
          - GIF: 5 (8 MB)
        - Documents: 12 files (45 MB)
          - PDF: 8 (40 MB)
          - DOCX: 4 (5 MB)
        - Archives: 3 files (120 MB)
        - Code: 25 files (2 MB)
        Total: 85 files (190.5 MB)
        """
```

## 🔄 Implementation Approach

### Option A: Minimal Phase 3 (4-5 hours)
- Extract current image logic to processor
- Add basic file detection/counting
- Keep same functionality, better structure
- Foundation for future expansion

### Option B: Medium Phase 3 (8-10 hours)
- Minimal + SVG conversion
- Basic file attachment support
- Media inventory/statistics
- Smart emoji/icon filtering

### Option C: Full Phase 3 (15-20 hours)
- Complete media processor
- All file type strategies
- Preview generation
- Format conversions
- Full statistics

## 📊 Complexity Analysis

### Added Complexity:
1. **File Type Detection** - Need robust MIME type detection
2. **Storage Strategy** - Different handling per type
3. **Conversion Pipeline** - Multiple converters needed
4. **Preview Generation** - Thumbnails for non-images
5. **Notion Block Types** - Different blocks for different media

### Mitigation Strategy:
1. **Plugin Architecture** - Each handler as a plugin
2. **Progressive Enhancement** - Start basic, add handlers
3. **Configuration Driven** - Enable/disable features
4. **Async Ready** - Prepare for parallel processing

## 🎯 Recommendation

### Split Phase 3 into Sub-phases:

**Phase 3.1: Core Media Processor** (Current Phase 3)
- Extract image logic
- Create processor architecture  
- Add media scanning/inventory
- Basic file support

**Phase 3.2: Advanced Handlers** (New Phase)
- SVG conversion
- PDF handling
- Office document support
- Archive handling

**Phase 3.3: Converters & Renderers** (New Phase)
- Diagram rendering
- Preview generation
- Format conversions
- Optimization

This keeps Phase 3 manageable while setting up for comprehensive media handling.

