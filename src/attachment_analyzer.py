"""
Attachment Analyzer for Confluence Export
Scans and categorizes attachment files by type
"""
import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict


# File type categories
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv', '.flv', '.m4v'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods'}
DATA_EXTENSIONS = {'.csv', '.json', '.xml', '.yaml', '.yml'}
ARCHIVE_EXTENSIONS = {'.zip', '.tar', '.gz', '.rar', '.7z'}
CODE_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.css', '.html', '.sql'}


def get_file_category(extension: str) -> str:
    """Get category for a file extension."""
    ext = extension.lower()
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    elif ext in AUDIO_EXTENSIONS:
        return 'audio'
    elif ext in IMAGE_EXTENSIONS:
        return 'image'
    elif ext in DOCUMENT_EXTENSIONS:
        return 'document'
    elif ext in DATA_EXTENSIONS:
        return 'data'
    elif ext in ARCHIVE_EXTENSIONS:
        return 'archive'
    elif ext in CODE_EXTENSIONS:
        return 'code'
    elif ext == '':
        return 'no_extension'
    else:
        return 'other'


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def analyze_attachments(source_dir: str) -> Dict[str, Any]:
    """
    Analyze all attachments in a Confluence export directory.
    
    Args:
        source_dir: Path to Confluence export directory
    
    Returns:
        Dictionary with analysis results
    """
    source_path = Path(source_dir)
    attachments_dir = source_path / 'attachments'
    
    if not attachments_dir.exists():
        return {
            'success': False,
            'error': f"Attachments folder not found: {attachments_dir}",
            'total_files': 0,
            'total_size': 0,
            'categories': {},
            'files': []
        }
    
    # Collect all files
    files_by_category: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    stats_by_extension: Dict[str, Dict[str, Any]] = defaultdict(lambda: {'count': 0, 'size': 0})
    total_files = 0
    total_size = 0
    
    for page_folder in attachments_dir.iterdir():
        if not page_folder.is_dir():
            continue
        
        page_id = page_folder.name
        
        for file_path in page_folder.iterdir():
            if not file_path.is_file():
                continue
            
            try:
                file_size = file_path.stat().st_size
            except OSError:
                file_size = 0
            
            extension = file_path.suffix.lower()
            category = get_file_category(extension)
            
            file_info = {
                'name': file_path.name,
                'path': str(file_path),
                'relative_path': f"attachments/{page_id}/{file_path.name}",
                'page_id': page_id,
                'extension': extension if extension else '(none)',
                'category': category,
                'size': file_size,
                'size_formatted': format_size(file_size)
            }
            
            files_by_category[category].append(file_info)
            stats_by_extension[extension if extension else '(none)']['count'] += 1
            stats_by_extension[extension if extension else '(none)']['size'] += file_size
            total_files += 1
            total_size += file_size
    
    # Build category summary
    categories = {}
    for category, files in files_by_category.items():
        category_size = sum(f['size'] for f in files)
        categories[category] = {
            'count': len(files),
            'size': category_size,
            'size_formatted': format_size(category_size),
            'files': sorted(files, key=lambda x: x['size'], reverse=True)
        }
    
    # Build extension summary
    extensions = {}
    for ext, stats in stats_by_extension.items():
        extensions[ext] = {
            'count': stats['count'],
            'size': stats['size'],
            'size_formatted': format_size(stats['size'])
        }
    
    return {
        'success': True,
        'total_files': total_files,
        'total_size': total_size,
        'total_size_formatted': format_size(total_size),
        'categories': categories,
        'extensions': extensions,
        'video_files': files_by_category.get('video', []),
        'has_videos': len(files_by_category.get('video', [])) > 0
    }


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    return shutil.which('ffmpeg') is not None


