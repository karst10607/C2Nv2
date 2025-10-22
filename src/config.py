import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any

from .models import ImportConfig, BaseConfig, StrategyConfig

CONFIG_PATH = Path.home() / ".notion_importer" / "config.json"

@dataclass
class AppConfig:
    """Legacy configuration class for backwards compatibility"""
    notion_token: Optional[str] = None
    parent_id: Optional[str] = None
    source_dir: str = ""
    
    # This will hold all other attributes loaded from JSON
    _extra_attrs: Dict[str, Any] = None

    def __post_init__(self):
        if self._extra_attrs is None:
            self._extra_attrs = {}

    def __getattr__(self, name: str) -> Any:
        """Get dynamic attributes loaded from config"""
        if name in self._extra_attrs:
            return self._extra_attrs[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """Set dynamic attributes"""
        if name in ['notion_token', 'parent_id', 'source_dir', '_extra_attrs']:
            super().__setattr__(name, value)
        else:
            if self._extra_attrs is None:
                self._extra_attrs = {}
            self._extra_attrs[name] = value

    @staticmethod
    def load(env: bool = True) -> "AppConfig":
        """Load configuration from JSON file and environment variables"""
        cfg = AppConfig()
        
        # Load from JSON config
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                
                # Load base fields (supporting both naming conventions)
                cfg.notion_token = data.get("NOTION_TOKEN") or data.get("notion_token")
                cfg.parent_id = data.get("PARENT_ID") or data.get("parent_id")
                cfg.source_dir = data.get("SOURCE_DIR") or data.get("source_dir") or ""
                
                # Store all config data for strategy configuration
                for key, value in data.items():
                    if key.lower() not in ['notion_token', 'parent_id', 'source_dir']:
                        # Store in _extra_attrs for dynamic access
                        setattr(cfg, key.lower(), value)
                        
            except Exception:
                pass
        
        # Override with environment variables if enabled
        if env:
            cfg.notion_token = os.getenv("NOTION_TOKEN", cfg.notion_token)
            cfg.parent_id = os.getenv("PARENT_ID", cfg.parent_id)
            cfg.source_dir = os.getenv("SOURCE_DIR", cfg.source_dir)
        
        return cfg

    def save(self) -> None:
        """Save configuration to JSON file"""
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Build data dictionary
        data = {
            "NOTION_TOKEN": self.notion_token or "",
            "PARENT_ID": self.parent_id or "",
            "SOURCE_DIR": self.source_dir,
        }
        
        # Add any extra attributes
        if self._extra_attrs:
            data.update(self._extra_attrs)
        
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    def to_import_config(self) -> ImportConfig:
        """Convert to new ImportConfig model"""
        return ImportConfig.from_app_config(self)
