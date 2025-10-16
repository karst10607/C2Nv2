import time
from typing import Any, Dict, List, Optional
from notion_client import Client

class Notion:
    def __init__(self, token: str):
        self.client = Client(auth=token)

    def search_parents(self, query: str) -> List[Dict[str, Any]]:
        res = self.client.search(query=query, page_size=20)
        return res.get('results', [])

    def create_page(self, parent_id: str, title: str) -> str:
        parent = {"type": "page_id", "page_id": parent_id}
        page = self.client.pages.create(parent=parent, properties={
            "title": [{"type": "text", "text": {"content": title}}]
        })
        return page["id"]

    def append_blocks(self, page_id: str, blocks: List[Dict[str, Any]], chunk: int = 80):
        for i in range(0, len(blocks), chunk):
            part = blocks[i:i+chunk]
            self._retry(lambda: self.client.blocks.children.append(block_id=page_id, children=part))

    @staticmethod
    def _retry(fn, retries: int = 5, base: float = 0.8):
        for attempt in range(retries):
            try:
                return fn()
            except Exception as e:
                if attempt == retries - 1:
                    raise
                time.sleep(base * (2 ** attempt))
