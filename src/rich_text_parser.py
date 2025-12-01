"""
Rich text parser for preserving links, colors, and formatting from HTML.
Converts HTML elements to Notion rich text format with annotations.
"""
from typing import List, Dict, Any, Optional, Union
from bs4 import BeautifulSoup, NavigableString, Tag
import re
import logging

from .constants import NOTION_TEXT_LIMIT
from .models.errors import ErrorCode, get_error_message

# Map CSS color names and hex codes to Notion colors
COLOR_MAP = {
    # Basic colors
    'red': 'red', '#ff0000': 'red', '#f00': 'red', '#ff5630': 'red',  # Confluence red-orange
    'blue': 'blue', '#0000ff': 'blue', '#00f': 'blue', 
    'green': 'green', '#008000': 'green', '#00ff00': 'green', '#0f0': 'green',
    'yellow': 'yellow', '#ffff00': 'yellow', '#ff0': 'yellow',
    'orange': 'orange', '#ffa500': 'orange', '#ff8c00': 'orange',
    'purple': 'purple', '#800080': 'purple', '#ff00ff': 'purple',
    'pink': 'pink', '#ffc0cb': 'pink', '#ff69b4': 'pink',
    'brown': 'brown', '#a52a2a': 'brown', '#964b00': 'brown',
    'gray': 'gray', 'grey': 'gray', '#808080': 'gray', '#888': 'gray',
    'black': 'default',  # Notion uses default for black
    'white': 'default',  # White text shows as default
}

# Map background colors to Notion background annotation colors
BACKGROUND_MAP = {
    'yellow': 'yellow_background', '#ffff00': 'yellow_background', '#ff0': 'yellow_background',
    'red': 'red_background', '#ffeb9c': 'red_background', '#ffc7ce': 'red_background',
    'blue': 'blue_background', '#dae8fc': 'blue_background', '#d4e1f5': 'blue_background',
    'green': 'green_background', '#d5e8d4': 'green_background', '#c3e88d': 'green_background',
    'purple': 'purple_background', '#e1d5e7': 'purple_background',
    'pink': 'pink_background', '#f8cecc': 'pink_background',
    'orange': 'orange_background', '#ffe6cc': 'orange_background',
    'brown': 'brown_background', '#f5f5dc': 'brown_background',
    'gray': 'gray_background', 'grey': 'gray_background',
    '#f0f0f0': 'gray_background', '#e0e0e0': 'gray_background', 
    '#d0d0d0': 'gray_background', '#cccccc': 'gray_background',
}


def parse_style_attribute(style: str) -> Dict[str, str]:
    """Parse CSS style attribute into a dictionary"""
    styles = {}
    if not style:
        return styles
    
    # Split by semicolon and parse each property
    for prop in style.split(';'):
        if ':' in prop:
            key, value = prop.split(':', 1)
            styles[key.strip().lower()] = value.strip()
    
    return styles


def get_notion_color(css_color: str, is_background: bool = False) -> str:
    """Convert CSS color to Notion color annotation"""
    if not css_color:
        return 'default'
    
    css_color = css_color.lower().strip()
    
    # Check the appropriate map
    color_map = BACKGROUND_MAP if is_background else COLOR_MAP
    
    # Direct match
    if css_color in color_map:
        return color_map[css_color]
    
    # Try to parse rgb/rgba
    rgb_match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', css_color)
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        # Convert to hex and check again
        hex_color = f'#{r:02x}{g:02x}{b:02x}'
        if hex_color in color_map:
            return color_map[hex_color]
    
    # Default fallback
    return 'default'


