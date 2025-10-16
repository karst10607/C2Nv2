#!/usr/bin/env python3
import os
import sys
import argparse

# Ensure package imports work in both dev and bundled modes
def _prepare_path():
    # Dev: add project root containing `src/`
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)
    # Bundled (PyInstaller): include extracted data path for `src/`
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        src_path = os.path.join(sys._MEIPASS, 'src')
        if os.path.isdir(src_path) and src_path not in sys.path:
            sys.path.insert(0, src_path)


def main(argv=None):
    _prepare_path()
    from src.importer import main as importer_main
    parser = argparse.ArgumentParser(add_help=False)
    # Pass-through arguments to src.importer
    args, unknown = parser.parse_known_args(argv)
    return importer_main(unknown)


if __name__ == "__main__":
    sys.exit(main())
