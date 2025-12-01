"""
Error codes and exceptions for Notion Importer
Provides centralized error handling with clear codes and messages
"""
from enum import Enum
from typing import Optional


class ErrorCode(Enum):
    """Central error codes for consistent error handling"""
    
    # Configuration Errors (1xxx)
    CONFIG_MISSING_SOURCE = "E1001"
    CONFIG_INVALID_SOURCE = "E1002"
    CONFIG_SOURCE_NOT_DIR = "E1003"
    CONFIG_MISSING_TOKEN = "E1004"
    CONFIG_MISSING_PARENT = "E1005"
    CONFIG_INVALID_TUNNEL = "E1006"
    CONFIG_MISSING_S3 = "E1007"
    CONFIG_MISSING_CF = "E1008"
    CONFIG_INVALID_LIFECYCLE = "E1009"
    CONFIG_PARSE_ERROR = "E1010"
    CONFIG_S3_REGION_MISMATCH = "E1011"
    CONFIG_S3_PUBLIC_ACCESS = "E1012"
    
    # Upload Errors (2xxx)
    UPLOAD_IMAGE_FAILED = "E2001"
    UPLOAD_STRATEGY_FAILED = "E2002"
    UPLOAD_FALLBACK_FAILED = "E2003"
    UPLOAD_INVALID_PATH = "E2004"
    
    # Tunnel Errors (3xxx)
    TUNNEL_NOT_FOUND = "E3001"
    TUNNEL_START_FAILED = "E3002"
    TUNNEL_CONNECTION_FAILED = "E3003"
    
    # Notion API Errors (4xxx)
    NOTION_API_ERROR = "E4001"
    NOTION_RATE_LIMIT = "E4002"
    NOTION_AUTH_FAILED = "E4003"
    NOTION_PAGE_NOT_FOUND = "E4004"
    NOTION_TABLE_ROW_LIMIT = "E4005"
    NOTION_BLOCK_LIMIT = "E4006"
    NOTION_INVALID_IMAGE_URL = "E4007"
    NOTION_INVALID_LINK_URL = "E4008"
    NOTION_INVALID_FILE_URL = "E4009"
    
    # Verification Errors (5xxx)
    VERIFY_TIMEOUT = "E5001"
    VERIFY_API_ERROR = "E5002"
    VERIFY_INCOMPLETE = "E5003"
    
    # Import Process Errors (6xxx)
    IMPORT_PAGE_FAILED = "E6001"
    IMPORT_CANCELLED = "E6002"
    
    # Conversion Errors (7xxx)
    CONVERSION_ERROR = "E7001"
    
    # Parsing Errors (8xxx)
    PARSE_NESTED_LIST = "E8001"
    PARSE_DEEP_NESTED_LIST = "E8002"
    
    # Warning Codes (9xxx) - Not errors but important notifications
    WARN_TABLE_CELL_TRUNCATED = "W9001"
    WARN_ATTACHMENT_NOT_SUPPORTED = "W9002"
    WARN_ATTACHMENT_SKIPPED = "W9003"
    WARN_MISSING_MEDIA_SKIPPED = "W9004"
    WARN_PLACEHOLDER_IMAGE_SKIPPED = "W9005"
    WARN_TEMP_FILE_SKIPPED = "W9006"
    WARN_FILE_URL_INVALID = "W9007"
    WARN_RELATIVE_HTML_LINK_SKIPPED = "W9008"
    WARN_ANCHOR_LINK_SKIPPED = "W9009"
    WARN_METADATA_DATE_INCOMPLETE = "W9010"  # Date missing year or malformed
    WARN_METADATA_AUTHOR_INCOMPLETE = "W9011"  # Author name extraction incomplete
    WARN_METADATA_EXTRACTION_FAILED = "W9012"  # Failed to extract page metadata
    WARN_EMBEDDED_WRAPPER_SKIPPED = "W9013"  # Content wrapped in confluence-embedded-file-wrapper not processed
    WARN_UNRECOGNIZED_BLOCK_SKIPPED = "W9014"  # HTML block element not recognized and skipped
    WARN_CONTENT_WRAPPER_SKIPPED = "W9015"  # Content wrapper element skipped causing content loss
    WARN_EMOTICON_NO_FALLBACK = "W9016"  # Emoticon image found but no emoji fallback available
    WARN_EMOTICON_CONVERSION_FAILED = "W9017"  # Failed to convert emoticon image to emoji character
    WARN_EMOTICON_FALLBACK_INVALID = "W9018"  # Emoticon emoji fallback is empty or invalid
    WARN_TABLE_ROW_CELL_LIMIT = "W9019"  # Table row exceeds Notion's 100 cell limit - truncated


