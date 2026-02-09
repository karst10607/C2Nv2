"""Parser for Confluence macros (JIRA, Google embeds, etc.)"""

from bs4 import Tag
from typing import Any, Dict, List, Optional
import re
import logging

from ..models.errors import ErrorCode, get_error_message


def is_jira_macro(el: Tag) -> bool:
    """
    Check if element is a JIRA macro.
    
    Args:
        el: The HTML element to check
        
    Returns:
        True if it's a JIRA macro
    """
    classes = el.get('class', [])
    
    # Can be in div or span elements
    if el.name in ['div', 'span']:
        return 'confluence-jim-macro' in classes or 'jira-issue' in classes
    
    return False


def parse_jira_macro(el: Tag, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a JIRA macro into a Notion callout block.
    
    Args:
        el: The div element containing JIRA macro
        context: Context with colorid_map, soup, etc.
        
    Returns:
        Callout block with JIRA information
    """
    # Extract JIRA key from data attributes
    jira_key = el.get('data-jira-key', '')
    
    # Try to extract from classes if not in data attribute
    if not jira_key:
        for class_name in el.get('class', []):
            if class_name.startswith('jira-issue-'):
                jira_key = class_name.replace('jira-issue-', '')
                break
    
    # Extract summary text
    summary = ''
    summary_el = el.find(class_='summary')
    if summary_el:
        summary = summary_el.get_text(strip=True)
    
    # Extract status
    status = ''
    status_el = el.find(class_='aui-lozenge')
    if status_el:
        status = status_el.get_text(strip=True)
    
    # Build the callout content
    if jira_key:
        content = f"JIRA: {jira_key}"
        if summary:
            content += f" - {summary}"
        if status:
            content += f" [{status}]"
    else:
        # Fallback to any text content
        content = el.get_text(strip=True) or "JIRA Issue"
    
    # Log that we found a JIRA macro
    logging.info(f"Found JIRA macro: {jira_key or 'unknown'}")
    
    return {
        'type': 'callout',
        'callout': {
            'rich_text': [{'type': 'text', 'text': {'content': content}}],
            'icon': {'emoji': '🎫'},
            'color': 'blue'
        }
    }


def is_google_embed(el: Tag) -> bool:
    """
    Check if element is a Google embed (Docs, Sheets, Slides).
    
    Args:
        el: The HTML element to check
        
    Returns:
        True if it's a Google embed
    """
    # Check for data-card-appearance="embed"
    if el.get('data-card-appearance') == 'embed':
        href = el.get('href', '')
        return any(domain in href for domain in ['docs.google.com', 'sheets.google.com', 'slides.google.com'])
    
    # Check for iframe with Google domains
    if el.name == 'iframe':
        src = el.get('src', '')
        return any(domain in src for domain in ['docs.google.com', 'sheets.google.com', 'slides.google.com'])
    
    return False


def parse_google_embed(el: Tag, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a Google embed into a Notion embed block.
    
    Args:
        el: The element containing Google embed
        context: Context with colorid_map, soup, etc.
        
    Returns:
        Embed block with Google content
    """
    # Get the URL
    url = ''
    if el.name == 'a':
        url = el.get('href', '')
    elif el.name == 'iframe':
        url = el.get('src', '')
    
    if not url:
        return None
    
    # Determine the type
    embed_type = 'Google Document'
    if 'sheets.google.com' in url:
        embed_type = 'Google Sheets'
    elif 'slides.google.com' in url:
        embed_type = 'Google Slides'
    
    # Extract title if available
    title = el.get_text(strip=True) or embed_type
    
    logging.info(f"Found {embed_type} embed: {url}")
    
    # Notion doesn't support direct embeds, so create a callout with link
    return {
        'type': 'callout',
        'callout': {
            'rich_text': [{
                'type': 'text',
                'text': {'content': f"{embed_type}: {title}\n{url}"}
            }],
            'icon': {'emoji': '📄' if 'docs' in url else '📊' if 'sheets' in url else '📽️'},
            'color': 'gray'
        }
    }


def is_info_panel(el: Tag) -> bool:
    """
    Check if element is a Confluence info/warning/tip/note panel.
    
    These panels have classes like:
    - confluence-information-macro
    - confluence-information-macro-information (info)
    - confluence-information-macro-warning (warning)
    - confluence-information-macro-tip (tip)
    - confluence-information-macro-note (note)
    
    Args:
        el: The HTML element to check
        
    Returns:
        True if it's an info panel
    """
    if el.name != 'div':
        return False
    
    classes = el.get('class', [])
    if isinstance(classes, str):
        classes = classes.split()
    
    return 'confluence-information-macro' in classes


def parse_info_panel(el: Tag, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a Confluence info panel into a panel block for markdown.
    
    Args:
        el: The div element containing the info panel
        context: Context with colorid_map, soup, etc.
        
    Returns:
        Panel block with type, icon, and content
    """
    from ..rich_text_parser import extract_rich_text
    
    classes = el.get('class', [])
    if isinstance(classes, str):
        classes = classes.split()
    
    # Determine panel type from classes
    panel_type = 'info'  # default
    icon = 'ℹ️'
    
    if 'confluence-information-macro-warning' in classes:
        panel_type = 'warning'
        icon = '⚠️'
    elif 'confluence-information-macro-tip' in classes:
        panel_type = 'tip'
        icon = '💡'
    elif 'confluence-information-macro-note' in classes:
        panel_type = 'note'
        icon = '📝'
    elif 'confluence-information-macro-information' in classes:
        panel_type = 'info'
        icon = 'ℹ️'
    
    # Extract title if present
    title = ''
    title_el = el.find(class_='confluence-information-macro-title')
    if title_el:
        title = title_el.get_text(strip=True)
    
    # Extract body content
    body = ''
    body_el = el.find(class_='confluence-information-macro-body')
    if body_el:
        body = body_el.get_text(separator='\n', strip=True)
    else:
        # Fallback to full element content minus the icon
        body = el.get_text(separator='\n', strip=True)
    
    # Combine title and body
    content = f"**{title}**\n{body}" if title else body
    
    # Extract rich text for better formatting
    colorid_map = context.get('colorid_map')
    rich_text = []
    if body_el:
        rich_text = extract_rich_text(body_el, colorid_map=colorid_map)
    
    logging.info(f"Found info panel: {panel_type}")
    
    return {
        'type': 'panel',
        'panel_type': panel_type,
        'icon': icon,
        'title': title,
        'text': content,
        'rich_text': rich_text
    }


def detect_other_macros(el: Tag) -> Optional[str]:
    """
    Detect other Confluence macros that might need handling.
    
    Args:
        el: The HTML element to check
        
    Returns:
        Macro type if detected, None otherwise
    """
    if el.name == 'div':
        classes = el.get('class', [])
        
        # Code macro
        if 'code-macro' in classes:
            return 'code-macro'
        
        # Panel macro
        if 'panel-macro' in classes:
            return 'panel-macro'
        
        # Info/Warning/Tip macros
        if any(macro in classes for macro in ['info-macro', 'warning-macro', 'tip-macro', 'note-macro']):
            return 'alert-macro'
        
        # Expand macro
        if 'expand-macro' in classes:
            return 'expand-macro'
    
    return None
