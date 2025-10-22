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
    
    # Upload Errors (2xxx)
    UPLOAD_IMAGE_FAILED = "E2001"
    UPLOAD_STRATEGY_FAILED = "E2002"
    UPLOAD_FALLBACK_FAILED = "E2003"
    
    # Tunnel Errors (3xxx)
    TUNNEL_NOT_FOUND = "E3001"
    TUNNEL_START_FAILED = "E3002"
    TUNNEL_CONNECTION_FAILED = "E3003"
    
    # Notion API Errors (4xxx)
    NOTION_API_ERROR = "E4001"
    NOTION_RATE_LIMIT = "E4002"
    NOTION_AUTH_FAILED = "E4003"
    
    # Verification Errors (5xxx)
    VERIFY_TIMEOUT = "E5001"
    VERIFY_API_ERROR = "E5002"
    VERIFY_INCOMPLETE = "E5003"
    
    # Import Process Errors (6xxx)
    IMPORT_PAGE_FAILED = "E6001"
    IMPORT_CANCELLED = "E6002"


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
    
    ErrorCode.UPLOAD_IMAGE_FAILED: "Failed to upload image",
    ErrorCode.UPLOAD_STRATEGY_FAILED: "Upload strategy initialization failed",
    ErrorCode.UPLOAD_FALLBACK_FAILED: "Fallback strategy also failed",
    
    ErrorCode.TUNNEL_NOT_FOUND: "No tunnel tool found (cloudflared or ngrok)",
    ErrorCode.TUNNEL_START_FAILED: "Failed to start tunnel",
    ErrorCode.TUNNEL_CONNECTION_FAILED: "Tunnel connection failed",
    
    ErrorCode.NOTION_API_ERROR: "Notion API error",
    ErrorCode.NOTION_RATE_LIMIT: "Notion API rate limit exceeded",
    ErrorCode.NOTION_AUTH_FAILED: "Notion authentication failed",
    
    ErrorCode.VERIFY_TIMEOUT: "Image verification timeout",
    ErrorCode.VERIFY_API_ERROR: "Error during verification",
    ErrorCode.VERIFY_INCOMPLETE: "Not all images verified",
    
    ErrorCode.IMPORT_PAGE_FAILED: "Failed to import page",
    ErrorCode.IMPORT_CANCELLED: "Import cancelled by user",
}


def get_error_message(code: ErrorCode, details: Optional[str] = None) -> str:
    """Get formatted error message for a code"""
    message = ERROR_MESSAGES.get(code, "Unknown error")
    if details:
        return f"{message}: {details}"
    return message
