# Changelog

All notable changes to this project will be documented in this file.

## [2.6.1] - 2025-10-21

### 🔧 Code Refactoring (Option A Quick Refactor)

### Added
- **src/image_utils.py**: Centralized image filtering utilities
  - `should_skip_image()`: Single source of truth for filtering
  - `extract_image_src()`: Normalize image URLs
  - `is_content_image()`: Check if image is actual content
- **src/verification.py**: ImageVerifier class for clean verification logic
  - `verify_page_images()`: Returns (success, verified_count)
  - `count_verified_images_in_blocks()`: Extracted nested loop logic
  - Easier to test and maintain

### Changed
- **html_parser.py**: Reduced from 195 → 115 lines (-80 lines, -41%)
  - Uses image_utils for all image filtering
  - No more code duplication (was in 3 places)
  - Single fix applies everywhere
- **importer.py**: Reduced from 326 → 253 lines (-73 lines, -22%)
  - Uses ImageVerifier for verification
  - Cleaner main() function
  - Better separation of concerns
- **python_tools/retry_failed.py**: Uses ImageVerifier

### Removed
- Duplicated icon filtering logic (3 copies → 1 utility function)
- Complex nested verification loops (→ ImageVerifier class)

### Benefits
- ✅ Fix bugs once, works everywhere
- ✅ Easier to test (utilities are isolated)
- ✅ Easier to add features (clear responsibilities)
- ✅ Better maintainability for 1000+ page imports

## [2.6.0] - 2025-10-21

### 🎉 Major Update: SQLite Database & Auto-Retry

### Added
- **SQLite database** for tracking import history and failed images
  - Schema: `import_runs` and `failed_pages` tables with indexes
  - Tracks: retry counts, timestamps, verification status, errors
  - Scales to 1000+ pages and 500+ images
- **Auto-Retry Failed button** in GUI
  - Re-checks failed pages without re-importing
  - Updates retry counts and status automatically
  - Shows resolved vs still-failing pages
- **Query capabilities:**
  - Get pages that failed 3+ times
  - Get pending retries
  - Get import run history
- **Database location:** `out/import_history.db`
- **JSON export:** Still exports to `failed_images.json` for compatibility

### Changed
- Import tracking now uses SQLite instead of JSON-only
- Failed pages include verified_images count and last_error details
- Retry script: `python_tools/retry_failed.py`

### Developer Benefits
- Fast queries on large datasets (indexed)
- Track improvement over multiple import runs
- Identify persistent problem pages
- Retry logic with exponential backoff built-in

## [2.5.3] - 2025-10-21

### Fixed
- Filter out UI icons and avatars (JIRA icons, emoticons, bullets) from image import
- Apply icon filters to all image capture points: standalone, paragraphs, table cells
- Reduce false positive image counts from UI elements
- Images showing as "unverified" were actually icon URLs that shouldn't be imported

### Changed
- More comprehensive image filtering across all HTML contexts

## [2.5.2] - 2025-10-21

### Fixed
- **CRITICAL:** Increased tunnel keepalive from 30s to 180s (3 minutes)
- Images not loading because tunnel closed before Notion backend fetched them
- Notion queues image fetching asynchronously, needs longer tunnel lifetime
- Verification checks if fetched but doesn't keep tunnel alive long enough

### Changed
- Default IMAGE_TUNNEL_KEEPALIVE_SEC: 30s → 180s

## [2.5.1] - 2025-10-21

### Added
- GUI now displays pre-scan summary with pages, blocks, images, and estimated time
- Summary shown before import starts for better planning
- Visual summary cards in Electron interface

## [2.5.0] - 2025-10-16

### Added
- Pre-scan all HTML files before importing to show total statistics upfront
- Import summary shows: total pages, blocks, images, and estimated time
- Final summary shows success/failure counts for both pages and images

### Changed
- Parse HTML files only once (pre-scan) instead of during import loop
- More informative progress display with running totals

## [2.4.9] - 2025-10-16

### Added
- API rate limiting throttle: enforces ~3 requests/sec to prevent Notion rate limit errors
- Dynamic timeout scaling: 10s + 8s per image (max 180s) for large pages
- Initial 10s wait before verification to let Notion backend start processing

### Changed
- Increased poll interval from 3s to 5s to reduce API call frequency
- Better rate limit handling in verification loop

### Fixed
- Random image verification failures due to Notion API rate limiting
- Timeout too short for pages with many images (14+ images)
- Aggressive polling causing cached/stale responses from Notion API

## [2.4.8] - 2025-10-16

### Fixed
- False negatives in image verification: now checks both 'file' and 'external' type images
- Images marked as failed even when successfully cached (Notion keeps some as external type)
- Added s3.amazonaws.com to CDN domain detection

## [2.4.7] - 2025-10-16

### Added
- Per-page image verification: polls Notion API to confirm images are cached before moving to next page
- Image loading progress indicator with real-time count updates
- Failed images tracking: saves pages with incomplete images to `out/failed_images.json`
- Final import summary showing success/failure counts

### Changed
- Reduced default tunnel keepalive from 120s to 30s (images now verified per-page)
- Enhanced logging: shows image count per page during import
- Improved error handling with detailed warnings for timeout cases

### Fixed
- Images missing in imported pages due to insufficient wait time
- No feedback when images fail to load from tunnel

## [2.4.6] - 2025-10-16

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
