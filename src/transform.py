from typing import Any, Dict, List, Optional, Tuple
from bs4 import Tag
import logging
import re

from .constants import NOTION_TEXT_LIMIT, MAX_COLUMNS_PER_ROW, MIN_COLUMN_HEIGHT, NOTION_TABLE_ROW_LIMIT
from .image_utils import is_table_icon, extract_image_src
from .models.errors import ErrorCode, get_error_message
from .rich_text_parser import split_rich_text_by_length

# URL scheme for Notion native file uploads
NOTION_NATIVE_URL_SCHEME = "notion-file-upload://"


def sanitize_rich_text(rich_text_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure all rich_text segments are within Notion's 2000 character limit.
    
    Notion API rejects any rich_text segment where text.content > 2000 characters.
    This function splits oversized segments while preserving formatting and links.
    """
    if not rich_text_list:
        return rich_text_list
    return split_rich_text_by_length(rich_text_list, NOTION_TEXT_LIMIT)


def sanitize_block_rich_text(block: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all rich_text fields in a block and its children.
    
    This ensures no rich_text segment exceeds Notion's 2000 char limit.
    """
    if not isinstance(block, dict):
        return block
    
    block_type = block.get('type')
    
    # List of block types that have rich_text directly
    rich_text_block_types = [
        'paragraph', 'heading_1', 'heading_2', 'heading_3',
        'bulleted_list_item', 'numbered_list_item', 'to_do',
        'toggle', 'callout', 'quote', 'code'
    ]
    
    # Sanitize rich_text in the block itself
    if block_type in rich_text_block_types:
        block_content = block.get(block_type, {})
        if 'rich_text' in block_content:
            block_content['rich_text'] = sanitize_rich_text(block_content['rich_text'])
    
    # Handle table rows specially - cells are arrays of rich_text
    if block_type == 'table_row':
        cells = block.get('table_row', {}).get('cells', [])
        for i, cell in enumerate(cells):
            if isinstance(cell, list):
                cells[i] = sanitize_rich_text(cell)
    
    # Recursively process children
    if 'children' in block:
        block['children'] = [sanitize_block_rich_text(child) for child in block['children']]
    
    return block


def create_media_block(block_type: str, url: str, caption: List[Dict] = None) -> Dict[str, Any]:
    """
    Create a Notion media block (image, video, file) with correct type.
    
    Handles both external URLs and Notion native file uploads.
    If URL starts with 'notion-file-upload://', uses file_upload type.
    Otherwise uses external type.
    
    Args:
        block_type: 'image', 'video', or 'file'
        url: The URL or notion-file-upload://id
        caption: Optional rich_text caption (only for file blocks)
    
    Returns:
        Notion block dictionary
    """
    if url.startswith(NOTION_NATIVE_URL_SCHEME):
        # Notion native upload - extract file_upload ID
        file_upload_id = url[len(NOTION_NATIVE_URL_SCHEME):]
        media_obj = {
            "type": "file_upload",
            "file_upload": {"id": file_upload_id}
        }
    else:
        # External URL
        media_obj = {
            "type": "external",
            "external": {"url": url}
        }
    
    # Add caption for file blocks
    if block_type == "file" and caption:
        media_obj["caption"] = caption
    
    return {
        "object": "block",
        "type": block_type,
        block_type: media_obj
    }


def create_metadata_callout(metadata: Dict[str, Optional[str]]) -> Optional[Dict[str, Any]]:
    """
    Create a Notion callout block with page metadata (author, dates).
    
    Args:
        metadata: Dict with 'created_by', 'created_date', 'last_modified_by', 'last_modified_date'
    
    Returns:
        Notion callout block dict or None if no metadata available
    """
    if not metadata or not any(metadata.values()):
        return None
    
    # Build metadata text
    parts = []
    
    # Created info
    if metadata.get('created_by'):
        created_info = f"Created by {metadata['created_by']}"
        if metadata.get('created_date'):
            # Validate date has year before adding
            date_str = metadata['created_date']
            if not re.search(r'\d{4}', date_str):
                logging.warning(get_error_message(
                    ErrorCode.WARN_METADATA_DATE_INCOMPLETE,
                    f"Created date missing year in callout: '{date_str}'"
                ))
            created_info += f" on {date_str}"
        parts.append(created_info)
    
    # Last modified info
    if metadata.get('last_modified_date'):
        modified_info = "Last modified"
        if metadata.get('last_modified_by'):
            modified_info += f" by {metadata['last_modified_by']}"
        date_str = metadata['last_modified_date']
        # Validate date has year before adding
        if not re.search(r'\d{4}', date_str):
            logging.warning(get_error_message(
                ErrorCode.WARN_METADATA_DATE_INCOMPLETE,
                f"Last modified date missing year in callout: '{date_str}'"
            ))
        modified_info += f" on {date_str}"
        parts.append(modified_info)
    
    if not parts:
        return None
    
    # Create rich text for callout
    callout_text = " • ".join(parts)
    rich_text = [{"type": "text", "text": {"content": callout_text}}]
    
    # Create callout block with info icon (ℹ️)
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": rich_text,
            "icon": {
                "emoji": "ℹ️"
            },
            "color": "gray"
        }
    }


