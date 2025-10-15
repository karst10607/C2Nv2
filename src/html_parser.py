from bs4 import BeautifulSoup, NavigableString, Tag
from pathlib import Path
from typing import Any, Dict, List

# Minimal AST nodes
# Node: { 'type': 'heading'|'paragraph'|'list'|'code'|'image'|'table', 'level', 'text', 'children', 'rows' }

def parse_html_file(path: Path) -> Dict[str, Any]:
    html = Path(path).read_text(encoding='utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'lxml')
    title = (soup.title.string.strip() if soup.title and soup.title.string else Path(path).stem)

    body = soup.body or soup
    blocks: List[Dict[str, Any]] = []

    for el in body.descendants:
        if isinstance(el, Tag):
            name = el.name.lower()
            if name in ('h1', 'h2', 'h3') and el.string and el.parent == body:
                blocks.append({'type': 'heading', 'level': int(name[1]), 'text': el.get_text(strip=True)})
            elif name == 'p' and el.parent == body:
                text = el.get_text(" ", strip=True)
                if text:
                    blocks.append({'type': 'paragraph', 'text': text})
            elif name in ('ul', 'ol') and el.parent == body:
                items = []
                for li in el.find_all('li', recursive=False):
                    items.append({'text': li.get_text(" ", strip=True)})
                blocks.append({'type': 'list', 'ordered': name == 'ol', 'items': items})
            elif name == 'pre' and el.parent == body:
                code_el = el.find('code') or el
                blocks.append({'type': 'code', 'text': code_el.get_text("\n", strip=False)})
            elif name == 'img' and el.parent == body:
                src = el.get('src')
                if src:
                    blocks.append({'type': 'image', 'src': src})
            elif name == 'table' and el.parent == body:
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
                                    cell_children.append({'type':'image','src':c.get('src')})
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
                blocks.append({'type':'table','rows': rows})
    return {'title': title, 'blocks': blocks}
