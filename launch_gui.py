#!/usr/bin/env python3
"""
Standalone launcher for Notion Importer GUI
Double-click this file to open the configuration window
"""
import sys
import tkinter as tk
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

from src.gui_config import App

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