def analyze_table_content(table_ast: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze table content to determine best rendering strategy.
    
    Returns:
        {
            'has_images': bool,
            'has_mixed_content': bool,  # Image + text in same cell
            'has_only_text': bool,
            'has_only_icons': bool,     # Only small GIFs/emojis
            'total_images': int,
            'total_icons': int,
            'cell_complexity': 'simple'|'moderate'|'complex'
        }
    """
    has_images = False
    has_text = False
    has_mixed_content = False
    has_merged_cells = False
    has_header_row = False
    has_header_cells = False
    total_images = 0
    total_icons = 0
    has_videos = False
    total_videos = 0
    has_files = False
    total_files = 0
    
    for row in table_ast.get('rows', []):
        # Check for header rows
        if row.get('is_header_row', False):
            has_header_row = True
        
        for cell in row.get('cells', []):
            # Check for header cells
            if cell.get('is_header', False):
                has_header_cells = True
            
            # Check for merged cells
            colspan = cell.get('colspan', 1)
            rowspan = cell.get('rowspan', 1)
            if colspan > 1 or rowspan > 1:
                has_merged_cells = True
            
            cell_has_image = False
            cell_has_text = False
            
            for child in cell.get('children', []):
                child_type = child.get('type')
                
                if child_type == 'image':
                    src = child.get('src', '')
                    # Create a minimal Tag object for icon detection
                    # In the actual implementation, we'd need the original img element
                    # For now, we'll use URL pattern matching only
                    if any(pattern in src.lower() for pattern in ['/icon', '/emoji', '/16x16/', '/24x24/', '/32x32/']):
                        total_icons += 1
                    else:
                        has_images = True
                        total_images += 1
                        cell_has_image = True
                
                elif child_type == 'video':
                    has_videos = True
                    total_videos += 1
                    cell_has_image = True  # Treat videos similarly to images for complexity
                
                elif child_type == 'file':
                    has_files = True
                    total_files += 1
                    cell_has_image = True  # Treat files similarly to images for complexity
                        
                elif child_type in ['paragraph', 'list', 'code']:
                    text = child.get('text', '')
                    if text and text.strip():
                        has_text = True
                        cell_has_text = True
            
            # Check for mixed content in single cell
            if cell_has_image and cell_has_text:
                has_mixed_content = True
    
    # Count total rows
    total_rows = len(table_ast.get('rows', []))
    
    # Determine complexity
    if has_mixed_content or total_images > 2:
        cell_complexity = 'complex'
    elif total_images > 0 or total_icons > 3:
        cell_complexity = 'moderate'
    else:
        cell_complexity = 'simple'
    
    return {
        'has_images': has_images,
        'has_videos': has_videos,
        'has_files': has_files,
        'has_mixed_content': has_mixed_content,
        'has_only_text': not has_images and not has_videos and not has_files and has_text,
        'has_only_icons': total_icons > 0 and total_images == 0 and total_videos == 0 and total_files == 0 and not has_text,
        'has_merged_cells': has_merged_cells,
        'has_header_row': has_header_row,
        'has_header_cells': has_header_cells,
        'total_images': total_images,
        'total_videos': total_videos,
        'total_files': total_files,
        'total_icons': total_icons,
        'total_rows': total_rows,
        'cell_complexity': cell_complexity
    }


def extract_cell_rich_text(cell: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all rich text content from a cell for native table rendering."""
    rich_text_parts = []
    
    for child in cell.get('children', []):
        child_type = child.get('type')
        
        if child_type == 'paragraph':
            rt = child.get('rich_text')
            if rt:
                rich_text_parts.extend(rt)
            else:
                text = child.get('text', '')
                if text:
                    rich_text_parts.extend(rich_text(text))
        elif child_type == 'list':
            # For lists in table cells, convert to inline text with bullets
            for item in child.get('items', []):
                prefix = "• " if not child.get('ordered') else f"{child.get('items', []).index(item) + 1}. "
                item_rt = item.get('rich_text')
                if item_rt:
                    # Prepend the bullet/number to the first text item
                    if item_rt and item_rt[0].get('type') == 'text':
                        first_item = item_rt[0].copy()
                        first_item['text']['content'] = prefix + first_item['text']['content']
                        rich_text_parts.append(first_item)
                        rich_text_parts.extend(item_rt[1:])
                else:
                    text = item.get('text', '')
                    if text:
                        rich_text_parts.extend(rich_text(prefix + text))
                # Add line break between items
                rich_text_parts.append({"type": "text", "text": {"content": "\n"}, "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}})
        elif child_type == 'code':
            text = child.get('text', '')
            if text:
                # Code blocks in table cells should be rendered as inline code
                rich_text_parts.extend(rich_text(text, code=True))
    
    # Remove trailing newline if present
    if rich_text_parts and rich_text_parts[-1].get('text', {}).get('content') == '\n':
        rich_text_parts = rich_text_parts[:-1]
    
    return rich_text_parts if rich_text_parts else rich_text("")

def extract_cell_text(cell: Dict[str, Any]) -> str:
    """Extract all text content from a cell for native table rendering (backwards compatibility)."""
    texts = []
    
    def extract_list_items(items, ordered=False, level=0):
        """Recursively extract text from list items, including nested lists."""
        result = []
        for i, item in enumerate(items):
            item_text = item.get('text', '')
            if item_text:
                indent = '  ' * level
                prefix = f"{i+1}. " if ordered else "• "
                result.append(indent + prefix + item_text)
            
            # Handle nested lists within this item
            if 'children' in item:
                for child in item['children']:
                    if child.get('type') == 'list':
                        nested_items = extract_list_items(
                            child.get('items', []), 
                            child.get('ordered', False), 
                            level + 1
                        )
                        result.extend(nested_items)
        return result
    
    for child in cell.get('children', []):
        child_type = child.get('type')
        
        if child_type == 'paragraph':
            text = child.get('text', '')
            if text:
                texts.append(text)
        elif child_type == 'list':
            items = child.get('items', [])
            list_texts = extract_list_items(items, child.get('ordered', False))
            texts.extend(list_texts)
        elif child_type == 'code':
            code = child.get('text', '')
            if code:
                texts.append(f"`{code}`")
    
    return '\n'.join(texts) if texts else ''


def transform_to_notion_table(table_ast: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Create native Notion table blocks for simple text-only tables.
    Splits large tables to respect Notion's 100-row limit.
    Handles merged cells by keeping content in first cell and emptying spanned cells.
    """
    rows = table_ast.get('rows', [])
    if not rows:
        return []
    
    # Calculate actual table width considering colspan
    max_width = 0
    for row in rows:
        width = sum(cell.get('colspan', 1) for cell in row.get('cells', []))
        max_width = max(max_width, width)
    
    if max_width == 0:
        return []
    
    blocks = []
    
    # Determine if first row/column are headers
    first_row_is_header = rows[0].get('is_header_row', False) if rows else False
    
    # Check if first column is all headers (for row headers)
    first_col_is_header = all(
        row['cells'][0].get('is_header', False) if row.get('cells') else False
        for row in rows
    ) if rows else False
    
    # Split rows into chunks of max 100 rows each
    for chunk_start in range(0, len(rows), NOTION_TABLE_ROW_LIMIT):
        chunk_rows = rows[chunk_start:chunk_start + NOTION_TABLE_ROW_LIMIT]
        
        # Only the first chunk gets the header flags
        is_first_chunk = chunk_start == 0
        
        # Create table block for this chunk
        table_block = {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": max_width,
                "has_column_header": first_row_is_header and is_first_chunk,
                "has_row_header": first_col_is_header,
                "children": []
            }
        }
        
        # Track cells affected by rowspan from previous rows
        rowspan_map = {}  # column_index -> (remaining_rows, text)
        
        # Add rows to this chunk
        for row_idx, row in enumerate(chunk_rows):
            cells = row.get('cells', [])
            
            row_block = {
                "object": "block",
                "type": "table_row",
                "table_row": {
                    "cells": []
                }
            }
            
            col_idx = 0
            cell_idx = 0
            
            # Build the complete row considering colspan and rowspan
            while col_idx < max_width:
                # Check if this column is affected by rowspan from above
                if col_idx in rowspan_map and rowspan_map[col_idx][0] > 0:
                    # Use empty cell for rowspanned position
                    row_block['table_row']['cells'].append(
                        rich_text("", bold=False)
                    )
                    rowspan_map[col_idx] = (rowspan_map[col_idx][0] - 1, rowspan_map[col_idx][1])
                    if rowspan_map[col_idx][0] == 0:
                        del rowspan_map[col_idx]
                    col_idx += 1
                elif cell_idx < len(cells):
                    cell = cells[cell_idx]
                    cell_rich_text = extract_cell_rich_text(cell)
                    colspan = cell.get('colspan', 1)
                    rowspan = cell.get('rowspan', 1)
                    is_header = cell.get('is_header', False)
                    
                    # Determine if this cell should be bold
                    # Bold if it's a header cell that's NOT in the primary header row/column
                    actual_row_idx = chunk_start + row_idx
                    should_be_bold = is_header and not (
                        (actual_row_idx == 0 and first_row_is_header) or
                        (col_idx == 0 and first_col_is_header)
                    )
                    
                    # Check if total text length exceeds limit
                    total_text_length = sum(len(rt.get('text', {}).get('content', '')) for rt in cell_rich_text)
                    if total_text_length > NOTION_TEXT_LIMIT:
                        # Fallback to plain text with truncation
                        cell_text = extract_cell_text(cell)
                        original_length = len(cell_text)
                        cell_text = cell_text[:NOTION_TEXT_LIMIT-3] + "..."
                        cell_rich_text = rich_text(cell_text, bold=should_be_bold)
                        # Log warning about truncation
                        logging.warning(
                            get_error_message(
                                ErrorCode.WARN_TABLE_CELL_TRUNCATED,
                                f"Cell at row {actual_row_idx + 1}, col {col_idx + 1} truncated from {original_length} to {NOTION_TEXT_LIMIT} characters"
                            )
                        )
                    elif should_be_bold:
                        # Apply bold to all rich text items if needed
                        for rt_item in cell_rich_text:
                            if 'annotations' in rt_item:
                                rt_item['annotations']['bold'] = True
                    
                    # Add the main cell with rich text
                    row_block['table_row']['cells'].append(cell_rich_text)
                    
                    # Handle colspan - add empty cells
                    for _ in range(1, colspan):
                        if col_idx + 1 < max_width:
                            row_block['table_row']['cells'].append(
                                rich_text("", bold=False)
                            )
                    
                    # Track rowspan for future rows
                    if rowspan > 1:
                        for span_col in range(col_idx, min(col_idx + colspan, max_width)):
                            rowspan_map[span_col] = (rowspan - 1, "")
                    
                    col_idx += colspan
                    cell_idx += 1
                else:
                    # Fill remaining columns with empty cells
                    row_block['table_row']['cells'].append(
                        rich_text("", bold=False)
                    )
                    col_idx += 1
            
            table_block['table']['children'].append(row_block)
        
        blocks.append(table_block)
        
        # Add a note if table was split
        if chunk_start + NOTION_TABLE_ROW_LIMIT < len(rows):
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": rich_text(f"... table continues (rows {chunk_start + NOTION_TABLE_ROW_LIMIT + 1}-{min(chunk_start + 2*NOTION_TABLE_ROW_LIMIT, len(rows))})")
                }
            })
    
    return blocks


def rich_text(text: str, bold: bool = False, italic: bool = False, code: bool = False) -> List[Dict[str, Any]]:
    """
    Create rich text with optional formatting.
    
    Args:
        text: The text content
        bold: Whether to make text bold
        italic: Whether to make text italic
        code: Whether to format as inline code
    """
    # Notion has a NOTION_TEXT_LIMIT character limit per rich text item
    if len(text) <= NOTION_TEXT_LIMIT:
        return [{
            "type": "text", 
            "text": {"content": text},
            "annotations": {
                "bold": bold,
                "italic": italic,
                "strikethrough": False,
                "underline": False,
                "code": code,
                "color": "default"
            }
        }]
    
    # Split long text into multiple rich text items
    parts = []
    for i in range(0, len(text), NOTION_TEXT_LIMIT):
        parts.append({
            "type": "text",
            "text": {"content": text[i:i+NOTION_TEXT_LIMIT]},
            "annotations": {
                "bold": bold,
                "italic": italic,
                "strikethrough": False,
                "underline": False,
                "code": code,
                "color": "default"
            }
        })
    return parts

def split_long_paragraph(text: str, max_length: int = NOTION_TEXT_LIMIT) -> List[Dict[str, Any]]:
    """Split a long paragraph into multiple paragraph blocks."""
    if len(text) <= max_length:
        return [{"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(text)}}]
    
    # Try to split at sentence boundaries
    blocks = []
    current = ""
    sentences = text.replace(". ", ".|").replace("! ", "!|").replace("? ", "?|").split("|")
    
    for sentence in sentences:
        if len(current) + len(sentence) <= max_length:
            current += sentence + (" " if sentence and not sentence.endswith((".", "!", "?")) else "")
        else:
            if current:
                blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(current.strip())}})
            current = sentence + (" " if sentence and not sentence.endswith((".", "!", "?")) else "")
    
    if current:
        # If still too long, hard split
        while len(current) > max_length:
            blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(current[:max_length].strip())}})
            current = current[max_length:]
        if current.strip():
            blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(current.strip())}})
    
    return blocks

def flatten_deep_lists(blocks: List[Dict[str, Any]], current_depth: int = 0, max_depth: int = 2) -> List[Dict[str, Any]]:
    """
    Flatten deeply nested lists to avoid Notion API errors.
    Notion only supports 2-3 levels of list nesting.
    
    Args:
        blocks: List of blocks to process
        current_depth: Current nesting depth
        max_depth: Maximum allowed nesting depth (default 2)
    
    Returns:
        Flattened list of blocks
    """
    flattened = []
    
    for block in blocks:
        if block.get('type') in ['bulleted_list_item', 'numbered_list_item']:
            # Add the current block
            block_copy = block.copy()
            list_key = block['type']
            
            if current_depth >= max_depth and list_key in block and 'children' in block[list_key]:
                # We've hit max depth - flatten remaining nested lists
                children = block[list_key].get('children', [])
                # Remove children from the block
                block_copy[list_key] = block[list_key].copy()
                block_copy[list_key].pop('children', None)
                flattened.append(block_copy)
                
                # Convert nested list items to indented text
                for child in children:
                    if child.get('type') in ['bulleted_list_item', 'numbered_list_item']:
                        # Convert nested list item to indented paragraph
                        child_text = child.get(child['type'], {}).get('rich_text', [])
                        if child_text:
                            indent = "  " * (current_depth + 1)
                            prefix = "• " if child['type'] == 'bulleted_list_item' else "◦ "
                            
                            # Create indented paragraph
                            para_block = {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {"content": indent + prefix + child_text[0].get('text', {}).get('content', '')},
                                            "annotations": child_text[0].get('annotations', {})
                                        }
                                    ]
                                }
                            }
                            flattened.append(para_block)
                            
                            # Log warning about flattening
                            logging.warning(
                                get_error_message(
                                    ErrorCode.PARSE_DEEP_NESTED_LIST,
                                    f"List nesting exceeds Notion's limit at depth {current_depth + 1}"
                                )
                            )
                    else:
                        # Non-list child block
                        flattened.append(child)
            else:
                # Not at max depth yet or no children
                if list_key in block and 'children' in block[list_key]:
                    # Recursively process children
                    block_copy[list_key]['children'] = flatten_deep_lists(
                        block[list_key]['children'], 
                        current_depth + 1, 
                        max_depth
                    )
                flattened.append(block_copy)
        else:
            # Not a list item
            flattened.append(block)
    
    return flattened


def to_notion_blocks(ast: Dict[str, Any], image_base_url: str, max_cols: int = MAX_COLUMNS_PER_ROW,
                     preserve_table_layout: bool = True, min_column_height: int = MIN_COLUMN_HEIGHT,
                     smart_table_rendering: bool = True, table_image_threshold: int = 2) -> List[Dict[str, Any]]:
    """
    Convert AST to Notion blocks.
    
    Args:
        ast: The parsed HTML AST
        image_base_url: Base URL for images
        max_cols: Maximum columns per row
        preserve_table_layout: If True, add spacers to maintain consistent column height
        min_column_height: Minimum number of blocks per column (for tables)
        smart_table_rendering: If True, use native tables for simple content
        table_image_threshold: Max images before switching to column layout
    """
    blocks: List[Dict[str, Any]] = []
    
    # Add metadata callout at the top if available
    metadata = ast.get('metadata')
    if metadata:
        metadata_callout = create_metadata_callout(metadata)
        if metadata_callout:
            blocks.append(metadata_callout)
    for b in ast.get('blocks', []):
        t = b['type']
        if t == 'heading':
            # Use parsed rich text if available, otherwise create plain rich text
            rt = b.get('rich_text')
            if rt:
                blocks.append({f"heading_{min(3, max(1, b.get('level',1)))}": {"rich_text": rt}, "object":"block", "type": f"heading_{min(3, max(1, b.get('level',1)))}"})
            else:
                blocks.append({f"heading_{min(3, max(1, b.get('level',1)))}": {"rich_text": rich_text(b.get('text',''))}, "object":"block", "type": f"heading_{min(3, max(1, b.get('level',1)))}"})
        elif t == 'paragraph':
            text = b.get('text','')
            rt = b.get('rich_text')
            if len(text) > NOTION_TEXT_LIMIT:
                # For long text, we need to split but preserve rich text formatting
                # This is complex, so fall back to plain text for now
                blocks.extend(split_long_paragraph(text))
            else:
                if rt:
                    blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rt}})
                else:
                    blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(text)}})
        elif t == 'list':
            list_items = []
            for it in b.get('items', []):
                key = 'numbered_list_item' if b.get('ordered') else 'bulleted_list_item'
                text = it.get('text','')
                rt = it.get('rich_text')
                
                # For list items, truncate if too long rather than split
                if len(text) > NOTION_TEXT_LIMIT:
                    text = text[:NOTION_TEXT_LIMIT-3] + "..."
                    # If we have rich text, we need to truncate it too
                    # For now, fall back to plain text when truncating
                    rt = None
                
                # Create the list item block
                if rt:
                    item_block = {"object":"block","type":key, key:{"rich_text": rt}}
                else:
                    item_block = {"object":"block","type":key, key:{"rich_text": rich_text(text)}}
                
                # If the item has nested content (children), add them as children of this block
                if 'children' in it and it['children']:
                    item_block[key]['children'] = []
                    for child in it['children']:
                        child_blocks = to_notion_blocks({'blocks': [child]}, image_base_url, max_cols, 
                                                       preserve_table_layout, min_column_height,
                                                       smart_table_rendering, table_image_threshold)
                        item_block[key]['children'].extend(child_blocks)
                
                list_items.append(item_block)
            
            # Flatten deeply nested lists to avoid Notion API errors
            flattened_items = flatten_deep_lists(list_items)
            blocks.extend(flattened_items)
        elif t == 'code':
            text = b.get('text','')
            # For code blocks, truncate if too long
            if len(text) > NOTION_TEXT_LIMIT:
                text = text[:NOTION_TEXT_LIMIT-3] + "..."
            blocks.append({"object":"block","type":"code","code":{"rich_text": rich_text(text), "language":"plain text"}})
        elif t == 'image':
            url = b.get('src','')
            if url and not url.startswith(('http://','https://', NOTION_NATIVE_URL_SCHEME)):
                url = image_base_url.rstrip('/') + '/' + url.lstrip('/')
            blocks.append(create_media_block('image', url))
        elif t == 'drawio':
            # Handle Draw.io diagrams
            attachment_path = b.get('attachment_path')
            if attachment_path:
                # Only create image block if it's already a PNG
                if attachment_path.endswith('.png'):
                    url = image_base_url.rstrip('/') + '/' + attachment_path.lstrip('/')
                    blocks.append(create_media_block('image', url))
                    # Add caption
                    diagram_name = b.get('diagram_name') or b.get('attachment_id', 'Unknown')
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": rich_text(f"📊 Draw.io diagram: {diagram_name}")
                        }
                    })
                else:
                    # For .drawio files (XML), create a placeholder since we can't display them directly
                    diagram_name = b.get('diagram_name') or attachment_path.split('/')[-1]
                    blocks.append({
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": rich_text(f"Draw.io diagram: {diagram_name}\n(Original .drawio file - PNG export not available)"),
                            "icon": {"emoji": "📊"},
                            "color": "blue_background"
                        }
                    })
            else:
                # No attachment found, create placeholder
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": rich_text(f"⚠️ Draw.io diagram placeholder (ID: {b.get('container_id', 'Unknown')})"),
                        "icon": {"emoji": "📊"},
                        "color": "yellow_background"
                    }
                })
        elif t == 'file':
            # Handle file attachments (PDFs, docs, etc.)
            url = b.get('src','')
            if url and not url.startswith(('http://','https://', NOTION_NATIVE_URL_SCHEME)):
                # Relative URL - prepend base URL
                url = image_base_url.rstrip('/') + '/' + url.lstrip('/')
            
            file_name = b.get('name', 'Attachment')
            
            # Validate URL before creating block
            # For S3/CDN strategies (empty base URL), allow relative paths that will be uploaded later
            # Only reject truly invalid URLs (empty, just slash, etc.)
            if not url or url == '/' or url == image_base_url + '/':
                # Extract file extension for better logging
                from pathlib import Path
                file_ext = Path(file_name).suffix.lower() if file_name else 'unknown'
                logging.warning(get_error_message(ErrorCode.WARN_FILE_URL_INVALID, f"File: {file_name} ({file_ext}), URL: {url}"))
                print(f"[yellow]Warning: Cannot create file block for {file_name} ({file_ext}) - invalid URL[/yellow]")
                # Create a text block instead to preserve the information
                blocks.append({
                    "object":"block",
                    "type":"paragraph",
                    "paragraph":{
                        "rich_text": rich_text(f"📎 File attachment: {file_name} (invalid path)")
                    }
                })
                continue
                
            blocks.append(create_media_block('file', url, rich_text(file_name)))
        elif t == 'table':
            # Smart table rendering - analyze content first
            if smart_table_rendering:
                analysis = analyze_table_content(b)
                
            # Use native table for simple text content
            # Native tables in Notion cannot contain images, videos, or files, only text
            if (analysis['has_only_text'] or 
                (analysis['has_only_icons'] and analysis['total_icons'] <= 5)):
                    
                    # Try native table rendering
                    native_table = transform_to_notion_table(b)
                    if native_table:
                        blocks.extend(native_table)
                        continue
            
            # Fall back to column-based rendering for complex tables
            # For each row, make a column_list; split > MAX_COLS into multiple lists
            rows = b.get('rows', [])
            
            for row_idx, row in enumerate(rows):
                cells = row.get('cells', [])
                # Check if this is a header row
                is_header_row = row.get('is_header_row', False)
                
                # Check if this row contains images (for better layout preservation)
                has_images = any(
                    any(child.get('type') == 'image' for child in cell.get('children', []))
                    for cell in cells
                )
                
                for start in range(0, len(cells), max_cols):
                    chunk = cells[start:start+max_cols]
                    
                    # Skip empty chunks
                    if not chunk:
                        continue
                    
                    # Create column children with optional height normalization
                    column_children = []
                    max_height = 0
                    
                    # First pass: create columns and find max height
                    for c in chunk:
                        # Pass header info to style cells appropriately
                        children = _cell_children(c.get('children',[]), image_base_url, is_header_row)
                        
                        # For header rows, wrap content in a callout for visual distinction
                        if is_header_row and children:
                            # Extract text from first paragraph if exists
                            header_text = ""
                            if children[0].get('type') == 'paragraph':
                                rich_texts = children[0].get('paragraph', {}).get('rich_text', [])
                                if rich_texts:
                                    header_text = rich_texts[0].get('text', {}).get('content', '')
                            
                            # Create callout block with gray background for headers
                            header_block = {
                                "object": "block",
                                "type": "callout",
                                "callout": {
                                    "rich_text": rich_text(header_text, bold=True),
                                    "icon": {"emoji": "📊"},
                                    "color": "gray_background"
                                }
                            }
                            column_children.append([header_block])
                        else:
                            column_children.append(children)
                        
                        max_height = max(max_height, len(column_children[-1]))
                    
                    # Apply minimum height if preserving layout
                    if preserve_table_layout and has_images:
                        max_height = max(max_height, min_column_height)
                    
                    # Second pass: normalize heights if needed
                    if preserve_table_layout and has_images:
                        for i, children in enumerate(column_children):
                            while len(children) < max_height:
                                # Add empty paragraph as spacer
                                children.append({
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {"rich_text": rich_text("")}
                                })
                    
                    # Create the column_list block
                    # Notion requires at least 2 columns in a column_list
                    columns = [
                        {
                            "object": "block",
                            "type": "column",
                            "column": {"children": children}
                        }
                        for children in column_children
                    ]
                    
                    # If we only have 1 column, add an empty second column
                    if len(columns) == 1:
                        columns.append({
                            "object": "block",
                            "type": "column",
                            "column": {"children": [{
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {"rich_text": []}
                            }]}
                        })
                    
                    blocks.append({
                        "object": "block",
                        "type": "column_list",
                        "column_list": {"children": columns}
                    })
                    
                    # Add a divider after header rows to simulate table appearance
                    if is_header_row and row_idx == 0:
                        blocks.append({
                            "object": "block",
                            "type": "divider",
                            "divider": {}
                        })
    
    # Sanitize all rich_text to ensure no segment exceeds Notion's 2000 char limit
    blocks = [sanitize_block_rich_text(block) for block in blocks]
    
    return blocks

def _cell_children(children: List[Dict[str, Any]], image_base_url: str, is_header: bool = False) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ch in children:
        t = ch['type']
        if t == 'paragraph':
            text = ch.get('text','')
            rt = ch.get('rich_text')
            if len(text) > NOTION_TEXT_LIMIT:
                out.extend(split_long_paragraph(text))
            else:
                # Make header text bold
                if is_header and rt:
                    # Add bold to all rich text items
                    rt_bold = []
                    for item in rt:
                        item_copy = item.copy()
                        if 'annotations' in item_copy:
                            item_copy['annotations']['bold'] = True
                        rt_bold.append(item_copy)
                    out.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rt_bold}})
                elif is_header:
                    out.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(text, bold=True)}})
                elif rt:
                    out.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rt}})
                else:
                    out.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(text)}})
        elif t == 'list':
            for it in ch.get('items', []):
                key = 'numbered_list_item' if ch.get('ordered') else 'bulleted_list_item'
                text = it.get('text','')
                rt = it.get('rich_text')
                
                if len(text) > NOTION_TEXT_LIMIT:
                    text = text[:NOTION_TEXT_LIMIT-3] + "..."
                    rt = None  # Fall back to plain text when truncating
                
                # Create the list item block
                if rt:
                    item_block = {"object":"block","type":key, key:{"rich_text": rt}}
                else:
                    item_block = {"object":"block","type":key, key:{"rich_text": rich_text(text)}}
                
                # Note: Nested list items in table cells may not be well-supported by Notion
                # but we'll include them for completeness
                if 'children' in it and it['children']:
                    # For table cells, we can't have nested blocks, so we'll flatten the text
                    for child in it['children']:
                        if child.get('type') == 'list':
                            # Add nested list items as indented text
                            for nested_item in child.get('items', []):
                                nested_text = "  • " + nested_item.get('text', '')
                                if len(nested_text) > NOTION_TEXT_LIMIT:
                                    nested_text = nested_text[:NOTION_TEXT_LIMIT-3] + "..."
                                out.append({"object":"block","type":"paragraph",
                                          "paragraph":{"rich_text": rich_text(nested_text)}})
                
                out.append(item_block)
        elif t == 'code':
            text = ch.get('text','')
            if len(text) > NOTION_TEXT_LIMIT:
                text = text[:NOTION_TEXT_LIMIT-3] + "..."
            out.append({"object":"block","type":"code","code":{"rich_text": rich_text(text), "language":"plain text"}})
        elif t == 'image':
            url = ch.get('src','')
            if url and not url.startswith(('http://','https://', NOTION_NATIVE_URL_SCHEME)):
                url = image_base_url.rstrip('/') + '/' + url.lstrip('/')
            out.append(create_media_block('image', url))
        elif t == 'video':
            url = ch.get('src','')
            if url and not url.startswith(('http://','https://', NOTION_NATIVE_URL_SCHEME)):
                url = image_base_url.rstrip('/') + '/' + url.lstrip('/')
            out.append(create_media_block('video', url))
        elif t == 'file':
            url = ch.get('src','')
            if url and not url.startswith(('http://','https://', NOTION_NATIVE_URL_SCHEME)):
                url = image_base_url.rstrip('/') + '/' + url.lstrip('/')
            file_name = ch.get('name', 'Attachment')
            
            # Validate URL before creating block
            # For S3/CDN strategies (empty base URL), allow relative paths that will be uploaded later
            # Only reject truly invalid URLs (empty, just slash, etc.)
            if not url or url == '/' or url == image_base_url + '/':
                # Extract file extension for better logging
                from pathlib import Path
                file_ext = Path(file_name).suffix.lower() if file_name else 'unknown'
                logging.warning(get_error_message(ErrorCode.WARN_FILE_URL_INVALID, f"File in table: {file_name} ({file_ext}), URL: {url}"))
                print(f"[yellow]Warning: Cannot create file block in table for {file_name} ({file_ext}) - invalid URL[/yellow]")
                # Create a text block instead to preserve the information
                out.append({
                    "object":"block",
                    "type":"paragraph",
                    "paragraph":{
                        "rich_text": rich_text(f"📎 File: {file_name} (invalid path)")
                    }
                })
                continue
                
            out.append(create_media_block('file', url, rich_text(file_name)))
    if not out:
        out.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text("")}})
    return out
