from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_json_config(path: str | Path) -> Dict[str, Any]:
    cfg_path = Path(path).expanduser().resolve()
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {cfg_path}. Copy config/paths.example.json to config/paths.json and edit it."
        )
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def require_keys(d: Dict[str, Any], keys: list[str], context: str) -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise KeyError(f"Missing keys in {context}: {missing}")
