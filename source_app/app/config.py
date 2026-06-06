"""发射端配置。"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
IMAGE_DIR = DATA_DIR / "images"
EVENT_DIR = DATA_DIR / "events"
RETRY_DIR = DATA_DIR / "retry"

EVENT_API_URL = "http://127.0.0.1:8000/events"
IMAGE_API_URL = "http://127.0.0.1:8000/images"
