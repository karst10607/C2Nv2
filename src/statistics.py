"""
Lightweight HTML statistics scanner.
Completely separate from conversion parser - read-only analysis.
"""

from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Any
from collections import defaultdict
import json
import re


def scan_html_statistics(source_dir: Path) -> Dict[str, Any]:
    """
    Scan HTML files and collect statistics about:
    - Merged cells (colspan/rowspan in tables)
    - Side-by-side layouts (columnLayout divs)
    - Videos
    - Draw.io diagrams
    - PlantUML diagrams
    
    This is a READ-ONLY operation - no conversion, no AST creation.
    Just counts structural elements in HTML.
    
    Args:
        source_dir: Directory containing HTML files
        
    Returns:
        Dictionary with statistics
    """
    stats = {
        'total_files': 0,
        'tables': {
            'total': 0,
            'with_merged_cells': 0,
            'merged_cell_count': 0,
            'colspan_count': 0,
            'rowspan_count': 0,
            'files_with_tables': 0
        },
        'layouts': {
            'total': 0,
            'by_type': {},
            'files_with_layouts': 0
        },
        'videos': {
            'total': 0,
            'files_with_videos': 0
        },
        'drawio': {
            'total': 0,
            'files_with_drawio': 0
        },
        'plantuml': {
            'total': 0,
            'files_with_plantuml': 0
        }
    }
    
    html_files = list(source_dir.rglob('*.html'))
    stats['total_files'] = len(html_files)
    
    if not html_files:
        return stats
    
    files_with_tables = set()
    files_with_layouts = set()
    files_with_videos = set()
    files_with_drawio = set()
    files_with_plantuml = set()
    
    for html_file in html_files:
        file_stats = analyze_single_file(html_file)
        
        # Aggregate table statistics
        if file_stats['tables']['count'] > 0:
            files_with_tables.add(html_file.name)
            stats['tables']['total'] += file_stats['tables']['count']
            stats['tables']['with_merged_cells'] += file_stats['tables']['with_merged']
            stats['tables']['merged_cell_count'] += file_stats['tables']['merged_total']
            stats['tables']['colspan_count'] += file_stats['tables']['colspan_total']
            stats['tables']['rowspan_count'] += file_stats['tables']['rowspan_total']
        
        # Aggregate layout statistics
        if file_stats['layouts']['count'] > 0:
            files_with_layouts.add(html_file.name)
            stats['layouts']['total'] += file_stats['layouts']['count']
            for layout_type, count in file_stats['layouts']['by_type'].items():
                if layout_type not in stats['layouts']['by_type']:
                    stats['layouts']['by_type'][layout_type] = 0
                stats['layouts']['by_type'][layout_type] += count
        
        # Aggregate video statistics
        if file_stats['videos']['count'] > 0:
            files_with_videos.add(html_file.name)
            stats['videos']['total'] += file_stats['videos']['count']
        
        # Aggregate Draw.io statistics
        if file_stats['drawio']['count'] > 0:
            files_with_drawio.add(html_file.name)
            stats['drawio']['total'] += file_stats['drawio']['count']
        
        # Aggregate PlantUML statistics
        if file_stats['plantuml']['count'] > 0:
            files_with_plantuml.add(html_file.name)
            stats['plantuml']['total'] += file_stats['plantuml']['count']
    
    stats['tables']['files_with_tables'] = len(files_with_tables)
    stats['layouts']['files_with_layouts'] = len(files_with_layouts)
    stats['videos']['files_with_videos'] = len(files_with_videos)
    stats['drawio']['files_with_drawio'] = len(files_with_drawio)
    stats['plantuml']['files_with_plantuml'] = len(files_with_plantuml)
    
    return stats


