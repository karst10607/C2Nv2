"""
GitHub Flavored Markdown Exporter

Converts Confluence HTML exports to GitHub-compatible Markdown files.
Handles:
- Simple tables → GFM table syntax
- Complex tables (nested, images inside) → HTML blocks
- Nested folder structure with page titles
- Asset copying to output folder with relative paths

Design Decision: See docs/MARKDOWN_EXPORT_DESIGN.md for why we chose
nested folders with README.md structure.
"""

import os
import re
import shutil
import argparse
import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from .html_parser import parse_html_file, is_drawio_container
from .transform import analyze_table_content
from .rich_text_parser import extract_colorid_mappings


# Default max image width for tables (prevents oversized images)
DEFAULT_TABLE_IMAGE_WIDTH = 400
DEFAULT_IMAGE_WIDTH = 600
MAX_FOLDER_NAME_LENGTH = 100


def sanitize_folder_name(title: str) -> str:
    """
    Sanitize a page title for use as a folder name.
    
    - Replaces special characters with dashes
    - Replaces spaces with dashes
    - Truncates to MAX_FOLDER_NAME_LENGTH
    - Preserves Unicode (Japanese, etc.)
    """
    if not title:
        return "untitled"
    
    # Normalize unicode (NFC form)
    title = unicodedata.normalize('NFC', title)
    
    # Replace problematic characters with dash
    # These chars are invalid in Windows/Mac/Linux paths or cause issues
    invalid_chars = r'[/\\:*?"<>|#\[\]{}()@!$%^&+=`~;,]'
    sanitized = re.sub(invalid_chars, '-', title)
    
    # Replace multiple spaces or dashes with single dash
    sanitized = re.sub(r'[\s\-]+', '-', sanitized)
    
    # Remove leading/trailing dashes
    sanitized = sanitized.strip('-')
    
    # Truncate to max length
    if len(sanitized) > MAX_FOLDER_NAME_LENGTH:
        sanitized = sanitized[:MAX_FOLDER_NAME_LENGTH].rstrip('-')
    
    # Fallback if empty after sanitization
    if not sanitized:
        return "untitled"
    
    return sanitized


def get_unique_folder_name(base_name: str, existing_names: set) -> str:
    """
    Ensure folder name is unique by adding suffix if needed.
    """
    if base_name not in existing_names:
        return base_name
    
    counter = 2
    while f"{base_name}-{counter}" in existing_names:
        counter += 1
    
    return f"{base_name}-{counter}"


def rich_text_to_markdown(rich_text: List[Dict[str, Any]]) -> str:
    """Convert Notion-style rich_text array to Markdown string."""
    result = []
    
    for item in rich_text:
        if item.get('type') != 'text':
            continue
            
        text = item.get('text', {}).get('content', '')
        annotations = item.get('annotations', {})
        
        # Apply formatting
        if annotations.get('code'):
            text = f'`{text}`'
        if annotations.get('bold'):
            text = f'**{text}**'
        if annotations.get('italic'):
            text = f'*{text}*'
        if annotations.get('strikethrough'):
            text = f'~~{text}~~'
        
        # Handle links
        link = item.get('text', {}).get('link', {})
        if link and link.get('url'):
            text = f'[{text}]({link["url"]})'
        
        result.append(text)
    
    return ''.join(result)


def escape_markdown(text: str) -> str:
    """Escape special Markdown characters in plain text."""
    # Don't escape if already looks like markdown
    if re.search(r'\*\*|__|\[.*\]\(.*\)|`', text):
        return text
    
    # Escape pipe characters for tables
    text = text.replace('|', '\\|')
    return text


