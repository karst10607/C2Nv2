"""Paragraph parser for extracting HTML paragraphs into Notion-compatible format"""

from bs4 import BeautifulSoup, NavigableString, Tag
from typing import Any, Dict, List, Optional
import logging

from ..image_utils import should_skip_image, extract_image_src
from ..models.errors import ErrorCode, get_error_message
from ..rich_text_parser import extract_rich_text
from .utils import replace_emoticons_with_emoji


def parse_paragraph(el: Tag, colorid_map: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Parse a paragraph element into Notion blocks.
    
    This handles emoticon conversion to inline emoji and extracts remaining images.
    
    Args:
        el: The paragraph Tag element
        colorid_map: Optional color ID mappings for rich text
        
    Returns:
        List of blocks (paragraph block and optional image blocks)
    """
    blocks = []
    
    # Replace emoticons with emoji characters BEFORE extracting text
    # This makes them inline emoji in rich text, not separate image blocks
    replace_emoticons_with_emoji(el)
    
    # Extract rich text preserving links and colors (emoticons are now emoji)
    paragraph_text = el.get_text(strip=True)
    
    if paragraph_text:
        rich_text = extract_rich_text(el, colorid_map=colorid_map)
        blocks.append({
            'type': 'paragraph', 
            'text': paragraph_text,
            'rich_text': rich_text
        })
    
    # Add remaining inline images (non-emoticon) after the paragraph
    remaining_imgs = el.find_all('img')
    for img in remaining_imgs:
        src = extract_image_src(img)
        if src and not should_skip_image(img, src):
            blocks.append({'type': 'image', 'src': src})
    
    return blocks


