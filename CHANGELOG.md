# Changelog

All notable changes to this project will be documented in this file.

## [2.4.5.1] - 2025-10-16

### Fixed
- Remove hardcoded Linux path from default config; use empty string
- Fix image parsing to prefer data-image-src and skip Confluence thumbnails
- Add support for images nested in paragraphs and table cells

## [2.4.5] - 2025-10-16

### Changed
- Move large binaries out of git; add fetch script for tools
- Add electron-updater and GitHub publish config
- Bump app version to 2.4.5; clean product name/title

## [2.4] - 2025-10-15

### 🐰 Enhanced Progress Bar & Rabbit Animation

#### Real-time Import Progress
- **Visual Progress Bar**: Beautiful gradient progress bar with animated hopping rabbit
- **File Counter**: Shows "X / Y files" processed in real-time
- **Time Tracking**: Live elapsed time display (MM:SS format)
- **ETA Calculation**: Estimates remaining time based on processing speed
- **Smooth Animations**: Rabbit hops along progress bar with realistic physics

#### Progress Information Display
- **Percentage Indicator**: Bold percentage with smooth transitions
- **Time Display**: Current elapsed time updates every second
- **Completion Status**: Shows "Complete!" when finished
- **Clean Design**: Modern rounded corners, shadows, and monospace info boxes

### 🔧 Technical Improvements

#### Image Import Reliability
- **Query Parameter Cleanup**: Removed `?width=760` parameters from image URLs that were causing 404s
- **Tunnel Timeout Fix**: Added 30-second delay after import to let Notion cache images
- **Enhanced Logging**: Added detailed server logs to track image requests and responses
- **CORS Headers**: Improved cross-origin support for Notion image fetching

#### Progress Bar Fixes
- **Accurate Counting**: Progress now correctly counts all processed files, not just first match
- **Completion Detection**: Bar reaches 100% and rabbit stops at end on successful import
- **Robust Parsing**: Handles multiple file log lines in single IPC message
- **Error Recovery**: Maintains progress state even if parsing fails

### 🖥️ GUI Enhancements
- **Better Error Display**: Cleaner error messages with hover tooltips for full details
- **Responsive Layout**: Improved spacing and visual hierarchy
- **Progress Section**: Dedicated area that appears only during import
- **Real-time Updates**: All progress elements update smoothly during operation

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
