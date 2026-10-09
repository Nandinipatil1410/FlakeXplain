"""Pinned configurations for previously unconfigured CANNIER subjects."""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "cannier-replication" / "remaining-configs.json"
NEW_CANNIER_REPOS = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