def ast_to_github_markdown(
    ast: Dict[str, Any],
    assets_dir: str = 'assets',
    table_image_width: int = DEFAULT_TABLE_IMAGE_WIDTH,
    image_width: int = DEFAULT_IMAGE_WIDTH,
    use_standard_markdown: bool = False
) -> str:
    """
    Convert parsed HTML AST to GitHub Flavored Markdown.
    
    Args:
        ast: The parsed AST from html_parser.parse_html_file()
        assets_dir: Relative path to assets folder (for image references)
        table_image_width: Max width for images inside tables
        image_width: Max width for standalone images
        use_standard_markdown: If True, use standard Markdown for all images
                               (no HTML, compatible with Obsidian/VS Code)
    
    Returns:
        GitHub Flavored Markdown string
    """
    lines = []
    
    # Add title as H1
    title = ast.get('title', 'Untitled')
    lines.append(f'# {title}')
    lines.append('')
    
    # Add metadata if present
    metadata = ast.get('metadata', {})
    if metadata and any(metadata.values()):
        meta_parts = []
        if metadata.get('created_by'):
            created_info = f"Created by {metadata['created_by']}"
            if metadata.get('created_date'):
                created_info += f" on {metadata['created_date']}"
            meta_parts.append(created_info)
        
        if metadata.get('last_modified_date'):
            modified_info = "Last modified"
            if metadata.get('last_modified_by'):
                modified_info += f" by {metadata['last_modified_by']}"
            modified_info += f" on {metadata['last_modified_date']}"
            meta_parts.append(modified_info)
        
        if meta_parts:
            lines.append(f'> {" • ".join(meta_parts)}')
            lines.append('')
    
    # Process blocks
    for block in ast.get('blocks', []):
        block_md = block_to_markdown(
            block, assets_dir, table_image_width, image_width,
            use_standard_markdown=use_standard_markdown
        )
        if block_md:
            lines.append(block_md)
            lines.append('')
    
    return '\n'.join(lines)


def block_to_markdown(
    block: Dict[str, Any],
    assets_dir: str,
    table_image_width: int,
    image_width: int,
    indent: str = '',
    use_standard_markdown: bool = False
) -> str:
    """Convert a single AST block to Markdown."""
    block_type = block.get('type')
    
    if block_type == 'heading':
        level = min(6, max(1, block.get('level', 1)))
        text = block.get('text', '')
        if block.get('rich_text'):
            text = rich_text_to_markdown(block['rich_text'])
        return f"{'#' * level} {text}"
    
    elif block_type == 'paragraph':
        text = block.get('text', '')
        if block.get('rich_text'):
            text = rich_text_to_markdown(block['rich_text'])
        return f"{indent}{text}"
    
    elif block_type == 'code':
        text = block.get('text', '')
        language = block.get('language', '')
        return f"```{language}\n{text}\n```"
    
    elif block_type == 'image':
        # For standard markdown, never use HTML
        return image_to_markdown(block, assets_dir, image_width, use_html=not use_standard_markdown)
    
    elif block_type == 'drawio':
        return drawio_to_markdown(block, assets_dir, image_width, use_html=not use_standard_markdown)
    
    elif block_type == 'file':
        return file_to_markdown(block, assets_dir)
    
    elif block_type == 'list':
        return list_to_markdown(block, assets_dir, table_image_width, image_width, indent, use_standard_markdown)
    
    elif block_type == 'table':
        return table_to_markdown(block, assets_dir, table_image_width, image_width, use_standard_markdown)
    
    return ''


def image_to_markdown(
    block: Dict[str, Any],
    assets_dir: str,
    width: int,
    in_table: bool = False,
    use_html: bool = False
) -> str:
    """
    Convert image block to Markdown.
    
    Args:
        block: Image block from AST
        assets_dir: Relative path to assets folder
        width: Image width (only used if use_html=True)
        in_table: Whether image is inside a table
        use_html: If True, use HTML img tag with width; if False, use standard Markdown
    """
    src = block.get('src', '')
    alt = block.get('alt', 'image')
    
    if not src:
        return ''
    
    # Convert to relative asset path if it's a local file
    if not src.startswith(('http://', 'https://')):
        # Extract filename from path
        filename = Path(src).name
        src = f"{assets_dir}/{filename}"
    
    # Use HTML only for tables (GitHub) or when explicitly requested
    if use_html or in_table:
        return f'<img src="{src}" alt="{alt}" width="{width}">'
    
    # Standard Markdown syntax - works in Obsidian and GitHub
    return f'![{alt}]({src})'


def drawio_to_markdown(
    block: Dict[str, Any],
    assets_dir: str,
    width: int,
    use_html: bool = False
) -> str:
    """Convert Draw.io diagram to Markdown."""
    attachment_path = block.get('attachment_path', '')
    diagram_name = block.get('diagram_name', 'Draw.io Diagram')
    
    if attachment_path and attachment_path.endswith('.png'):
        filename = Path(attachment_path).name
        src = f"{assets_dir}/{filename}"
        
        if use_html:
            return f'<img src="{src}" alt="{diagram_name}" width="{width}">\n\n*📊 {diagram_name}*'
        else:
            # Standard Markdown - works in Obsidian
            return f'![{diagram_name}]({src})\n\n*📊 {diagram_name}*'
    else:
        # .drawio file - can't display directly
        return f'> 📊 **Draw.io Diagram:** {diagram_name}\n> *(Original .drawio file - view in Draw.io)*'


