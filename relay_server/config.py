"""中转服务器配置。"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("RELAY_DATA_DIR", str(BASE_DIR / "data")))
DB_PATH = DATA_DIR / "events.db"
