from bs4 import BeautifulSoup, NavigableString, Tag
from pathlib import Path
from typing import Any, Dict, List

# Minimal AST nodes
# Node: { 'type': 'heading'|'paragraph'|'list'|'code'|'image'|'table', 'level', 'text', 'children', 'rows' }


def parse_html_file(path: Path) -> Dict[str, Any]:
    html = Path(path).read_text(encoding='utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'lxml')
    title = (soup.title.string.strip() if soup.title and soup.title.string else Path(path).stem)

    # Find the main content area (Confluence specific)
    content = soup.find('div', id='main-content') or soup.find('div', id='content') or soup.body or soup
    
    blocks: List[Dict[str, Any]] = []
    processed = set()  # Track processed elements to avoid duplicates

    for el in content.descendants:
        if isinstance(el, Tag) and el not in processed:
            name = el.name.lower()
            
            # Skip if this element is inside another block element we'll process
            if any(parent in processed for parent in el.parents):
                continue
                
            if name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                text = el.get_text(strip=True)
                if text:
                    blocks.append({'type': 'heading', 'level': min(3, int(name[1])), 'text': text})
                    processed.add(el)
            elif name == 'p':
                # Capture paragraph text and any inline images within
                imgs = list(el.find_all('img'))
                # Prefer data-image-src over src; sanitize src by stripping query
                def _img_src(img_el: Tag) -> str:
                    src = img_el.get('data-image-src') or img_el.get('src')
                    if not src:
                        return ''
                    if '?' in src:
                        src = src.split('?')[0]
                    return src
                # Paragraph text (excluding img alt texts)
                text_parts = []
                for child in el.children:
                    if isinstance(child, NavigableString):
                        t = str(child).strip()
                        if t:
                            text_parts.append(t)
                    elif isinstance(child, Tag) and child.name.lower() != 'img':
                        t = child.get_text(" ", strip=True)
                        if t:
                            text_parts.append(t)
                paragraph_text = " ".join([t for t in text_parts if t])
                if paragraph_text:
                    blocks.append({'type': 'paragraph', 'text': paragraph_text})
                # Add inline images after the paragraph
                for img in imgs:
                    # Skip UI icons by class name
                    img_class = img.get('class', [])
                    if isinstance(img_class, list):
                        img_class = ' '.join(img_class)
                    if any(x in str(img_class) for x in ['icon', 'emoticon', 'bullet']):
                        continue
                    
                    src = _img_src(img)
                    if not src:
                        continue
                    # Ignore Confluence thumbnail placeholders
                    if src.startswith('attachments/thumbnails/'):
                        continue
                    # Skip UI icons and avatars by URL pattern
                    if any(x in src for x in ['/universal_avatar/', '/icons/', 'emoticons/']):
                        continue
                    # Skip tiny gifs
                    if src.endswith('.gif'):
                        continue
                    
                    blocks.append({'type': 'image', 'src': src})
                processed.add(el)
            elif name in ('ul', 'ol'):
                items = []
                for li in el.find_all('li', recursive=False):
                    items.append({'text': li.get_text(" ", strip=True)})
                if items:
                    blocks.append({'type': 'list', 'ordered': name == 'ol', 'items': items})
                    processed.add(el)
            elif name == 'pre':
                code_el = el.find('code') or el
                blocks.append({'type': 'code', 'text': code_el.get_text("\n", strip=False)})
                processed.add(el)
            elif name == 'img':
                # Skip UI icons by class name
                img_class = el.get('class', [])
                if isinstance(img_class, list):
                    img_class = ' '.join(img_class)
                if any(x in str(img_class) for x in ['icon', 'emoticon', 'bullet']):
                    processed.add(el)
                    continue
                
                # Prefer data-image-src if present; fall back to src
                src = el.get('data-image-src') or el.get('src')
                if src:
                    # Remove query parameters from image URLs
                    if '?' in src:
                        src = src.split('?')[0]
                    # Skip Confluence-generated thumbnails (non-file endpoints)
                    if src.startswith('attachments/thumbnails/'):
                        processed.add(el)
                        continue
                    # Skip UI icons and avatars by URL pattern
                    if any(x in src for x in ['/universal_avatar/', '/icons/', 'emoticons/']):
                        processed.add(el)
                        continue
                    # Skip tiny gifs (usually UI elements)
                    if src.endswith('.gif'):
                        processed.add(el)
                        continue
                    blocks.append({'type': 'image', 'src': src})
                    processed.add(el)
            elif name == 'table':
                rows = []
                for tr in el.find_all('tr', recursive=True):
                    cells = []
                    for td in tr.find_all(['td','th'], recursive=False):
                        cell_children = []
                        # collect direct children blocks inside cell
                        for c in td.children:
                            if isinstance(c, NavigableString):
                                t = str(c).strip()
                                if t:
                                    cell_children.append({'type':'paragraph','text':t})
                            elif isinstance(c, Tag):
                                if c.name == 'img':
                                    # Skip UI icons by class
                                    img_class = c.get('class', [])
                                    if isinstance(img_class, list):
                                        img_class = ' '.join(img_class)
                                    if any(x in str(img_class) for x in ['icon', 'emoticon', 'bullet']):
                                        continue
                                    
                                    # Prefer data-image-src if present; fall back to src
                                    src = c.get('data-image-src') or c.get('src')
                                    if src:
                                        if '?' in src:
                                            src = src.split('?')[0]
                                        if src.startswith('attachments/thumbnails/'):
                                            continue
                                        if any(x in src for x in ['/universal_avatar/', '/icons/', 'emoticons/']):
                                            continue
                                        if src.endswith('.gif'):
                                            continue
                                        cell_children.append({'type':'image','src':src})
                                elif c.name in ('p','span','div'):
                                    # Add text
                                    text = c.get_text(" ", strip=True)
                                    if text:
                                        cell_children.append({'type':'paragraph','text':text})
                                    # Add any nested images
                                    for img in c.find_all('img'):
                                        # Skip UI icons by class
                                        img_class = img.get('class', [])
                                        if isinstance(img_class, list):
                                            img_class = ' '.join(img_class)
                                        if any(x in str(img_class) for x in ['icon', 'emoticon', 'bullet']):
                                            continue
                                        
                                        src = img.get('data-image-src') or img.get('src')
                                        if src:
                                            if '?' in src:
                                                src = src.split('?')[0]
                                            if src.startswith('attachments/thumbnails/'):
                                                continue
                                            if any(x in src for x in ['/universal_avatar/', '/icons/', 'emoticons/']):
                                                continue
                                            if src.endswith('.gif'):
                                                continue
                                            cell_children.append({'type':'image','src':src})
                                elif c.name in ('ul','ol'):
                                    items = []
                                    for li in c.find_all('li', recursive=False):
                                        items.append({'text': li.get_text(" ", strip=True)})
                                    cell_children.append({'type':'list','ordered': c.name=='ol','items': items})
                                elif c.name in ('pre','code'):
                                    cell_children.append({'type':'code','text': c.get_text("\n", strip=False)})
                        if not cell_children:
                            cell_children.append({'type':'paragraph','text':''})
                        cells.append({'children': cell_children})
                    if cells:
                        rows.append({'cells': cells})
                if rows:
                    blocks.append({'type':'table','rows': rows})
                    processed.add(el)
    return {'title': title, 'blocks': blocks}
