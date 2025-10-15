# Notion Importer (Confluence HTML → Notion)

- Cross-platform: macOS + Linux
- Images kept local; served via temporary tunnel during import (cloudflared → ngrok fallback)
- Tables with images converted to Notion column_list/column; wrap rows >6 cells
- Use HTML <title> as Notion page title

## GUI Options

### Option 1: Electron GUI (Recommended)
Modern desktop app with live logs and better UX.

```bash
npm install
npm start
```

See [README_ELECTRON.md](README_ELECTRON.md) for details.

### Option 2: Tkinter GUI (Lightweight)
Simple Python GUI, no Node.js required.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.gui_config  # or: ./launch_gui.py
```

## CLI Usage

```bash
python -m src.importer --dry-run  # preview
python -m src.importer --run --parent-id <YOUR_PARENT_ID>
```

## Config
- GUI stores config at `~/.notion_importer/config.json`.
- CLI flags override config.

## Source Directory
Default: `/home/koto/C2Nv2/work 2`
