# Plugin Architecture (#5)

## What is Plugin Architecture?

**Plugin architecture** allows users to **extend functionality without modifying core code**.

Think of it like:
- **Chrome extensions** (add features without changing Chrome)
- **VS Code extensions** (custom languages, themes)
- **WordPress plugins** (custom post types, widgets)

---

## Why Plugins for Confluence → Notion?

### **Current Problem: Hard-Coded Transformations**

```python
# In transform.py - ONE way to handle tables
def to_notion_blocks(ast, ...):
    if block['type'] == 'table':
        # Convert to column_list (hard-coded)
        return column_list_blocks
```

**Issues:**
- ❌ Different teams want different table formats
- ❌ Some want actual Notion tables, not column_list
- ❌ Custom macro handling (different per company)
- ❌ Need to modify core code for each variant

---

### **With Plugins:**

```python
# Core code stays unchanged
# Users create plugins:

# plugins/table_to_native.py
class TableToNativeTransformer:
    """Convert HTML tables to Notion table blocks (not column_list)"""
    
    def can_handle(self, ast_node):
        return ast_node['type'] == 'table'
    
    def transform(self, ast_node, config):
        # Custom logic: convert to Notion table_row blocks
        return notion_table_blocks

# plugins/jira_macro_handler.py
class JiraMacroTransformer:
    """Handle Confluence JIRA macros"""
    
    def can_handle(self, ast_node):
        return ast_node.get('macro') == 'jira'
    
    def transform(self, ast_node, config):
        # Extract JIRA ticket, create callout block
        return notion_callout_with_link
```

**Users can pick:**
```python
# config.yml
plugins:
  - table_to_native  # Use native tables
  - jira_macro_handler  # Handle JIRA macros
  - custom_diagram_handler  # Company-specific
```

---

## Plugin Architecture Design

### **Core Interface:**

```python
# src/plugins/base.py
class TransformerPlugin:
    """Base class for transformation plugins"""
    
    def __init__(self, config: ImportConfig):
        self.config = config
    
    def can_handle(self, ast_node: Dict) -> bool:
        """Return True if this plugin can transform this node"""
        raise NotImplementedError
    
    def priority(self) -> int:
        """Higher priority plugins checked first (default: 100)"""
        return 100
    
    def transform(self, ast_node: Dict, context: Dict) -> List[Dict]:
        """Transform AST node to Notion blocks"""
        raise NotImplementedError


class ImagePlugin:
    """Base class for image handling plugins"""
    
    def should_skip(self, img_element, src: str) -> bool:
        """Return True to skip this image"""
        return False
    
    def transform_url(self, src: str, context: Dict) -> str:
        """Transform image URL (e.g., upload to CDN)"""
        return src
```

---

### **Plugin Manager:**

```python
# src/plugins/manager.py
class PluginManager:
    """Loads and manages plugins"""
    
    def __init__(self, config: ImportConfig):
        self.config = config
        self.transformers: List[TransformerPlugin] = []
        self.image_plugins: List[ImagePlugin] = []
    
    def load_plugins(self, plugin_dir: Path):
        """Auto-discover and load plugins from directory"""
        for py_file in plugin_dir.glob('*.py'):
            module = import_module(py_file)
            # Find all TransformerPlugin subclasses
            for cls in get_plugin_classes(module):
                self.transformers.append(cls(self.config))
        
        # Sort by priority
        self.transformers.sort(key=lambda p: p.priority(), reverse=True)
    
    def transform_node(self, ast_node: Dict, context: Dict) -> List[Dict]:
        """Find matching plugin and transform"""
        for plugin in self.transformers:
            if plugin.can_handle(ast_node):
                return plugin.transform(ast_node, context)
        
        # Fallback to default transformation
        return default_transform(ast_node, context)
```

---

## Real-World Plugin Examples

### **Example 1: Notion Native Tables**

