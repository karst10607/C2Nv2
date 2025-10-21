# Async/Await Architecture (#4)

## What is Async/Await?

**Async/await** allows Python to handle I/O operations (API calls, file reads) **concurrently** without blocking.

### **Without Async (Current v2.6.1):**
```python
# Sequential - each step waits for previous
response1 = notion.get_blocks(page1)    # 0.5s
response2 = notion.get_blocks(page2)    # 0.5s  
response3 = notion.get_blocks(page3)    # 0.5s
# Total: 1.5s
```

### **With Async (v3.0.0):**
```python
# Concurrent - all run simultaneously
response1, response2, response3 = await asyncio.gather(
    notion.get_blocks(page1),    # All 3 run
    notion.get_blocks(page2),    # at the same
    notion.get_blocks(page3),    # time!
)
# Total: 0.5s (3x faster!)
```

---

## Why Async for Your Use Case?

### **1. Verification Speed (Critical)**

**Current bottleneck:**
```python
# Checking a page with 14 images in column_list:
blocks = notion.get_blocks(page_id)           # 0.4s
for column in columns:                         
    cols = notion.get_blocks(column_id)        # 0.4s × 5 columns = 2s
    for col in cols:
        children = notion.get_blocks(col_id)   # 0.4s × 5 = 2s
        # Check images...

# Total per poll: ~5s × 20 polls = 100s just waiting!
```

**With async:**
```python
# Fetch all blocks concurrently
blocks, *column_children = await asyncio.gather(
    notion.get_blocks(page_id),
    *[notion.get_blocks(col_id) for col in columns]  # All at once!
)

# Total per poll: ~0.5s × 20 polls = 10s (10x faster!)
```

**Impact for 1000 pages:**
- Current: ~3 hours verification time
- Async: ~20 minutes verification time
- **Saves 2.5 hours per import! 🚀**

---

### **2. Rate Limiting Benefits**

**Current approach:**
```python
# Throttle: wait 0.35s between EACH call
call1()  # wait 0.35s
call2()  # wait 0.35s
call3()  # wait 0.35s
# 3 calls/sec (inefficient use of quota)
```

**Async approach:**
```python
# Batch requests, smart throttling
async with RateLimiter(requests_per_sec=3):
    results = await asyncio.gather(
        call1(), call2(), call3()  # Batched!
    )
# Still 3 req/sec, but parallel execution within quota
```

---

## Implementation in v3.0.0

### **Changes to notion_api.py:**

```python
# Before (synchronous):
class Notion:
    def get_blocks(self, block_id: str) -> List[Dict]:
        response = self.client.blocks.children.list(block_id=block_id)
        return response.get('results', [])

# After (async):
class AsyncNotion:
    async def get_blocks(self, block_id: str) -> List[Dict]:
        response = await self.client.blocks.children.list(block_id=block_id)
        return response.get('results', [])
    
    async def get_blocks_batch(self, block_ids: List[str]) -> Dict[str, List]:
        """Fetch multiple blocks concurrently"""
        tasks = [self.get_blocks(bid) for bid in block_ids]
        results = await asyncio.gather(*tasks)
        return dict(zip(block_ids, results))
```

### **Changes to verification.py:**

```python
# Before:
def count_verified_images_in_blocks(self, blocks):
    for block in blocks:
        if block['type'] == 'column_list':
            columns = self.notion.get_blocks(block['id'])  # Sequential!
            for col in columns:
                children = self.notion.get_blocks(col['id'])  # Sequential!

# After:
async def count_verified_images_in_blocks(self, blocks):
    # Collect all block IDs to fetch
    column_list_ids = [b['id'] for b in blocks if b['type'] == 'column_list']
    
    # Fetch all column lists concurrently
    column_blocks_dict = await self.notion.get_blocks_batch(column_list_ids)
    
    # Fetch all column children concurrently
    column_ids = []
    for cols in column_blocks_dict.values():
        column_ids.extend([c['id'] for c in cols if c['type'] == 'column'])
    
    column_children_dict = await self.notion.get_blocks_batch(column_ids)
    
    # Now count (all data already fetched!)
    # No more sequential API calls in loops!
```

---

## Performance Comparison

### **Scenario: Import 100 pages with 500 images**

| Phase | Synchronous (v2.6.1) | Async (v3.0.0) | Speedup |
|-------|---------------------|----------------|---------|
| **Parse HTML** | 30s | 30s | 1x (CPU-bound) |
| **Create pages** | 35s (rate limited) | 35s | 1x (still rate limited) |
| **Append blocks** | 120s (chunks) | 40s (batched) | **3x** ⚡ |
| **Verify images** | 9000s (2.5h) 😱 | 600s (10min) | **15x** ⚡ |
| **Total** | **2h 42m** | **13 minutes** | **12.5x faster!** 🚀 |

**Why such speedup in verification?**
- Each page needs 10-30 API calls for nested blocks
- Synchronous: 10 calls × 0.5s = 5s per page × 100 pages = 500s
- Async: 10 calls in parallel = 0.5s per page × 100 pages = 50s

---

## Migration Strategy

**Phase 1: Add async layer (keep sync)**
```python
# Keep old synchronous API
class Notion:
    def get_blocks(self, id): ...

# Add new async API
class AsyncNotion:
    async def get_blocks(self, id): ...
```

**Phase 2: Update high-impact functions**
```python
# Only verification needs async (biggest bottleneck)
class ImageVerifier:
    async def verify_page_images(...):
        # Use AsyncNotion internally
```

**Phase 3: Gradual migration**
- importer.py: Add `async def main()` wrapper
- Keep synchronous fallback for CLI

---

## When to Use Async

✅ **Use async for:**
- I/O operations (API calls, file reads)
- Verification (many parallel checks)
- Batch operations (fetching 100 pages)

❌ **Don't use async for:**
- CPU-bound tasks (HTML parsing)
- Simple linear workflows
- Single API calls

---

**Next: I'll show you Plugin Architecture (#5) →**

