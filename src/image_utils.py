"""
Utilities for image processing and filtering.
Centralizes image-related logic to avoid duplication.
"""
from typing import Optional
from bs4 import Tag
import logging
from .models.errors import ErrorCode, get_error_message


def should_skip_image(img_element: Tag, src: str, allow_emoticons: bool = False) -> bool:
    """
    Determine if an image should be skipped during import.
    
    Filters out:
    - UI icons (JIRA, Confluence icons)
    - Emoticons (unless allow_emoticons=True)
    - Bullets and decorative elements
    - Confluence thumbnails
    - GIF animations (usually UI elements)
    
    Args:
        img_element: BeautifulSoup Tag element
        src: Image source URL
        allow_emoticons: If True, allow emoticons as images (default: False, convert to emoji)
    
    Returns:
        True if image should be skipped, False if it should be imported
    """
    # Check element class for UI indicators
    img_class = img_element.get('class', [])
    if isinstance(img_class, list):
        img_class = ' '.join(img_class)
    
    # Skip icons and bullets (but allow emoticons if requested)
    skip_classes = ['icon', 'bullet']
    if not allow_emoticons:
        skip_classes.append('emoticon')
    
    if any(x in str(img_class) for x in skip_classes):
        return True
    
    # Check URL patterns
    skip_patterns = [
        '/universal_avatar/',  # JIRA/Confluence avatars
        '/icons/',             # UI icons
        'attachments/thumbnails/',  # Confluence thumbnail endpoints
        'placeholder/unknown-attachment',  # Placeholder for missing attachments
        'unknown-attachment',  # Generic unknown attachment placeholder
        '/plugins/servlet/confluence/placeholder/'  # Confluence placeholder images
    ]
    
    # Only skip emoticons from URL if not explicitly allowed
    if not allow_emoticons:
        skip_patterns.append('emoticons/')
    
    for pattern in skip_patterns:
        if pattern in src:
            if 'placeholder' in pattern or 'unknown-attachment' in pattern:
                logging.debug(get_error_message(
                    ErrorCode.WARN_PLACEHOLDER_IMAGE_SKIPPED,
                    f"Skipping placeholder image: {src}"
                ))
            return True
    
    # Skip temporary files
    if src.endswith('.tmp'):
        logging.debug(get_error_message(
            ErrorCode.WARN_TEMP_FILE_SKIPPED,
            f"Skipping temporary file: {src}"
        ))
        return True
    
    # Skip GIF files (usually UI animations)
    # Exception: Allow GIFs if they're emoticons and allow_emoticons=True
    if src.endswith('.gif'):
        if allow_emoticons and 'emoticon' in str(img_class).lower():
            return False  # Allow emoticon GIFs
        return True
    
    return False


def extract_image_src(img_element: Tag) -> Optional[str]:
    """
    Extract and normalize image source URL from img element.
    
    Prefers data-image-src over src (Confluence exports use data-image-src
    for full-size images, src for thumbnails).
    
    Removes query parameters that can cause 404s.
    
    Args:
        img_element: BeautifulSoup Tag element
    
    Returns:
        Normalized image URL, or None if no valid source
    """
    src = img_element.get('data-image-src') or img_element.get('src')
    
    if not src:
        return None
    
    # Remove query parameters (e.g., ?width=760)
    if '?' in src:
        src = src.split('?')[0]
    
    return src


def is_content_image(img_element: Tag) -> bool:
    """
    Check if an image is actual content (not UI decoration).
    
    Args:
        img_element: BeautifulSoup Tag element
    
    Returns:
        True if this is a content image that should be imported
    """
    src = extract_image_src(img_element)
    
    if not src:
        return False
    
    if should_skip_image(img_element, src):
        return False
    
    return True


def normalize_image_url(src: str, base_url: str) -> str:
    """
    Convert relative image path to absolute URL using base URL.
    
    Args:
        src: Image source (relative or absolute)
        base_url: Base URL for serving images (e.g., tunnel URL)
    
    Returns:
        Absolute URL for the image
    """
    if src.startswith(('http://', 'https://')):
        # Already absolute
        return src
    
    # Make relative paths absolute
    base = base_url.rstrip('/')
    src = src.lstrip('/')
    return f"{base}/{src}"


def is_table_icon(img_element: Tag, src: str) -> bool:
    """
    Check if image is likely a small icon/emoji suitable for tables.
    
    Icons are small images that can be rendered inline in Notion tables
    as emojis or small decorative elements.
    
    Args:
        img_element: BeautifulSoup Tag element
        src: Image source URL
        
    Returns:
        True if image is a small icon suitable for table cells
    """
    # Check explicit size attributes
    width = img_element.get('width')
    height = img_element.get('height')
    
    if width and height:
        try:
            w = int(str(width).replace('px', ''))
            h = int(str(height).replace('px', ''))
            # Icons are typically 32x32 or smaller
            if w <= 32 and h <= 32:
                return True
        except (ValueError, TypeError):
            pass
    
    # Check common icon URL patterns
    icon_patterns = [
        'icon', 'emoji', 'emoticon', 
        '/16x16/', '/24x24/', '/32x32/', '/48x48/',
        '/small/', '/tiny/', '/mini/'
    ]
    
    src_lower = src.lower()
    if any(pattern in src_lower for pattern in icon_patterns):
        return True
    
    # Check filename patterns
    filename = src.split('/')[-1].lower()
    
    # Small GIFs are often icons
    if filename.endswith('.gif') and len(filename) < 20:
        return True
    
    # Common icon file patterns
    if filename.endswith('.ico'):
        return True
    
    # Check for status/priority icons
    status_patterns = ['status', 'priority', 'flag', 'check', 'cross', 'tick']
    if any(pattern in filename for pattern in status_patterns):
        return True
    
    return False

