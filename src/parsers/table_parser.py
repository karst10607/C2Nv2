"""Table parser for extracting HTML tables into Notion-compatible format"""

from bs4 import BeautifulSoup, NavigableString, Tag
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging

from ..image_utils import should_skip_image, extract_image_src
from ..models.errors import ErrorCode, get_error_message
from ..rich_text_parser import extract_rich_text

# Notion API limit: maximum 100 cells per table row
NOTION_MAX_CELLS_PER_ROW = 100

# Color name mappings for background colors
COLOR_NAME_MAP = {
    # Reds
    'red': 'red', '#ff0000': 'red', '#f44336': 'red', '#e53935': 'red',
    '#ffcdd2': 'red', '#ef9a9a': 'red', '#ffebee': 'red',
    # Greens
    'green': 'green', '#00ff00': 'green', '#4caf50': 'green', '#43a047': 'green',
    '#c8e6c9': 'green', '#a5d6a7': 'green', '#e8f5e9': 'green',
    '#adf0d1': 'green', '#b3d4c4': 'green',
    # Blues
    'blue': 'blue', '#0000ff': 'blue', '#2196f3': 'blue', '#1e88e5': 'blue',
    '#bbdefb': 'blue', '#90caf9': 'blue', '#e3f2fd': 'blue',
    # Yellows
    'yellow': 'yellow', '#ffff00': 'yellow', '#ffeb3b': 'yellow', '#fdd835': 'yellow',
    '#fff9c4': 'yellow', '#fff59d': 'yellow', '#fffde7': 'yellow',
    '#fffae6': 'yellow',
    # Oranges
    'orange': 'orange', '#ff9800': 'orange', '#fb8c00': 'orange',
    '#ffe0b2': 'orange', '#ffcc80': 'orange', '#fff3e0': 'orange',
    # Purples
    'purple': 'purple', '#9c27b0': 'purple', '#8e24aa': 'purple',
    '#e1bee7': 'purple', '#ce93d8': 'purple', '#f3e5f5': 'purple',
    # Grays
    'gray': 'gray', 'grey': 'gray', '#9e9e9e': 'gray', '#757575': 'gray',
    '#e0e0e0': 'gray', '#bdbdbd': 'gray', '#f5f5f5': 'gray',
}


def extract_cell_background_color(td: Tag) -> Optional[str]:
    """
    Extract background color from a table cell.
    
    Args:
        td: The table cell element
        
    Returns:
        Normalized color name (red, green, blue, yellow, orange, purple, gray) or None
    """
    import re
    
    # Check style attribute for background-color
    style = td.get('style', '')
    if style:
        # Match background-color: #xxx or background-color: colorname
        bg_match = re.search(r'background(?:-color)?\s*:\s*([^;]+)', style, re.IGNORECASE)
        if bg_match:
            color_value = bg_match.group(1).strip().lower()
            return normalize_color(color_value)
    
    # Check bgcolor attribute (older HTML)
    bgcolor = td.get('bgcolor', '')
    if bgcolor:
        return normalize_color(bgcolor.lower())
    
    # Check data-highlight-colour (Confluence specific)
    highlight = td.get('data-highlight-colour', '')
    if highlight:
        return normalize_color(highlight.lower())
    
    return None


def normalize_color(color_value: str) -> Optional[str]:
    """
    Normalize a color value to a standard color name.
    
    Args:
        color_value: CSS color value (hex, rgb, or name)
        
    Returns:
        Normalized color name or None
    """
    import re
    
    color_value = color_value.strip().lower()
    
    # Direct lookup
    if color_value in COLOR_NAME_MAP:
        return COLOR_NAME_MAP[color_value]
    
    # Handle rgb() format
    rgb_match = re.match(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_value)
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return classify_rgb_color(r, g, b)
    
    # Handle hex format
    hex_match = re.match(r'#?([0-9a-f]{6})', color_value)
    if hex_match:
        hex_val = hex_match.group(1)
        r = int(hex_val[0:2], 16)
        g = int(hex_val[2:4], 16)
        b = int(hex_val[4:6], 16)
        return classify_rgb_color(r, g, b)
    
    # Handle short hex format
    hex_short_match = re.match(r'#?([0-9a-f]{3})$', color_value)
    if hex_short_match:
        hex_val = hex_short_match.group(1)
        r = int(hex_val[0] * 2, 16)
        g = int(hex_val[1] * 2, 16)
        b = int(hex_val[2] * 2, 16)
        return classify_rgb_color(r, g, b)
    
    return None


def classify_rgb_color(r: int, g: int, b: int) -> Optional[str]:
    """
    Classify an RGB color into a named color category.
    
    Args:
        r, g, b: RGB values (0-255)
        
    Returns:
        Color name (red, green, blue, yellow, orange, purple, gray) or None
    """
    # Skip white or near-white backgrounds
    if r > 240 and g > 240 and b > 240:
        return None
    
    # Gray detection (low saturation)
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    diff = max_val - min_val
    
    if diff < 30:  # Low saturation = gray
        if max_val < 200:  # Not too light
            return 'gray'
        return None
    
    # Determine dominant color
    if r >= g and r >= b:
        if g > b * 1.5:  # Red + significant green = yellow/orange
            if g > r * 0.7:
                return 'yellow'
            return 'orange'
        if b > g * 1.2:  # Red + blue = purple
            return 'purple'
        return 'red'
    elif g >= r and g >= b:
        return 'green'
    else:  # Blue dominant
        if r > g * 1.2:  # Blue + red = purple
            return 'purple'
        return 'blue'


