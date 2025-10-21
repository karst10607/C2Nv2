"""
Base classes for plugin system.
All plugins must inherit from these base classes.
"""
from typing import Dict, List, Any
from abc import ABC, abstractmethod


class TransformerPlugin(ABC):
    """
    Base class for AST node transformation plugins.
    
    Example:
        class CustomTableTransformer(TransformerPlugin):
            def can_handle(self, ast_node):
                return ast_node['type'] == 'table'
            
            def transform(self, ast_node, context):
                # Custom table transformation logic
                return notion_blocks
    """
    
    def __init__(self, config=None):
        """
        Initialize plugin with configuration.
        
        Args:
            config: ImportConfig object or dict with plugin settings
        """
        self.config = config
    
    @abstractmethod
    def can_handle(self, ast_node: Dict[str, Any]) -> bool:
        """
        Check if this plugin can handle the given AST node.
        
        Args:
            ast_node: Dictionary with 'type' and other node data
        
        Returns:
            True if this plugin should transform this node
        """
        pass
    
    def priority(self) -> int:
        """
        Plugin priority (higher = checked first).
        
        Default: 100
        Built-in plugins: 50-100
        Custom plugins: 100-200
        Override plugins: 200+
        
        Returns:
            Priority integer
        """
        return 100
    
    @abstractmethod
    def transform(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform AST node to Notion blocks.
        
        Args:
            ast_node: Dictionary with node data (type, text, children, etc.)
            context: Dictionary with import context (image_base_url, config, etc.)
        
        Returns:
            List of Notion block dictionaries
        """
        pass
    
    def get_name(self) -> str:
        """Get plugin name (default: class name)"""
        return self.__class__.__name__


class ImagePlugin(ABC):
    """
    Base class for image processing plugins.
    
    Example:
        class CDNUploader(ImagePlugin):
            def transform_url(self, src, context):
                # Upload to CDN and return new URL
                return cdn_url
    """
    
    def __init__(self, config=None):
        self.config = config
    
    def should_skip(self, img_element, src: str) -> bool:
        """
        Check if image should be skipped.
        
        Args:
            img_element: BeautifulSoup Tag element
            src: Image source URL
        
        Returns:
            True to skip this image
        """
        return False
    
    def priority(self) -> int:
        """Plugin priority (higher = checked first)"""
        return 100
    
    def transform_url(self, src: str, context: Dict[str, Any]) -> str:
        """
        Transform image URL (e.g., upload to CDN, proxy, etc.).
        
        Args:
            src: Original image source
            context: Import context with source_dir, base_url, etc.
        
        Returns:
            Transformed URL
        """
        return src
    
    def get_name(self) -> str:
        """Get plugin name"""
        return self.__class__.__name__


class VerificationPlugin(ABC):
    """
    Base class for custom verification strategies.
    
    Example:
        class SlackNotifier(VerificationPlugin):
            async def on_verification_complete(self, result):
                await send_slack_message(f"Import: {result}")
    """
    
    def __init__(self, config=None):
        self.config = config
    
    async def on_page_complete(self, page_id: str, success: bool, verified_count: int):
        """Called after each page verification"""
        pass
    
    async def on_import_complete(self, total_pages: int, success_count: int):
        """Called after entire import"""
        pass
    
    def get_name(self) -> str:
        return self.__class__.__name__

