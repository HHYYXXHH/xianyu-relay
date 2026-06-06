"""本地图片与事件存储。

图片按 message_key + 时间戳组织目录，事件以 JSON 行格式追加存储。
所有写操作自动创建目录。
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from source_app.app.config import EVENT_DIR, IMAGE_DIR, RETRY_DIR


def ensure_dirs() -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    EVENT_DIR.mkdir(parents=True, exist_ok=True)
    RETRY_DIR.mkdir(parents=True, exist_ok=True)


def save_image(image_data: bytes, *, message_key: str = "", timestamp: str = "") -> str:
    """保存图片二进制数据，返回图片引用路径。

    文件名由 message_key + 时间戳 + sha256 前8位组成，避免冲突。
    """
    ensure_dirs()
    sha = hashlib.sha256(image_data).hexdigest()[:8]
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    key = message_key or "unknown"
    file_name = f"{key}_{ts}_{sha}.jpg"
    path = IMAGE_DIR / file_name
    path.write_bytes(image_data)
    return str(path)


def save_image_from_file(source_path: str | Path, *, message_key: str = "", timestamp: str = "") -> str:
    """从已有文件复制图片到本地存储，返回引用路径。"""
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"源图片不存在: {source_path}")

    ensure_dirs()
    image_data = src.read_bytes()
    sha = hashlib.sha256(image_data).hexdigest()[:8]
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    key = message_key or "unknown"
    suffix = src.suffix or ".jpg"
    file_name = f"{key}_{ts}_{sha}{suffix}"
    dest = IMAGE_DIR / file_name
    shutil.copy2(src, dest)
    return str(dest)


def save_event(event: dict[str, Any]) -> str:
    """保存事件到本地缓存（JSON 文件）。"""
    ensure_dirs()
    path = EVENT_DIR / f"{event.get('event_id', 'event')}.json"
    path.write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def resolve_image_ref(image_ref: str) -> Path:
    """解析图片引用，返回绝对路径。"""
    p = Path(image_ref)
    if p.is_absolute():
        return p
    return IMAGE_DIR / p


def get_stored_events() -> list[dict[str, Any]]:
    """读取所有本地缓存事件。"""
    ensure_dirs()
    events: list[dict[str, Any]] = []
    for path in sorted(EVENT_DIR.glob("*.json")):
        try:
            events.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return events


def cleanup_event(event_id: str) -> bool:
    """删除本地缓存事件（上传成功后调用）。"""
    path = EVENT_DIR / f"{event_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