def parse_table(el: Tag, colorid_map: Optional[Dict[str, str]] = None, soup: Optional[BeautifulSoup] = None) -> Optional[Dict[str, Any]]:
    """
    Parse an HTML table element into Notion table format.
    
    Args:
        el: The table Tag element to parse
        colorid_map: Optional color ID mappings for rich text
        soup: Optional BeautifulSoup instance for creating new tags
    
    Returns:
        Dictionary with table data or None if empty
    """
    rows = []
    all_trs = el.find_all('tr')
    
    # Skip single header row tables without content
    thead = el.find('thead')
    tbody = el.find('tbody')
    
    if thead and tbody:
        thead_trs = thead.find_all('tr', recursive=False)
        tbody_trs = tbody.find_all('tr', recursive=False)
        
        if len(thead_trs) == 1 and len(tbody_trs) == 0:
            # Skip tables with only header and no content
            return None
    
    # Process all table rows
    for tr_idx, tr in enumerate(all_trs):
        in_thead = thead and tr in thead.descendants
        cells = []
        tds = tr.find_all(['td', 'th'])
        
        if not tds:
            continue
            
        all_cells_are_headers = all(td.name == 'th' for td in tds)
        
        for td_idx, td in enumerate(tds):
            is_header = td.name == 'th'
            scope = td.get('scope', None)  # 'row', 'col', or None
            
            # Check for Confluence-specific header classes
            cell_classes = td.get('class', [])
            if isinstance(cell_classes, list):
                cell_classes = ' '.join(cell_classes)
            if 'confluenceTh' in str(cell_classes) or 'header' in str(cell_classes):
                is_header = True
            
            colspan = int(td.get('colspan', 1))
            rowspan = int(td.get('rowspan', 1))
            
            # Extract background color from style or bgcolor attribute
            bg_color = extract_cell_background_color(td)
            
            # Process cell content
            cell_data = parse_table_cell(td, is_header, colorid_map, soup)
            
            cell_info = {
                'children': cell_data['children'],
                'colspan': colspan,
                'rowspan': rowspan,
                'is_header': is_header,
                'scope': scope
            }
            
            # Add background color if present
            if bg_color:
                cell_info['bg_color'] = bg_color
            
            cells.append(cell_info)
        
        # Validate and truncate if row exceeds Notion's limit
        if len(cells) > NOTION_MAX_CELLS_PER_ROW:
            logging.warning(get_error_message(
                ErrorCode.WARN_TABLE_ROW_CELL_LIMIT,
                f"Table row {tr_idx + 1} has {len(cells)} cells (limit: {NOTION_MAX_CELLS_PER_ROW}) - truncating to first {NOTION_MAX_CELLS_PER_ROW} cells"
            ))
            cells = cells[:NOTION_MAX_CELLS_PER_ROW]
        
        if cells:
            rows.append({
                'cells': cells,
                'is_header_row': in_thead or all_cells_are_headers
            })
    
    return {'type': 'table', 'rows': rows} if rows else None