```python
# plugins/native_table_transformer.py
class NativeTableTransformer(TransformerPlugin):
    """Convert HTML tables to Notion table blocks instead of column_list"""
    
    def can_handle(self, ast_node):
        return ast_node['type'] == 'table'
    
    def priority(self):
        return 200  # Higher than default
    
    def transform(self, ast_node, context):
        rows = ast_node['rows']
        
        # Create Notion table block
        table_block = {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": len(rows[0]['cells']) if rows else 0,
                "has_column_header": True,
                "has_row_header": False,
                "children": []
            }
        }
        
        # Add table_row children
        for row in rows:
            table_row = {
                "type": "table_row",
                "table_row": {
                    "cells": [
                        # Convert cell children to rich_text
                        self._cell_to_rich_text(cell)
                        for cell in row['cells']
                    ]
                }
            }
            table_block["table"]["children"].append(table_row)
        
        return [table_block]
```

**Why plugin?**
- ✅ Some teams prefer column_list (better for images)
- ✅ Some teams prefer native tables (better for data)
- ✅ Choice via config, no code changes

---

### **Example 2: PlantUML Diagram Handler**

```python
# plugins/plantuml_handler.py
class PlantUMLTransformer(TransformerPlugin):
    """Convert PlantUML macros to rendered images"""
    
    def can_handle(self, ast_node):
        return ast_node.get('type') == 'macro' and 'plantuml' in ast_node.get('name', '')
    
    def transform(self, ast_node, context):
        # Extract PlantUML code
        uml_code = ast_node['content']
        
        # Option 1: Render to image via PlantUML server
        image_url = self._render_plantuml(uml_code)
        
        # Option 2: Create code block with UML source
        return [
            {
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": "PlantUML Diagram"}}],
                    "icon": {"emoji": "📊"},
                    "children": [
                        {
                            "type": "code",
                            "code": {
                                "rich_text": [{"type": "text", "text": {"content": uml_code}}],
                                "language": "plain text"
                            }
                        }
                    ]
                }
            }
        ]
```

