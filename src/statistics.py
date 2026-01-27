"""
Lightweight HTML statistics scanner.
Completely separate from conversion parser - read-only analysis.

Now includes:
- Content analysis (tables, layouts, videos, drawio, plantuml)
- Author/editor extraction
- Temporal analysis (activity by year/month)
- Visualization support (pie charts, timelines)
"""

from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import json
import re
import math


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


def extract_page_metadata_simple(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """
    Extract page metadata from Confluence HTML export (simplified version for statistics).
    
    Returns:
        Dict with 'created_by', 'created_date', 'last_modified_by', 'last_modified_date'
    """
    metadata = {
        'created_by': None,
        'created_date': None,
        'last_modified_by': None,
        'last_modified_date': None
    }
    
    # Find page-metadata div
    metadata_div = soup.find('div', class_='page-metadata')
    if not metadata_div:
        return metadata
    
    metadata_text = metadata_div.get_text()
    if not metadata_text:
        return metadata
    
    # Extract author span (creator)
    author_span = metadata_div.find('span', class_='author')
    if author_span:
        metadata['created_by'] = author_span.get_text(strip=True)
    
    # Extract editor span (last modifier)
    editor_span = metadata_div.find('span', class_='editor')
    if editor_span:
        metadata['last_modified_by'] = editor_span.get_text(strip=True)
    
    # Try to parse dates from text
    # Pattern: "last modified on DATE"
    last_modified_match = re.search(
        r'last modified(?:\s+by\s+[^,]+)?\s+on\s+([^<\n]+)',
        metadata_text,
        re.IGNORECASE
    )
    
    if last_modified_match:
        date_str = last_modified_match.group(1)
        if date_str:
            metadata['last_modified_date'] = date_str.strip()
    
    # Pattern: "Created by NAME on DATE"
    created_date_match = re.search(
        r'created(?:\s+by\s+[^,]+)?\s+on\s+([^<\n]+?)(?:,\s*last|$)',
        metadata_text,
        re.IGNORECASE
    )
    if created_date_match:
        date_str = created_date_match.group(1).strip()
        if date_str.endswith(',') and not re.search(r'\d{4},?\s*$', date_str):
            date_str = date_str.rstrip(',').strip()
        metadata['created_date'] = date_str
    
    return metadata


def parse_date_string(date_str: str) -> Optional[Tuple[int, int, int]]:
    """
    Parse a date string into (year, month, day) tuple.
    
    Supports formats like:
    - "Oct 31, 2025"
    - "Oct 31 2025"
    - "October 31, 2025"
    - "2025-10-31"
    
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Month name mapping
    month_names = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    
    # Try "Month DD, YYYY" or "Month DD YYYY" format
    match = re.match(
        r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',
        date_str,
        re.IGNORECASE
    )
    if match:
        month_str, day_str, year_str = match.groups()
        month = month_names.get(month_str.lower()[:3])
        if month:
            return (int(year_str), month, int(day_str))
    
    # Try ISO format "YYYY-MM-DD"
    match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if match:
        year, month, day = match.groups()
        return (int(year), int(month), int(day))
    
    # Try to extract just the year if nothing else works
    year_match = re.search(r'\b(20\d{2})\b', date_str)
    if year_match:
        return (int(year_match.group(1)), 1, 1)  # Default to Jan 1
    
    return None


def scan_html_with_metadata(source_dir: Path) -> Dict[str, Any]:
    """
    Scan HTML files and collect comprehensive statistics including:
    - Structural elements (tables, layouts, videos, etc.)
    - Author/editor information
    - Temporal analysis (when pages were created/modified)
    
    Args:
        source_dir: Directory containing HTML files
        
    Returns:
        Dictionary with statistics and metadata
    """
    stats = scan_html_statistics(source_dir)
    
    # Additional metadata tracking
    authors = defaultdict(lambda: {'created': 0, 'edited': 0})
    timeline_created = defaultdict(int)  # key: (year, month)
    timeline_modified = defaultdict(int)  # key: (year, month)
    pages_with_metadata = []
    
    html_files = list(source_dir.rglob('*.html'))
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                soup = BeautifulSoup(content, 'lxml')
        except Exception:
            continue
        
        metadata = extract_page_metadata_simple(soup)
        
        # Track authors
        if metadata.get('created_by'):
            authors[metadata['created_by']]['created'] += 1
        if metadata.get('last_modified_by'):
            authors[metadata['last_modified_by']]['edited'] += 1
        
        # Track timeline - created dates
        if metadata.get('created_date'):
            parsed = parse_date_string(metadata['created_date'])
            if parsed:
                year, month, _ = parsed
                timeline_created[(year, month)] += 1
        
        # Track timeline - modified dates
        if metadata.get('last_modified_date'):
            parsed = parse_date_string(metadata['last_modified_date'])
            if parsed:
                year, month, _ = parsed
                timeline_modified[(year, month)] += 1
        
        # Store page metadata
        if any(metadata.values()):
            title = soup.title.string.strip() if soup.title and soup.title.string else html_file.stem
            pages_with_metadata.append({
                'file': html_file.name,
                'title': title,
                **metadata
            })
    
    # Convert to regular dicts
    stats['authors'] = {
        name: dict(data) for name, data in authors.items()
    }
    
    # Timeline by year-month
    stats['timeline'] = {
        'created': {f"{year}-{month:02d}": count 
                   for (year, month), count in sorted(timeline_created.items())},
        'modified': {f"{year}-{month:02d}": count 
                    for (year, month), count in sorted(timeline_modified.items())}
    }
    
    # Aggregate by year
    yearly_created = defaultdict(int)
    yearly_modified = defaultdict(int)
    for (year, month), count in timeline_created.items():
        yearly_created[year] += count
    for (year, month), count in timeline_modified.items():
        yearly_modified[year] += count
    
    stats['yearly'] = {
        'created': dict(sorted(yearly_created.items())),
        'modified': dict(sorted(yearly_modified.items()))
    }
    
    stats['pages_with_metadata'] = pages_with_metadata
    stats['metadata_count'] = len(pages_with_metadata)
    
    return stats


def generate_pie_chart_ascii(data: Dict[str, int], title: str = "Content Distribution", 
                              width: int = 40) -> str:
    """
    Generate an ASCII pie chart representation.
    
    Args:
        data: Dictionary of {label: count}
        title: Chart title
        width: Width of the bars
        
    Returns:
        ASCII art string representing the pie chart
    """
    if not data or sum(data.values()) == 0:
        return f"{title}\n  (no data)"
    
    total = sum(data.values())
    lines = [f"📊 {title}", "─" * (width + 25), ""]
    
    # Define colors/symbols for different categories
    symbols = ['█', '▓', '▒', '░', '▀', '▄', '▌', '▐']
    
    # Sort by value (descending)
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
    
    for i, (label, count) in enumerate(sorted_data):
        if count == 0:
            continue
        
        percentage = (count / total) * 100
        bar_length = int((count / total) * width)
        symbol = symbols[i % len(symbols)]
        bar = symbol * max(bar_length, 1)
        
        # Format: Label (count, percentage) [bar]
        line = f"  {label:<20} {count:>5} ({percentage:>5.1f}%) │{bar}"
        lines.append(line)
    
    lines.append("─" * (width + 25))
    lines.append(f"  Total: {total}")
    
    return "\n".join(lines)


def generate_timeline_chart(timeline: Dict[str, int], title: str = "Activity Timeline",
                            width: int = 50) -> str:
    """
    Generate an ASCII timeline bar chart.
    
    Args:
        timeline: Dictionary of {YYYY-MM: count}
        title: Chart title
        width: Width of the bars
        
    Returns:
        ASCII art string representing the timeline
    """
    if not timeline or sum(timeline.values()) == 0:
        return f"{title}\n  (no data)"
    
    max_count = max(timeline.values()) if timeline.values() else 1
    
    lines = [f"📅 {title}", "─" * (width + 20), ""]
    
    for period, count in sorted(timeline.items()):
        bar_length = int((count / max_count) * width) if max_count > 0 else 0
        bar = "█" * bar_length
        lines.append(f"  {period} │{bar} {count}")
    
    lines.append("─" * (width + 20))
    lines.append(f"  Total: {sum(timeline.values())}")
    
    return "\n".join(lines)


def generate_yearly_chart(yearly: Dict[int, int], title: str = "Yearly Activity",
                          width: int = 50) -> str:
    """
    Generate an ASCII chart for yearly activity.
    
    Args:
        yearly: Dictionary of {year: count}
        title: Chart title
        width: Width of the bars
        
    Returns:
        ASCII art string
    """
    if not yearly or sum(yearly.values()) == 0:
        return f"{title}\n  (no data)"
    
    max_count = max(yearly.values()) if yearly.values() else 1
    
    lines = [f"📆 {title}", "─" * (width + 15), ""]
    
    for year, count in sorted(yearly.items()):
        bar_length = int((count / max_count) * width) if max_count > 0 else 0
        bar = "▓" * bar_length
        percentage = (count / sum(yearly.values())) * 100
        lines.append(f"  {year} │{bar} {count} ({percentage:.1f}%)")
    
    lines.append("─" * (width + 15))
    lines.append(f"  Total: {sum(yearly.values())} pages")
    
    return "\n".join(lines)


def generate_author_chart(authors: Dict[str, Dict[str, int]], title: str = "Top Contributors",
                          max_authors: int = 15, width: int = 40) -> str:
    """
    Generate an ASCII chart for author contributions.
    
    Args:
        authors: Dictionary of {author: {created: N, edited: M}}
        title: Chart title
        max_authors: Maximum number of authors to show
        width: Width of the bars
        
    Returns:
        ASCII art string
    """
    if not authors:
        return f"{title}\n  (no data)"
    
    # Calculate totals and sort
    author_totals = [(name, data['created'] + data['edited'], data['created'], data['edited'])
                     for name, data in authors.items()]
    author_totals.sort(key=lambda x: x[1], reverse=True)
    
    max_count = author_totals[0][1] if author_totals else 1
    
    lines = [f"👥 {title}", "─" * (width + 35), ""]
    lines.append(f"  {'Name':<25} {'Total':>6} {'Created':>8} {'Edited':>8}")
    lines.append(f"  {'-'*25} {'-'*6} {'-'*8} {'-'*8}")
    
    for name, total, created, edited in author_totals[:max_authors]:
        # Truncate long names
        display_name = name[:24] + "…" if len(name) > 25 else name
        bar_length = int((total / max_count) * 20) if max_count > 0 else 0
        bar = "█" * bar_length
        lines.append(f"  {display_name:<25} {total:>6} {created:>8} {edited:>8} │{bar}")
    
    if len(author_totals) > max_authors:
        lines.append(f"  ... and {len(author_totals) - max_authors} more contributors")
    
    lines.append("─" * (width + 35))
    total_created = sum(data['created'] for data in authors.values())
    total_edited = sum(data['edited'] for data in authors.values())
    lines.append(f"  Total: {len(authors)} authors, {total_created} pages created, {total_edited} edits")
    
    return "\n".join(lines)


def print_comprehensive_stats(source_dir: Path, use_rich: bool = True) -> Dict[str, Any]:
    """
    Print comprehensive statistics with visualizations.
    
    Args:
        source_dir: Directory containing HTML files
        use_rich: Whether to use rich library for colored output
        
    Returns:
        Statistics dictionary
    """
    stats = scan_html_with_metadata(source_dir)
    
    if use_rich:
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            console = Console()
            
            # Print header
            console.print("\n[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]")
            console.print("[bold cyan]       HTML ANALYSIS REPORT[/bold cyan]")
            console.print("[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]\n")
            
            # Content Type Pie Chart
            content_data = {
                'Tables': stats['tables']['total'],
                'Layouts': stats['layouts']['total'],
                'Videos': stats['videos']['total'],
                'Draw.io': stats['drawio']['total'],
                'PlantUML': stats['plantuml']['total']
            }
            # Filter out zero values for cleaner display
            content_data = {k: v for k, v in content_data.items() if v > 0}
            
            console.print(Panel(
                generate_pie_chart_ascii(content_data, "Content Type Distribution"),
                border_style="green"
            ))
            
            # Files summary
            files_data = {
                'With Tables': stats['tables']['files_with_tables'],
                'With Layouts': stats['layouts']['files_with_layouts'],
                'With Videos': stats['videos']['files_with_videos'],
                'With Draw.io': stats['drawio']['files_with_drawio'],
                'With PlantUML': stats['plantuml']['files_with_plantuml']
            }
            files_data = {k: v for k, v in files_data.items() if v > 0}
            
            console.print(Panel(
                generate_pie_chart_ascii(files_data, f"Files with Special Content (of {stats['total_files']} total)"),
                border_style="blue"
            ))
            
            # Author Statistics
            if stats.get('authors'):
                console.print(Panel(
                    generate_author_chart(stats['authors'], "Top Contributors"),
                    border_style="magenta"
                ))
            
            # Yearly Activity
            if stats.get('yearly', {}).get('modified'):
                console.print(Panel(
                    generate_yearly_chart(stats['yearly']['modified'], "Activity by Year (Last Modified)"),
                    border_style="yellow"
                ))
            
            # Monthly Timeline (last 12 months with data)
            if stats.get('timeline', {}).get('modified'):
                timeline = stats['timeline']['modified']
                # Show last 24 periods with data
                recent_timeline = dict(list(sorted(timeline.items()))[-24:])
                if recent_timeline:
                    console.print(Panel(
                        generate_timeline_chart(recent_timeline, "Monthly Activity (Last Modified)"),
                        border_style="cyan"
                    ))
            
            console.print("\n[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]\n")
            
        except ImportError:
            # Fallback to plain text
            use_rich = False
    
    if not use_rich:
        # Plain text output
        print("\n" + "=" * 55)
        print("       HTML ANALYSIS REPORT")
        print("=" * 55 + "\n")
        
        content_data = {
            'Tables': stats['tables']['total'],
            'Layouts': stats['layouts']['total'],
            'Videos': stats['videos']['total'],
            'Draw.io': stats['drawio']['total'],
            'PlantUML': stats['plantuml']['total']
        }
        content_data = {k: v for k, v in content_data.items() if v > 0}
        print(generate_pie_chart_ascii(content_data))
        print()
        
        if stats.get('authors'):
            print(generate_author_chart(stats['authors']))
            print()
        
        if stats.get('yearly', {}).get('modified'):
            print(generate_yearly_chart(stats['yearly']['modified']))
            print()
        
        print("=" * 55 + "\n")
    
    return stats


# =============================================================================
# Export Functions
# =============================================================================

def export_to_csv(stats: Dict[str, Any], output_path: Path) -> Path:
    """
    Export statistics to CSV files.
    
    Creates multiple CSV files:
    - {output_path}_summary.csv - Overall summary
    - {output_path}_authors.csv - Author statistics
    - {output_path}_timeline.csv - Monthly timeline
    - {output_path}_pages.csv - Per-page metadata
    
    Args:
        stats: Statistics dictionary from scan_html_with_metadata()
        output_path: Base path for output files (without extension)
        
    Returns:
        Path to the summary CSV file
    """
    import csv
    
    output_path = Path(output_path)
    base_name = output_path.stem
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Summary CSV
    summary_path = output_dir / f"{base_name}_summary.csv"
    with open(summary_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Files', stats['total_files']])
        writer.writerow(['Tables', stats['tables']['total']])
        writer.writerow(['Tables with Merged Cells', stats['tables']['with_merged_cells']])
        writer.writerow(['Layouts', stats['layouts']['total']])
        writer.writerow(['Videos', stats['videos']['total']])
        writer.writerow(['Draw.io Diagrams', stats['drawio']['total']])
        writer.writerow(['PlantUML Diagrams', stats['plantuml']['total']])
        writer.writerow(['Files with Tables', stats['tables']['files_with_tables']])
        writer.writerow(['Files with Layouts', stats['layouts']['files_with_layouts']])
        writer.writerow(['Files with Videos', stats['videos']['files_with_videos']])
        writer.writerow(['Files with Draw.io', stats['drawio']['files_with_drawio']])
        writer.writerow(['Files with PlantUML', stats['plantuml']['files_with_plantuml']])
    
    # Authors CSV
    if stats.get('authors'):
        authors_path = output_dir / f"{base_name}_authors.csv"
        with open(authors_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Author', 'Created', 'Edited', 'Total'])
            for name, data in sorted(stats['authors'].items(), 
                                     key=lambda x: x[1]['created'] + x[1]['edited'], 
                                     reverse=True):
                writer.writerow([name, data['created'], data['edited'], 
                               data['created'] + data['edited']])
    
    # Timeline CSV
    if stats.get('timeline', {}).get('modified'):
        timeline_path = output_dir / f"{base_name}_timeline.csv"
        with open(timeline_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Year-Month', 'Pages Modified'])
            for period, count in sorted(stats['timeline']['modified'].items()):
                writer.writerow([period, count])
    
    # Yearly CSV
    if stats.get('yearly', {}).get('modified'):
        yearly_path = output_dir / f"{base_name}_yearly.csv"
        with open(yearly_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Year', 'Pages Modified'])
            for year, count in sorted(stats['yearly']['modified'].items()):
                writer.writerow([year, count])
    
    # Per-page metadata CSV
    if stats.get('pages_with_metadata'):
        pages_path = output_dir / f"{base_name}_pages.csv"
        with open(pages_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['File', 'Title', 'Created By', 'Created Date', 
                           'Last Modified By', 'Last Modified Date'])
            for page in stats['pages_with_metadata']:
                writer.writerow([
                    page.get('file', ''),
                    page.get('title', ''),
                    page.get('created_by', ''),
                    page.get('created_date', ''),
                    page.get('last_modified_by', ''),
                    page.get('last_modified_date', '')
                ])
    
    return summary_path


def export_to_html(stats: Dict[str, Any], output_path: Path, 
                   source_dir_name: str = "HTML Export") -> Path:
    """
    Export statistics to an HTML report with interactive charts.
    
    Uses matplotlib if available, otherwise creates a CSS-only visual report.
    
    Args:
        stats: Statistics dictionary from scan_html_with_metadata()
        output_path: Path for the HTML output file
        source_dir_name: Name of the source directory for the report title
        
    Returns:
        Path to the HTML file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Try to use matplotlib for charts
    charts_html = ""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import base64
        from io import BytesIO
        
        def fig_to_base64(fig) -> str:
            """Convert matplotlib figure to base64 string."""
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', 
                       facecolor='#1a1a2e', edgecolor='none')
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            return img_str
        
        # Set dark theme
        plt.style.use('dark_background')
        
        # 1. Content Type Pie Chart
        content_data = {
            'Tables': stats['tables']['total'],
            'Layouts': stats['layouts']['total'],
            'Videos': stats['videos']['total'],
            'Draw.io': stats['drawio']['total'],
            'PlantUML': stats['plantuml']['total']
        }
        content_data = {k: v for k, v in content_data.items() if v > 0}
        
        if content_data:
            fig, ax = plt.subplots(figsize=(8, 6))
            colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7']
            wedges, texts, autotexts = ax.pie(
                content_data.values(), 
                labels=content_data.keys(),
                autopct='%1.1f%%',
                colors=colors[:len(content_data)],
                explode=[0.02] * len(content_data),
                shadow=True
            )
            ax.set_title('Content Type Distribution', fontsize=16, fontweight='bold', color='white')
            for text in texts + autotexts:
                text.set_color('white')
            charts_html += f'<img src="data:image/png;base64,{fig_to_base64(fig)}" class="chart" alt="Content Distribution">\n'
        
        # 2. Files with Content Bar Chart
        files_data = {
            'Tables': stats['tables']['files_with_tables'],
            'Layouts': stats['layouts']['files_with_layouts'],
            'Videos': stats['videos']['files_with_videos'],
            'Draw.io': stats['drawio']['files_with_drawio'],
            'PlantUML': stats['plantuml']['files_with_plantuml']
        }
        files_data = {k: v for k, v in files_data.items() if v > 0}
        
        if files_data:
            fig, ax = plt.subplots(figsize=(10, 5))
            bars = ax.bar(files_data.keys(), files_data.values(), color=['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7'][:len(files_data)])
            ax.set_title(f'Files with Special Content (of {stats["total_files"]} total)', fontsize=14, fontweight='bold')
            ax.set_ylabel('Number of Files')
            for bar, val in zip(bars, files_data.values()):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, str(val), 
                       ha='center', va='bottom', fontweight='bold', color='white')
            ax.set_facecolor('#1a1a2e')
            fig.patch.set_facecolor('#1a1a2e')
            charts_html += f'<img src="data:image/png;base64,{fig_to_base64(fig)}" class="chart" alt="Files Distribution">\n'
        
        # 3. Yearly Activity Bar Chart
        if stats.get('yearly', {}).get('modified'):
            yearly = stats['yearly']['modified']
            fig, ax = plt.subplots(figsize=(10, 5))
            years = [str(y) for y in sorted(yearly.keys())]
            counts = [yearly[int(y)] for y in years]
            bars = ax.bar(years, counts, color='#4ecdc4')
            ax.set_title('Activity by Year (Last Modified)', fontsize=14, fontweight='bold')
            ax.set_ylabel('Pages Modified')
            ax.set_xlabel('Year')
            for bar, val in zip(bars, counts):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, str(val),
                       ha='center', va='bottom', fontweight='bold', color='white')
            ax.set_facecolor('#1a1a2e')
            fig.patch.set_facecolor('#1a1a2e')
            charts_html += f'<img src="data:image/png;base64,{fig_to_base64(fig)}" class="chart" alt="Yearly Activity">\n'
        
        # 4. Monthly Timeline
        if stats.get('timeline', {}).get('modified'):
            timeline = stats['timeline']['modified']
            fig, ax = plt.subplots(figsize=(14, 5))
            periods = sorted(timeline.keys())[-24:]  # Last 24 months
            counts = [timeline[p] for p in periods]
            ax.fill_between(range(len(periods)), counts, alpha=0.3, color='#45b7d1')
            ax.plot(range(len(periods)), counts, marker='o', color='#45b7d1', linewidth=2, markersize=6)
            ax.set_xticks(range(len(periods)))
            ax.set_xticklabels(periods, rotation=45, ha='right')
            ax.set_title('Monthly Activity Timeline (Last Modified)', fontsize=14, fontweight='bold')
            ax.set_ylabel('Pages Modified')
            ax.grid(True, alpha=0.3)
            ax.set_facecolor('#1a1a2e')
            fig.patch.set_facecolor('#1a1a2e')
            plt.tight_layout()
            charts_html += f'<img src="data:image/png;base64,{fig_to_base64(fig)}" class="chart" alt="Monthly Timeline">\n'
        
        # 5. Top Contributors Bar Chart
        if stats.get('authors'):
            author_totals = [(name, data['created'] + data['edited'], data['created'], data['edited'])
                           for name, data in stats['authors'].items()]
            author_totals.sort(key=lambda x: x[1], reverse=True)
            top_authors = author_totals[:10]
            
            if top_authors:
                fig, ax = plt.subplots(figsize=(12, 6))
                names = [a[0][:20] + '...' if len(a[0]) > 20 else a[0] for a in top_authors]
                created = [a[2] for a in top_authors]
                edited = [a[3] for a in top_authors]
                
                x = range(len(names))
                width = 0.35
                bars1 = ax.bar([i - width/2 for i in x], created, width, label='Created', color='#4ecdc4')
                bars2 = ax.bar([i + width/2 for i in x], edited, width, label='Edited', color='#ff6b6b')
                
                ax.set_ylabel('Pages')
                ax.set_title('Top Contributors', fontsize=14, fontweight='bold')
                ax.set_xticks(x)
                ax.set_xticklabels(names, rotation=45, ha='right')
                ax.legend()
                ax.set_facecolor('#1a1a2e')
                fig.patch.set_facecolor('#1a1a2e')
                plt.tight_layout()
                charts_html += f'<img src="data:image/png;base64,{fig_to_base64(fig)}" class="chart" alt="Top Contributors">\n'
        
        # ============================================
        # TAB GALLERY CHARTS (4 Better Approaches)
        # ============================================
        tab_charts = {}  # Store charts for tab gallery
        
        if stats.get('timeline', {}).get('modified') and len(stats['timeline']['modified']) >= 2:
            import numpy as np
            
            timeline = stats['timeline']['modified']
            periods = sorted(timeline.keys())
            counts = [timeline[p] for p in periods]
            x_pos = np.arange(len(periods))
            
            # TAB 1: Peak Highlighted (Simple bar chart with peak marker)
            fig, ax = plt.subplots(figsize=(14, 6))
            bars = ax.bar(x_pos, counts, color='#4ecdc4', alpha=0.8)
            
            # Highlight peak
            peak_idx = counts.index(max(counts))
            bars[peak_idx].set_color('#ff6b6b')
            bars[peak_idx].set_alpha(1.0)
            
            # Add peak annotation
            ax.annotate(f'Peak: {max(counts)} edits', 
                       xy=(peak_idx, max(counts)), 
                       xytext=(peak_idx, max(counts) * 1.15),
                       ha='center', fontsize=11, color='#ffeaa7', fontweight='bold',
                       arrowprops=dict(arrowstyle='->', color='#ffeaa7', lw=2))
            
            ax.set_xticks(x_pos[::max(1, len(x_pos)//12)])  # Show ~12 labels
            ax.set_xticklabels([periods[i] for i in range(0, len(periods), max(1, len(periods)//12))], 
                              rotation=45, ha='right')
            ax.set_title(f'Monthly Activity - Peak: {periods[peak_idx]}', fontsize=14, fontweight='bold')
            ax.set_xlabel('Month')
            ax.set_ylabel('Number of Edits')
            ax.set_facecolor('#1a1a2e')
            fig.patch.set_facecolor('#1a1a2e')
            plt.tight_layout()
            tab_charts['peak'] = fig_to_base64(fig)
            
            # TAB 2: Moving Average Trend
            fig, ax = plt.subplots(figsize=(14, 6))
            ax.bar(x_pos, counts, color='#4ecdc4', alpha=0.4, label='Monthly Edits')
            
            # Calculate moving averages (3-month and 6-month)
            def moving_avg(data, window):
                return [sum(data[max(0,i-window+1):i+1])/min(i+1, window) for i in range(len(data))]
            
            ma3 = moving_avg(counts, 3)
            ma6 = moving_avg(counts, 6)
            
            ax.plot(x_pos, ma3, 'r-', linewidth=2.5, label='3-Month Moving Avg', marker='o', markersize=3)
            ax.plot(x_pos, ma6, 'y-', linewidth=2.5, label='6-Month Moving Avg', marker='s', markersize=3)
            
            ax.set_xticks(x_pos[::max(1, len(x_pos)//12)])
            ax.set_xticklabels([periods[i] for i in range(0, len(periods), max(1, len(periods)//12))], 
                              rotation=45, ha='right')
            ax.set_title('Monthly Activity with Moving Average Trends', fontsize=14, fontweight='bold')
            ax.set_xlabel('Month')
            ax.set_ylabel('Number of Edits')
            ax.legend(loc='upper left')
            ax.set_facecolor('#1a1a2e')
            fig.patch.set_facecolor('#1a1a2e')
            plt.tight_layout()
            tab_charts['moving_avg'] = fig_to_base64(fig)
            
            # TAB 3: Cumulative Chart
            fig, ax = plt.subplots(figsize=(14, 6))
            cumulative = np.cumsum(counts)
            
            ax.fill_between(x_pos, cumulative, alpha=0.3, color='#45b7d1')
            ax.plot(x_pos, cumulative, 'o-', color='#45b7d1', linewidth=2, markersize=4, label='Cumulative Edits')
            
            # Mark milestones
            total = cumulative[-1]
            for milestone in [0.25, 0.5, 0.75]:
                target = total * milestone
                idx = np.argmax(cumulative >= target)
                ax.axhline(y=target, color='#ffeaa7', linestyle=':', alpha=0.5)
                ax.annotate(f'{int(milestone*100)}%: {periods[idx]}', 
                           xy=(idx, target), xytext=(idx+2, target),
                           fontsize=9, color='#ffeaa7')
            
            ax.set_xticks(x_pos[::max(1, len(x_pos)//12)])
            ax.set_xticklabels([periods[i] for i in range(0, len(periods), max(1, len(periods)//12))], 
                              rotation=45, ha='right')
            ax.set_title(f'Cumulative Activity Over Time (Total: {int(total)} edits)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Month')
            ax.set_ylabel('Cumulative Edits')
            ax.legend(loc='upper left')
            ax.set_facecolor('#1a1a2e')
            fig.patch.set_facecolor('#1a1a2e')
            plt.tight_layout()
            tab_charts['cumulative'] = fig_to_base64(fig)
            
            # TAB 4: Heat Map (Year x Month grid)
            fig, ax = plt.subplots(figsize=(14, 6))
            
            # Parse periods into year/month matrix
            year_month_data = {}
            for period, count in timeline.items():
                parts = period.split('-')
                if len(parts) == 2:
                    year, month = int(parts[0]), int(parts[1])
                    if year not in year_month_data:
                        year_month_data[year] = {}
                    year_month_data[year][month] = count
            
            if year_month_data:
                years = sorted(year_month_data.keys())
                months = list(range(1, 13))
                
                # Create matrix
                matrix = []
                for year in years:
                    row = [year_month_data.get(year, {}).get(m, 0) for m in months]
                    matrix.append(row)
                
                matrix = np.array(matrix)
                
                im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
                
                # Labels
                ax.set_xticks(range(12))
                ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
                ax.set_yticks(range(len(years)))
                ax.set_yticklabels(years)
                
                # Add colorbar
                cbar = plt.colorbar(im, ax=ax)
                cbar.set_label('Number of Edits', color='white')
                cbar.ax.yaxis.set_tick_params(color='white')
                plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
                
                # Add values on cells
                for i in range(len(years)):
                    for j in range(12):
                        val = matrix[i, j]
                        if val > 0:
                            text_color = 'white' if val > matrix.max()/2 else 'black'
                            ax.text(j, i, int(val), ha='center', va='center', 
                                   fontsize=8, color=text_color, fontweight='bold')
                
                ax.set_title('Activity Heat Map (Year × Month)', fontsize=14, fontweight='bold')
                ax.set_xlabel('Month')
                ax.set_ylabel('Year')
                ax.set_facecolor('#1a1a2e')
                fig.patch.set_facecolor('#1a1a2e')
                plt.tight_layout()
                tab_charts['heatmap'] = fig_to_base64(fig)
            
            # TAB 5: Log Scale View
            fig, ax = plt.subplots(figsize=(14, 6))
            counts_log = [max(c, 0.5) for c in counts]
            
            bars = ax.bar(x_pos, counts_log, color='#96ceb4', alpha=0.8)
            ax.set_yscale('log')
            
            # Trend line
            if any(c > 0 for c in counts):
                log_counts = np.log10([max(c, 0.1) for c in counts])
                z = np.polyfit(x_pos, log_counts, 1)
                p = np.poly1d(z)
                trend_line = 10 ** p(x_pos)
                trend_dir = "↑ Growing" if z[0] > 0 else "↓ Declining"
                ax.plot(x_pos, trend_line, 'r--', linewidth=2.5, 
                       label=f'Trend: {trend_dir} ({z[0]*12:.2f}/year)')
            
            ax.set_xticks(x_pos[::max(1, len(x_pos)//12)])
            ax.set_xticklabels([periods[i] for i in range(0, len(periods), max(1, len(periods)//12))], 
                              rotation=45, ha='right')
            ax.set_title('Monthly Activity (Logarithmic Scale)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Month')
            ax.set_ylabel('Edits (Log Scale)')
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3, axis='y')
            ax.set_facecolor('#1a1a2e')
            fig.patch.set_facecolor('#1a1a2e')
            plt.tight_layout()
            tab_charts['logscale'] = fig_to_base64(fig)
        
        # Build tab gallery HTML
        if tab_charts:
            charts_html += """
            <div class="tab-gallery">
                <h3>📊 Activity Analysis Views</h3>
                <div class="tab-buttons">
                    <button class="tab-btn active" data-tab="peak">📍 Peak Highlighted</button>
                    <button class="tab-btn" data-tab="moving_avg">📈 Moving Average</button>
                    <button class="tab-btn" data-tab="cumulative">📊 Cumulative</button>
                    <button class="tab-btn" data-tab="heatmap">🔥 Heat Map</button>
                    <button class="tab-btn" data-tab="logscale">📐 Log Scale</button>
                </div>
                <div class="tab-content">
            """
            
            for tab_id, img_data in tab_charts.items():
                active = 'active' if tab_id == 'peak' else ''
                charts_html += f'<img src="data:image/png;base64,{img_data}" class="tab-image {active}" data-tab="{tab_id}" alt="{tab_id}">\n'
            
            charts_html += """
                </div>
            </div>
            """
        
        matplotlib_available = True
    except ImportError:
        matplotlib_available = False
        charts_html = "<p class='warning'>⚠️ Install matplotlib for visual charts: <code>pip install matplotlib</code></p>"
    
    # Build authors table
    authors_table = ""
    if stats.get('authors'):
        author_totals = [(name, data['created'] + data['edited'], data['created'], data['edited'])
                        for name, data in stats['authors'].items()]
        author_totals.sort(key=lambda x: x[1], reverse=True)
        
        authors_table = """
        <h2>👥 Contributors</h2>
        <table class="data-table">
            <thead>
                <tr><th>Author</th><th>Created</th><th>Edited</th><th>Total</th></tr>
            </thead>
            <tbody>
        """
        for name, total, created, edited in author_totals[:20]:
            authors_table += f"<tr><td>{name}</td><td>{created}</td><td>{edited}</td><td>{total}</td></tr>\n"
        authors_table += "</tbody></table>"
        if len(author_totals) > 20:
            authors_table += f"<p class='note'>... and {len(author_totals) - 20} more contributors</p>"
    
    # Build timeline table
    timeline_table = ""
    if stats.get('timeline', {}).get('modified'):
        timeline_table = """
        <h2>📅 Monthly Activity</h2>
        <table class="data-table">
            <thead>
                <tr><th>Period</th><th>Pages Modified</th></tr>
            </thead>
            <tbody>
        """
        for period, count in sorted(stats['timeline']['modified'].items(), reverse=True)[:24]:
            timeline_table += f"<tr><td>{period}</td><td>{count}</td></tr>\n"
        timeline_table += "</tbody></table>"
    
    # Generate timestamp
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Prepare Plotly data
    plotly_data = {
        'timeline': stats.get('timeline', {}).get('modified', {}),
        'authors': {name: data['created'] + data['edited'] for name, data in stats.get('authors', {}).items()},
        'yearly': stats.get('yearly', {}).get('modified', {}),
        'content': {
            'Tables': stats['tables']['total'],
            'Layouts': stats['layouts']['total'],
            'Videos': stats['videos']['total'],
            'Draw.io': stats['drawio']['total'],
            'PlantUML': stats['plantuml']['total']
        }
    }
    
    # Build HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTML Analysis Report - {source_dir_name}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {{
            --bg-primary: #0f0f1a;
            --bg-secondary: #1a1a2e;
            --bg-card: #16213e;
            --text-primary: #eee;
            --text-secondary: #aaa;
            --accent-cyan: #4ecdc4;
            --accent-pink: #ff6b6b;
            --accent-yellow: #ffeaa7;
            --accent-blue: #45b7d1;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            padding: 2rem;
            margin-bottom: 2rem;
            background: var(--bg-card);
            border-radius: 16px;
            border: 1px solid rgba(78, 205, 196, 0.2);
        }}
        
        h1 {{
            font-size: 2.5rem;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(78, 205, 196, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 32px rgba(78, 205, 196, 0.2);
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--accent-cyan);
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }}
        
        .charts-section {{
            background: var(--bg-card);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            border: 1px solid rgba(78, 205, 196, 0.1);
        }}
        
        .charts-section h2 {{
            color: var(--accent-cyan);
            margin-bottom: 1.5rem;
            font-size: 1.5rem;
        }}
        
        .chart {{
            max-width: 100%;
            margin: 1rem auto;
            display: block;
            border-radius: 8px;
        }}
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}
        
        .data-table th, .data-table td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .data-table th {{
            background: rgba(78, 205, 196, 0.1);
            color: var(--accent-cyan);
            font-weight: 600;
        }}
        
        .data-table tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        
        .warning {{
            background: rgba(255, 107, 107, 0.1);
            border: 1px solid var(--accent-pink);
            padding: 1rem;
            border-radius: 8px;
            color: var(--accent-pink);
        }}
        
        .note {{
            color: var(--text-secondary);
            font-style: italic;
            margin-top: 0.5rem;
        }}
        
        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
        
        @media (max-width: 768px) {{
            body {{ padding: 1rem; }}
            h1 {{ font-size: 1.8rem; }}
            .stat-value {{ font-size: 2rem; }}
        }}
        
        /* Tab Gallery Styles */
        .tab-gallery {{
            margin: 2rem 0;
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
        }}
        
        .tab-gallery h3 {{
            color: var(--accent-cyan);
            margin-bottom: 1rem;
        }}
        
        .tab-buttons {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid rgba(78, 205, 196, 0.2);
            padding-bottom: 1rem;
        }}
        
        .tab-btn {{
            padding: 0.7rem 1.2rem;
            border: none;
            background: var(--bg-card);
            color: var(--text-secondary);
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}
        
        .tab-btn:hover {{
            background: rgba(78, 205, 196, 0.2);
            color: var(--text-primary);
        }}
        
        .tab-btn.active {{
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
            color: white;
            font-weight: 600;
        }}
        
        .tab-content {{
            position: relative;
            min-height: 400px;
        }}
        
        .tab-image {{
            display: none;
            max-width: 100%;
            border-radius: 8px;
        }}
        
        .tab-image.active {{
            display: block;
        }}
        
        /* Interactive Chart Section */
        .interactive-section {{
            background: var(--bg-card);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            border: 2px solid var(--accent-cyan);
        }}
        
        .interactive-section h2 {{
            color: var(--accent-cyan);
            margin-bottom: 1rem;
        }}
        
        .axis-controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1rem;
            align-items: center;
        }}
        
        .axis-control {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .axis-control label {{
            color: var(--text-secondary);
            font-weight: 600;
        }}
        
        .axis-control select {{
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: 1px solid var(--accent-cyan);
            background: var(--bg-secondary);
            color: var(--text-primary);
            font-size: 0.9rem;
            cursor: pointer;
        }}
        
        .chart-type-btns {{
            display: flex;
            gap: 0.5rem;
            margin-left: auto;
        }}
        
        .chart-type-btn {{
            padding: 0.5rem 1rem;
            border: 1px solid var(--accent-cyan);
            background: transparent;
            color: var(--accent-cyan);
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .chart-type-btn:hover, .chart-type-btn.active {{
            background: var(--accent-cyan);
            color: var(--bg-primary);
        }}
        
        #plotly-chart {{
            width: 100%;
            height: 500px;
            background: var(--bg-secondary);
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 HTML Analysis Report</h1>
            <p class="subtitle">{source_dir_name} | Generated: {generated_at}</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats['total_files']}</div>
                <div class="stat-label">Total Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['tables']['total']}</div>
                <div class="stat-label">Tables</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['drawio']['total']}</div>
                <div class="stat-label">Draw.io Diagrams</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['layouts']['total']}</div>
                <div class="stat-label">Column Layouts</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['videos']['total']}</div>
                <div class="stat-label">Videos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['plantuml']['total']}</div>
                <div class="stat-label">PlantUML Diagrams</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(stats.get('authors', {}))}</div>
                <div class="stat-label">Contributors</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('metadata_count', 0)}</div>
                <div class="stat-label">Pages with Metadata</div>
            </div>
        </div>
        
        <div class="charts-section">
            <h2>📈 Visual Analytics</h2>
            {charts_html}
        </div>
        
        <div class="charts-section">
            {authors_table}
        </div>
        
        <div class="charts-section">
            {timeline_table}
        </div>
        
        <div class="interactive-section">
            <h2>🎛️ Interactive Chart Builder</h2>
            <div class="axis-controls">
                <div class="axis-control">
                    <label>X-Axis:</label>
                    <select id="x-axis-select">
                        <option value="month">Month</option>
                        <option value="year">Year</option>
                        <option value="author">Author</option>
                    </select>
                </div>
                <div class="axis-control">
                    <label>Y-Axis:</label>
                    <select id="y-axis-select">
                        <option value="edits">Edit Count</option>
                        <option value="cumulative">Cumulative</option>
                    </select>
                </div>
                <div class="chart-type-btns">
                    <button class="chart-type-btn active" data-type="bar">Bar</button>
                    <button class="chart-type-btn" data-type="line">Line</button>
                    <button class="chart-type-btn" data-type="scatter">Scatter</button>
                </div>
            </div>
            <div id="plotly-chart"></div>
        </div>
        
        <footer>
            <p>Generated by C2N Statistics Module</p>
        </footer>
    </div>
    
    <script>
        // Tab Gallery Logic
        document.querySelectorAll('.tab-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const tabId = btn.dataset.tab;
                
                // Update buttons
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Update images
                document.querySelectorAll('.tab-image').forEach(img => {{
                    img.classList.remove('active');
                    if (img.dataset.tab === tabId) {{
                        img.classList.add('active');
                    }}
                }});
            }});
        }});
        
        // Plotly Interactive Chart
        const statsData = {json.dumps(plotly_data)};
        
        let currentChartType = 'bar';
        
        function updatePlotlyChart() {{
            const xAxis = document.getElementById('x-axis-select').value;
            const yAxis = document.getElementById('y-axis-select').value;
            
            let xData = [];
            let yData = [];
            let title = '';
            
            if (xAxis === 'month') {{
                const timeline = statsData.timeline;
                xData = Object.keys(timeline).sort();
                if (yAxis === 'cumulative') {{
                    let cumsum = 0;
                    yData = xData.map(k => {{ cumsum += timeline[k]; return cumsum; }});
                    title = 'Cumulative Edits by Month';
                }} else {{
                    yData = xData.map(k => timeline[k]);
                    title = 'Edits by Month';
                }}
            }} else if (xAxis === 'year') {{
                const yearly = statsData.yearly;
                xData = Object.keys(yearly).sort();
                if (yAxis === 'cumulative') {{
                    let cumsum = 0;
                    yData = xData.map(k => {{ cumsum += yearly[k]; return cumsum; }});
                    title = 'Cumulative Edits by Year';
                }} else {{
                    yData = xData.map(k => yearly[k]);
                    title = 'Edits by Year';
                }}
            }} else if (xAxis === 'author') {{
                const authors = statsData.authors;
                const sorted = Object.entries(authors).sort((a, b) => b[1] - a[1]).slice(0, 15);
                xData = sorted.map(a => a[0]);
                yData = sorted.map(a => a[1]);
                title = 'Top Contributors';
            }}
            
            const trace = {{
                x: xData,
                y: yData,
                type: currentChartType === 'line' ? 'scatter' : currentChartType,
                mode: currentChartType === 'line' ? 'lines+markers' : (currentChartType === 'scatter' ? 'markers' : undefined),
                marker: {{ color: '#4ecdc4', size: currentChartType === 'scatter' ? 10 : undefined }},
                line: {{ color: '#4ecdc4', width: 2 }}
            }};
            
            const layout = {{
                title: {{ text: title, font: {{ color: '#eee' }} }},
                paper_bgcolor: '#1a1a2e',
                plot_bgcolor: '#1a1a2e',
                font: {{ color: '#aaa' }},
                xaxis: {{ 
                    title: xAxis.charAt(0).toUpperCase() + xAxis.slice(1),
                    gridcolor: 'rgba(255,255,255,0.1)',
                    tickangle: xAxis === 'month' ? -45 : 0
                }},
                yaxis: {{ 
                    title: yAxis === 'cumulative' ? 'Cumulative Edits' : 'Number of Edits',
                    gridcolor: 'rgba(255,255,255,0.1)'
                }},
                margin: {{ t: 50, l: 60, r: 30, b: xAxis === 'month' ? 100 : 60 }}
            }};
            
            Plotly.newPlot('plotly-chart', [trace], layout, {{ responsive: true }});
        }}
        
        // Event listeners
        document.getElementById('x-axis-select').addEventListener('change', updatePlotlyChart);
        document.getElementById('y-axis-select').addEventListener('change', updatePlotlyChart);
        
        document.querySelectorAll('.chart-type-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.chart-type-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentChartType = btn.dataset.type;
                updatePlotlyChart();
            }});
        }});
        
        // Initial render
        updatePlotlyChart();
    </script>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_path


def export_to_pdf(stats: Dict[str, Any], output_path: Path,
                  source_dir_name: str = "HTML Export") -> Path:
    """
    Export statistics to a PDF report.
    
    Requires matplotlib and reportlab. Falls back to HTML if not available.
    
    Args:
        stats: Statistics dictionary from scan_html_with_metadata()
        output_path: Path for the PDF output file
        source_dir_name: Name of the source directory for the report title
        
    Returns:
        Path to the PDF file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.enums import TA_CENTER
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from io import BytesIO
        import tempfile
        
        # Create PDF
        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#3498db')
        )
        
        story = []
        
        # Title
        story.append(Paragraph(f"📊 HTML Analysis Report", title_style))
        story.append(Paragraph(f"{source_dir_name}", styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Summary table
        story.append(Paragraph("Summary Statistics", heading_style))
        summary_data = [
            ['Metric', 'Value'],
            ['Total Files', str(stats['total_files'])],
            ['Tables', str(stats['tables']['total'])],
            ['Draw.io Diagrams', str(stats['drawio']['total'])],
            ['Layouts', str(stats['layouts']['total'])],
            ['Videos', str(stats['videos']['total'])],
            ['PlantUML Diagrams', str(stats['plantuml']['total'])],
            ['Contributors', str(len(stats.get('authors', {})))],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Create chart images
        plt.style.use('default')
        
        # Content pie chart
        content_data = {
            'Tables': stats['tables']['total'],
            'Layouts': stats['layouts']['total'],
            'Videos': stats['videos']['total'],
            'Draw.io': stats['drawio']['total'],
            'PlantUML': stats['plantuml']['total']
        }
        content_data = {k: v for k, v in content_data.items() if v > 0}
        
        if content_data:
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.pie(content_data.values(), labels=content_data.keys(), autopct='%1.1f%%',
                  colors=['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6'])
            ax.set_title('Content Type Distribution')
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                fig.savefig(tmp.name, dpi=100, bbox_inches='tight')
                plt.close(fig)
                story.append(Paragraph("Content Distribution", heading_style))
                story.append(Image(tmp.name, width=4*inch, height=3*inch))
                story.append(Spacer(1, 20))
        
        # Yearly activity chart
        if stats.get('yearly', {}).get('modified'):
            yearly = stats['yearly']['modified']
            fig, ax = plt.subplots(figsize=(6, 3))
            years = [str(y) for y in sorted(yearly.keys())]
            counts = [yearly[int(y)] for y in years]
            ax.bar(years, counts, color='#3498db')
            ax.set_title('Activity by Year')
            ax.set_ylabel('Pages')
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                fig.savefig(tmp.name, dpi=100, bbox_inches='tight')
                plt.close(fig)
                story.append(Paragraph("Yearly Activity", heading_style))
                story.append(Image(tmp.name, width=5*inch, height=2.5*inch))
                story.append(Spacer(1, 20))
        
        # Authors table
        if stats.get('authors'):
            story.append(Paragraph("Top Contributors", heading_style))
            author_data = [['Author', 'Created', 'Edited', 'Total']]
            author_totals = [(name, data['created'] + data['edited'], data['created'], data['edited'])
                           for name, data in stats['authors'].items()]
            author_totals.sort(key=lambda x: x[1], reverse=True)
            
            for name, total, created, edited in author_totals[:15]:
                display_name = name[:30] + '...' if len(name) > 30 else name
                author_data.append([display_name, str(created), str(edited), str(total)])
            
            author_table = Table(author_data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch])
            author_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            story.append(author_table)
        
        # Build PDF
        doc.build(story)
        return output_path
        
    except ImportError as e:
        # Fallback: generate HTML and suggest conversion
        print(f"Note: PDF generation requires 'reportlab'. Install with: pip install reportlab")
        print(f"Generating HTML report instead...")
        html_path = output_path.with_suffix('.html')
        export_to_html(stats, html_path, source_dir_name)
        return html_path


def export_statistics(source_dir: Path, output_path: Path, 
                      format: str = 'html') -> Path:
    """
    Export statistics to the specified format.
    
    Args:
        source_dir: Directory containing HTML files to analyze
        output_path: Output file path
        format: Export format ('html', 'csv', 'pdf', 'json')
        
    Returns:
        Path to the exported file
    """
    stats = scan_html_with_metadata(source_dir)
    source_dir_name = source_dir.name
    
    format = format.lower()
    
    if format == 'csv':
        return export_to_csv(stats, output_path)
    elif format == 'pdf':
        return export_to_pdf(stats, output_path, source_dir_name)
    elif format == 'json':
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, default=str)
        return output_path
    else:  # default to HTML
        return export_to_html(stats, output_path, source_dir_name)


def main():
    """CLI entry point for statistics"""
    import argparse
    import sys
    
    ap = argparse.ArgumentParser(
        description="Scan HTML files for statistics and export reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Terminal display with rich formatting
  python -m src.statistics --source-dir EP --comprehensive
  
  # Export to HTML report with charts
  python -m src.statistics --source-dir EP --export report.html
  
  # Export to CSV files
  python -m src.statistics --source-dir EP --export stats.csv --format csv
  
  # Export to PDF (requires reportlab)
  python -m src.statistics --source-dir EP --export report.pdf --format pdf
  
  # Export to JSON
  python -m src.statistics --source-dir EP --export data.json --format json
"""
    )
    ap.add_argument('--source-dir', required=True, help='Source directory with HTML files')
    ap.add_argument('--comprehensive', '-c', action='store_true',
                    help='Show comprehensive analysis with authors, timeline, and visualizations')
    ap.add_argument('--json', '-j', action='store_true',
                    help='Output raw JSON to stdout')
    ap.add_argument('--no-rich', action='store_true',
                    help='Disable rich library formatting (plain text)')
    
    # Export options
    ap.add_argument('--export', '-e', metavar='FILE',
                    help='Export report to file (auto-detects format from extension)')
    ap.add_argument('--format', '-f', choices=['html', 'csv', 'pdf', 'json'],
                    help='Export format (default: auto-detect from filename)')
    
    args = ap.parse_args()
    
    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        print(f"Error: Directory not found: {source_dir}", file=sys.stderr)
        return 1
    
    # Handle export
    if args.export:
        output_path = Path(args.export)
        
        # Auto-detect format from extension if not specified
        if args.format:
            export_format = args.format
        else:
            ext = output_path.suffix.lower()
            format_map = {'.html': 'html', '.htm': 'html', '.csv': 'csv', 
                         '.pdf': 'pdf', '.json': 'json'}
            export_format = format_map.get(ext, 'html')
        
        print(f"Analyzing {source_dir}...")
        result_path = export_statistics(source_dir, output_path, export_format)
        print(f"✓ Exported to: {result_path}")
        
        if export_format == 'csv':
            print(f"  Additional files created with _authors, _timeline, _yearly, _pages suffixes")
        
        return 0
    
    # Handle display modes
    if args.comprehensive:
        if args.json:
            stats = scan_html_with_metadata(source_dir)
            print(json.dumps(stats, indent=2, default=str))
        else:
            print_comprehensive_stats(source_dir, use_rich=not args.no_rich)
    else:
        stats = scan_html_statistics(source_dir)
        print(json.dumps(stats, indent=2))
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())

