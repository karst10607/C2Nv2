#!/usr/bin/env python3
"""Setup script for Sphinx documentation"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success status"""
    try:
        subprocess.check_call(cmd, shell=True, cwd=cwd)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    """Setup and build Sphinx documentation"""
    
    docs_dir = Path(__file__).parent / "docs"
    os.makedirs(docs_dir / "_static", exist_ok=True)
    os.makedirs(docs_dir / "_templates", exist_ok=True)
    os.makedirs(docs_dir / "api", exist_ok=True)
    
    # Create more directory structure
    dirs_to_create = [
        "getting_started",
        "user_guide", 
        "tutorials",
        "developer"
    ]
    
    for dir_name in dirs_to_create:
        os.makedirs(docs_dir / dir_name, exist_ok=True)
    
    print("📚 Setting up Sphinx documentation...")
    
    # Install documentation dependencies
    print("\n📦 Installing documentation dependencies...")
    if not run_command(f"{sys.executable} -m pip install -r docs/requirements.txt"):
        print("❌ Failed to install dependencies")
        return 1
    
    # Generate API documentation
    print("\n🔧 Generating API documentation...")
    if not run_command(f"{sys.executable} -m sphinx.ext.apidoc -f -o docs/api src", cwd="."):
        print("❌ Failed to generate API docs")
        return 1
    
    # Build HTML documentation
    print("\n🏗️ Building HTML documentation...")
    if not run_command("sphinx-build -b html docs docs/_build/html"):
        print("❌ Failed to build HTML docs")
        return 1
    
    print("\n✅ Documentation built successfully!")
    print(f"📂 Open docs/_build/html/index.html to view")
    
    # Optional: Build PDF
    if "--pdf" in sys.argv:
        print("\n📄 Building PDF documentation...")
        if run_command("sphinx-build -b latex docs docs/_build/latex"):
            if run_command("make", cwd="docs/_build/latex"):
                print("✅ PDF documentation built successfully!")
                print(f"📂 PDF available at docs/_build/latex/c2n-importer.pdf")
            else:
                print("❌ Failed to compile PDF (LaTeX required)")
        else:
            print("❌ Failed to generate LaTeX files")
    
    # Optional: Start development server
    if "--serve" in sys.argv:
        print("\n🌐 Starting documentation server...")
        print("📡 Documentation available at http://localhost:8000")
        print("Press Ctrl+C to stop")
        try:
            os.chdir("docs/_build/html")
            run_command(f"{sys.executable} -m http.server 8000")
        except KeyboardInterrupt:
            print("\n👋 Server stopped")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


