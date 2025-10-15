from typing import Any, Dict, List, Optional

def rich_text(text: str) -> List[Dict[str, Any]]:
    # Notion has a 2000 character limit per rich text item
    if len(text) <= 2000:
        return [{"type": "text", "text": {"content": text}}]
    
    # Split long text into multiple rich text items
    parts = []
    for i in range(0, len(text), 2000):
        parts.append({"type": "text", "text": {"content": text[i:i+2000]}})
    return parts

def split_long_paragraph(text: str, max_length: int = 2000) -> List[Dict[str, Any]]:
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

def to_notion_blocks(ast: Dict[str, Any], image_base_url: str, max_cols: int = 6, 
                     preserve_table_layout: bool = True, min_column_height: int = 3) -> List[Dict[str, Any]]:
    """
    Convert AST to Notion blocks.
    
    Args:
        ast: The parsed HTML AST
        image_base_url: Base URL for images
        max_cols: Maximum columns per row
        preserve_table_layout: If True, add spacers to maintain consistent column height
        min_column_height: Minimum number of blocks per column (for tables)
    """
    blocks: List[Dict[str, Any]] = []
    for b in ast.get('blocks', []):
        t = b['type']
        if t == 'heading':
            blocks.append({f"heading_{min(3, max(1, b.get('level',1)))}": {"rich_text": rich_text(b.get('text',''))}, "object":"block", "type": f"heading_{min(3, max(1, b.get('level',1)))}"})
        elif t == 'paragraph':
            text = b.get('text','')
            if len(text) > 2000:
                blocks.extend(split_long_paragraph(text))
            else:
                blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(text)}})
        elif t == 'list':
            for it in b.get('items', []):
                key = 'numbered_list_item' if b.get('ordered') else 'bulleted_list_item'
                text = it.get('text','')
                # For list items, truncate if too long rather than split
                if len(text) > 2000:
                    text = text[:1997] + "..."
                blocks.append({"object":"block","type":key, key:{"rich_text": rich_text(text)}})
        elif t == 'code':
            text = b.get('text','')
            # For code blocks, truncate if too long
            if len(text) > 2000:
                text = text[:1997] + "..."
            blocks.append({"object":"block","type":"code","code":{"rich_text": rich_text(text), "language":"plain text"}})
        elif t == 'image':
            url = b.get('src','')
            if url and not url.startswith(('http://','https://')):
                url = image_base_url.rstrip('/') + '/' + url.lstrip('/')
            blocks.append({"object":"block","type":"image","image":{"type":"external","external":{"url": url}}})
        elif t == 'table':
            # For each row, make a column_list; split > MAX_COLS into multiple lists
            for row in b.get('rows', []):
                cells = row.get('cells', [])
                # Check if this row contains images (for better layout preservation)
                has_images = any(
                    any(child.get('type') == 'image' for child in cell.get('children', []))
                    for cell in cells
                )
                
                for start in range(0, len(cells), max_cols):
                    chunk = cells[start:start+max_cols]
                    
                    # Create column children with optional height normalization
                    column_children = []
                    max_height = 0
                    
                    # First pass: create columns and find max height
                    for c in chunk:
                        children = _cell_children(c.get('children',[]), image_base_url)
                        column_children.append(children)
                        max_height = max(max_height, len(children))
                    
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
                    blocks.append({
                        "object": "block",
                        "type": "column_list",
                        "column_list": {
                            "children": [
                                {
                                    "object": "block",
                                    "type": "column",
                                    "column": {"children": children}
                                }
                                for children in column_children
                            ]
                        }
                    })
    return blocks

def _cell_children(children: List[Dict[str, Any]], image_base_url: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ch in children:
        t = ch['type']
        if t == 'paragraph':
            text = ch.get('text','')
            if len(text) > 2000:
                out.extend(split_long_paragraph(text))
            else:
                out.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(text)}})
        elif t == 'list':
            for it in ch.get('items', []):
                key = 'numbered_list_item' if ch.get('ordered') else 'bulleted_list_item'
                text = it.get('text','')
                if len(text) > 2000:
                    text = text[:1997] + "..."
                out.append({"object":"block","type":key, key:{"rich_text": rich_text(text)}})
        elif t == 'code':
            text = ch.get('text','')
            if len(text) > 2000:
                text = text[:1997] + "..."
            out.append({"object":"block","type":"code","code":{"rich_text": rich_text(text), "language":"plain text"}})
        elif t == 'image':
            url = ch.get('src','')
            if url and not url.startswith(('http://','https://')):
                url = image_base_url.rstrip('/') + '/' + url.lstrip('/')
            out.append({"object":"block","type":"image","image":{"type":"external","external":{"url": url}}})
    if not out:
        out.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text("")}})
    return out
