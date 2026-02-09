"""
Constants for Notion Importer
All magic numbers and configuration limits in one place
"""

# Notion API Limits
NOTION_TEXT_LIMIT = 2000  # Maximum characters per rich text item
NOTION_BLOCK_CHUNK_SIZE = 80  # Maximum blocks per API call
NOTION_API_BLOCK_LIMIT = 1000  # Notion API hard limit per request
NOTION_API_RATE_LIMIT = 0.35  # Minimum seconds between API calls (~3 requests/sec)
NOTION_TABLE_ROW_LIMIT = 100  # Maximum rows per table block

# Image Verification
DEFAULT_VERIFICATION_TIMEOUT = 60  # Default timeout for image verification (seconds)
VERIFICATION_POLL_INTERVAL = 5  # Seconds between verification polls
INITIAL_IMAGE_WAIT = 10  # Initial wait before checking images (seconds)
MIN_IMAGE_TIMEOUT = 30  # Minimum timeout for image verification
MAX_IMAGE_TIMEOUT = 180  # Maximum timeout for image verification
IMAGE_TIMEOUT_BASE = 10  # Base timeout for images
IMAGE_TIMEOUT_PER_IMAGE = 8  # Additional seconds per image

# Upload Strategies
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

# Time Formatting
SECONDS_PER_MINUTE = 60  # Seconds in a minute for time display
