"""
Default transformation plugins.
These handle the standard Confluence → Notion conversion.
"""
from typing import Dict, List, Any
from ..base import TransformerPlugin
from ...transform import rich_text, split_long_paragraph, _cell_children


class DefaultTableTransformer(TransformerPlugin):
    """
    Default table transformation: converts to column_list/column blocks.
    This is the current behavior - preserves layout with images.
    """
    
    def can_handle(self, ast_node: Dict[str, Any]) -> bool:
        return ast_node.get('type') == 'table'
    
    def priority(self) -> int:
        return 50  # Low priority - others can override
    
    def transform(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert table to column_list blocks"""
        blocks = []
        image_base_url = context.get('image_base_url', '')
        max_cols = context.get('max_cols', 6)
        preserve_layout = context.get('preserve_table_layout', True)
        min_height = context.get('min_column_height', 3)
        
        for row in ast_node.get('rows', []):
            cells = row.get('cells', [])
            
            # Check if row has images
            has_images = any(
                any(child.get('type') == 'image' for child in cell.get('children', []))
                for cell in cells
            )
            
            # Split into chunks if > max_cols
            for start in range(0, len(cells), max_cols):
                chunk = cells[start:start+max_cols]
                
                # Create columns
                column_children = []
                max_height = 0
                
                # First pass: create columns and find max height
                for c in chunk:
                    children = _cell_children(c.get('children', []), image_base_url)
                    column_children.append(children)
                    max_height = max(max_height, len(children))
                
                # Apply minimum height if preserving layout
                if preserve_layout and has_images:
                    max_height = max(max_height, min_height)
                
                # Normalize heights
                if preserve_layout and has_images:
                    for children in column_children:
                        while len(children) < max_height:
                            children.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {"rich_text": rich_text("")}
                            })
                
                # Create column_list
                blocks.append({
                    "object": "block",
                    "type": "column_list",
                    "column_list": {
                        "children": [
                            {
                                "object": "block",
                                "type": "column",
                                "column": {"children": children}
                            }
                            for children in column_children
                        ]
                    }
                })
        
        return blocks


class DefaultHeadingTransformer(TransformerPlugin):
    """Transform headings"""
    
    def can_handle(self, ast_node: Dict[str, Any]) -> bool:
        return ast_node.get('type') == 'heading'
    
    def priority(self) -> int:
        return 50
    
    def transform(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        level = min(3, max(1, ast_node.get('level', 1)))
        heading_type = f"heading_{level}"
        
        return [{
            "object": "block",
            "type": heading_type,
            heading_type: {"rich_text": rich_text(ast_node.get('text', ''))}
        }]


class DefaultParagraphTransformer(TransformerPlugin):
    """Transform paragraphs"""
    
    def can_handle(self, ast_node: Dict[str, Any]) -> bool:
        return ast_node.get('type') == 'paragraph'
    
    def priority(self) -> int:
        return 50
    
    def transform(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        text = ast_node.get('text', '')
        
        if len(text) > 2000:
            return split_long_paragraph(text)
        
        return [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": rich_text(text)}
        }]


class DefaultListTransformer(TransformerPlugin):
    """Transform lists"""
    
    def can_handle(self, ast_node: Dict[str, Any]) -> bool:
        return ast_node.get('type') == 'list'
    
    def priority(self) -> int:
        return 50
    
    def transform(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        blocks = []
        key = 'numbered_list_item' if ast_node.get('ordered') else 'bulleted_list_item'
        
        for item in ast_node.get('items', []):
            text = item.get('text', '')
            if len(text) > 2000:
                text = text[:1997] + "..."
            
            blocks.append({
                "object": "block",
                "type": key,
                key: {"rich_text": rich_text(text)}
            })
        
        return blocks


class DefaultCodeTransformer(TransformerPlugin):
    """Transform code blocks"""
    
    def can_handle(self, ast_node: Dict[str, Any]) -> bool:
        return ast_node.get('type') == 'code'
    
    def priority(self) -> int:
        return 50
    
    def transform(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        text = ast_node.get('text', '')
        if len(text) > 2000:
            text = text[:1997] + "..."
        
        return [{
            "object": "block",
            "type": "code",
            "code": {"rich_text": rich_text(text), "language": "plain text"}
        }]


class DefaultImageTransformer(TransformerPlugin):
    """Transform images"""
    
    def can_handle(self, ast_node: Dict[str, Any]) -> bool:
        return ast_node.get('type') == 'image'
    
    def priority(self) -> int:
        return 50
    
    def transform(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        from ...image_utils import normalize_image_url
        
        src = ast_node.get('src', '')
        image_base_url = context.get('image_base_url', '')
        
        url = normalize_image_url(src, image_base_url)
        
        return [{
            "object": "block",
            "type": "image",
            "image": {"type": "external", "external": {"url": url}}
        }]