def analyze_single_file(html_file: Path) -> Dict[str, Any]:
    """
    Analyze a single HTML file for statistics.
    
    This function ONLY reads HTML structure - no conversion logic.
    
    Args:
        html_file: Path to HTML file
        
    Returns:
        Dictionary with file-level statistics
    """
    try:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            soup = BeautifulSoup(content, 'lxml')
    except Exception:
        # Skip files that can't be read
        return {
            'file': html_file.name,
            'tables': {'count': 0, 'with_merged': 0, 'merged_total': 0, 'colspan_total': 0, 'rowspan_total': 0},
            'layouts': {'count': 0, 'by_type': {}},
            'videos': {'count': 0},
            'drawio': {'count': 0},
            'plantuml': {'count': 0}
        }
    
    file_stats = {
        'file': html_file.name,
        'tables': {
            'count': 0,
            'with_merged': 0,
            'merged_total': 0,
            'colspan_total': 0,
            'rowspan_total': 0
        },
        'layouts': {
            'count': 0,
            'by_type': defaultdict(int)
        },
        'videos': {
            'count': 0
        },
        'drawio': {
            'count': 0
        },
        'plantuml': {
            'count': 0
        }
    }
    
    # Count tables and merged cells
    tables = soup.find_all('table')
    file_stats['tables']['count'] = len(tables)
    
    for table in tables:
        has_merged = False
        colspan_count = 0
        rowspan_count = 0
        
        for td in table.find_all(['td', 'th']):
            try:
                colspan = int(td.get('colspan', 1))
                rowspan = int(td.get('rowspan', 1))
                
                if colspan > 1:
                    has_merged = True
                    colspan_count += 1
                if rowspan > 1:
                    has_merged = True
                    rowspan_count += 1
            except (ValueError, TypeError):
                # Skip invalid colspan/rowspan values
                continue
        
        if has_merged:
            file_stats['tables']['with_merged'] += 1
            file_stats['tables']['merged_total'] += colspan_count + rowspan_count
            file_stats['tables']['colspan_total'] += colspan_count
            file_stats['tables']['rowspan_total'] += rowspan_count
    
    # Count columnLayout divs
    layouts = soup.find_all('div', class_=lambda x: x and 'columnLayout' in x)
    file_stats['layouts']['count'] = len(layouts)
    
    for layout in layouts:
        layout_type = layout.get('data-layout', 'unknown')
        if not layout_type or layout_type == 'unknown':
            # Try to infer from class names
            classes = layout.get('class', [])
            for cls in classes:
                if cls != 'columnLayout' and 'column' in cls.lower():
                    layout_type = cls
                    break
            if layout_type == 'unknown':
                layout_type = 'columnLayout'  # Default
        
        file_stats['layouts']['by_type'][layout_type] += 1
    
    # Convert defaultdict to regular dict for JSON serialization
    file_stats['layouts']['by_type'] = dict(file_stats['layouts']['by_type'])
    
    # Count videos
    # Use a set to track unique video references
    video_refs = set()
    
    # Look for <video> tags
    video_tags = soup.find_all('video')
    for tag in video_tags:
        src = tag.get('src', '')
        if src:
            video_refs.add(src)
        else:
            # Count as unique video even without src
            video_refs.add(f"video_tag_{len(video_refs)}")
    
    # Look for <a> tags with video file extensions
    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv']
    video_links = soup.find_all('a', href=True)
    for link in video_links:
        href = link.get('href', '').lower()
        if any(ext in href for ext in video_extensions):
            # Remove query parameters for uniqueness
            clean_href = href.split('?')[0] if '?' in href else href
            video_refs.add(clean_href)
    
    file_stats['videos']['count'] = len(video_refs)
    
    # Count Draw.io diagrams
    # Use a set to track unique Draw.io diagram references
    drawio_refs = set()
    
    # Look for divs with drawio-related classes or ids (avoid double counting)
    drawio_divs = soup.find_all('div', class_=lambda x: x and 'drawio' in str(x).lower())
    for div in drawio_divs:
        div_id = div.get('id', '')
        if div_id:
            drawio_refs.add(f"div_id_{div_id}")
        else:
            drawio_refs.add(f"div_class_{id(div)}")
    
    # Look for divs with id containing 'diagramly' (if not already counted)
    diagramly_divs = soup.find_all('div', id=lambda x: x and 'diagramly' in str(x).lower())
    for div in diagramly_divs:
        div_id = div.get('id', '')
        if div_id:
            drawio_refs.add(f"div_id_{div_id}")
    
    # Look for mxfile tags
    mxfile_tags = soup.find_all('mxfile')
    for tag in mxfile_tags:
        tag_id = tag.get('id', tag.get('host', ''))
        if tag_id:
            drawio_refs.add(f"mxfile_{tag_id}")
        else:
            drawio_refs.add(f"mxfile_{id(tag)}")
    
    # Look for Draw.io attachments in hrefs
    drawio_attachment_pattern = re.compile(
        r'href=["\']attachments/\d+/([\w.-]+\.drawio(?:\.png|\.svg)?)["\']',
        re.IGNORECASE
    )
    for match in drawio_attachment_pattern.finditer(content):
        filename = match.group(1)
        drawio_refs.add(f"attachment_{filename}")
    
    # Look for mxGraphModel in content (embedded Draw.io)
    # Count unique mxGraphModel blocks
    mxgraph_pattern = re.compile(r'<mxGraphModel[^>]*>.*?</mxGraphModel>', re.DOTALL | re.IGNORECASE)
    mxgraph_matches = mxgraph_pattern.findall(content)
    for i, match in enumerate(mxgraph_matches):
        drawio_refs.add(f"mxgraph_{i}")
    
    # Look for Confluence Draw.io macros
    confluence_drawio_macro = re.compile(
        r'<ac:structured-macro[^>]*ac:name=["\']drawio["\'][^>]*>.*?</ac:structured-macro>',
        re.DOTALL | re.IGNORECASE
    )
    macro_matches = confluence_drawio_macro.findall(content)
    for i, match in enumerate(macro_matches):
        drawio_refs.add(f"macro_{i}")
    
    file_stats['drawio']['count'] = len(drawio_refs)
    
    # Count PlantUML diagrams
    # Use a set to track unique PlantUML diagram references
    plantuml_refs = set()
    
    # Look for divs with id containing 'plantuml'
    plantuml_divs = soup.find_all('div', id=lambda x: x and 'plantuml' in str(x).lower())
    for div in plantuml_divs:
        div_id = div.get('id', '')
        if div_id:
            plantuml_refs.add(f"div_id_{div_id}")
    
    # Look for script tags with PlantUML addon key
    plantuml_script_pattern = re.compile(
        r'"addon_key"\s*:\s*"com\.mxgraph\.confluence\.plugins\.plantuml".*?"uniqueKey"\s*:\s*"([^"]+)"',
        re.DOTALL | re.IGNORECASE
    )
    script_matches = plantuml_script_pattern.findall(content)
    for unique_key in script_matches:
        plantuml_refs.add(f"script_{unique_key}")
    
    # Look for ap-container divs with plantuml in id (if not already counted above)
    plantuml_ap_containers = soup.find_all('div', class_='ap-container', 
                                          id=lambda x: x and 'plantuml' in str(x).lower())
    for div in plantuml_ap_containers:
        div_id = div.get('id', '')
        if div_id:
            plantuml_refs.add(f"div_id_{div_id}")
    
    file_stats['plantuml']['count'] = len(plantuml_refs)
    
    return file_stats


def main():
    """CLI entry point for statistics"""
    import argparse
    import sys
    
    ap = argparse.ArgumentParser(description="Scan HTML files for statistics")
    ap.add_argument('--source-dir', required=True, help='Source directory with HTML files')
    args = ap.parse_args()
    
    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        print(f"Error: Directory not found: {source_dir}", file=sys.stderr)
        return 1
    
    stats = scan_html_statistics(source_dir)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())