def parse_table_cell(td: Tag, is_header: bool, colorid_map: Optional[Dict[str, str]] = None, 
                     soup: Optional[BeautifulSoup] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse a single table cell (td or th element).
    
    Args:
        td: The cell Tag element
        is_header: Whether this is a header cell
        colorid_map: Optional color ID mappings
        soup: Optional BeautifulSoup instance
        
    Returns:
        Dictionary with 'children' list containing cell content blocks
    """
    cell_children = []
    
    # For header cells, use the entire rich text content
    if is_header:
        header_text = td.get_text(strip=True)
        if header_text:
            rich_text = extract_rich_text(td, colorid_map=colorid_map)
            cell_children.append({
                'type': 'paragraph',
                'text': header_text,
                'rich_text': rich_text
            })
    else:
        # Check if it's a simple cell (only text, no nested elements)
        only_text = all(isinstance(c, NavigableString) or 
                       (isinstance(c, Tag) and c.name in ['br']) 
                       for c in td.children)
        
        if only_text:
            cell_text = td.get_text(strip=True)
            if cell_text:
                rich_text = extract_rich_text(td, colorid_map=colorid_map)
                cell_children.append({
                    'type': 'paragraph',
                    'text': cell_text,
                    'rich_text': rich_text
                })
        else:
            # Complex cell - process each child element
            cell_children = process_complex_cell_content(td, colorid_map, soup)
    
    # Ensure cells have at least one child
    if not cell_children:
        cell_children.append({'type': 'paragraph', 'text': '', 'rich_text': []})
    
    return {'children': cell_children}


def process_complex_cell_content(td: Tag, colorid_map: Optional[Dict[str, str]] = None,
                                soup: Optional[BeautifulSoup] = None) -> List[Dict[str, Any]]:
    """
    Process complex cell content with multiple elements.
    
    Args:
        td: The table cell element
        colorid_map: Optional color ID mappings
        soup: Optional BeautifulSoup instance
        
    Returns:
        List of content blocks for the cell
    """
    from ..parsers.utils import parse_list_item
    
    cell_children = []
    
    for c in td.children:
        if isinstance(c, NavigableString):
            text = str(c).strip()
            if text:
                # Create temporary element for rich text extraction
                if soup:
                    temp_span = soup.new_tag('span')
                    temp_span.string = text
                    rich_text = extract_rich_text(temp_span, colorid_map=colorid_map)
                else:
                    rich_text = [{'type': 'text', 'text': {'content': text}}]
                
                cell_children.append({
                    'type': 'paragraph',
                    'text': text,
                    'rich_text': rich_text
                })
        
        elif isinstance(c, Tag):
            # Handle different element types
            if c.name == 'img':
                img_block = process_table_cell_image(c)
                if img_block:
                    cell_children.append(img_block)
                    
            elif c.name in ('p', 'span', 'div'):
                content_blocks = process_table_cell_container(c, colorid_map)
                cell_children.extend(content_blocks)
                
            elif c.name in ('ul', 'ol'):
                list_block = process_table_cell_list(c, colorid_map)
                if list_block:
                    cell_children.append(list_block)
                    
            elif c.name in ('pre', 'code'):
                cell_children.append({
                    'type': 'code',
                    'text': c.get_text("\n", strip=False),
                    'rich_text': []
                })
    
    return cell_children


def process_table_cell_image(img: Tag) -> Optional[Dict[str, Any]]:
    """Process image element in table cell."""
    src = extract_image_src(img)
    
    # Handle emoticons
    if 'emoticon' in img.get('class', []):
        emoji_fallback = img.get('data-emoji-fallback') or img.get('alt', '')
        if emoji_fallback:
            emoji_fallback = emoji_fallback.strip()
            if not emoji_fallback:
                logging.warning(get_error_message(
                    ErrorCode.WARN_EMOTICON_FALLBACK_INVALID,
                    f"Emoticon fallback is empty in table cell: {src or 'unknown'}"
                ))
                return None
            
            return {
                'type': 'paragraph',
                'text': emoji_fallback,
                'rich_text': [{'type': 'text', 'text': {'content': emoji_fallback}}]
            }
        else:
            logging.warning(get_error_message(
                ErrorCode.WARN_EMOTICON_NO_FALLBACK,
                f"Emoticon in table cell has no emoji fallback: {src or 'unknown'}"
            ))
            return None
    
    # Regular image
    elif src and not should_skip_image(img, src):
        return {'type': 'image', 'src': src}
    
    return None


def process_table_cell_container(element: Tag, colorid_map: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Process container elements (p, span, div) in table cells."""
    blocks = []
    
    # Handle embedded file wrapper
    if element.name == 'span' and 'confluence-embedded-file-wrapper' in element.get('class', []):
        file_block = process_embedded_file_in_cell(element)
        if file_block:
            blocks.append(file_block)
            return blocks
    
    # Replace emoticons with emoji before extracting text
    from .utils import replace_emoticons_with_emoji
    replace_emoticons_with_emoji(element)
    
    # Extract text content
    text = element.get_text(" ", strip=True)
    if text:
        blocks.append({
            'type': 'paragraph',
            'text': text,
            'rich_text': extract_rich_text(element, colorid_map=colorid_map)
        })
    
    # Process remaining images
    for img in element.find_all('img'):
        img_block = process_table_cell_image(img)
        if img_block:
            blocks.append(img_block)
    
    return blocks


def process_embedded_file_in_cell(wrapper: Tag) -> Optional[Dict[str, Any]]:
    """Process Confluence embedded file wrapper in table cell."""
    file_link = wrapper.find('a', href=True)
    if not file_link:
        return None
    
    file_href = file_link.get('href', '')
    file_name = file_link.get_text(strip=True)
    
    # Check if it's a video
    if any(ext in file_href for ext in ['.mp4', '.mov', '.avi', '.webm']):
        # Remove query parameters
        if '?' in file_href:
            file_href = file_href.split('?')[0]
        return {'type': 'video', 'src': file_href, 'name': file_name}
    
    # Check if it's a document attachment
    elif file_href.startswith('attachments/'):
        file_ext = Path(file_name).suffix.lower()
        image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']
        if file_ext not in image_exts:
            return {'type': 'file', 'src': file_href, 'name': file_name}
    
    return None




def process_table_cell_list(list_el: Tag, colorid_map: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Process list (ul/ol) in table cell."""
    from ..parsers.utils import parse_list_item
    
    items = []
    for li in list_el.find_all('li', recursive=False):
        li_content = parse_list_item(li, colorid_map=colorid_map)
        items.append(li_content)
    
    if items:
        return {
            'type': 'list',
            'ordered': list_el.name == 'ol',
            'items': items
        }
    
    return None
