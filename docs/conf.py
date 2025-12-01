# Configuration file for the Sphinx documentation builder.

import os
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------
project = 'C2N Importer'
copyright = f'{datetime.now().year}, C2N Team'
author = 'C2N Team'
release = '2.0.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx_autodoc_typehints',
    'sphinx_copybutton',
    'myst_nb',  # This includes myst_parser functionality
    'sphinxcontrib.mermaid',
    'sphinx_tabs.tabs',
    'sphinx_design',
]

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}
autodoc_typehints = 'description'
autodoc_typehints_format = 'short'

# MyST settings for Markdown support
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
    "html_image",
    "html_admonition",
]

# MyST-NB settings for Jupyter notebooks
nb_execution_mode = "cache"  # or "off" to disable execution
nb_execution_timeout = 600  # seconds
nb_execution_raise_on_error = True
nb_merge_streams = True
nb_execution_cache_path = ".jupyter_cache"

# Custom notebook rendering - removed problematic format
# nb_custom_formats = {}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '.jupyter_cache', '**.ipynb_checkpoints']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

# Theme options
html_theme_options = {
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'style_nav_header_background': '#2980B9',
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
}

# Add any paths that contain custom static files (such as style sheets) here,
html_static_path = ['_static']

# Custom CSS files
html_css_files = [
    'custom.css',
]

# Custom sidebar templates
html_sidebars = {
    '**': [
        'globaltoc.html',
        'relations.html',
        'sourcelink.html',
        'searchbox.html',
    ]
}

# -- Options for PDF output --------------------------------------------------
# For PDF generation with LaTeX
latex_engine = 'pdflatex'
latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '11pt',
    'preamble': r'''
\usepackage{charter}
\usepackage[defaultsans]{lato}
\usepackage{inconsolata}
''',
}

# Grouping the document tree into LaTeX files
latex_documents = [
    ('index', 'c2n-importer.tex', 'C2N Importer Documentation',
     'C2N Team', 'manual'),
]

# -- Extension configuration -------------------------------------------------

# Intersphinx mapping to link to other projects' documentation
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'notion': ('https://developers.notion.com/', None),
}

# Todo extension settings
todo_include_todos = True

# Copy button for code blocks
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# Mermaid settings for diagrams
mermaid_version = "10.6.1"
