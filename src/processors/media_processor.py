"""
Core Media Processor for handling all media types in Notion Importer
Phase 3.1: Foundation with image support, extensible for other media types
"""
import mimetypes
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bs4 import Tag

from ..constants import MAX_COLUMNS_PER_ROW
from ..models import ErrorCode, NotionImporterError


class MediaType(Enum):
    """Supported media types"""
    IMAGE = auto()
    DOCUMENT = auto()
    SPREADSHEET = auto()
    PRESENTATION = auto()
    PDF = auto()
    ARCHIVE = auto()
    VIDEO = auto()
    AUDIO = auto()
    CODE = auto()
    DIAGRAM = auto()
    UNKNOWN = auto()


@dataclass
class MediaItem:
    """Represents a media item found in the source"""
    source_path: Path
    relative_path: str  # Relative to source directory
    media_type: MediaType
    mime_type: str
    size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_element: Optional['Tag'] = None  # HTML element if from parser


@dataclass
class ProcessedMedia:
    """Result of processing a media item"""
    notion_block_type: str  # 'image', 'file', 'embed', 'video', 'audio', 'code'
    upload_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    filename: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class MediaInventory:
    """Complete inventory of all media found"""
    total_count: int = 0
    total_size: int = 0
    by_type: Dict[MediaType, List[MediaItem]] = field(default_factory=dict)
    skipped_count: int = 0
    
    def add_item(self, item: MediaItem) -> None:
        """Add item to inventory"""
        self.total_count += 1
        self.total_size += item.size
        
        if item.media_type not in self.by_type:
            self.by_type[item.media_type] = []
        self.by_type[item.media_type].append(item)
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        lines = ["Media Inventory Summary:"]
        lines.append(f"Total: {self.total_count} files ({self._format_size(self.total_size)})")
        
        for media_type, items in sorted(self.by_type.items(), key=lambda x: x[0].name):
            if items:
                type_size = sum(item.size for item in items)
                lines.append(f"- {media_type.name.title()}: {len(items)} files ({self._format_size(type_size)})")
                
                # Show breakdown for images
                if media_type == MediaType.IMAGE:
                    ext_counts = {}
                    for item in items:
                        ext = Path(item.source_path).suffix.lower()
                        ext_counts[ext] = ext_counts.get(ext, 0) + 1
                    for ext, count in sorted(ext_counts.items()):
                        lines.append(f"  {ext}: {count}")
        
        if self.skipped_count > 0:
            lines.append(f"\nSkipped: {self.skipped_count} items (UI elements, icons, etc.)")
        
        return "\n".join(lines)
    
    def _format_size(self, size: int) -> str:
        """Format size in human-readable form"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class MediaHandler(ABC):
    """Abstract base class for media type handlers"""
    
    @abstractmethod
    def can_handle(self, item: MediaItem) -> bool:
        """Check if this handler can process the item"""
        pass
    
    @abstractmethod
    def process(self, item: MediaItem, context: Dict[str, Any]) -> ProcessedMedia:
        """Process the media item"""
        pass
    
    @abstractmethod
    def get_notion_block_type(self) -> str:
        """Return the Notion block type for this media"""
        pass


class ImageHandler(MediaHandler):
    """Handler for image files"""
    
    SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico', '.tiff'}
    
    def can_handle(self, item: MediaItem) -> bool:
        """Check if this is an image we can handle"""
        ext = Path(item.source_path).suffix.lower()
        return item.media_type == MediaType.IMAGE or ext in self.SUPPORTED_EXTENSIONS
    
    def process(self, item: MediaItem, context: Dict[str, Any]) -> ProcessedMedia:
        """Process image - for now just pass through"""
        # TODO: In phase 3.2+, add SVG conversion, optimization, etc.
        return ProcessedMedia(
            notion_block_type='image',
            filename=Path(item.source_path).name,
            metadata={
                'width': item.metadata.get('width'),
                'height': item.metadata.get('height'),
                'format': Path(item.source_path).suffix.lower()
            }
        )
    
    def get_notion_block_type(self) -> str:
        return 'image'


class MediaProcessor:
    """Central processor for all media types"""
    
    # File extension to MediaType mapping
    EXTENSION_MAP = {
        # Images
        '.png': MediaType.IMAGE,
        '.jpg': MediaType.IMAGE,
        '.jpeg': MediaType.IMAGE,
        '.gif': MediaType.IMAGE,
        '.webp': MediaType.IMAGE,
        '.svg': MediaType.IMAGE,
        '.bmp': MediaType.IMAGE,
        '.ico': MediaType.IMAGE,
        '.tiff': MediaType.IMAGE,
        
        # Documents
        '.pdf': MediaType.PDF,
        '.doc': MediaType.DOCUMENT,
        '.docx': MediaType.DOCUMENT,
        '.odt': MediaType.DOCUMENT,
        '.rtf': MediaType.DOCUMENT,
        '.txt': MediaType.DOCUMENT,
        
        # Spreadsheets
        '.xls': MediaType.SPREADSHEET,
        '.xlsx': MediaType.SPREADSHEET,
        '.csv': MediaType.SPREADSHEET,
        '.ods': MediaType.SPREADSHEET,
        
        # Presentations
        '.ppt': MediaType.PRESENTATION,
        '.pptx': MediaType.PRESENTATION,
        '.odp': MediaType.PRESENTATION,
        
        # Archives
        '.zip': MediaType.ARCHIVE,
        '.tar': MediaType.ARCHIVE,
        '.gz': MediaType.ARCHIVE,
        '.7z': MediaType.ARCHIVE,
        '.rar': MediaType.ARCHIVE,
        
        # Media
        '.mp4': MediaType.VIDEO,
        '.avi': MediaType.VIDEO,
        '.mov': MediaType.VIDEO,
        '.webm': MediaType.VIDEO,
        '.mp3': MediaType.AUDIO,
        '.wav': MediaType.AUDIO,
        '.ogg': MediaType.AUDIO,
        
        # Code/Data
        '.json': MediaType.CODE,
        '.xml': MediaType.CODE,
        '.yaml': MediaType.CODE,
        '.yml': MediaType.CODE,
        '.py': MediaType.CODE,
        '.js': MediaType.CODE,
        '.java': MediaType.CODE,
        '.cpp': MediaType.CODE,
        '.sql': MediaType.CODE,
        
        # Diagrams
        '.drawio': MediaType.DIAGRAM,
        '.dio': MediaType.DIAGRAM,
        '.vsd': MediaType.DIAGRAM,
        '.vsdx': MediaType.DIAGRAM,
        '.puml': MediaType.DIAGRAM,
        '.plantuml': MediaType.DIAGRAM,
    }
    
    def __init__(self):
        """Initialize with available handlers"""
        self.handlers: List[MediaHandler] = [
            ImageHandler()
            # Future: DocumentHandler(), VideoHandler(), etc.
        ]
        
        # Initialize mimetypes
        mimetypes.init()
    
    def scan_directory(self, source_dir: Path, extensions: Optional[Set[str]] = None) -> MediaInventory:
        """
        Scan directory for all media files
        
        Args:
            source_dir: Directory to scan
            extensions: Optional set of extensions to filter (e.g., {'.png', '.jpg'})
        
        Returns:
            MediaInventory with all found media
        """
        inventory = MediaInventory()
        
        if not source_dir.exists() or not source_dir.is_dir():
            return inventory
        
        # Scan all files recursively
        for file_path in source_dir.rglob('*'):
            if file_path.is_file():
                # Skip if extension filter provided and doesn't match
                if extensions and file_path.suffix.lower() not in extensions:
                    continue
                
                try:
                    item = self._create_media_item(file_path, source_dir)
                    inventory.add_item(item)
                except Exception:
                    # Skip files we can't process
                    continue
        
        return inventory
    
    def process_html_image(self, img_element: 'Tag', source_dir: Path) -> Optional[MediaItem]:
        """
        Process an image element from HTML parser
        
        Args:
            img_element: BeautifulSoup img tag
            source_dir: Base directory for relative paths
        
        Returns:
            MediaItem if valid, None if should skip
        """
        # Import here to avoid circular dependency
        from ..image_utils import extract_image_src, should_skip_image
        
        src = extract_image_src(img_element)
        if not src:
            return None
        
        # Check if we should skip this image
        if should_skip_image(img_element, src):
            return None
        
        # Handle relative paths
        if not src.startswith(('http://', 'https://')):
            file_path = source_dir / src
            if file_path.exists():
                item = self._create_media_item(file_path, source_dir)
                item.source_element = img_element
                return item
        
        # For remote images, create item without local file
        return MediaItem(
            source_path=Path(src),
            relative_path=src,
            media_type=MediaType.IMAGE,
            mime_type='image/unknown',
            metadata={'remote': True},
            source_element=img_element
        )
    
    def process_item(self, item: MediaItem, context: Dict[str, Any]) -> ProcessedMedia:
        """
        Process a media item using appropriate handler
        
        Args:
            item: Media item to process
            context: Processing context (upload strategy, etc.)
        
        Returns:
            ProcessedMedia with results
        """
        # Find appropriate handler
        for handler in self.handlers:
            if handler.can_handle(item):
                return handler.process(item, context)
        
        # No handler found - return as generic file
        return ProcessedMedia(
            notion_block_type='file',
            filename=Path(item.source_path).name,
            error=f"No handler for {item.media_type.name} files"
        )
    
    def count_images_in_blocks(self, blocks: List[Dict[str, Any]]) -> int:
        """
        Count total images in a list of blocks (including nested in column_list)
        Replaces the function in importer.py
        """
        count = 0
        for block in blocks:
            if block.get('type') == 'image':
                count += 1
            elif block.get('type') == 'column_list':
                for col in block.get('column_list', {}).get('children', []):
                    for child in col.get('column', {}).get('children', []):
                        if child.get('type') == 'image':
                            count += 1
        return count
    
    def extract_images_from_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract all image blocks for processing"""
        images = []
        
        for block in blocks:
            if block.get('type') == 'image':
                images.append(block)
            elif block.get('type') == 'column_list':
                for col in block.get('column_list', {}).get('children', []):
                    for child in col.get('column', {}).get('children', []):
                        if child.get('type') == 'image':
                            images.append(child)
        
        return images
    
    def _create_media_item(self, file_path: Path, source_dir: Path) -> MediaItem:
        """Create MediaItem from file path"""
        stat = file_path.stat()
        ext = file_path.suffix.lower()
        
        # Determine media type
        media_type = self.EXTENSION_MAP.get(ext, MediaType.UNKNOWN)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Calculate relative path
        try:
            relative_path = file_path.relative_to(source_dir)
        except ValueError:
            relative_path = file_path
        
        return MediaItem(
            source_path=file_path,
            relative_path=str(relative_path),
            media_type=media_type,
            mime_type=mime_type,
            size=stat.st_size,
            metadata={
                'modified': stat.st_mtime,
                'created': stat.st_ctime if hasattr(stat, 'st_ctime') else stat.st_mtime
            }
        )
    
    def get_notion_block_type(self, media_type: MediaType) -> str:
        """Get appropriate Notion block type for media type"""
        mapping = {
            MediaType.IMAGE: 'image',
            MediaType.VIDEO: 'video',
            MediaType.AUDIO: 'audio',
            MediaType.CODE: 'code',  # For small code files
            # Everything else is 'file'
            MediaType.DOCUMENT: 'file',
            MediaType.SPREADSHEET: 'file',
            MediaType.PRESENTATION: 'file',
            MediaType.PDF: 'file',
            MediaType.ARCHIVE: 'file',
            MediaType.DIAGRAM: 'file',
            MediaType.UNKNOWN: 'file'
        }
        return mapping.get(media_type, 'file')
