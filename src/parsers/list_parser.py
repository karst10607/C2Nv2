"""List parser for extracting HTML lists into Notion-compatible format"""

from bs4 import Tag
from typing import Any, Dict, List, Optional
from .utils import parse_list_item


def parse_list(el: Tag, colorid_map: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """
    Parse a list element (ul or ol) into a Notion list block.
    
    Args:
        el: The ul or ol Tag element
        colorid_map: Optional color ID mappings for rich text
        
    Returns:
        Dictionary with list block or None if empty
    """
    items = []
    
    # Only process direct children <li> elements
    for li in el.find_all('li', recursive=False):
        # Parse complex list items that may contain multiple paragraphs and nested lists
        li_content = parse_list_item(li, colorid_map=colorid_map)
        items.append(li_content)
    
    if items:
        return {
            'type': 'list',
            'ordered': el.name == 'ol',
            'items': items
        }
    
    return None


