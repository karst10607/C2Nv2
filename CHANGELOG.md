# Changelog

All notable changes to this project will be documented in this file.

## [2.3] - 2025-10-15

### 🎯 Major Fixes

#### Content Import Issues (FIXED)
- Fixed HTML parser not extracting content from nested Confluence divs
- Parser now correctly finds content in #main-content and #content containers
- All text, images, and tables now import successfully

#### Image Import Issues (FIXED)
- Added cloudflared tunnel installation and setup
- Implemented DNS propagation wait mechanism (prevents 'image not found')
- Images now properly cached in Notion through public tunnel URLs
- Fixed attachment path handling for Confluence exports

#### Text Length Limits (FIXED)
- Handle Notion's 2000 character limit per text block
- Long paragraphs automatically split at sentence boundaries
- List items and code blocks truncated with '...' indicator
- Prevents '400 Bad Request' errors during import

### ✨ New Features

#### Table Layout Preservation
- New 'Preserve Table Layout' option in GUI
- Configurable minimum column height (1-10 blocks)
- Automatic height normalization for columns with mixed content
- Better visual alignment of images and text in multi-column layouts

#### Enhanced GUI Controls
- Added checkbox for layout preservation toggle
- Added input for minimum column height configuration
- Cleaner error messages without breaking UI layout
- Hover tooltips show full error details

### 🔧 Technical Improvements
- Smarter content extraction from complex HTML structures
- Robust tunnel creation with retry logic
- DNS resolution verification before import
- Better validation before import starts

## [2.1] - 2025-10-15

### Added
- Electron GUI with configuration interface
- Test Connection button with clean error display
- Browse folder, Save config, Dry run, and Import functionality
- Improved error handling (no traceback in UI)
- Support for macOS and Linux
- Local image server with tunnel support

## [2.0] - 2025-10-14

### Initial Release
- Import Confluence HTML exports to Notion
- Convert tables with images to column_list/column blocks
- Support for images via local server and tunnel
- Command-line interface
- Basic HTML parsing and transformation
