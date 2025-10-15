from typing import Any, Dict, List

def rich_text(text: str) -> List[Dict[str, Any]]:
    return [{"type": "text", "text": {"content": text}}]

def to_notion_blocks(ast: Dict[str, Any], image_base_url: str, max_cols: int = 6) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    for b in ast.get('blocks', []):
        t = b['type']
        if t == 'heading':
            blocks.append({f"heading_{min(3, max(1, b.get('level',1)))}": {"rich_text": rich_text(b.get('text',''))}, "object":"block", "type": f"heading_{min(3, max(1, b.get('level',1)))}"})
        elif t == 'paragraph':
            blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(b.get('text',''))}})
        elif t == 'list':
            for it in b.get('items', []):
                key = 'numbered_list_item' if b.get('ordered') else 'bulleted_list_item'
                blocks.append({"object":"block","type":key, key:{"rich_text": rich_text(it.get('text',''))}})
        elif t == 'code':
            blocks.append({"object":"block","type":"code","code":{"rich_text": rich_text(b.get('text','')), "language":"plain text"}})
        elif t == 'image':
            url = b.get('src','')
            if url and not url.startswith(('http://','https://')):
                url = image_base_url.rstrip('/') + '/' + url.lstrip('/')
            blocks.append({"object":"block","type":"image","image":{"type":"external","external":{"url": url}}})
        elif t == 'table':
            # For each row, make a column_list; split > MAX_COLS into multiple lists
            for row in b.get('rows', []):
                cells = row.get('cells', [])
                for start in range(0, len(cells), max_cols):
                    chunk = cells[start:start+max_cols]
                    blocks.append({"object":"block","type":"column_list","column_list":{"children": [
                        {"object":"block","type":"column","column":{"children": _cell_children(c.get('children',[]), image_base_url)}}
                        for c in chunk
                    ]}})
    return blocks

def _cell_children(children: List[Dict[str, Any]], image_base_url: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ch in children:
        t = ch['type']
        if t == 'paragraph':
            out.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text(ch.get('text',''))}})
        elif t == 'list':
            for it in ch.get('items', []):
                key = 'numbered_list_item' if ch.get('ordered') else 'bulleted_list_item'
                out.append({"object":"block","type":key, key:{"rich_text": rich_text(it.get('text',''))}})
        elif t == 'code':
            out.append({"object":"block","type":"code","code":{"rich_text": rich_text(ch.get('text','')), "language":"plain text"}})
        elif t == 'image':
            url = ch.get('src','')
            if url and not url.startswith(('http://','https://')):
                url = image_base_url.rstrip('/') + '/' + url.lstrip('/')
            out.append({"object":"block","type":"image","image":{"type":"external","external":{"url": url}}})
    if not out:
        out.append({"object":"block","type":"paragraph","paragraph":{"rich_text": rich_text("")}})
    return out
