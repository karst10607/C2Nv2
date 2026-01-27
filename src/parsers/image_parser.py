"""Image parser for extracting HTML images into Notion-compatible format"""

from bs4 import Tag
from typing import Any, Dict, Optional
import logging

from ..image_utils import extract_image_src, should_skip_image
from ..models.errors import ErrorCode, get_error_message


def parse_image(el: Tag) -> Optional[Dict[str, Any]]:
    """
    Parse an image element into a Notion block.
    
    This handles:
    - Regular images
    - Emoticons (converts to inline emoji text)
    - Skips UI elements, bullets, icons
    
    Args:
        el: The img Tag element
        
    Returns:
        Dictionary with image or paragraph block, or None if skipped
    """
    src = extract_image_src(el)
    
    # Check if it's an emoticon - convert to emoji (inline)
    if 'emoticon' in el.get('class', []):
        emoji_fallback = el.get('data-emoji-fallback') or el.get('alt', '')
        if emoji_fallback:
            emoji_fallback = emoji_fallback.strip()
            if not emoji_fallback:
                logging.warning(get_error_message(
                    ErrorCode.WARN_EMOTICON_FALLBACK_INVALID,
                    f"Emoticon fallback is empty for image: {src or 'unknown'}"
                ))
                return None
            else:
                # Return emoticon as inline text paragraph
                return {
                    'type': 'paragraph',
                    'text': emoji_fallback,
                    'rich_text': [{'type': 'text', 'text': {'content': emoji_fallback}}]
                }
        else:
            logging.warning(get_error_message(
                ErrorCode.WARN_EMOTICON_NO_FALLBACK,
                f"Emoticon image has no emoji fallback: {src or 'unknown'}"
            ))
            return None
    
    # Regular image - check if should skip
    if src and not should_skip_image(el, src):
        return {'type': 'image', 'src': src}
    
    return None


