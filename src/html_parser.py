from bs4 import BeautifulSoup, NavigableString, Tag
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from .image_utils import should_skip_image, extract_image_src
from .processors import MediaProcessor
from .models.errors import ErrorCode, get_error_message
from .rich_text_parser import extract_rich_text, extract_colorid_mappings
from .parsers.table_parser import parse_table
from .parsers.utils import parse_list_item
from .parsers.paragraph_parser import parse_paragraph
from .parsers.embedded_wrapper_parser import parse_embedded_wrapper
from .parsers.image_parser import parse_image
from .parsers.list_parser import parse_list
from .parsers.heading_parser import parse_heading
from .parsers.macro_parser import is_jira_macro, parse_jira_macro, is_google_embed, parse_google_embed, is_info_panel, parse_info_panel
import logging

# Minimal AST nodes
# Node: { 'type': 'heading'|'paragraph'|'list'|'code'|'image'|'table'|'drawio'|'file', 'level', 'text', 'rich_text', 'children', 'rows', 'container_id', 'attachment_id', 'src', 'name' }

def is_drawio_container(el: Tag) -> bool:
    """Check if element is a Draw.io container div"""
    if el.name != 'div':
        return False
    
    # Check for ap-container class with diagramly in id
    classes = el.get('class', [])
    el_id = el.get('id', '')
    
    return 'ap-container' in classes and 'diagramly' in el_id

