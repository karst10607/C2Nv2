"""
Plugin manager for discovering and orchestrating plugins.
Handles plugin loading, priority ordering, and delegation.
"""
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

from .base import TransformerPlugin, ImagePlugin, VerificationPlugin


class PluginManager:
    """Manages transformation and image processing plugins"""
    
    def __init__(self, config=None):
        self.config = config
        self.transformers: List[TransformerPlugin] = []
        self.image_plugins: List[ImagePlugin] = []
        self.verification_plugins: List[VerificationPlugin] = []
    
    def discover_and_load_plugins(self, additional_paths: Optional[List[Path]] = None):
        """
        Auto-discover plugins from standard locations.
        
        Search order:
        1. Built-in plugins (src/plugins/builtin/)
        2. User plugins (~/.notion_importer/plugins/)
        3. Project plugins (./custom_plugins/)
        4. Additional paths provided
        
        Args:
            additional_paths: Optional list of additional directories to search
        """
        plugin_dirs = [
            Path(__file__).parent / 'builtin',  # Built-in
            Path.home() / '.notion_importer' / 'plugins',  # User
            Path.cwd() / 'custom_plugins',  # Project
        ]
        
        if additional_paths:
            plugin_dirs.extend(additional_paths)
        
        for plugin_dir in plugin_dirs:
            if not plugin_dir.exists():
                continue
            
            self._load_plugins_from_directory(plugin_dir)
        
        # Sort by priority (highest first)
        self.transformers.sort(key=lambda p: p.priority(), reverse=True)
        self.image_plugins.sort(key=lambda p: p.priority(), reverse=True)
    
    def _load_plugins_from_directory(self, directory: Path):
        """Load all plugin modules from a directory"""
        for py_file in directory.glob('*.py'):
            if py_file.name.startswith('_'):
                continue  # Skip __init__.py and private files
            
            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                if not spec or not spec.loader:
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find and register plugin classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    
                    if not isinstance(attr, type):
                        continue
                    
                    # Check if it's a plugin class (not the base class itself)
                    if issubclass(attr, TransformerPlugin) and attr != TransformerPlugin:
                        self.register_transformer(attr(self.config))
                    
                    elif issubclass(attr, ImagePlugin) and attr != ImagePlugin:
                        self.register_image_plugin(attr(self.config))
                    
                    elif issubclass(attr, VerificationPlugin) and attr != VerificationPlugin:
                        self.register_verification_plugin(attr(self.config))
            
            except Exception as e:
                print(f"Warning: Failed to load plugin {py_file.name}: {e}")
    
    def register_transformer(self, plugin: TransformerPlugin):
        """Register a transformer plugin"""
        self.transformers.append(plugin)
    
    def register_image_plugin(self, plugin: ImagePlugin):
        """Register an image plugin"""
        self.image_plugins.append(plugin)
    
    def register_verification_plugin(self, plugin: VerificationPlugin):
        """Register a verification plugin"""
        self.verification_plugins.append(plugin)
    
    def transform_node(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform an AST node using registered plugins.
        
        Tries plugins in priority order. First matching plugin wins.
        Falls back to default transformation if no plugin matches.
        
        Args:
            ast_node: AST node to transform
            context: Transformation context
        
        Returns:
            List of Notion blocks
        """
        for plugin in self.transformers:
            if plugin.can_handle(ast_node):
                return plugin.transform(ast_node, context)
        
        # No plugin handled it - this shouldn't happen with default plugins
        # but return empty list as fallback
        return []
    
    def should_skip_image(self, img_element, src: str) -> bool:
        """Check if any image plugin wants to skip this image"""
        for plugin in self.image_plugins:
            if plugin.should_skip(img_element, src):
                return True
        return False
    
    def transform_image_url(self, src: str, context: Dict[str, Any]) -> str:
        """Transform image URL through registered plugins"""
        for plugin in self.image_plugins:
            src = plugin.transform_url(src, context)
        return src
    
    async def trigger_verification_hooks(self, event: str, **kwargs):
        """Trigger verification plugin hooks"""
        for plugin in self.verification_plugins:
            if event == 'page_complete':
                await plugin.on_page_complete(
                    kwargs.get('page_id'),
                    kwargs.get('success'),
                    kwargs.get('verified_count')
                )
            elif event == 'import_complete':
                await plugin.on_import_complete(
                    kwargs.get('total_pages'),
                    kwargs.get('success_count')
                )
    
    def list_plugins(self) -> Dict[str, List[str]]:
        """List all registered plugins"""
        return {
            'transformers': [p.get_name() for p in self.transformers],
            'image_plugins': [p.get_name() for p in self.image_plugins],
            'verification_plugins': [p.get_name() for p in self.verification_plugins]
        }

