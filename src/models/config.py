"""
Configuration models for Notion Importer
Provides type-safe configuration with validation
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path

from ..constants import (
    DEFAULT_TUNNEL_KEEPALIVE,
    S3_DEFAULT_LIFECYCLE_DAYS,
    MAX_COLUMNS_PER_ROW,
    MIN_COLUMN_HEIGHT
)
from .errors import ConfigurationError, ErrorCode


class UploadMode(Enum):
    """Available upload strategies"""
    TUNNEL = "tunnel"
    S3_TEMP = "s3_temp"
    S3_PERMANENT = "s3_permanent"
    CLOUDFLARE = "cloudflare"
    NOTION_NATIVE = "notion_native"
    
    @classmethod
    def from_string(cls, value: str) -> 'UploadMode':
        """Convert string to UploadMode, with fallback to TUNNEL"""
        try:
            # Handle s3 as alias for s3_temp
            if value == "s3":
                return cls.S3_TEMP
            return cls(value.lower())
        except (ValueError, AttributeError):
            return cls.TUNNEL


@dataclass
class BaseConfig:
    """Base configuration for Notion Importer"""
    notion_token: Optional[str] = None
    parent_id: Optional[str] = None
    source_dir: str = ""
    
    # Import settings
    max_columns: int = MAX_COLUMNS_PER_ROW
    min_column_height: int = MIN_COLUMN_HEIGHT
    preserve_table_layout: bool = True
    
    def validate(self) -> None:
        """Validate base configuration"""
        if not self.source_dir:
            raise ConfigurationError(
                ErrorCode.CONFIG_MISSING_SOURCE,
                "Source directory not configured",
                "Use --source-dir or configure in settings"
            )
        
        source_path = Path(self.source_dir)
        if not source_path.exists():
            raise ConfigurationError(
                ErrorCode.CONFIG_INVALID_SOURCE,
                "Source directory does not exist",
                str(self.source_dir)
            )
        
        if not source_path.is_dir():
            raise ConfigurationError(
                ErrorCode.CONFIG_SOURCE_NOT_DIR,
                "Source path is not a directory",
                str(self.source_dir)
            )


@dataclass
class TunnelConfig:
    """Configuration for tunnel upload strategy"""
    keepalive_sec: int = DEFAULT_TUNNEL_KEEPALIVE
    
    def validate(self) -> None:
        """Validate tunnel configuration"""
        if self.keepalive_sec < 60:
            raise ConfigurationError(
                ErrorCode.CONFIG_INVALID_TUNNEL,
                "Tunnel keepalive must be at least 60 seconds",
                f"Current value: {self.keepalive_sec}s"
            )
        if self.keepalive_sec > 3600:
            raise ConfigurationError(
                ErrorCode.CONFIG_INVALID_TUNNEL,
                "Tunnel keepalive cannot exceed 1 hour (3600 seconds)",
                f"Current value: {self.keepalive_sec}s"
            )


@dataclass
class S3Config:
    """Configuration for S3 upload strategies"""
    bucket: str = ""
    region: str = "us-west-2"
    access_key: str = ""
    secret_key: str = ""
    lifecycle_days: int = S3_DEFAULT_LIFECYCLE_DAYS
    use_presigned: bool = True
    
    def validate(self) -> None:
        """Validate S3 configuration"""
        missing = []
        if not self.bucket:
            missing.append("bucket")
        if not self.access_key:
            missing.append("access_key")
        if not self.secret_key:
            missing.append("secret_key")
        if not self.region:
            missing.append("region")
        
        if missing:
            raise ConfigurationError(
                ErrorCode.CONFIG_MISSING_S3,
                "S3 configuration incomplete",
                f"Missing fields: {', '.join(missing)}"
            )
        
        if self.lifecycle_days < 1:
            raise ConfigurationError(
                ErrorCode.CONFIG_INVALID_LIFECYCLE,
                "S3 lifecycle days must be at least 1",
                f"Current value: {self.lifecycle_days}"
            )


@dataclass
class CloudflareConfig:
    """Configuration for Cloudflare R2 upload strategy"""
    bucket: str = ""
    account_id: str = ""
    access_key: str = ""
    secret_key: str = ""
    public_domain: str = ""
    
    def validate(self) -> None:
        """Validate Cloudflare configuration"""
        missing = []
        if not self.bucket:
            missing.append("bucket")
        if not self.account_id:
            missing.append("account_id")
        if not self.access_key:
            missing.append("access_key")
        if not self.secret_key:
            missing.append("secret_key")
        if not self.public_domain:
            missing.append("public_domain")
        
        if missing:
            raise ConfigurationError(
                ErrorCode.CONFIG_MISSING_CF,
                "Cloudflare configuration incomplete",
                f"Missing fields: {', '.join(missing)}"
            )


@dataclass
class StrategyConfig:
    """Combined configuration for upload strategies"""
    upload_mode: UploadMode = UploadMode.TUNNEL
    tunnel: TunnelConfig = field(default_factory=TunnelConfig)
    s3: S3Config = field(default_factory=S3Config)
    cloudflare: CloudflareConfig = field(default_factory=CloudflareConfig)
    
    def validate(self) -> None:
        """Validate strategy configuration based on upload mode"""
        if self.upload_mode == UploadMode.TUNNEL:
            self.tunnel.validate()
        elif self.upload_mode in (UploadMode.S3_TEMP, UploadMode.S3_PERMANENT, UploadMode.NOTION_NATIVE):
            self.s3.validate()
        elif self.upload_mode == UploadMode.CLOUDFLARE:
            self.cloudflare.validate()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """Create StrategyConfig from dictionary (e.g., from JSON)"""
        config = cls()
        
        # Parse upload mode
        if 'upload_mode' in data:
            config.upload_mode = UploadMode.from_string(data['upload_mode'])
        
        # Parse tunnel config
        if 'tunnel_keepalive_sec' in data:
            config.tunnel.keepalive_sec = int(data['tunnel_keepalive_sec'])
        
        # Parse S3 config
        s3_fields = ['s3_bucket', 's3_region', 's3_access_key', 's3_secret_key', 
                     's3_lifecycle_days', 's3_use_presigned']
        for field in s3_fields:
            if field in data:
                attr_name = field.replace('s3_', '')
                setattr(config.s3, attr_name, data[field])
        
        # Parse Cloudflare config
        cf_fields = ['cf_bucket', 'cf_account_id', 'cf_access_key', 
                     'cf_secret_key', 'cf_public_domain']
        for field in cf_fields:
            if field in data:
                attr_name = field.replace('cf_', '')
                setattr(config.cloudflare, attr_name, data[field])
        
        return config


@dataclass
class ImportConfig:
    """Complete configuration for import process"""
    base: BaseConfig = field(default_factory=BaseConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    
    def validate(self, require_notion: bool = True) -> None:
        """
        Validate complete configuration
        
        Args:
            require_notion: Whether Notion credentials are required (False for dry-run)
        """
        self.base.validate()
        
        if require_notion:
            if not self.base.notion_token:
                raise ConfigurationError(
                    ErrorCode.CONFIG_MISSING_TOKEN,
                    "Notion token is required",
                    "Set via GUI, config file, or NOTION_TOKEN environment variable"
                )
            if not self.base.parent_id:
                raise ConfigurationError(
                    ErrorCode.CONFIG_MISSING_PARENT,
                    "Parent ID is required",
                    "Set via GUI, config file, --parent-id flag, or PARENT_ID environment variable"
                )
        
        self.strategy.validate()
    
    @classmethod
    def from_app_config(cls, app_config: Any) -> 'ImportConfig':
        """Create ImportConfig from legacy AppConfig"""
        import_config = cls()
        
        # Base config
        import_config.base.notion_token = app_config.notion_token
        import_config.base.parent_id = app_config.parent_id
        import_config.base.source_dir = app_config.source_dir
        
        # Strategy config from dynamic attributes
        strategy_dict = {}
        for attr in dir(app_config):
            if not attr.startswith('_'):
                value = getattr(app_config, attr)
                if attr in ['upload_mode', 'tunnel_keepalive_sec'] or \
                   attr.startswith('s3_') or attr.startswith('cf_'):
                    strategy_dict[attr] = value
        
        import_config.strategy = StrategyConfig.from_dict(strategy_dict)
        
        return import_config
