"""Heading parser for extracting HTML headings into Notion-compatible format"""

from bs4 import Tag
from typing import Any, Dict, Optional

from ..rich_text_parser import extract_rich_text


def parse_heading(el: Tag, colorid_map: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """
    Parse a heading element (h1-h6) into a Notion heading block.
    
    Args:
        el: The heading Tag element (h1, h2, h3, etc.)
        colorid_map: Optional color ID mappings for rich text
        
    Returns:
        Dictionary with heading block or None if empty
    """
    text = el.get_text(strip=True)
    
    if text:
        # Extract heading level from tag name (h1 -> 1, h2 -> 2, etc.)
        level = int(el.name[1]) if el.name and len(el.name) > 1 else 1
        
        # Notion only supports heading levels 1-3
        level = min(3, level)
        
        # Extract rich text with links and colors
        rich_text = extract_rich_text(el, colorid_map=colorid_map)
        
        return {
            'type': 'heading',
            'level': level,
            'text': text,
            'rich_text': rich_text
        }
    
    return None