class NotionImporterError(Exception):
    """Base exception for Notion Importer with error code support"""
    
    def __init__(self, code: ErrorCode, message: str, details: Optional[str] = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(self._format_error())
    
    def _format_error(self) -> str:
        """Format error message with code"""
        base = f"[{self.code.value}] {self.message}"
        if self.details:
            base += f" - {self.details}"
        return base


class ConfigurationError(NotionImporterError):
    """Configuration-related errors"""
    pass


class UploadError(NotionImporterError):
    """Upload strategy errors"""
    pass


class TunnelError(NotionImporterError):
    """Tunnel-related errors"""
    pass


class NotionAPIError(NotionImporterError):
    """Notion API errors"""
    pass


class VerificationError(NotionImporterError):
    """Image verification errors"""
    pass


class ImportProcessError(NotionImporterError):
    """Import process errors"""
    pass


# Error message templates
ERROR_MESSAGES = {
    ErrorCode.CONFIG_MISSING_SOURCE: "Source directory not configured",
    ErrorCode.CONFIG_INVALID_SOURCE: "Source directory does not exist",
    ErrorCode.CONFIG_SOURCE_NOT_DIR: "Source path is not a directory",
    ErrorCode.CONFIG_MISSING_TOKEN: "Notion token is required",
    ErrorCode.CONFIG_MISSING_PARENT: "Parent ID is required",
    ErrorCode.CONFIG_INVALID_TUNNEL: "Invalid tunnel keepalive duration",
    ErrorCode.CONFIG_MISSING_S3: "S3 configuration incomplete",
    ErrorCode.CONFIG_MISSING_CF: "Cloudflare configuration incomplete",
    ErrorCode.CONFIG_INVALID_LIFECYCLE: "Invalid S3 lifecycle days",
    ErrorCode.CONFIG_S3_PUBLIC_ACCESS: "S3 bucket requires public read access for notion-temp/* prefix",
    
    ErrorCode.UPLOAD_IMAGE_FAILED: "Failed to upload image",
    ErrorCode.UPLOAD_STRATEGY_FAILED: "Upload strategy initialization failed",
    ErrorCode.UPLOAD_FALLBACK_FAILED: "Fallback strategy also failed",
    ErrorCode.UPLOAD_INVALID_PATH: "Invalid image path - relative URLs with leading slash",
    
    ErrorCode.TUNNEL_NOT_FOUND: "No tunnel tool found (cloudflared or ngrok)",
    ErrorCode.TUNNEL_START_FAILED: "Failed to start tunnel",
    ErrorCode.TUNNEL_CONNECTION_FAILED: "Tunnel connection failed",
    
    ErrorCode.NOTION_API_ERROR: "Notion API error",
    ErrorCode.NOTION_RATE_LIMIT: "Notion API rate limit exceeded",
    ErrorCode.NOTION_AUTH_FAILED: "Notion authentication failed",
    ErrorCode.NOTION_PAGE_NOT_FOUND: "Parent page not found. Verify the page exists and is shared with your integration",
    ErrorCode.NOTION_TABLE_ROW_LIMIT: "Table row exceeds Notion's 100 cell limit - table row truncated",
    ErrorCode.NOTION_INVALID_IMAGE_URL: "Invalid image URL. Draw.io XML files (.drawio) cannot be used as images",
    ErrorCode.NOTION_INVALID_LINK_URL: "Invalid URL for link. Relative HTML links are not supported by Notion - links must be absolute URLs (http/https) or mailto",
    ErrorCode.NOTION_INVALID_FILE_URL: "Invalid file URL. File attachments require absolute URLs - use S3/CDN upload strategy for file imports",
    
    ErrorCode.VERIFY_TIMEOUT: "Image verification timeout",
    ErrorCode.VERIFY_API_ERROR: "Error during verification",
    ErrorCode.VERIFY_INCOMPLETE: "Not all images verified",
    
    ErrorCode.IMPORT_PAGE_FAILED: "Failed to import page",
    ErrorCode.IMPORT_CANCELLED: "Import cancelled by user",
    
    ErrorCode.CONVERSION_ERROR: "Media conversion failed",
    
    ErrorCode.PARSE_NESTED_LIST: "Complex list structure flattened - nested paragraphs combined",
    ErrorCode.PARSE_DEEP_NESTED_LIST: "Deeply nested lists flattened - Notion only supports 2-3 levels of nesting",
    
    ErrorCode.WARN_TABLE_CELL_TRUNCATED: "Table cell content truncated to fit Notion's 2000 character limit",
    ErrorCode.WARN_ATTACHMENT_NOT_SUPPORTED: "Attachment type not supported for Notion import",
    ErrorCode.WARN_ATTACHMENT_SKIPPED: "Document attachment found but not imported - upload manually to Notion",
    ErrorCode.WARN_MISSING_MEDIA_SKIPPED: "Missing media files skipped - continuing import",
    ErrorCode.WARN_PLACEHOLDER_IMAGE_SKIPPED: "Placeholder/unknown attachment image skipped",
    ErrorCode.WARN_TEMP_FILE_SKIPPED: "Temporary file (.tmp) skipped - not required for import",
    ErrorCode.WARN_FILE_URL_INVALID: "File attachment cannot be imported without valid URL - use S3/CDN upload strategy for file attachments",
    ErrorCode.WARN_RELATIVE_HTML_LINK_SKIPPED: "Relative HTML link converted to plain text - Notion only supports absolute URLs",
    ErrorCode.WARN_ANCHOR_LINK_SKIPPED: "Internal anchor/bookmark link converted to plain text - Notion doesn't support in-page navigation links",
    ErrorCode.WARN_METADATA_DATE_INCOMPLETE: "Page metadata date missing year or malformed - date may not display correctly",
    ErrorCode.WARN_METADATA_AUTHOR_INCOMPLETE: "Page metadata author extraction incomplete - author name may be missing or truncated",
    ErrorCode.WARN_METADATA_EXTRACTION_FAILED: "Failed to extract page metadata (author/date) - metadata callout may be incomplete",
    ErrorCode.WARN_EMBEDDED_WRAPPER_SKIPPED: "Content wrapped in confluence-embedded-file-wrapper span was not processed - images/videos may be missing from page",
    ErrorCode.WARN_UNRECOGNIZED_BLOCK_SKIPPED: "HTML block element not recognized by parser - content may be missing from imported page",
    ErrorCode.WARN_CONTENT_WRAPPER_SKIPPED: "Content wrapper element skipped during parsing - this may cause content loss in imported pages",
    ErrorCode.WARN_EMOTICON_NO_FALLBACK: "Emoticon image found but no emoji fallback (data-emoji-fallback or alt) available - emoticon may be skipped",
    ErrorCode.WARN_EMOTICON_CONVERSION_FAILED: "Failed to convert emoticon image to emoji character - emoticon may appear as missing or broken",
    ErrorCode.WARN_EMOTICON_FALLBACK_INVALID: "Emoticon emoji fallback is empty or invalid - emoticon may not display correctly",
    ErrorCode.WARN_TABLE_ROW_CELL_LIMIT: "Table row exceeds Notion's 100 cell limit - row truncated to first 100 cells",
}


def get_error_message(code: ErrorCode, details: Optional[str] = None) -> str:
    """Get formatted error message for a code"""
    message = ERROR_MESSAGES.get(code, "Unknown error")
    if details:
        return f"{message}: {details}"
    return message