def file_to_markdown(block: Dict[str, Any], assets_dir: str) -> str:
    """Convert file attachment to Markdown link."""
    src = block.get('src', '')
    name = block.get('name', 'Attachment')
    
    if not src:
        return f'📎 {name} *(file not available)*'
    
    if not src.startswith(('http://', 'https://')):
        filename = Path(src).name
        src = f"{assets_dir}/{filename}"
    
    return f'📎 [{name}]({src})'


def list_to_markdown(
    block: Dict[str, Any],
    assets_dir: str,
    table_image_width: int,
    image_width: int,
    indent: str = '',
    use_standard_markdown: bool = False
) -> str:
    """Convert list block to Markdown."""
    lines = []
    ordered = block.get('ordered', False)
    
    for i, item in enumerate(block.get('items', [])):
        prefix = f"{i + 1}. " if ordered else "- "
        text = item.get('text', '')
        if item.get('rich_text'):
            text = rich_text_to_markdown(item['rich_text'])
        
        lines.append(f"{indent}{prefix}{text}")
        
        # Handle nested content
        for child in item.get('children', []):
            child_md = block_to_markdown(
                child, assets_dir, table_image_width, image_width,
                indent=indent + '  ',
                use_standard_markdown=use_standard_markdown
            )
            if child_md:
                lines.append(child_md)
    
    return '\n'.join(lines)


def table_to_markdown(
    block: Dict[str, Any],
    assets_dir: str,
    table_image_width: int,
    image_width: int,
    use_standard_markdown: bool = False
) -> str:
    """
    Convert table to Markdown.
    Simple text-only tables → GFM table syntax
    Complex tables (images, nested) → HTML block (unless use_standard_markdown)
    """
    # Analyze table complexity
    analysis = analyze_table_content(block)
    
    # For standard markdown mode, always use GFM tables with standard image syntax
    if use_standard_markdown:
        return table_to_gfm_with_images(block, assets_dir)
    
    # Use HTML for complex tables (GitHub mode)
    if (analysis['has_images'] or 
        analysis['has_videos'] or 
        analysis['has_files'] or 
        analysis['has_merged_cells']):
        return table_to_html(block, assets_dir, table_image_width)
    
    # Use GFM for simple text tables
    return table_to_gfm(block)


def table_to_gfm(block: Dict[str, Any]) -> str:
    """Convert simple table to GitHub Flavored Markdown table syntax."""
    rows = block.get('rows', [])
    if not rows:
        return ''
    
    lines = []
    
    # Calculate column count
    max_cols = max(len(row.get('cells', [])) for row in rows)
    
    for row_idx, row in enumerate(rows):
        cells = row.get('cells', [])
        cell_texts = []
        
        for cell in cells:
            text = extract_cell_text_md(cell)
            # Escape pipe characters
            text = text.replace('|', '\\|').replace('\n', ' ')
            cell_texts.append(text)
        
        # Pad to max columns
        while len(cell_texts) < max_cols:
            cell_texts.append('')
        
        lines.append('| ' + ' | '.join(cell_texts) + ' |')
        
        # Add header separator after first row
        if row_idx == 0:
            lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
    
    return '\n'.join(lines)


def table_to_gfm_with_images(block: Dict[str, Any], assets_dir: str) -> str:
    """
    Convert table to GFM with standard Markdown images.
    Works in Obsidian/VS Code but has no image size control.
    """
    rows = block.get('rows', [])
    if not rows:
        return ''
    
    lines = []
    
    # Calculate column count
    max_cols = max(len(row.get('cells', [])) for row in rows)
    
    for row_idx, row in enumerate(rows):
        cells = row.get('cells', [])
        cell_texts = []
        
        for cell in cells:
            text = extract_cell_content_standard_md(cell, assets_dir)
            # Escape pipe characters but preserve markdown image syntax
            text = text.replace('\n', ' ').strip()
            cell_texts.append(text)
        
        # Pad to max columns
        while len(cell_texts) < max_cols:
            cell_texts.append('')
        
        lines.append('| ' + ' | '.join(cell_texts) + ' |')
        
        # Add header separator after first row
        if row_idx == 0:
            lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
    
    return '\n'.join(lines)


