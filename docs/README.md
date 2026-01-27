# C2N Importer Documentation

This directory contains the Sphinx documentation for C2N Importer.

## Quick Start

1. Install documentation dependencies:
   ```bash
   pip install -r docs/requirements.txt
   ```

2. Build the documentation:
   ```bash
   python setup_docs.py
   ```

3. View the documentation:
   - Open `docs/_build/html/index.html` in your browser
   - Or run `python setup_docs.py --serve` to start a local server

## Building Documentation

### HTML Documentation
```bash
cd docs
make html
# or on Windows: make.bat html
```

### PDF Documentation
```bash
python setup_docs.py --pdf
# Requires LaTeX installation
```

### Auto-rebuild During Development
```bash
sphinx-autobuild docs docs/_build/html
```

## Documentation Structure

```
docs/
├── getting_started/      # Installation and setup guides
├── user_guide/          # How to use the application
├── tutorials/           # Step-by-step tutorials
├── developer/           # Developer documentation
├── api/                 # Auto-generated API docs
├── _static/            # Images, CSS, etc.
├── _templates/         # Custom templates
└── conf.py             # Sphinx configuration
```

## Writing Documentation

### Markdown Support
We use MyST Parser for Markdown support. You can write docs in either:
- `.rst` files (reStructuredText)
- `.md` files (Markdown with MyST extensions)

### MyST Extensions
- **Admonitions**: `:::{note}`, `:::{warning}`, etc.
- **Code tabs**: ````{tab-set}` with `{tab-item}`
- **Mermaid diagrams**: ````{mermaid}`
- **Cards**: Using `sphinx-design` grid system

### API Documentation
API docs are auto-generated from docstrings:
```bash
sphinx-apidoc -f -o docs/api src
```

## Deployment

The documentation can be deployed to:
- GitHub Pages
- Read the Docs
- Any static hosting service

### GitHub Pages
```yaml
# .github/workflows/docs.yml
name: Build Documentation
on:
  push:
    branches: [main]
jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r docs/requirements.txt
      - run: python setup_docs.py
      - uses: actions/upload-pages-artifact@v2
        with:
          path: docs/_build/html
```

## Tips

1. **Use semantic markup**: Proper headings, code blocks, etc.
2. **Add examples**: Show actual code and output
3. **Include diagrams**: Use Mermaid for flowcharts
4. **Cross-reference**: Link between related topics
5. **Keep it updated**: Update docs with code changes




