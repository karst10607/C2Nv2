import time
from typing import Any, Dict, List, Optional
from notion_client import Client

class Notion:
    def __init__(self, token: str):
        self.client = Client(auth=token)
        self.last_api_call = 0
        self.min_interval = 0.35  # ~3 requests/sec with safety margin

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

    def get_blocks(self, block_id: str) -> List[Dict[str, Any]]:
        """Retrieve all child blocks of a page or block"""
        all_blocks = []
        has_more = True
        start_cursor = None
        
        while has_more:
            response = self._retry(lambda: self.client.blocks.children.list(
                block_id=block_id,
                start_cursor=start_cursor,
                page_size=100
            ))
            all_blocks.extend(response.get('results', []))
            has_more = response.get('has_more', False)
            start_cursor = response.get('next_cursor')
        
        return all_blocks

    def _throttle(self):
        """Enforce rate limiting: ~3 requests/sec"""
        now = time.time()
        elapsed = now - self.last_api_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_api_call = time.time()
    
    def _retry(self, fn, retries: int = 5, base: float = 0.8):
        for attempt in range(retries):
            try:
                self._throttle()  # Rate limit before each API call
                return fn()
            except Exception as e:
                if attempt == retries - 1:
                    raise
                time.sleep(base * (2 ** attempt))
