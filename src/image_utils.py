"""
Utilities for image processing and filtering.
Centralizes image-related logic to avoid duplication.
"""
from typing import Optional
from bs4 import Tag


def should_skip_image(img_element: Tag, src: str) -> bool:
    """
    Determine if an image should be skipped during import.
    
    Filters out:
    - UI icons (JIRA, Confluence icons)
    - Emoticons
    - Bullets and decorative elements
    - Confluence thumbnails
    - GIF animations (usually UI elements)
    
    Args:
        img_element: BeautifulSoup Tag element
        src: Image source URL
    
    Returns:
        True if image should be skipped, False if it should be imported
    """
    # Check element class for UI indicators
    img_class = img_element.get('class', [])
    if isinstance(img_class, list):
        img_class = ' '.join(img_class)
    
    if any(x in str(img_class) for x in ['icon', 'emoticon', 'bullet']):
        return True
    
    # Check URL patterns
    skip_patterns = [
        '/universal_avatar/',  # JIRA/Confluence avatars
        '/icons/',             # UI icons
        'emoticons/',          # Emoticon images
        'attachments/thumbnails/'  # Confluence thumbnail endpoints
    ]
    
    if any(pattern in src for pattern in skip_patterns):
        return True
    
    # Skip GIF files (usually UI animations)
    if src.endswith('.gif'):
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

