"""Draw.io diagram detection and conversion to PNG."""
import re
import base64
import zlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from xml.etree import ElementTree as ET
import urllib.parse

from .converters import MediaConverter, ConversionFormat, ConversionResult, ConversionError, converter_registry
from ..models.logger import logger


class DrawioConverter(MediaConverter):
    """Converter for Draw.io diagrams embedded in HTML or as .drawio files."""
    
    def __init__(self):
        self.drawio_pattern = re.compile(
            r'<div[^>]*class="[^"]*drawio[^"]*"[^>]*>.*?</div>',
            re.DOTALL | re.IGNORECASE
        )
        self.mxfile_pattern = re.compile(
            r'<mxfile[^>]*>.*?</mxfile>',
            re.DOTALL | re.IGNORECASE
        )
        # Confluence specific patterns
        self.confluence_drawio_macro = re.compile(
            r'<ac:structured-macro[^>]*ac:name="drawio"[^>]*>.*?</ac:structured-macro>',
            re.DOTALL | re.IGNORECASE
        )
        self.confluence_attachment_ref = re.compile(
            r'<ri:attachment[^>]*ri:filename="([^"]+\.drawio(?:\.png|\.svg)?)"[^>]*/>',
            re.IGNORECASE
        )
        # Pattern for Confluence HTML export with Draw.io containers
        self.confluence_ap_container = re.compile(
            r'<div\s+class="ap-container"[^>]*id="[^"]*diagramly[^"]*"[^>]*>',
            re.IGNORECASE
        )
        # Pattern to find Draw.io attachments in href
        self.attachment_href_pattern = re.compile(
            r'href="attachments/\d+/([\w.-]+\.drawio(?:\.png|\.svg)?)"',
            re.IGNORECASE
        )
        
    def supported_input_types(self) -> list[str]:
        """Return supported file extensions."""
        return ['.drawio', '.drawio.svg', '.drawio.png', '.html', '.htm']
    
    def can_convert(self, source_path: Path, target_format: ConversionFormat) -> bool:
        """Check if file contains Draw.io content and can be converted to target format."""
        if target_format not in [ConversionFormat.PNG, ConversionFormat.JPG]:
            return False
            
        suffix = source_path.suffix.lower()
        
        # Direct .drawio files
        if suffix == '.drawio' or source_path.name.endswith('.drawio.svg'):
            return True
            
        # HTML files that might contain embedded diagrams
        if suffix in ['.html', '.htm']:
            try:
                content = source_path.read_text(encoding='utf-8', errors='ignore')
                return self._contains_drawio_diagram(content)
            except Exception:
                return False
                
        return False
    
    def convert(self, source_path: Path, target_format: ConversionFormat,
                output_dir: Optional[Path] = None) -> ConversionResult:
        """Convert Draw.io diagram to PNG format."""
        try:
            # Determine output path
            output_dir = output_dir or source_path.parent
            output_name = source_path.stem
            if output_name.endswith('.drawio'):
                output_name = output_name[:-7]  # Remove .drawio
            output_path = output_dir / f"{output_name}_diagram.{target_format.value}"
            
            # Extract diagram data
            diagram_data = self._extract_diagram_data(source_path)
            if not diagram_data:
                return ConversionResult(
                    success=False,
                    error_message=f"No Draw.io diagram found in {source_path}"
                )
            
            # Convert to image
            success = self._convert_diagram_to_image(diagram_data, output_path, target_format)
            
            if success:
                logger.info(f"Converted Draw.io diagram to {output_path}")
                return ConversionResult(
                    success=True,
                    output_path=output_path,
                    format=target_format,
                    metadata={'source_type': 'drawio', 'diagram_count': len(diagram_data)}
                )
            else:
                return ConversionResult(
                    success=False,
                    error_message="Failed to convert diagram to image"
                )
                
        except Exception as e:
            logger.error(f"Draw.io conversion failed: {e}")
            return ConversionResult(
                success=False,
                error_message=str(e)
            )
    
    def _contains_drawio_diagram(self, content: str) -> bool:
        """Check if HTML content contains Draw.io diagram."""
        return bool(self.drawio_pattern.search(content) or 
                   self.mxfile_pattern.search(content) or
                   'mxGraphModel' in content or
                   self.confluence_drawio_macro.search(content) or
                   self.confluence_attachment_ref.search(content) or
                   self.confluence_ap_container.search(content) or
                   'diagramly' in content)
    
    def find_drawio_attachments(self, html_path: Path) -> list[Dict[str, Any]]:
        """
        Find Draw.io attachments referenced in Confluence HTML export.
        
        Returns list of dicts with:
        - filename: The Draw.io filename
        - attachment_path: Full path to the attachment (if found)
        - in_html: Whether it's embedded in HTML
        """
        results = []
        
        try:
            content = html_path.read_text(encoding='utf-8', errors='ignore')
            
            # Extract the page ID from the path to find the right attachment folder
            page_id = html_path.stem  # e.g., "2753397032" from "2753397032.html"
            attachments_dir = html_path.parent / 'attachments' / page_id
            
            # Look for href references to Draw.io files
            for match in self.attachment_href_pattern.finditer(content):
                filename = match.group(1)
                if attachments_dir.exists():
                    attachment_path = attachments_dir / filename
                    if attachment_path.exists():
                        results.append({
                            'filename': filename,
                            'attachment_path': attachment_path,
                            'in_html': False
                        })
            
            # Also look for files where the display text contains "drawio"
            # Pattern: href="attachments/pageId/fileId.png">...drawio...png</a>
            drawio_display_pattern = re.compile(
                r'href="attachments/\d+/(\d+\.(?:png|svg|jpg))"[^>]*>[^<]*drawio[^<]*</a>',
                re.IGNORECASE
            )
            for match in drawio_display_pattern.finditer(content):
                filename = match.group(1)
                if attachments_dir.exists():
                    attachment_path = attachments_dir / filename
                    if attachment_path.exists() and not any(r['attachment_path'] == attachment_path for r in results):
                        results.append({
                            'filename': filename,
                            'attachment_path': attachment_path,
                            'in_html': False,
                            'is_drawio_export': True
                        })
            
            # Also look for .drawio files in the attachment directory directly
            if attachments_dir.exists():
                # Find all .drawio files
                for file_path in attachments_dir.glob('*.drawio'):
                    if not any(r['attachment_path'] == file_path for r in results):
                        results.append({
                            'filename': file_path.name,
                            'attachment_path': file_path,
                            'in_html': False
                        })
                
                # Find all .drawio.png files
                for file_path in attachments_dir.glob('*.drawio.png'):
                    if not any(r['attachment_path'] == file_path for r in results):
                        results.append({
                            'filename': file_path.name,
                            'attachment_path': file_path,
                            'in_html': False
                        })
            
            # Check if diagram is embedded in HTML (ap-container divs)
            if self.confluence_ap_container.search(content):
                # Count how many embedded diagrams
                containers = self.confluence_ap_container.findall(content)
                for idx, container in enumerate(containers):
                    results.append({
                        'filename': f"{html_path.stem}_embedded_{idx}.drawio",
                        'attachment_path': None,
                        'in_html': True,
                        'html_path': html_path,
                        'container_html': container
                    })
                
        except Exception as e:
            logger.error(f"Error scanning for Draw.io attachments: {e}")
            
        return results
    
    def _extract_diagram_data(self, source_path: Path) -> Optional[Dict[str, Any]]:
        """Extract Draw.io diagram data from file."""
        content = source_path.read_text(encoding='utf-8', errors='ignore')
        
        # Try to find mxfile XML directly
        mxfile_match = self.mxfile_pattern.search(content)
        if mxfile_match:
            return {'xml': mxfile_match.group(0), 'type': 'mxfile'}
        
        # Try to find encoded diagram in HTML
        # Draw.io often embeds diagrams as base64 encoded, compressed data
        encoded_pattern = re.compile(r'data-mxgraph="([^"]+)"', re.IGNORECASE)
        encoded_match = encoded_pattern.search(content)
        if encoded_match:
            try:
                encoded_data = encoded_match.group(1)
                # Decode the data
                decoded = self._decode_drawio_data(encoded_data)
                return {'xml': decoded, 'type': 'encoded'}
            except Exception as e:
                logger.warning(f"Failed to decode Draw.io data: {e}")
        
        # For .drawio files, the entire content might be XML
        if source_path.suffix.lower() == '.drawio':
            try:
                ET.fromstring(content)  # Validate it's XML
                return {'xml': content, 'type': 'drawio'}
            except Exception:
                pass
                
        return None
    
    def _decode_drawio_data(self, encoded_data: str) -> str:
        """Decode Draw.io's encoded diagram data."""
        # Draw.io uses URL encoding, then base64, then zlib compression
        try:
            # URL decode
            url_decoded = urllib.parse.unquote(encoded_data)
            # Base64 decode
            base64_decoded = base64.b64decode(url_decoded)
            # Decompress
            decompressed = zlib.decompress(base64_decoded, -zlib.MAX_WBITS)
            # Decode to string
            return decompressed.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decode Draw.io data: {e}")
            raise
    
    def _convert_diagram_to_image(self, diagram_data: Dict[str, Any], 
                                  output_path: Path, format: ConversionFormat) -> bool:
        """
        Convert diagram XML to image format.
        
        Note: This is a placeholder. Actual implementation would require either:
        1. Using draw.io export server API
        2. Using headless browser with draw.io
        3. Using a library that can render mxGraph XML
        
        For now, we'll save the XML and return success=False to indicate
        manual conversion is needed.
        """
        # Save the extracted XML for manual processing
        xml_path = output_path.with_suffix('.xml')
        xml_path.write_text(diagram_data['xml'], encoding='utf-8')
        logger.info(f"Extracted Draw.io XML to {xml_path}")
        
        # TODO: Implement actual conversion
        # Options:
        # 1. Use requests to call draw.io export API
        # 2. Use selenium/playwright to render in headless browser
        # 3. Use external tool like drawio-cli
        
        logger.warning(f"Draw.io to {format.value} conversion not yet implemented. "
                      f"XML saved to {xml_path}")
        
        return False


# Register the converter
converter_registry.register('drawio', DrawioConverter)
