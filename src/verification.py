"""
Image verification module for checking if Notion has cached images.
Extracted from importer.py to simplify testing and maintenance.
"""
import time
from typing import Dict, Any, List, Tuple
from rich import print

from .notion_api import Notion
from .constants import DEFAULT_VERIFICATION_TIMEOUT, VERIFICATION_POLL_INTERVAL
from .processors import MediaProcessor


class ImageVerifier:
    """Handles verification that Notion has cached images from external URLs"""
    
    CDN_DOMAINS = ['notion.so', 's3.us-west', 'prod-files-secure', 's3.amazonaws.com']
    
    def __init__(self, notion: Notion):
        self.notion = notion
    
    def is_cached_url(self, url: str) -> bool:
        """Check if URL points to Notion's CDN (image was cached)"""
        return any(domain in url for domain in self.CDN_DOMAINS)
    
    def get_image_url(self, image_block: Dict[str, Any]) -> str:
        """Extract URL from image block (handles both 'file' and 'external' types)"""
        img_data = image_block.get('image', {})
        
        if img_data.get('type') == 'file':
            return img_data.get('file', {}).get('url', '')
        elif img_data.get('type') == 'external':
            return img_data.get('external', {}).get('url', '')
        
        return ''
    
    def count_verified_images_in_blocks(self, blocks: List[Dict[str, Any]]) -> int:
        """
        Count how many images in a block list have been cached by Notion.
        
        Handles:
        - Top-level image blocks
        - Images inside column_list > column structures
        
        Args:
            blocks: List of Notion blocks
        
        Returns:
            Count of images with cached URLs
        """
        # Get all image blocks using MediaProcessor
        processor = MediaProcessor()
        image_blocks = processor.extract_images_from_blocks(blocks)
        
        # Count verified images
        verified_count = 0
        for img_block in image_blocks:
            url = self.get_image_url(img_block)
            if url and self.is_cached_url(url):
                verified_count += 1
        
        # Also check nested column_list blocks (if they have IDs)
        for block in blocks:
            if block.get('type') == 'column_list' and block.get('id'):
                verified_count += self._count_images_in_column_list(block['id'])
        
        return verified_count
    
    def _count_images_in_column_list(self, column_list_id: str) -> int:
        """Count verified images inside a column_list block"""
        count = 0
        
        try:
            # Get columns in this column_list
            columns = self.notion.get_blocks(column_list_id)
            
            for col_block in columns:
                if col_block.get('type') == 'column':
                    # Get children of this column
                    children = self.notion.get_blocks(col_block['id'])
                    
                    for child in children:
                        if child.get('type') == 'image':
                            url = self.get_image_url(child)
                            if url and self.is_cached_url(url):
                                count += 1
        
        except Exception as e:
            # Silently fail - column might be empty or inaccessible
            pass
        
        return count
    
    def verify_page_images(self, page_id: str, expected_count: int, 
                          timeout: int = DEFAULT_VERIFICATION_TIMEOUT, poll_interval: int = VERIFICATION_POLL_INTERVAL) -> Tuple[bool, int]:
        """
        Poll Notion API to verify images have been cached.
        
        Args:
            page_id: Notion page ID
            expected_count: Expected number of images
            timeout: Maximum seconds to wait
            poll_interval: Seconds between polls
        
        Returns:
            Tuple of (success: bool, verified_count: int)
        """
        if expected_count == 0:
            return (True, 0)
        
        print(f"  [cyan]Verifying {expected_count} images...[/cyan]", end='', flush=True)
        start_time = time.time()
        last_count = 0
        
        while time.time() - start_time < timeout:
            try:
                # Fetch current page blocks
                page_blocks = self.notion.get_blocks(page_id)
                
                # Count verified images
                verified_count = self.count_verified_images_in_blocks(page_blocks)
                
                # Show progress if changed
                if verified_count != last_count:
                    print(f"\r  [cyan]Verifying images: {verified_count}/{expected_count}[/cyan]", 
                          end='', flush=True)
                    last_count = verified_count
                
                # Success if all verified
                if verified_count >= expected_count:
                    elapsed = int(time.time() - start_time)
                    print(f"\r  [green]✓ All {verified_count} images verified ({elapsed}s)[/green]")
                    return (True, verified_count)
                
                # Wait before next poll
                time.sleep(poll_interval)
            
            except Exception as e:
                print(f"\r  [yellow]Warning during verification: {e}[/yellow]")
                time.sleep(poll_interval)
        
        # Timeout
        elapsed = int(time.time() - start_time)
        print(f"\r  [yellow]⚠ Timeout: {last_count}/{expected_count} images verified ({elapsed}s)[/yellow]")
        return (False, last_count)

