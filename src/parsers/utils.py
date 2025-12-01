"""Utility functions for HTML parsing"""

from bs4 import NavigableString, Tag
from typing import Any, Dict, List, Optional
import logging

from ..image_utils import extract_image_src, should_skip_image
from ..models.errors import ErrorCode, get_error_message
from ..rich_text_parser import extract_rich_text


def replace_emoticons_with_emoji(element: Tag) -> None:
    """
    Replace emoticon images with their emoji fallback text in-place.
    
    Args:
        element: The element to process
    """
    emoticon_imgs = element.find_all('img', class_=lambda x: x and 'emoticon' in x)
    
    for img in emoticon_imgs:
        emoji_fallback = img.get('data-emoji-fallback') or img.get('alt', '')
        if emoji_fallback:
            emoji_fallback = emoji_fallback.strip()
            if not emoji_fallback:
                logging.warning(get_error_message(
                    ErrorCode.WARN_EMOTICON_FALLBACK_INVALID,
                    f"Emoticon fallback is empty in element: {img.get('src', 'unknown')}"
                ))
                continue
            
            try:
                img.replace_with(emoji_fallback)
            except Exception as e:
                logging.warning(get_error_message(
                    ErrorCode.WARN_EMOTICON_CONVERSION_FAILED,
                    f"Failed to convert emoticon to emoji: {str(e)}"
                ))
        else:
            logging.warning(get_error_message(
                ErrorCode.WARN_EMOTICON_NO_FALLBACK,
                f"Emoticon has no emoji fallback: {img.get('src', 'unknown')}"
            ))


def parse_list_item(li: Tag, colorid_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Parse a list item that may contain multiple paragraphs, nested lists, etc.
    
    Args:
        li: The list item Tag element
        colorid_map: Optional color ID mappings for rich text
        
    Returns:
        Dictionary with 'text', 'rich_text', and optional 'children' for nested content
    """
    item_data = {'text': '', 'children': []}
    text_parts = []
    
    # Process direct children of the list item
    for child in li.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                text_parts.append(text)
                
        elif isinstance(child, Tag):
            if child.name == 'p':
                # Paragraph - preserve spacing around inline elements
                para_text = child.get_text(' ', strip=True)
                if para_text:
                    text_parts.append(para_text)
                    
            elif child.name in ('ul', 'ol'):
                # Nested list - parse recursively
                nested_items = []
                for nested_li in child.find_all('li', recursive=False):
                    nested_items.append(parse_list_item(nested_li, colorid_map=colorid_map))
                    
                if nested_items:
                    item_data['children'].append({
                        'type': 'list',
                        'ordered': child.name == 'ol',
                        'items': nested_items
                    })
                    
            elif child.name == 'code':
                # Inline code
                text_parts.append(child.get_text(strip=True))
                
            elif child.name == 'img':
                # Handle emoticons
                if 'emoticon' in child.get('class', []):
                    emoji_fallback = child.get('data-emoji-fallback') or child.get('alt', '')
                    if emoji_fallback:
                        emoji_fallback = emoji_fallback.strip()
                        if not emoji_fallback:
                            logging.warning(get_error_message(
                                ErrorCode.WARN_EMOTICON_FALLBACK_INVALID,
                                f"Emoticon fallback is empty in list item: {child.get('src', 'unknown')}"
                            ))
                        else:
                            text_parts.append(emoji_fallback)
                    else:
                        logging.warning(get_error_message(
                            ErrorCode.WARN_EMOTICON_NO_FALLBACK,
                            f"Emoticon in list item has no emoji fallback: {child.get('src', 'unknown')}"
                        ))
                else:
                    # Regular image - add to children
                    src = extract_image_src(child)
                    if src and not should_skip_image(child, src):
                        item_data['children'].append({'type': 'image', 'src': src})
                        
            else:
                # Other elements - extract text
                elem_text = child.get_text(' ', strip=True)
                if elem_text:
                    text_parts.append(elem_text)
    
    # Join text parts with line breaks to preserve structure
    item_data['text'] = '\n'.join(text_parts) if text_parts else li.get_text(strip=True)
    
    # Extract rich text for the list item
    item_data['rich_text'] = extract_rich_text(li, colorid_map=colorid_map)
    
    # If no children, remove the empty list
    if not item_data['children']:
        del item_data['children']
    
    return item_data
