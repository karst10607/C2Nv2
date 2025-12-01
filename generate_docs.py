#!/usr/bin/env python3
"""Generate API documentation for C2N Importer"""

import subprocess
import sys
from pathlib import Path

def main():
    """Generate HTML documentation using pdoc"""
    
    # Check if pdoc is installed
    try:
        import pdoc
    except ImportError:
        print("Installing pdoc...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pdoc"])
    
    # Generate docs
    print("Generating documentation...")
    subprocess.check_call([
        sys.executable, "-m", "pdoc",
        "--html",
        "--force",
        "--output-dir", "docs",
        "--config", "show_source_code=True",
        "--config", "latex_math=True",
        "src"
    ])
    
    print("\nDocumentation generated in ./docs/")
    print("Open ./docs/src/index.html in your browser to view.")
    
    # Optional: Start a local server
    if "--serve" in sys.argv:
        print("\nStarting documentation server on http://localhost:8080")
        subprocess.call([
            sys.executable, "-m", "pdoc",
            "--http", "localhost:8080",
            "src"
        ])

if __name__ == "__main__":
    main()


