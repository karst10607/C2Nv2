# Minimal Sphinx configuration for quick start

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# Project info
project = 'C2N Importer'
author = 'C2N Team'

# Basic extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'myst_parser',
]

# File patterns
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '.jupyter_cache']
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# HTML output
html_theme = 'alabaster'
html_static_path = ['_static']

# MyST settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]