def extract_drawio_info(el: Tag, html_path: Path) -> Dict[str, Any]:
    """Extract Draw.io information from container element"""
    container_id = el.get('id', '')
    
    # Try to find associated attachment
    page_id = html_path.stem
    attachments_dir = html_path.parent / 'attachments' / page_id
    
    drawio_info = {
        'type': 'drawio',
        'container_id': container_id,
        'attachment_id': None,
        'attachment_path': None,
        'diagram_name': None,
        'aspect_hash': None
    }
    
    # Try to extract diagram info from the container's script
    script_el = el.find('script')
    if script_el and script_el.string:
        script_content = script_el.string
        
        # Look for diagramName in the script data
        import re
        
        # Extract various identifiers that can help match attachments
        # Look for custContentId
        content_id_match = re.search(r'"custContentId"\s*:\s*"(\d+)"', script_content)
        if content_id_match:
            drawio_info['content_id'] = content_id_match.group(1)
            
        # Try productCtx for diagram name
        product_ctx_match = re.search(r'"productCtx"\s*:\s*"([^"]+)"', script_content)
        if product_ctx_match:
            ctx_str = product_ctx_match.group(1)
            # Look for diagramName in productCtx - it's a simple key:value format
            name_match = re.search(r'"diagramName":"([^"]+)"', ctx_str)
            if name_match:
                try:
                    # The name might have unicode escapes like \u5728
                    raw_name = name_match.group(1)
                    # Decode unicode escapes
                    if '\\u' in raw_name:
                        drawio_info['diagram_name'] = raw_name.encode().decode('unicode-escape')
                    else:
                        drawio_info['diagram_name'] = raw_name
                except Exception as e:
                    drawio_info['diagram_name'] = name_match.group(1)
        
        # Also check the URL parameter for diagramName
        if not drawio_info['diagram_name']:
            url_match = re.search(r'"url"\s*:\s*"[^"]*diagramName=([^&"]+)', script_content)
            if url_match:
                try:
                    # URL decode the name
                    import urllib.parse
                    decoded_name = urllib.parse.unquote(url_match.group(1))
                    # Remove file extension if present for better matching
                    if decoded_name.endswith('.drawio'):
                        decoded_name = decoded_name[:-7]
                    drawio_info['diagram_name'] = decoded_name
                except:
                    pass
                    
        # Also check the main data object
        if not drawio_info['diagram_name']:
            name_match = re.search(r'"diagramName"\s*:\s*"([^"]+)"', script_content)
            if name_match:
                drawio_info['diagram_name'] = name_match.group(1)
        
        # Look for aspectHash which can help match PNG files
        aspect_hash_match = re.search(r'"aspectHash"\s*:\s*"([^"]+)"', script_content)
        if aspect_hash_match:
            drawio_info['aspect_hash'] = aspect_hash_match.group(1)
        
    # Find attachments - try to match by name, hash, or content ID
    if attachments_dir.exists():
        # Get all potential Draw.io files
        all_drawio_files = []
        aspect_hash = drawio_info.get('aspect_hash', '')
        diagram_name = drawio_info.get('diagram_name', '')
        content_id = drawio_info.get('content_id', '')
        
        # Strategy 1: Direct content ID match (most reliable)
        if content_id:
            # Look for files with the content ID in the name
            for file in attachments_dir.iterdir():
                if content_id in file.name:
                    all_drawio_files.append((file, file.suffix, 5))  # Highest priority
        
        # Strategy 2: Match by diagram name + hash combination (very reliable for PNGs)
        if diagram_name and aspect_hash:
            for png_file in attachments_dir.glob('*.png'):
                # Confluence often exports as "DiagramName-aspectHash.png"
                expected_pattern = f"{diagram_name}-{aspect_hash}"
                if expected_pattern in png_file.name or (diagram_name in png_file.name and aspect_hash in png_file.name):
                    all_drawio_files.append((png_file, '.png', 10))
        
        # Strategy 2b: For "Untitled Diagram" pattern, match more precisely
        if diagram_name and "Untitled" in diagram_name:
            for png_file in attachments_dir.glob('*.png'):
                # Look for files that match the Untitled pattern
                if "Untitled" in png_file.name and "Diagram" in png_file.name:
                    # Check if the timestamp/ID matches
                    if any(part in diagram_name for part in png_file.stem.split('-') if part.isdigit()):
                        all_drawio_files.append((png_file, '.png', 12))
        
        # Strategy 3: Match by diagram name alone
        if diagram_name:
            for file in attachments_dir.iterdir():
                if file.suffix.lower() in ['.png', '.drawio', '.svg'] and diagram_name in file.name:
                    priority = 20 if file.suffix == '.drawio' else 25
                    # Avoid duplicates
                    if not any(f[0] == file for f in all_drawio_files):
                        all_drawio_files.append((file, file.suffix, priority))
        
        # Strategy 4: .drawio.png files
        for png_file in attachments_dir.glob('*.drawio.png'):
            if not any(f[0] == png_file for f in all_drawio_files):
                all_drawio_files.append((png_file, '.png', 30))
        
        # Strategy 5: Any .drawio files (good fallback)
        for drawio_file in attachments_dir.glob('*.drawio'):
            if not any(f[0] == drawio_file for f in all_drawio_files):
                all_drawio_files.append((drawio_file, '.drawio', 15))
        
        # Sort by priority (lower number = higher priority), then prefer .drawio over .png
        all_drawio_files.sort(key=lambda x: (x[2], x[1] != '.drawio', x[0].name))
        
        if all_drawio_files:
            chosen_file = all_drawio_files[0][0]
            drawio_info['attachment_path'] = str(chosen_file.relative_to(html_path.parent))
            drawio_info['attachment_id'] = chosen_file.stem
            
            # Log what we matched for debugging
            import logging
            logging.debug(f"Matched Draw.io container {drawio_info['container_id'][:20]}... to {chosen_file.name}")
    
    return drawio_info