def extract_cell_content_standard_md(cell: Dict[str, Any], assets_dir: str) -> str:
    """Extract cell content using standard Markdown syntax for images."""
    parts = []
    
    for child in cell.get('children', []):
        child_type = child.get('type')
        
        if child_type == 'paragraph':
            if child.get('rich_text'):
                parts.append(rich_text_to_markdown(child['rich_text']))
            else:
                text = child.get('text', '')
                if text:
                    parts.append(text)
        
        elif child_type == 'image':
            src = child.get('src', '')
            alt = child.get('alt', 'image')
            if src:
                if not src.startswith(('http://', 'https://')):
                    filename = Path(src).name
                    src = f"{assets_dir}/{filename}"
                parts.append(f'![{alt}]({src})')
        
        elif child_type == 'list':
            for item in child.get('items', []):
                text = item.get('text', '')
                if item.get('rich_text'):
                    text = rich_text_to_markdown(item['rich_text'])
                parts.append(f'• {text}')
        
        elif child_type == 'code':
            parts.append(f"`{child.get('text', '')}`")
        
        elif child_type == 'file':
            name = child.get('name', 'File')
            src = child.get('src', '')
            if src and not src.startswith(('http://', 'https://')):
                filename = Path(src).name
                src = f"{assets_dir}/{filename}"
            parts.append(f'[📎 {name}]({src})')
    
    return ' '.join(parts) if parts else ''


def extract_cell_text_md(cell: Dict[str, Any]) -> str:
    """Extract text content from a table cell for Markdown."""
    texts = []
    
    for child in cell.get('children', []):
        child_type = child.get('type')
        
        if child_type == 'paragraph':
            if child.get('rich_text'):
                texts.append(rich_text_to_markdown(child['rich_text']))
            else:
                texts.append(child.get('text', ''))
        
        elif child_type == 'list':
            for item in child.get('items', []):
                prefix = '• ' if not child.get('ordered') else f"{child.get('items', []).index(item) + 1}. "
                if item.get('rich_text'):
                    texts.append(prefix + rich_text_to_markdown(item['rich_text']))
                else:
                    texts.append(prefix + item.get('text', ''))
        
        elif child_type == 'code':
            texts.append(f"`{child.get('text', '')}`")
    
    return ' '.join(texts)


def table_to_html(
    block: Dict[str, Any],
    assets_dir: str,
    image_width: int
) -> str:
    """Convert complex table to HTML block for GitHub Markdown."""
    rows = block.get('rows', [])
    if not rows:
        return ''
    
    lines = ['<table>']
    
    for row_idx, row in enumerate(rows):
        is_header = row.get('is_header_row', False) or row_idx == 0
        cells = row.get('cells', [])
        
        lines.append('  <tr>')
        
        for cell in cells:
            tag = 'th' if is_header or cell.get('is_header', False) else 'td'
            colspan = cell.get('colspan', 1)
            rowspan = cell.get('rowspan', 1)
            
            attrs = []
            if colspan > 1:
                attrs.append(f'colspan="{colspan}"')
            if rowspan > 1:
                attrs.append(f'rowspan="{rowspan}"')
            
            attr_str = ' ' + ' '.join(attrs) if attrs else ''
            
            cell_content = cell_to_html(cell, assets_dir, image_width)
            lines.append(f'    <{tag}{attr_str}>{cell_content}</{tag}>')
        
        lines.append('  </tr>')
    
    lines.append('</table>')
    
    return '\n'.join(lines)


