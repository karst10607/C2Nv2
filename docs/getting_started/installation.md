# Installation

This guide will help you install C2N Importer on your system.

## System Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **Python**: 3.8 or higher (for development)
- **Node.js**: 16.x or higher (for GUI development)
- **Storage**: At least 500MB free space

## Download Pre-built Application

The easiest way to use C2N Importer is to download the pre-built application:

```{tab-set}
```{tab-item} Windows
Download the latest `.exe` installer from the [releases page](https://github.com/your-repo/releases).

1. Run the installer
2. Follow the installation wizard
3. Launch from Start Menu
```

```{tab-item} macOS
Download the latest `.dmg` file from the [releases page](https://github.com/your-repo/releases).

1. Open the DMG file
2. Drag C2N Importer to Applications
3. Launch from Applications folder
```

```{tab-item} Linux
Download the latest `.AppImage` from the [releases page](https://github.com/your-repo/releases).

```bash
chmod +x C2N-Importer-*.AppImage
./C2N-Importer-*.AppImage
```
```
```

## Development Setup

For developers who want to run from source:

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/c2n-importer.git
cd c2n-importer
```

### 2. Install Python Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install Node Dependencies

```bash
npm install
```

### 4. Run the Application

```bash
npm start
```

## Verify Installation

To verify your installation:

1. Launch C2N Importer
2. Click the "About" menu item
3. Check that the version number is displayed

```{note}
If you encounter any issues during installation, please check our [troubleshooting guide](../user_guide/troubleshooting.md).
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Get started with your first import
- [Configuration](configuration.md) - Set up your Notion token and storage options




