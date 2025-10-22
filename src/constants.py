"""
Constants for Notion Importer
All magic numbers and configuration limits in one place
"""

# Notion API Limits
NOTION_TEXT_LIMIT = 2000  # Maximum characters per rich text item
NOTION_BLOCK_CHUNK_SIZE = 80  # Maximum blocks per API call
NOTION_API_RATE_LIMIT = 0.35  # Minimum seconds between API calls (~3 requests/sec)

# Image Verification
DEFAULT_VERIFICATION_TIMEOUT = 60  # Default timeout for image verification (seconds)
VERIFICATION_POLL_INTERVAL = 5  # Seconds between verification polls
INITIAL_IMAGE_WAIT = 10  # Initial wait before checking images (seconds)
MIN_IMAGE_TIMEOUT = 30  # Minimum timeout for image verification
MAX_IMAGE_TIMEOUT = 180  # Maximum timeout for image verification
IMAGE_TIMEOUT_BASE = 10  # Base timeout for images
IMAGE_TIMEOUT_PER_IMAGE = 8  # Additional seconds per image

# Upload Strategies
DEFAULT_TUNNEL_KEEPALIVE = 600  # Default tunnel keepalive time (10 minutes)
TUNNEL_KEEPALIVE_PER_FAILED_PAGE = 30  # Extra keepalive seconds per failed page
S3_PRESIGNED_URL_EXPIRY = 3600  # S3 presigned URL expiry time (1 hour)
S3_DEFAULT_LIFECYCLE_DAYS = 1  # Default S3 lifecycle for temp files

# Retry Logic
MAX_RETRY_COUNT = 3  # Maximum retry attempts for failed operations
RETRY_BASE_DELAY = 0.8  # Base delay for exponential backoff
API_RETRY_COUNT = 5  # Number of retries for API calls

# Time Estimates
SECONDS_PER_PAGE_ESTIMATE = 15  # Estimated seconds per page import
SECONDS_PER_IMAGE_ESTIMATE = 8  # Estimated seconds per image

# Display Limits
MAX_FAILED_PAGES_DISPLAY = 10  # Maximum failed pages to show in summary

# Database Limits
DEFAULT_RECENT_RUNS_LIMIT = 10  # Default limit for recent import runs query

# HTML Parsing
MAX_COLUMNS_PER_ROW = 6  # Maximum columns per row in tables
MIN_COLUMN_HEIGHT = 3  # Minimum blocks per column for table layout

# Tunnel Connection
TUNNEL_STARTUP_TIMEOUT = 10  # Timeout for tunnel startup (seconds)
TUNNEL_DNS_TIMEOUT = 15  # Timeout for tunnel DNS resolution (seconds)
NGROK_API_TIMEOUT = 1  # Timeout for ngrok API calls (seconds)
NGROK_POLL_INTERVAL = 0.5  # Polling interval for ngrok URL (seconds)
CLOUDFLARED_POLL_INTERVAL = 0.2  # Polling interval for cloudflared output (seconds)
DNS_RESOLVE_INTERVAL = 1  # Interval between DNS resolution attempts (seconds)
HTTP_CHECK_TIMEOUT = 3  # Timeout for HTTP accessibility check (seconds)
HTTP_CHECK_INTERVAL = 1  # Interval between HTTP checks (seconds)

# GUI Configuration
GUI_ENTRY_WIDTH = 60  # Width of entry fields in GUI

# Time Formatting
SECONDS_PER_MINUTE = 60  # Seconds in a minute for time display