def cell_to_html(
    cell: Dict[str, Any],
    assets_dir: str,
    image_width: int
) -> str:
    """Convert table cell content to HTML."""
    parts = []
    
    for child in cell.get('children', []):
        child_type = child.get('type')
        
        if child_type == 'paragraph':
            if child.get('rich_text'):
                parts.append(rich_text_to_markdown(child['rich_text']))
            else:
                parts.append(child.get('text', ''))
        
        elif child_type == 'image':
            src = child.get('src', '')
            if src and not src.startswith(('http://', 'https://')):
                filename = Path(src).name
                src = f"{assets_dir}/{filename}"
            parts.append(f'<img src="{src}" width="{image_width}">')
        
        elif child_type == 'list':
            list_items = []
            for item in child.get('items', []):
                text = item.get('text', '')
                if item.get('rich_text'):
                    text = rich_text_to_markdown(item['rich_text'])
                list_items.append(f'<li>{text}</li>')
            
            tag = 'ol' if child.get('ordered') else 'ul'
            parts.append(f'<{tag}>{"".join(list_items)}</{tag}>')
        
        elif child_type == 'code':
            parts.append(f'<code>{child.get("text", "")}</code>')
        
        elif child_type == 'file':
            name = child.get('name', 'File')
            src = child.get('src', '')
            if src and not src.startswith(('http://', 'https://')):
                filename = Path(src).name
                src = f"{assets_dir}/{filename}"
            parts.append(f'<a href="{src}">📎 {name}</a>')
    
    return '<br>'.join(parts) if parts else ''


def copy_assets(
    html_path: Path,
    output_dir: Path,
    assets_dir_name: str = 'assets',
    per_page_assets: bool = True
) -> Tuple[Dict[str, str], str]:
    """
    Copy all assets (images, files) from HTML attachments to output directory.
    
    Args:
        html_path: Path to the HTML file being converted
        output_dir: Output directory for markdown files (or page folder in nested mode)
        assets_dir_name: Name for assets folder (default: 'assets')
        per_page_assets: If True, create a separate assets folder per page
    
    Returns:
        Tuple of (path_mapping dict, assets_folder_relative_path)
    """
    # In nested mode, output_dir is already the page folder, so just use 'assets'
    # In flat mode with per_page_assets, use PageName_assets
    if per_page_assets:
        folder_name = assets_dir_name  # Just 'assets' since we're already in page folder
    else:
        folder_name = assets_dir_name
    
    assets_output = output_dir / folder_name
    assets_output.mkdir(parents=True, exist_ok=True)
    
    path_mapping = {}
    
    # Find attachments directory - extract just the page ID
    page_id = extract_page_id(html_path)
    attachments_dir = html_path.parent / 'attachments' / page_id
    
    if attachments_dir.exists():
        for file_path in attachments_dir.iterdir():
            if file_path.is_file():
                dest = assets_output / file_path.name
                shutil.copy2(file_path, dest)
                
                # Map original relative path to new path
                original_rel = f"attachments/{page_id}/{file_path.name}"
                path_mapping[original_rel] = f"{folder_name}/{file_path.name}"
    
    return path_mapping, folder_name


def extract_page_id(html_path: Path) -> str:
    """
    Extract the Confluence page ID from HTML filename.
    
    Handles two filename formats:
    - Just ID: "2830172669.html" → "2830172669"
    - Title_ID: "Archiving-Policy-1.4.5_2273479205.html" → "2273479205"
    """
    stem = html_path.stem
    
    # If filename contains underscore, the ID is after the last underscore
    if '_' in stem:
        # Extract the part after the last underscore
        parts = stem.rsplit('_', 1)
        potential_id = parts[-1]
        # Verify it looks like a numeric ID
        if potential_id.isdigit():
            return potential_id
    
    # Otherwise, the whole stem is the ID (or just use it as-is)
    return stem


def copy_assets_nested(
    html_path: Path,
    page_folder: Path
) -> Tuple[Dict[str, str], int]:
    """
    Copy assets into nested page folder structure.
    
    Args:
        html_path: Path to the source HTML file
        page_folder: Path to the page's folder (e.g., output/Page-Title/)
    
    Returns:
        Tuple of (path_mapping dict, asset_count)
    """
    assets_dir = page_folder / 'assets'
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    path_mapping = {}
    asset_count = 0
    
    # Find attachments directory - extract just the page ID
    page_id = extract_page_id(html_path)
    attachments_dir = html_path.parent / 'attachments' / page_id
    
    if attachments_dir.exists():
        for file_path in attachments_dir.iterdir():
            if file_path.is_file():
                dest = assets_dir / file_path.name
                shutil.copy2(file_path, dest)
                
                # Map original relative path to new path (relative to README.md)
                original_rel = f"attachments/{page_id}/{file_path.name}"
                path_mapping[original_rel] = f"assets/{file_path.name}"
                asset_count += 1
    
    return path_mapping, asset_count


