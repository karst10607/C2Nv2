import time
from typing import Any, Dict, List, Optional
from notion_client import Client

from .constants import NOTION_API_RATE_LIMIT, NOTION_BLOCK_CHUNK_SIZE, NOTION_API_BLOCK_LIMIT, API_RETRY_COUNT, RETRY_BASE_DELAY

class Notion:
    def __init__(self, token: str):
        self.client = Client(auth=token)
        self.last_api_call = 0
        self.min_interval = NOTION_API_RATE_LIMIT

    def search_parents(self, query: str) -> List[Dict[str, Any]]:
        res = self.client.search(query=query, page_size=20)
        return res.get('results', [])

    def create_page(self, parent_id: str, title: str) -> str:
        parent = {"type": "page_id", "page_id": parent_id}
        try:
            page = self.client.pages.create(parent=parent, properties={
                "title": [{"type": "text", "text": {"content": title}}]
            })
            return page["id"]
        except Exception as e:
            if "404" in str(e) or "Could not find page" in str(e):
                from .models.errors import NotionAPIError, ErrorCode
                raise NotionAPIError(
                    ErrorCode.NOTION_PAGE_NOT_FOUND,
                    f"Parent page {parent_id} not found",
                    f"Please verify:\n"
                    f"1. The page still exists in Notion\n"
                    f"2. Your integration has access to the page\n"
                    f"3. You're using the correct workspace"
                )
            raise

    def append_blocks(self, page_id: str, blocks: List[Dict[str, Any]], chunk: int = NOTION_BLOCK_CHUNK_SIZE):
        """Append blocks to a page, handling nested structures and API limits"""
        # Count actual blocks including nested ones
        actual_block_count = self._count_all_blocks(blocks)
        
        if actual_block_count > 900:  # Leave some margin from the 1000 limit
            print(f"  [yellow]Warning: {actual_block_count} total blocks (including nested). Chunking more aggressively.[/yellow]")
            # For pages with many nested blocks, use smaller chunks
            chunk = min(chunk, 20)
        
        for i in range(0, len(blocks), chunk):
            part = blocks[i:i+chunk]
            part_count = self._count_all_blocks(part)
            
            # If even a single chunk exceeds limits, we need to split it further
            if part_count > 900:
                print(f"  [yellow]Chunk has {part_count} blocks. Splitting further...[/yellow]")
                # Process each block individually if needed
                for block in part:
                    single_count = self._count_all_blocks([block])
                    if single_count > 900:
                        print(f"  [red]Single block has {single_count} nested blocks! This may fail.[/red]")
                    self._retry(lambda b=block: self.client.blocks.children.append(block_id=page_id, children=[b]))
            else:
                self._retry(lambda p=part: self.client.blocks.children.append(block_id=page_id, children=p))
    
    def _count_all_blocks(self, blocks: List[Dict[str, Any]]) -> int:
        """Count all blocks including nested ones (column_list children, etc.)"""
        count = 0
        for block in blocks:
            count += 1  # Count the block itself
            
            # Count nested blocks
            if block.get('type') == 'column_list':
                columns = block.get('column_list', {}).get('children', [])
                for col in columns:
                    count += 1  # Count the column block
                    # Count children in the column
                    col_children = col.get('column', {}).get('children', [])
                    count += self._count_all_blocks(col_children)
            
            # Handle other nested structures if any
            # (Currently only column_list has nested blocks in our transform)
        
        return count

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
    
    def _retry(self, fn, retries: int = API_RETRY_COUNT, base: float = RETRY_BASE_DELAY):
        for attempt in range(retries):
            try:
                self._throttle()  # Rate limit before each API call
                return fn()
            except Exception as e:
                if attempt == retries - 1:
                    raise
                time.sleep(base * (2 ** attempt))
