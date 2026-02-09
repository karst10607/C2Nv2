"""
Configuration models for Notion Importer
Provides type-safe configuration with validation
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path

from ..constants import (
    S3_DEFAULT_LIFECYCLE_DAYS,
    MAX_COLUMNS_PER_ROW,
    MIN_COLUMN_HEIGHT
)
from .errors import ConfigurationError, ErrorCode


class UploadMode(Enum):
    """Available upload strategies"""
    S3_TEMP = "s3_temp"
    S3_PERMANENT = "s3_permanent"
    GCS = "gcs"
    NOTION_NATIVE = "notion_native"
    
    @classmethod
    def from_string(cls, value: str) -> 'UploadMode':
        """Convert string to UploadMode, with fallback to S3_TEMP"""
        try:
            # Handle s3 as alias for s3_temp
            if value == "s3":
                return cls.S3_TEMP
            return cls(value.lower())
        except (ValueError, AttributeError):
            return cls.S3_TEMP


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
    
    # Smart table rendering options
    smart_table_rendering: bool = True
    table_image_threshold: int = 2  # Max images before switching to columns
    prefer_native_tables: bool = True
    icon_size_threshold: int = 32  # Pixels, to identify emoji-like images
    
    # Media handling options
    skip_missing_media: bool = True  # Continue import even if media files are missing
    fail_on_missing_media_threshold: int = 50  # Fail if more than this many media files are missing
    skip_verification: bool = False  # Skip image verification after upload
    
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
class GCSConfig:
    """Configuration for Google Cloud Storage upload strategy"""
    bucket: str = ""
    project_id: str = ""
    credentials_path: str = ""  # Path to service account JSON file (for local signing)
    lifecycle_days: int = 1
    # Impersonation mode - uses ADC + service account impersonation instead of local JSON
    use_impersonation: bool = False
    impersonate_service_account: str = ""  # SA email to impersonate (e.g., "sa@project.iam.gserviceaccount.com")
    
    def validate(self) -> None:
        """Validate GCS configuration"""
        missing = []
        if not self.bucket:
            missing.append("bucket")
        if not self.project_id:
            missing.append("project_id")
        
        # Validate based on mode
        if self.use_impersonation:
            # Impersonation mode: need service account email
            if not self.impersonate_service_account:
                missing.append("impersonate_service_account (SA email to impersonate)")
        else:
            # Local signing mode: need credentials file
            if not self.credentials_path:
                missing.append("credentials_path (service account JSON)")
        
        if missing:
            raise ConfigurationError(
                ErrorCode.CONFIG_MISSING_GCS,
                "GCS configuration incomplete",
                f"Missing fields: {', '.join(missing)}"
            )
        
        # Check if credentials file exists (only for local signing mode)
        from pathlib import Path
        if not self.use_impersonation and self.credentials_path and not Path(self.credentials_path).exists():
            raise ConfigurationError(
                ErrorCode.CONFIG_INVALID_GCS,
                "GCS credentials file not found",
                f"Path: {self.credentials_path}"
            )


@dataclass
class StrategyConfig:
    """Combined configuration for upload strategies"""
    upload_mode: UploadMode = UploadMode.S3_TEMP
    s3: S3Config = field(default_factory=S3Config)
    gcs: GCSConfig = field(default_factory=GCSConfig)
    notion_token: str = ""  # For NOTION_NATIVE mode
    
    def validate(self) -> None:
        """Validate strategy configuration based on upload mode"""
        if self.upload_mode in (UploadMode.S3_TEMP, UploadMode.S3_PERMANENT):
            self.s3.validate()
        elif self.upload_mode == UploadMode.GCS:
            self.gcs.validate()
        elif self.upload_mode == UploadMode.NOTION_NATIVE:
            if not self.notion_token:
                raise ConfigurationError(
                    ErrorCode.CONFIG_MISSING_TOKEN,
                    "Notion token is required for native upload",
                    "Set via GUI or NOTION_TOKEN environment variable"
                )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """Create StrategyConfig from dictionary (e.g., from JSON)"""
        config = cls()
        
        # Parse upload mode
        if 'upload_mode' in data:
            config.upload_mode = UploadMode.from_string(data['upload_mode'])
        
        # Parse S3 config
        s3_fields = ['s3_bucket', 's3_region', 's3_access_key', 's3_secret_key', 
                     's3_lifecycle_days', 's3_use_presigned']
        for field in s3_fields:
            if field in data:
                attr_name = field.replace('s3_', '')
                setattr(config.s3, attr_name, data[field])
        
        # Parse GCS config
        gcs_fields = ['gcs_bucket', 'gcs_project_id', 'gcs_credentials_path', 
                      'gcs_lifecycle_days', 'gcs_use_impersonation', 
                      'gcs_impersonate_service_account']
        for field in gcs_fields:
            if field in data:
                attr_name = field.replace('gcs_', '')
                setattr(config.gcs, attr_name, data[field])
        
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
        from .errors import ConfigurationError, ErrorCode
        
        try:
            import_config = cls()
            
            # Base config
            import_config.base.notion_token = app_config.notion_token
            import_config.base.parent_id = app_config.parent_id
            import_config.base.source_dir = app_config.source_dir
            
            # Check for skip_verification in _extra_attrs
            if hasattr(app_config, '_extra_attrs') and app_config._extra_attrs:
                if 'skip_verification' in app_config._extra_attrs:
                    import_config.base.skip_verification = bool(app_config._extra_attrs['skip_verification'])
                elif 'SKIP_VERIFICATION' in app_config._extra_attrs:
                    import_config.base.skip_verification = bool(app_config._extra_attrs['SKIP_VERIFICATION'])
            
            # Strategy config from dynamic attributes
            strategy_dict = {}
            
            # First check standard attributes
            for attr in dir(app_config):
                if not attr.startswith('_'):
                    try:
                        value = getattr(app_config, attr)
                        if attr == 'upload_mode' or \
                           attr.startswith('s3_') or attr.startswith('gcs_'):
                            strategy_dict[attr] = value
                    except AttributeError:
                        pass
            
            # IMPORTANT: Also check _extra_attrs where dynamic config values are stored
            if hasattr(app_config, '_extra_attrs') and app_config._extra_attrs:
                for key, value in app_config._extra_attrs.items():
                    if key == 'upload_mode' or \
                       key.startswith('s3_') or key.startswith('gcs_'):
                        strategy_dict[key] = value
            
            import_config.strategy = StrategyConfig.from_dict(strategy_dict)
            
            # For NOTION_NATIVE mode, pass the notion_token to strategy
            if import_config.strategy.upload_mode == UploadMode.NOTION_NATIVE:
                import_config.strategy.notion_token = import_config.base.notion_token
            
            return import_config
        except Exception as e:
            raise ConfigurationError(
                ErrorCode.CONFIG_PARSE_ERROR,
                f"Failed to parse configuration: {str(e)}",
                "Check your config file for missing or invalid values"
            )
