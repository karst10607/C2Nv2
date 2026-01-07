"""Scanner for finding and processing Draw.io diagrams in Confluence exports"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .drawio_converter import DrawioConverter
from .converters import ConversionFormat
from ..models.logger import logger


@dataclass
class DrawioDiagram:
    """Represents a found Draw.io diagram"""
    html_file: Path  # The HTML file that references this diagram
    filename: str    # Original filename
    source_path: Optional[Path] = None  # Path to actual file (if found)
    is_embedded: bool = False  # Whether it's embedded in HTML
    converted_path: Optional[Path] = None  # Path to converted PNG
    notion_ready: bool = False  # Whether it's ready for Notion upload


class DrawioScanner:
    """Scans Confluence exports for Draw.io diagrams and prepares them for Notion"""
    
    def __init__(self):
        self.converter = DrawioConverter()
        
    def scan_export(self, export_dir: Path) -> Dict[Path, List[DrawioDiagram]]:
        """
        Scan entire Confluence export for Draw.io content.
        
        Returns dict mapping HTML files to their Draw.io diagrams.
        """
        diagrams_by_file = {}
        
        # Find all HTML files
        html_files = list(export_dir.glob("*.html"))
        logger.info(f"Scanning {len(html_files)} HTML files for Draw.io content")
        
        for html_file in html_files:
            diagrams = self._scan_html_file(html_file)
            if diagrams:
                diagrams_by_file[html_file] = diagrams
                logger.info(f"Found {len(diagrams)} Draw.io diagram(s) in {html_file.name}")
                
        return diagrams_by_file
    
    def _scan_html_file(self, html_path: Path) -> List[DrawioDiagram]:
        """Scan a single HTML file for Draw.io references"""
        diagrams = []
        
        # Use converter to find attachments
        found_items = self.converter.find_drawio_attachments(html_path)
        
        for item in found_items:
            diagram = DrawioDiagram(
                html_file=html_path,
                filename=item['filename'],
                source_path=item.get('attachment_path'),
                is_embedded=item.get('in_html', False)
            )
            diagrams.append(diagram)
            
        return diagrams
    
    def prepare_for_notion(self, diagrams_by_file: Dict[Path, List[DrawioDiagram]], 
                          output_dir: Optional[Path] = None) -> int:
        """
        Prepare Draw.io diagrams for Notion import.
        
        For now, this extracts the diagram data and marks them.
        Future: Actually convert to PNG.
        
        Returns number of diagrams prepared.
        """
        total_prepared = 0
        
        for html_file, diagrams in diagrams_by_file.items():
            for diagram in diagrams:
                if self._prepare_diagram(diagram, output_dir):
                    total_prepared += 1
                    
        logger.info(f"Prepared {total_prepared} Draw.io diagrams for Notion")
        return total_prepared
    
    def _prepare_diagram(self, diagram: DrawioDiagram, output_dir: Optional[Path] = None) -> bool:
        """
        Prepare a single diagram for Notion.
        
        For now: Extract and save XML
        Future: Convert to PNG
        """
        try:
            if diagram.is_embedded:
                # For embedded diagrams, we need to extract from HTML
                logger.info(f"Processing embedded Draw.io diagram in {diagram.html_file.name}")
                # The converter will extract the XML
                if diagram.html_file:
                    result = self.converter.convert(
                        diagram.html_file, 
                        ConversionFormat.PNG,
                        output_dir
                    )
                    if result.success and result.output_path:
                        diagram.converted_path = result.output_path
                        diagram.notion_ready = True
                        return True
            elif diagram.source_path and diagram.source_path.exists():
                # For file attachments
                logger.info(f"Processing Draw.io file: {diagram.filename}")
                result = self.converter.convert(
                    diagram.source_path,
                    ConversionFormat.PNG,
                    output_dir
                )
                if result.success and result.output_path:
                    diagram.converted_path = result.output_path
                    diagram.notion_ready = True
                    return True
            else:
                logger.warning(f"Draw.io file not found: {diagram.filename}")
                
        except Exception as e:
            logger.error(f"Failed to prepare diagram {diagram.filename}: {e}")
            
        return False
    
    def get_notion_blocks_for_diagrams(self, diagrams: List[DrawioDiagram]) -> List[Dict]:
        """
        Generate Notion blocks for Draw.io diagrams.
        
        These blocks can be inserted into the page where the diagram was referenced.
        """
        blocks = []
        
        for diagram in diagrams:
            if diagram.notion_ready and diagram.converted_path:
                # Create an image block for the diagram
                block = {
                    'type': 'image',
                    'image': {
                        'type': 'file',
                        'file': {
                            'url': str(diagram.converted_path),  # Will be replaced with uploaded URL
                            'expiry_time': None
                        }
                    }
                }
                blocks.append(block)
                
                # Add a caption with the original filename
                caption_block = {
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [{
                            'type': 'text',
                            'text': {
                                'content': f'Draw.io diagram: {diagram.filename}'
                            }
                        }]
                    }
                }
                blocks.append(caption_block)
            else:
                # Add a placeholder for diagrams that couldn't be converted
                placeholder_block = {
                    'type': 'callout',
                    'callout': {
                        'rich_text': [{
                            'type': 'text',
                            'text': {
                                'content': f'⚠️ Draw.io diagram not converted: {diagram.filename}'
                            }
                        }],
                        'icon': {
                            'emoji': '📊'
                        }
                    }
                }
                blocks.append(placeholder_block)
                
        return blocks










