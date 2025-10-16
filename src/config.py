import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

CONFIG_PATH = Path.home() / ".notion_importer" / "config.json"

@dataclass
class AppConfig:
    notion_token: Optional[str] = None
    parent_id: Optional[str] = None
    source_dir: str = ""

    @staticmethod
    def load(env: bool = True) -> "AppConfig":
        cfg = AppConfig()
        # JSON config
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                cfg.notion_token = data.get("NOTION_TOKEN") or data.get("notion_token")
                cfg.parent_id = data.get("PARENT_ID") or data.get("parent_id")
                cfg.source_dir = data.get("SOURCE_DIR") or cfg.source_dir
            except Exception:
                pass
        # .env environment
        if env:
            cfg.notion_token = os.getenv("NOTION_TOKEN", cfg.notion_token)
            cfg.parent_id = os.getenv("PARENT_ID", cfg.parent_id)
            cfg.source_dir = os.getenv("SOURCE_DIR", cfg.source_dir)
        return cfg

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "NOTION_TOKEN": self.notion_token or "",
            "PARENT_ID": self.parent_id or "",
            "SOURCE_DIR": self.source_dir,
        }
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
