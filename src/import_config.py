"""
Configuration object pattern for import settings.
Replaces passing 7+ parameters to functions.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ImportConfig:
    """Configuration for HTML to Notion import process"""
    
    # Source and destination
    source_dir: Path
    parent_id: str
    notion_token: str
    
    # Image serving
    image_base_url: str = ""
    
    # Table transformation
    max_columns: int = 6
    preserve_table_layout: bool = True
    min_column_height: int = 3
    
    # Verification settings
    verify_images: bool = True
    verification_timeout_base: int = 10  # seconds
    verification_timeout_per_image: int = 8  # seconds per image
    verification_timeout_max: int = 180  # maximum timeout
    initial_wait_before_verify: int = 10  # seconds to let Notion start
    verification_poll_interval: int = 5  # seconds between polls
    
    # Tunnel settings
    tunnel_keepalive_sec: int = 180
    
    # Database and output
    enable_database: bool = True
    enable_json_export: bool = True
    output_dir: Optional[Path] = None
    
    def __post_init__(self):
        """Validate and normalize paths"""
        if isinstance(self.source_dir, str):
            self.source_dir = Path(self.source_dir)
        
        if self.output_dir is None:
            # Default to project_root/out
            from pathlib import Path
            self.output_dir = Path(__file__).resolve().parents[1] / 'out'
        
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
    
    def get_verification_timeout(self, image_count: int) -> int:
        """Calculate timeout based on image count"""
        timeout = self.verification_timeout_base + (image_count * self.verification_timeout_per_image)
        return max(30, min(self.verification_timeout_max, timeout))
    
    @classmethod
    def from_args_and_config(cls, args, app_config):
        """Create ImportConfig from CLI args and AppConfig"""
        source_dir = args.source_dir or app_config.source_dir
        parent_id = args.parent_id or app_config.parent_id or ""
        
        return cls(
            source_dir=Path(source_dir) if source_dir else Path.cwd(),
            parent_id=parent_id,
            notion_token=app_config.notion_token or "",
            max_columns=args.max_columns if hasattr(args, 'max_columns') else 6,
        )

