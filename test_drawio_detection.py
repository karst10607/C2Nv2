#!/usr/bin/env python3
"""Test script to verify Draw.io detection in Confluence exports"""
import sys
from pathlib import Path
from src.processors.drawio_scanner import DrawioScanner

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_drawio_detection.py <export_directory>")
        sys.exit(1)
    
    export_dir = Path(sys.argv[1])
    if not export_dir.exists():
        print(f"Error: Directory '{export_dir}' does not exist")
        sys.exit(1)
    
    scanner = DrawioScanner()
    print(f"Scanning {export_dir} for Draw.io content...\n")
    
    diagrams_by_file = scanner.scan_export(export_dir)
    
    if not diagrams_by_file:
        print("No Draw.io diagrams found.")
        return
    
    print(f"Found Draw.io content in {len(diagrams_by_file)} file(s):\n")
    
    for html_file, diagrams in diagrams_by_file.items():
        print(f"📄 {html_file.name}")
        for diagram in diagrams:
            status = "✅" if diagram.source_path and diagram.source_path.exists() else "❌"
            location = "embedded" if diagram.is_embedded else f"attachment: {diagram.source_path}"
            print(f"   {status} {diagram.filename} ({location})")
        print()
    
    # Test conversion
    output_dir = export_dir / 'drawio_test_output'
    output_dir.mkdir(exist_ok=True)
    
    print(f"\nTesting conversion to {output_dir}...")
    prepared = scanner.prepare_for_notion(diagrams_by_file, output_dir)
    print(f"Prepared {prepared} diagram(s)")
    
    # Show what files were created
    created_files = list(output_dir.glob('*'))
    if created_files:
        print("\nCreated files:")
        for f in created_files:
            print(f"  - {f.name}")

if __name__ == "__main__":
    main()








