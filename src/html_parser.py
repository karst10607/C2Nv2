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
                text = el.get_text(" ", strip=True)
                if text:
                    blocks.append({'type': 'paragraph', 'text': text})
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
                src = el.get('src')
                if src:
                    # Remove query parameters from image URLs
                    if '?' in src:
                        src = src.split('?')[0]
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
                                if c.name == 'img' and c.get('src'):
                                    src = c.get('src')
                                    # Remove query parameters from image URLs
                                    if '?' in src:
                                        src = src.split('?')[0]
                                    cell_children.append({'type':'image','src':src})
                                elif c.name in ('p','span','div'):
                                    text = c.get_text(" ", strip=True)
                                    if text:
                                        cell_children.append({'type':'paragraph','text':text})
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