**Why plugin?**
- ✅ Not all users have PlantUML diagrams
- ✅ Different rendering preferences
- ✅ Optional dependency (don't bloat core)

---

### **Example 3: Image CDN Upload Plugin**

```python
# plugins/image_cdn_uploader.py
class ImageCDNUploader(ImagePlugin):
    """Upload images to CDN instead of serving via tunnel"""
    
    def __init__(self, config):
        self.cdn_client = S3Client(config.aws_credentials)
    
    def transform_url(self, src: str, context: Dict) -> str:
        """Upload image to S3 and return CDN URL"""
        if src.startswith('http'):
            return src  # Already external
        
        # Read local file
        local_path = context['source_dir'] / src
        
        # Upload to S3
        cdn_url = self.cdn_client.upload(local_path)
        
        return cdn_url  # Notion fetches from S3 (faster, no tunnel needed!)
```

**Why plugin?**
- ✅ Eliminates tunnel dependency
- ✅ Images persist after import (tunnel URLs expire)
- ✅ Optional for users without CDN

---

## Plugin Configuration

### **User config file (`import_plugins.yml`):**

```yaml
# Load plugins from these directories
plugin_paths:
  - ~/.notion_importer/plugins
  - ./custom_plugins

# Enable specific plugins
enabled_plugins:
  # Table handling
  - name: native_table_transformer
    enabled: true
    config:
      max_columns: 10
      merge_cells: false
  
  # Macro handling
  - name: plantuml_handler
    enabled: true
    config:
      render_server: https://plantuml.example.com
  
  # Image handling
  - name: image_cdn_uploader
    enabled: false  # Disabled for now
    config:
      bucket: my-notion-images
      region: us-west-2

# Plugin priorities (higher = checked first)
priorities:
  native_table_transformer: 200
  plantuml_handler: 150
```

---

## Built-in vs Custom Plugins

### **Built-in Plugins (Shipped with app):**
```
src/plugins/
  ├── builtin/
  │   ├── default_table.py       # Current column_list behavior
  │   ├── default_image.py       # Current tunnel serving
  │   └── confluence_macros.py   # Basic macro handling
```

### **Custom Plugins (User-created):**
```
~/.notion_importer/plugins/
  ├── company_specific_macros.py
  ├── custom_diagram_handler.py
  └── team_table_formatter.py
```

### **Third-Party Plugins (Community):**
```
# Install from GitHub
notion-importer plugin install https://github.com/user/awesome-plugin

# Or pip
pip install notion-importer-plantuml-plugin
```

---

## Plugin Discovery & Loading

```python
# src/plugins/manager.py
class PluginManager:
    def discover_plugins(self):
        """Auto-discover plugins"""
        plugin_dirs = [
            Path(__file__).parent / 'builtin',     # Built-in
            Path.home() / '.notion_importer/plugins',  # User
            Path.cwd() / 'custom_plugins'          # Project-specific
        ]
        
        for plugin_dir in plugin_dirs:
            if not plugin_dir.exists():
                continue
            
            for py_file in plugin_dir.glob('*.py'):
                if py_file.name.startswith('_'):
                    continue
                
                # Import module
                spec = importlib.util.spec_from_file_location(
                    py_file.stem, py_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find plugin classes
                for name in dir(module):
                    obj = getattr(module, name)
                    if (isinstance(obj, type) and 
                        issubclass(obj, TransformerPlugin) and 
                        obj != TransformerPlugin):
                        
                        # Instantiate and register
                        self.register_plugin(obj(self.config))
```

---

## Example: Using Plugins in Import

```python
# In importer.py main():
def main(args):
    config = ImportConfig.from_args_and_config(args, cfg)
    
    # Load plugins
    plugin_manager = PluginManager(config)
    plugin_manager.load_plugins()  # Auto-discover
    
    # Parse HTML
    ast = parse_html_file(file)
    
    # Transform with plugins
    blocks = plugin_manager.transform_ast(ast)
    
    # Import to Notion
    notion.append_blocks(page_id, blocks)
```

**How it works:**
```python
def transform_ast(self, ast):
    blocks = []
    for node in ast['blocks']:
        # Try each plugin
        for plugin in self.transformers:
            if plugin.can_handle(node):
                blocks.extend(plugin.transform(node, context))
                break  # First match wins
        else:
            # No plugin matched, use default
            blocks.extend(default_transform(node))
    return blocks
```

---

## Benefits for Your 1000+ Page Migration

### **1. Team Customization**
```python
# Team A wants column_list for images
config: use_plugin: column_list_tables

# Team B wants native tables
config: use_plugin: native_tables

# Same codebase, different outputs!
```

### **2. Gradual Migration**
```python
# Start with defaults
plugins: []

# Add as needed
plugins:
  - custom_macro_handler  # Week 1
  - special_diagram_fix    # Week 2
  - team_specific_layout   # Week 3

# No core code changes!
```

### **3. A/B Testing**
```python
# Test which format works better:
# Run 1: use column_list_plugin
# Run 2: use native_table_plugin
# Compare results, pick winner
```

### **4. Community Contributions**
```
# Other users share plugins:
- plantuml-notion-plugin
- mermaid-diagram-plugin
- confluence-status-macro-plugin
- custom-table-formatter-plugin

# Install and use without modifying your code!
```

---

## Implementation in v3.0.0

I'll create:

1. **Plugin base classes** (`src/plugins/base.py`)
2. **Plugin manager** (`src/plugins/manager.py`)
3. **Built-in plugins** (`src/plugins/builtin/`)
4. **Plugin config** (YAML support)
5. **Plugin CLI** (`notion-importer plugin list|install|enable`)

---

**Next: Let me implement both #4 (Async) and #5 (Plugins) →**