def convert_video_to_mp3(
    video_path: str,
    output_path: Optional[str] = None,
    delete_original: bool = False
) -> Dict[str, Any]:
    """
    Convert a video file to MP3 audio.
    
    Args:
        video_path: Path to video file
        output_path: Optional output path (default: same name with .mp3)
        delete_original: If True, delete the original video after conversion
    
    Returns:
        Dictionary with conversion result
    """
    if not check_ffmpeg():
        return {
            'success': False,
            'error': 'ffmpeg not found. Install ffmpeg to convert videos.'
        }
    
    video_file = Path(video_path)
    if not video_file.exists():
        return {
            'success': False,
            'error': f'Video file not found: {video_path}'
        }
    
    if output_path:
        mp3_file = Path(output_path)
    else:
        mp3_file = video_file.with_suffix('.mp3')
    
    try:
        # Run ffmpeg conversion
        result = subprocess.run([
            'ffmpeg', '-i', str(video_file),
            '-vn',  # No video
            '-acodec', 'libmp3lame',
            '-ab', '192k',  # Audio bitrate
            '-y',  # Overwrite
            str(mp3_file)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return {
                'success': False,
                'error': f'ffmpeg error: {result.stderr[:500]}'
            }
        
        # Optionally delete original
        if delete_original:
            video_file.unlink()
        
        return {
            'success': True,
            'output_path': str(mp3_file),
            'output_size': mp3_file.stat().st_size,
            'output_size_formatted': format_size(mp3_file.stat().st_size),
            'original_deleted': delete_original
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def convert_all_videos_to_mp3(
    source_dir: str,
    delete_originals: bool = False
) -> Dict[str, Any]:
    """
    Convert all video files in attachments to MP3.
    
    Args:
        source_dir: Path to Confluence export directory
        delete_originals: If True, delete original videos after conversion
    
    Returns:
        Dictionary with batch conversion results
    """
    if not check_ffmpeg():
        return {
            'success': False,
            'error': 'ffmpeg not found. Install ffmpeg to convert videos.',
            'converted': 0,
            'failed': 0
        }
    
    # First analyze to get video files
    analysis = analyze_attachments(source_dir)
    if not analysis['success']:
        return {
            'success': False,
            'error': analysis.get('error', 'Analysis failed'),
            'converted': 0,
            'failed': 0
        }
    
    video_files = analysis.get('video_files', [])
    if not video_files:
        return {
            'success': True,
            'message': 'No video files found',
            'converted': 0,
            'failed': 0
        }
    
    results = []
    converted = 0
    failed = 0
    
    for video in video_files:
        result = convert_video_to_mp3(
            video['path'],
            delete_original=delete_originals
        )
        result['source_file'] = video['name']
        results.append(result)
        
        if result['success']:
            converted += 1
        else:
            failed += 1
    
    return {
        'success': True,
        'converted': converted,
        'failed': failed,
        'total': len(video_files),
        'results': results
    }


def delete_files_by_category(source_dir: str, category: str) -> Dict[str, Any]:
    """
    Delete all files of a specific category.
    
    Args:
        source_dir: Path to Confluence export directory
        category: Category to delete (video, audio, etc.)
    
    Returns:
        Dictionary with deletion results
    """
    analysis = analyze_attachments(source_dir)
    if not analysis['success']:
        return {
            'success': False,
            'error': analysis.get('error', 'Analysis failed'),
            'deleted': 0
        }
    
    category_data = analysis['categories'].get(category)
    if not category_data:
        return {
            'success': True,
            'message': f'No files found in category: {category}',
            'deleted': 0
        }
    
    deleted = 0
    errors = []
    
    for file_info in category_data['files']:
        try:
            Path(file_info['path']).unlink()
            deleted += 1
        except Exception as e:
            errors.append(f"{file_info['name']}: {str(e)}")
    
    return {
        'success': True,
        'deleted': deleted,
        'errors': errors if errors else None
    }


def delete_file(file_path: str) -> Dict[str, Any]:
    """Delete a single file."""
    try:
        path = Path(file_path)
        if not path.exists():
            return {'success': False, 'error': 'File not found'}
        
        path.unlink()
        return {'success': True, 'deleted': file_path}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def main():
    """CLI entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze Confluence export attachments')
    parser.add_argument('--source-dir', required=True, help='Confluence export directory')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--convert-videos', action='store_true', help='Convert videos to MP3')
    parser.add_argument('--delete-originals', action='store_true', help='Delete original videos after conversion')
    
    args = parser.parse_args()
    
    if args.convert_videos:
        result = convert_all_videos_to_mp3(args.source_dir, args.delete_originals)
    else:
        result = analyze_attachments(args.source_dir)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result['success']:
            print(f"\n📊 Attachment Analysis: {args.source_dir}")
            print(f"{'='*60}")
            print(f"Total files: {result['total_files']}")
            print(f"Total size: {result['total_size_formatted']}")
            print()
            
            print("📁 By Category:")
            for category, data in sorted(result['categories'].items()):
                print(f"  {category}: {data['count']} files ({data['size_formatted']})")
            
            print()
            print("📄 By Extension:")
            for ext, data in sorted(result['extensions'].items(), key=lambda x: x[1]['count'], reverse=True):
                print(f"  {ext}: {data['count']} files ({data['size_formatted']})")
            
            if result['has_videos']:
                print()
                print("🎬 Video files found:")
                for video in result['video_files'][:10]:
                    print(f"  - {video['name']} ({video['size_formatted']})")
                if len(result['video_files']) > 10:
                    print(f"  ... and {len(result['video_files']) - 10} more")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")


if __name__ == '__main__':
    main()
