"""Parser for Confluence embedded file wrappers"""

from bs4 import Tag
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging

from ..image_utils import extract_image_src, should_skip_image
from ..models.errors import ErrorCode, get_error_message
from ..rich_text_parser import extract_rich_text


def parse_embedded_wrapper(el: Tag, colorid_map: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Parse Confluence embedded file wrapper spans.
    
    These wrappers can contain:
    - Images (including emoticons)
    - Videos
    - Document attachments
    
    Args:
        el: The span element with 'confluence-embedded-file-wrapper' class
        colorid_map: Optional color ID mappings for rich text
        
    Returns:
        List of blocks extracted from the wrapper
    """
    blocks = []
    
    # First check for images
    img = el.find('img')
    if img:
        img_block = process_wrapper_image(img)
        if img_block:
            blocks.append(img_block)
            return blocks
    
    # Check for video or document links
    file_link = el.find('a', href=True)
    if file_link:
        file_block = process_wrapper_file_link(file_link)
        if file_block:
            blocks.append(file_block)
            return blocks
    
    # Log if we couldn't extract anything
    logging.debug(get_error_message(
        ErrorCode.WARN_EMBEDDED_WRAPPER_SKIPPED,
        f"Embedded wrapper span found but no recognized media extracted"
    ))
    
    return blocks


def process_wrapper_image(img: Tag) -> Optional[Dict[str, Any]]:
    """
    Process an image element within an embedded wrapper.
    
    Args:
        img: The image Tag element
        
    Returns:
        Dictionary with image or emoticon block, or None if skipped
    """
    # Check if it's an emoticon - convert to emoji (inline)
    if 'emoticon' in img.get('class', []):
        emoji_fallback = img.get('data-emoji-fallback') or img.get('alt', '')
        if emoji_fallback:
            emoji_fallback = emoji_fallback.strip()
            if not emoji_fallback:
                logging.warning(get_error_message(
                    ErrorCode.WARN_EMOTICON_FALLBACK_INVALID,
                    f"Emoticon fallback is empty in wrapper: {img.get('src', 'unknown')}"
                ))
                return None
            else:
                # Return as text paragraph for inline display
                return {
                    'type': 'paragraph',
                    'text': emoji_fallback,
                    'rich_text': [{'type': 'text', 'text': {'content': emoji_fallback}}]
                }
        else:
            logging.warning(get_error_message(
                ErrorCode.WARN_EMOTICON_NO_FALLBACK,
                f"Emoticon in wrapper has no emoji fallback: {img.get('src', 'unknown')}"
            ))
            return None
    
    # Regular image
    src = extract_image_src(img)
    if src and not should_skip_image(img, src):
        return {'type': 'image', 'src': src}
    
    return None


def process_wrapper_file_link(file_link: Tag) -> Optional[Dict[str, Any]]:
    """
    Process a file link within an embedded wrapper.
    
    Args:
        file_link: The anchor Tag element with href
        
    Returns:
        Dictionary with video or file block, or None if not recognized
    """
    file_href = file_link.get('href', '')
    file_name = file_link.get_text(strip=True) or Path(file_href).name
    
    # Check if it's a video
    if any(ext in file_href for ext in ['.mp4', '.mov', '.avi', '.webm']):
        # Remove query parameters from video URL if needed
        if '?' in file_href:
            file_href = file_href.split('?')[0]
        return {'type': 'video', 'src': file_href, 'name': file_name}
    
    # Check if it's a document attachment
    if file_href.startswith('attachments/'):
        file_ext = Path(file_name).suffix.lower()
        # Skip images - they're handled separately
        image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp']
        if file_ext not in image_exts:
            return {'type': 'file', 'src': file_href, 'name': file_name}
    
    return None