def extract_page_metadata(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """
    Extract page metadata from Confluence HTML export.
    
    Looks for patterns like:
    - "Created by <span class='author'>NAME</span>, last modified on DATE"
    - "Created by <span class='author'>NAME</span>, last modified by <span class='editor'>NAME</span> on DATE"
    - "Created by <span class='author'>NAME</span> on DATE"
    
    Preserves "(Deactivated)" status in names if present.
    
    Returns:
        Dict with 'created_by', 'created_date', 'last_modified_by', 'last_modified_date'
    """
    metadata = {
        'created_by': None,
        'created_date': None,
        'last_modified_by': None,
        'last_modified_date': None
    }
    
    # Find page-metadata div
    metadata_div = soup.find('div', class_='page-metadata')
    if not metadata_div:
        return metadata
    
    metadata_text = metadata_div.get_text()
    if not metadata_text:
        return metadata
    
    # Extract author span (creator)
    author_span = metadata_div.find('span', class_='author')
    if author_span:
        # Preserve "(Deactivated)" if present
        metadata['created_by'] = author_span.get_text(strip=True)
    
    # Extract editor span (last modifier, if different from creator)
    editor_span = metadata_div.find('span', class_='editor')
    if editor_span:
        # Preserve "(Deactivated)" if present
        metadata['last_modified_by'] = editor_span.get_text(strip=True)
    
    # Try to parse dates from text
    # Pattern 1: "Created by NAME, last modified on DATE"
    # Pattern 2: "Created by NAME, last modified by NAME on DATE"
    # Pattern 3: "Created by NAME on DATE"
    
    # Look for "last modified" patterns
    last_modified_match = re.search(
        r'last modified(?:\s+by\s+[^,]+)?\s+on\s+([^<\n]+)',
        metadata_text,
        re.IGNORECASE
    )
    
    if last_modified_match:
        date_str = last_modified_match.group(1)
        if date_str:
            metadata['last_modified_date'] = date_str.strip()
    
    # If we found editor span but no last_modified_by yet, try to extract from text
    if not metadata['last_modified_by']:
        modifier_match = re.search(
            r'last modified\s+by\s+([^,]+?)(?:\s+on\s+|$)',
            metadata_text,
            re.IGNORECASE
        )
        if modifier_match:
            metadata['last_modified_by'] = modifier_match.group(1).strip()
    
    # Try to extract created date if present
    # Match date after "on" - capture full date including year
    # Stop at ", last" (for "last modified") or end of string
    created_date_match = re.search(
        r'created(?:\s+by\s+[^,]+)?\s+on\s+([^<\n]+?)(?:,\s*last|$)',
        metadata_text,
        re.IGNORECASE
    )
    if created_date_match:
        date_str = created_date_match.group(1).strip()
        # Remove trailing comma if present (but keep comma in date like "Sep 01, 2025")
        # Only remove trailing comma if it's not part of the date format
        if date_str.endswith(',') and not re.search(r'\d{4},?\s*$', date_str):
            date_str = date_str.rstrip(',').strip()
        metadata['created_date'] = date_str
        
        # Validate date has year (4 digits)
        if date_str and not re.search(r'\d{4}', date_str):
            logging.warning(get_error_message(
                ErrorCode.WARN_METADATA_DATE_INCOMPLETE,
                f"Created date missing year: '{date_str}'"
            ))
    
    # Validate last modified date has year
    if metadata.get('last_modified_date') and not re.search(r'\d{4}', metadata['last_modified_date']):
        logging.warning(get_error_message(
            ErrorCode.WARN_METADATA_DATE_INCOMPLETE,
            f"Last modified date missing year: '{metadata['last_modified_date']}'"
        ))
    
    # Validate author extraction
    # Check if metadata text suggests author but we didn't extract it
    if metadata_text and 'created by' in metadata_text.lower():
        if not metadata.get('created_by'):
            logging.warning(get_error_message(
                ErrorCode.WARN_METADATA_AUTHOR_INCOMPLETE,
                "Created by author not found in metadata"
            ))
    
    # Check if we have any metadata at all - if metadata div exists but we got nothing, log warning
    if metadata_div and not any(metadata.values()):
        logging.warning(get_error_message(
            ErrorCode.WARN_METADATA_EXTRACTION_FAILED,
            "Page metadata div found but no data extracted"
        ))
    
    return metadata


def get_element_handler(el: Tag, context: Dict[str, Any]) -> Optional[Any]:
    """
    Get the appropriate handler function for an element.
    
    Args:
        el: The HTML element to process
        context: Context dict with colorid_map, soup, etc.
        
    Returns:
        Handler function or None
    """
    name = el.name.lower()
    
    # Check for macros first
    if is_jira_macro(el):
        return lambda el, ctx: parse_jira_macro(el, ctx)
    
    if is_google_embed(el):
        return lambda el, ctx: parse_google_embed(el, ctx)
    
    if is_info_panel(el):
        return lambda el, ctx: parse_info_panel(el, ctx)
    
    # Special case handlers
    if name == 'div' and 'toc-macro' in el.get('class', []):
        return None  # Skip TOC macros
    
    if is_drawio_container(el):
        return lambda el, ctx: extract_drawio_info(el, ctx['path'])
    
    if name == 'span' and 'confluence-embedded-file-wrapper' in el.get('class', []):
        return lambda el, ctx: parse_embedded_wrapper(el, colorid_map=ctx.get('colorid_map'))
    
    # Element name to handler mapping
    element_handlers = {
        'h1': lambda el, ctx: parse_heading(el, colorid_map=ctx.get('colorid_map')),
        'h2': lambda el, ctx: parse_heading(el, colorid_map=ctx.get('colorid_map')),
        'h3': lambda el, ctx: parse_heading(el, colorid_map=ctx.get('colorid_map')),
        'h4': lambda el, ctx: parse_heading(el, colorid_map=ctx.get('colorid_map')),
        'h5': lambda el, ctx: parse_heading(el, colorid_map=ctx.get('colorid_map')),
        'h6': lambda el, ctx: parse_heading(el, colorid_map=ctx.get('colorid_map')),
        'p': lambda el, ctx: parse_paragraph(el, colorid_map=ctx.get('colorid_map')),
        'ul': lambda el, ctx: parse_list(el, colorid_map=ctx.get('colorid_map')),
        'ol': lambda el, ctx: parse_list(el, colorid_map=ctx.get('colorid_map')),
        'pre': lambda el, ctx: {'type': 'code', 'text': (el.find('code') or el).get_text("\n", strip=False)},
        'img': lambda el, ctx: parse_image(el),
        'table': lambda el, ctx: parse_table(el, colorid_map=ctx.get('colorid_map'), soup=ctx.get('soup')),
    }
    
    return element_handlers.get(name)


def parse_html_file(path: Path, include_unused_attachments: bool = False) -> Dict[str, Any]:
    """
    Parse a Confluence HTML export file into an AST.
    
    Args:
        path: Path to the HTML file
        include_unused_attachments: If False (default), only include attachments that are 
            actually embedded/referenced in the page content. If True, include all 
            attachments listed in the Attachments section (Confluence legacy behavior).
    """
    html = Path(path).read_text(encoding='utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'lxml')
    title = (soup.title.string.strip() if soup.title and soup.title.string else Path(path).stem)

    # Extract page metadata (author, dates)
    metadata = extract_page_metadata(soup)

    # Extract color mappings from <style> tags for data-colorid attributes
    colorid_map = extract_colorid_mappings(soup)

    # Find the main content area (Confluence specific)
    content = soup.find('div', id='main-content') or soup.find('div', id='content') or soup.body or soup
    
    blocks: List[Dict[str, Any]] = []
    processed = set()  # Track processed elements to avoid duplicates
    referenced_attachments = set()  # Track attachments actually used in content
    
    # Create context for handlers
    context = {
        'colorid_map': colorid_map,
        'soup': soup,
        'path': path,
        'referenced_attachments': referenced_attachments  # Pass to handlers
    }

    for el in content.descendants:
        if isinstance(el, Tag) and el not in processed:
            # Skip if this element is inside another block element we'll process
            if any(parent in processed for parent in el.parents):
                continue
            
            # Get handler for this element
            handler = get_element_handler(el, context)
            if handler:
                # Call the handler
                result = handler(el, context)
                
                # Process the result
                if result:
                    if isinstance(result, list):
                        blocks.extend(result)
                    elif isinstance(result, dict):
                        blocks.append(result)
                    
                # Mark as processed
                processed.add(el)
    
    # Collect all attachment paths that are actually referenced in content
    def collect_referenced_attachments(blocks_list):
        """Recursively collect all attachment paths from blocks."""
        paths = set()
        for block in blocks_list:
            # Check src field (images, files, videos)
            src = block.get('src', '')
            if src and src.startswith('attachments/'):
                paths.add(src)
            # Check attachment_path (drawio)
            att_path = block.get('attachment_path', '')
            if att_path and 'attachments/' in att_path:
                paths.add(att_path)
            # Recursively check children
            if 'children' in block:
                paths.update(collect_referenced_attachments(block['children']))
            # Check table rows
            if 'rows' in block:
                for row in block['rows']:
                    for cell in row:
                        if 'children' in cell:
                            paths.update(collect_referenced_attachments(cell['children']))
        return paths
    
    referenced_attachments = collect_referenced_attachments(blocks)
    unused_attachments_count = 0
    unused_attachments = []  # Details of unused attachments for tracking
    
    # Parse attachments section - only include if explicitly enabled
    if include_unused_attachments:
        attachments_section = soup.find('div', class_='pageSection')
        if attachments_section:
            attachments_header = attachments_section.find('h2', id='attachments')
            if attachments_header:
                # Found attachments section
                attachment_links = attachments_section.find_all('a', href=True)
                for link in attachment_links:
                    href = link.get('href', '')
                    if href.startswith('attachments/'):
                        # Skip if already referenced in content
                        if href in referenced_attachments:
                            continue
                            
                        filename = link.get_text(strip=True)
                        file_ext = Path(filename).suffix.lower()
                        
                        # Skip if it's already been processed as an image or video
                        media_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp',
                                          '.mp4', '.mov', '.avi', '.webm']
                        
                        if file_ext not in media_extensions:
                            # Handle temporary files - these are often Draw.io backup files
                            if file_ext == '.tmp':
                                # Check if it's a Draw.io temp file
                                if 'drawio' in filename.lower():
                                    logging.info(f"Found Draw.io temp file: {filename} - these are auto-save backups")
                                logging.debug(get_error_message(
                                    ErrorCode.WARN_TEMP_FILE_SKIPPED,
                                    f"Skipping temporary file attachment: {filename}"
                                ))
                                continue
                                
                            # It's a document/file attachment not referenced in content
                            blocks.append({
                                'type': 'file',
                                'src': href,
                                'name': filename
                            })
                            logging.info(f"Added unused file attachment: {filename}")
    else:
        # Collect details about unused attachments for reporting
        attachments_section = soup.find('div', class_='pageSection')
        if attachments_section:
            attachments_header = attachments_section.find('h2', id='attachments')
            if attachments_header:
                attachment_links = attachments_section.find_all('a', href=True)
                for link in attachment_links:
                    href = link.get('href', '')
                    if href.startswith('attachments/') and href not in referenced_attachments:
                        unused_attachments_count += 1
                        
                        # Collect details for skipped media tracking
                        filename = link.get_text(strip=True) or Path(href).name
                        file_ext = Path(filename).suffix.lower()
                        
                        # Determine media type
                        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico'}
                        video_exts = {'.mp4', '.mov', '.avi', '.webm', '.mkv', '.wmv'}
                        if file_ext in image_exts:
                            media_type = 'image'
                        elif file_ext in video_exts:
                            media_type = 'video'
                        else:
                            media_type = 'file'
                        
                        # Try to get file size from actual file
                        file_path = path.parent / href
                        file_size = None
                        if file_path.exists():
                            try:
                                file_size = file_path.stat().st_size
                            except OSError:
                                pass
                        
                        unused_attachments.append({
                            'file_path': str(file_path),
                            'filename': filename,
                            'media_type': media_type,
                            'file_size_bytes': file_size,
                            'skip_reason': 'unused_orphan'
                        })
    
    # Log if unused attachments were skipped
    if unused_attachments_count > 0:
        logging.info(f"Skipped {unused_attachments_count} unused attachment(s) not referenced in content")
    
    return {
        'title': title,
        'blocks': blocks,
        'metadata': metadata,
        'attachment_stats': {
            'referenced': len(referenced_attachments),
            'unused_skipped': unused_attachments_count,
            'unused_details': unused_attachments
        }
    }