def export_to_markdown(
    source_dir: str,
    output_dir: str,
    table_image_width: int = DEFAULT_TABLE_IMAGE_WIDTH,
    image_width: int = DEFAULT_IMAGE_WIDTH,
    assets_dir_name: str = 'assets',
    per_page_assets: bool = True,
    nested_folders: bool = True,
    use_standard_markdown: bool = False
) -> Dict[str, Any]:
    """
    Export all HTML files from source directory to GitHub Markdown.
    
    Args:
        source_dir: Directory containing Confluence HTML export
        output_dir: Directory to write Markdown files and assets
        table_image_width: Max width for images in tables
        image_width: Max width for standalone images
        assets_dir_name: Base name of assets subdirectory
        per_page_assets: If True, each .md gets its own assets folder
        nested_folders: If True, use nested folder structure with page titles (recommended)
        use_standard_markdown: If True, use standard Markdown syntax for all images
                               (Obsidian/VS Code compatible, no size control)
    
    Returns:
        Dict with export statistics
    """
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    stats = {
        'total_files': 0,
        'successful': 0,
        'failed': 0,
        'assets_copied': 0,
        'errors': [],
        'pages': []  # Track created pages
    }
    
    # Find all HTML files
    html_files = list(source_path.glob('*.html'))
    stats['total_files'] = len(html_files)
    
    print(f"Found {len(html_files)} HTML files to convert...")
    
    if use_standard_markdown:
        print("Format: Standard Markdown (Obsidian/VS Code compatible)")
    else:
        print("Format: GitHub Flavored (with image sizing)")
    
    if nested_folders:
        print("Using nested folder structure (PageTitle/README.md)")
        return _export_nested(
            html_files, output_path, stats,
            table_image_width, image_width,
            use_standard_markdown
        )
    else:
        print("Using flat structure")
        return _export_flat(
            html_files, output_path, stats,
            table_image_width, image_width,
            assets_dir_name, per_page_assets,
            use_standard_markdown
        )


def _export_nested(
    html_files: List[Path],
    output_path: Path,
    stats: Dict[str, Any],
    table_image_width: int,
    image_width: int,
    use_standard_markdown: bool = False
) -> Dict[str, Any]:
    """Export using nested folder structure with page titles."""
    
    used_folder_names = set()
    
    for html_file in html_files:
        try:
            print(f"Converting: {html_file.name}")
            
            # Parse HTML to AST
            ast = parse_html_file(html_file)
            
            # Get page title and create sanitized folder name
            page_title = ast.get('title', html_file.stem)
            folder_name = sanitize_folder_name(page_title)
            folder_name = get_unique_folder_name(folder_name, used_folder_names)
            used_folder_names.add(folder_name)
            
            # Create page folder
            page_folder = output_path / folder_name
            page_folder.mkdir(parents=True, exist_ok=True)
            
            # Copy assets to page folder
            asset_mapping, asset_count = copy_assets_nested(html_file, page_folder)
            stats['assets_copied'] += asset_count
            
            # Convert to Markdown - use 'assets' as the relative path
            markdown = ast_to_github_markdown(
                ast,
                assets_dir='assets',
                table_image_width=table_image_width,
                image_width=image_width,
                use_standard_markdown=use_standard_markdown
            )
            
            # Write README.md in page folder
            md_path = page_folder / 'README.md'
            md_path.write_text(markdown, encoding='utf-8')
            
            stats['successful'] += 1
            stats['pages'].append({
                'title': page_title,
                'folder': folder_name,
                'assets': asset_count
            })
            
            if asset_count:
                print(f"  ✓ Created: {folder_name}/README.md ({asset_count} assets)")
            else:
                print(f"  ✓ Created: {folder_name}/README.md (no assets)")
            
        except Exception as e:
            stats['failed'] += 1
            stats['errors'].append({
                'file': str(html_file),
                'error': str(e)
            })
            print(f"  ✗ Failed: {html_file.name} - {e}")
    
    # Create index file with links to all pages
    _create_index(output_path, stats['pages'])
    
    print(f"\nExport complete:")
    print(f"  Successful: {stats['successful']}/{stats['total_files']}")
    print(f"  Assets copied: {stats['assets_copied']}")
    print(f"  Created _index.md with links to all pages")
    if stats['failed'] > 0:
        print(f"  Failed: {stats['failed']}")
    
    return stats


