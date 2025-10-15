# Electron GUI for Notion Importer

Modern cross-platform desktop app built with Electron.

## Setup

```bash
cd /home/koto/C2Nv2/notion_importer

# Install Node.js dependencies
npm install

# Start the app
npm start
```

## Features

- **Modern UI**: Beautiful gradient design with smooth animations
- **Configuration**: Save Notion token, Parent ID, and source folder
- **Test Connection**: Verify your Notion token works
- **Browse Folder**: GUI folder picker for source directory
- **Dry Run**: Preview import without writing to Notion
- **Live Logs**: Real-time output from the Python importer
- **Stop Button**: Cancel import mid-process

## Building Standalone Apps

```bash
# Build for macOS
npm run build:mac

# Build for Linux (AppImage + .deb)
npm run build:linux
```

Built apps will be in the `dist/` folder.

## Requirements

- Node.js 16+ and npm
- Python 3.10+ with requirements.txt installed
- cloudflared or ngrok for image tunneling

## How It Works

The Electron app provides a GUI that:
1. Saves config to `~/.notion_importer/config.json`
2. Spawns the Python importer (`python3 -m src.importer`)
3. Streams logs to the GUI in real-time
4. Allows stopping the process

The Python backend handles all the actual importing logic.