def extract_colorid_mappings(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Extract color mappings from <style> tags that define [data-colorid=...] rules.
    
    Example:
        <style>[data-colorid=k3hhw1tsvb]{color:#ff5630}</style>
        <span data-colorid="k3hhw1tsvb">colored text</span>
    
    Returns:
        Dictionary mapping colorid to CSS color value
    """
    colorid_map = {}
    
    # Find all style tags
    for style_tag in soup.find_all('style'):
        style_content = style_tag.string or ''
        
        # Match patterns like [data-colorid=xyz]{color:#ff5630}
        # or [data-colorid=xyz]{color:red}
        pattern = r'\[data-colorid=([^\]]+)\]\s*\{[^}]*color\s*:\s*([^;}]+)'
        matches = re.findall(pattern, style_content, re.IGNORECASE)
        
        for colorid, css_color in matches:
            colorid = colorid.strip().strip('"\'')
            css_color = css_color.strip().strip('"\'')
            colorid_map[colorid] = css_color
    
    return colorid_map


def extract_rich_text(element: Union[Tag, str], base_url: str = "", parent_style: Optional[Dict] = None, colorid_map: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Extract rich text with links and colors from HTML element.
    
    Args:
        element: BeautifulSoup Tag or HTML string to parse
        base_url: Base URL for resolving relative links
        parent_style: Inherited style from parent element
        colorid_map: Dictionary mapping data-colorid values to CSS colors
        
    Returns:
        List of Notion rich text objects
    """
    rich_text_parts = []
    
    def create_rich_text_object(text: str, style: Dict) -> Dict[str, Any]:
        """Create a single rich text object with given text and style"""
        if not text:
            return None
            
        # Create basic structure
        obj = {
            "type": "text",
            "text": {"content": text},
            "annotations": {
                "bold": style.get('bold', False),
                "italic": style.get('italic', False),
                "strikethrough": style.get('strikethrough', False),
                "underline": style.get('underline', False),
                "code": style.get('code', False),
                "color": style.get('color', 'default')
            }
        }
        
        # Add link if present
        if 'link' in style:
            obj["text"]["link"] = {"url": style['link']}
            # Links are typically underlined in Notion
            obj["annotations"]["underline"] = True
        
        return obj
    
    def process_node(node: Union[NavigableString, Tag], inherited_style: Optional[Dict] = None):
        """Process a single node and extract rich text"""
        style = inherited_style.copy() if inherited_style else {}
        
        if isinstance(node, NavigableString):
            text = str(node)
            if text.strip():  # Only create object for non-empty text
                obj = create_rich_text_object(text, style)
                if obj:
                    rich_text_parts.append(obj)
                    
        elif isinstance(node, Tag):
            # Handle links
            if node.name == 'a' and node.get('href'):
                href = node.get('href', '')
                # Resolve relative URLs
                if href.startswith('#'):
                    # Skip internal anchor links - Notion doesn't support them
                    # Convert to plain text to preserve the reference
                    logging.warning(get_error_message(ErrorCode.WARN_ANCHOR_LINK_SKIPPED, href))
                    pass
                elif href.startswith('http://') or href.startswith('https://'):
                    style['link'] = href
                elif href.startswith('mailto:'):
                    # Email links are valid
                    style['link'] = href
                elif href and base_url:
                    # Relative link - only add if we have a valid base URL
                    style['link'] = base_url.rstrip('/') + '/' + href.lstrip('/')
                elif href.endswith('.html') or href.endswith('.htm'):
                    # Skip relative HTML links - they're not valid for Notion
                    # Don't add 'link' to style, so it becomes plain text
                    logging.warning(get_error_message(ErrorCode.WARN_RELATIVE_HTML_LINK_SKIPPED, href))
                    pass
                elif href.startswith('/') or (href and not any(href.startswith(p) for p in ['http://', 'https://', 'mailto:', '#', 'ftp://', 'tel:'])):
                    # Skip other relative links without base URL - they're not valid for Notion
                    # This includes paths like /wiki/..., ../something, ./file, etc.
                    logging.warning(f"Skipping invalid relative link: {href}")
                    pass
                else:
                    # For any other edge cases, skip them
                    logging.debug(f"Skipping unrecognized link format: {href}")
                    pass
            
            # Handle data-colorid attributes (Confluence color system)
            if colorid_map and node.get('data-colorid'):
                colorid = node.get('data-colorid')
                if colorid in colorid_map:
                    css_color = colorid_map[colorid]
                    notion_color = get_notion_color(css_color)
                    if notion_color != 'default':
                        style['color'] = notion_color
            
            # Handle inline styles
            if node.get('style'):
                css_styles = parse_style_attribute(node.get('style'))
                
                # Text color
                if 'color' in css_styles:
                    notion_color = get_notion_color(css_styles['color'])
                    if notion_color != 'default':
                        style['color'] = notion_color
                
                # Background color
                if 'background-color' in css_styles or 'background' in css_styles:
                    bg_color = css_styles.get('background-color') or css_styles.get('background', '')
                    notion_bg = get_notion_color(bg_color, is_background=True)
                    if notion_bg != 'default':
                        style['color'] = notion_bg
                
                # Font weight
                if 'font-weight' in css_styles:
                    weight = css_styles['font-weight']
                    if weight in ['bold', '700', '800', '900']:
                        style['bold'] = True
                
                # Font style
                if 'font-style' in css_styles and css_styles['font-style'] == 'italic':
                    style['italic'] = True
                
                # Text decoration
                if 'text-decoration' in css_styles:
                    decoration = css_styles['text-decoration']
                    if 'underline' in decoration:
                        style['underline'] = True
                    if 'line-through' in decoration:
                        style['strikethrough'] = True
            
            # Handle semantic HTML tags
            if node.name in ['strong', 'b']:
                style['bold'] = True
            elif node.name in ['em', 'i']:
                style['italic'] = True
            elif node.name == 'u':
                style['underline'] = True
            elif node.name == 'code':
                style['code'] = True
            elif node.name in ['s', 'del', 'strike']:
                style['strikethrough'] = True
            elif node.name == 'mark':
                # HTML mark tag typically means highlighted/yellow background
                style['color'] = 'yellow_background'
            
            # Process children
            for child in node.children:
                process_node(child, style)
    
    # Start processing
    if isinstance(element, str):
        soup = BeautifulSoup(element, 'html.parser')
        for child in soup.children:
            process_node(child, parent_style)
    else:
        for child in element.children:
            process_node(child, parent_style)
    
    # If no rich text was extracted, return plain text
    if not rich_text_parts and isinstance(element, Tag):
        text = element.get_text()
        if text.strip():
            return [create_rich_text_object(text, parent_style or {})]
    
    return rich_text_parts


def split_rich_text_by_length(rich_text_list: List[Dict[str, Any]], max_length: int = NOTION_TEXT_LIMIT) -> List[Dict[str, Any]]:
    """
    Split rich text objects that exceed Notion's character limit.
    Preserves formatting and links across splits.
    """
    result = []
    
    for item in rich_text_list:
        text = item['text']['content']
        if len(text) <= max_length:
            result.append(item)
        else:
            # Split the text while preserving formatting
            for i in range(0, len(text), max_length):
                chunk = text[i:i + max_length]
                new_item = {
                    "type": item['type'],
                    "text": {"content": chunk},
                    "annotations": item['annotations'].copy()
                }
                # Preserve link if present
                if 'link' in item['text']:
                    new_item['text']['link'] = item['text']['link']
                result.append(new_item)
    
    return result