def _export_flat(
    html_files: List[Path],
    output_path: Path,
    stats: Dict[str, Any],
    table_image_width: int,
    image_width: int,
    assets_dir_name: str,
    per_page_assets: bool,
    use_standard_markdown: bool = False
) -> Dict[str, Any]:
    """Export using flat structure (original behavior)."""
    
    for html_file in html_files:
        try:
            print(f"Converting: {html_file.name}")
            
            # Parse HTML to AST
            ast = parse_html_file(html_file)
            
            # Copy assets - returns the actual folder name used
            asset_mapping, page_assets_dir = copy_assets(
                html_file, output_path, assets_dir_name, per_page_assets
            )
            stats['assets_copied'] += len(asset_mapping)
            
            # Convert to Markdown using the correct assets folder for this page
            markdown = ast_to_github_markdown(
                ast,
                assets_dir=page_assets_dir,
                table_image_width=table_image_width,
                image_width=image_width,
                use_standard_markdown=use_standard_markdown
            )
            
            # Write Markdown file
            md_filename = html_file.stem + '.md'
            md_path = output_path / md_filename
            md_path.write_text(markdown, encoding='utf-8')
            
            stats['successful'] += 1
            if asset_mapping:
                print(f"  ✓ Created: {md_filename} ({len(asset_mapping)} assets → {page_assets_dir}/)")
            else:
                print(f"  ✓ Created: {md_filename} (no assets)")
            
        except Exception as e:
            stats['failed'] += 1
            stats['errors'].append({
                'file': str(html_file),
                'error': str(e)
            })
            print(f"  ✗ Failed: {html_file.name} - {e}")
    
    print(f"\nExport complete:")
    print(f"  Successful: {stats['successful']}/{stats['total_files']}")
    print(f"  Assets copied: {stats['assets_copied']}")
    if stats['failed'] > 0:
        print(f"  Failed: {stats['failed']}")
    
    return stats


def _create_index(output_path: Path, pages: List[Dict[str, Any]]) -> None:
    """Create an index file with links to all exported pages."""
    
    lines = [
        "# Exported Pages Index",
        "",
        f"Total pages: {len(pages)}",
        "",
        "## Pages",
        ""
    ]
    
    # Sort pages alphabetically by title
    sorted_pages = sorted(pages, key=lambda p: p['title'].lower())
    
    for page in sorted_pages:
        folder = page['folder']
        title = page['title']
        assets = page['assets']
        
        asset_note = f" ({assets} assets)" if assets else ""
        lines.append(f"- [{title}](./{folder}/README.md){asset_note}")
    
    lines.append("")
    
    index_path = output_path / '_index.md'
    index_path.write_text('\n'.join(lines), encoding='utf-8')


def main():
    """CLI entry point for markdown exporter."""
    parser = argparse.ArgumentParser(
        description='Export Confluence HTML to GitHub Flavored Markdown'
    )
    parser.add_argument(
        '--source-dir',
        required=True,
        help='Directory containing Confluence HTML export'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory to write Markdown files'
    )
    parser.add_argument(
        '--table-image-width',
        type=int,
        default=DEFAULT_TABLE_IMAGE_WIDTH,
        help=f'Max width for images in tables (default: {DEFAULT_TABLE_IMAGE_WIDTH})'
    )
    parser.add_argument(
        '--image-width',
        type=int,
        default=DEFAULT_IMAGE_WIDTH,
        help=f'Max width for standalone images (default: {DEFAULT_IMAGE_WIDTH})'
    )
    parser.add_argument(
        '--assets-dir',
        default='assets',
        help='Name of assets subdirectory when using shared mode (default: assets)'
    )
    parser.add_argument(
        '--flat',
        action='store_true',
        help='Use flat structure instead of nested folders (not recommended)'
    )
    parser.add_argument(
        '--shared-assets',
        action='store_true',
        help='Use single shared assets folder instead of per-page folders (only with --flat)'
    )
    parser.add_argument(
        '--standard-markdown',
        action='store_true',
        help='Use standard Markdown for all images (Obsidian/VS Code compatible, no size control)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    args = parser.parse_args()
    
    stats = export_to_markdown(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        table_image_width=args.table_image_width,
        image_width=args.image_width,
        assets_dir_name=args.assets_dir,
        per_page_assets=not args.shared_assets,
        nested_folders=not args.flat,  # Default is nested
        use_standard_markdown=args.standard_markdown  # Obsidian/VS Code compatible
    )
    
    if args.json:
        print(json.dumps(stats))


if __name__ == '__main__':
    main()
