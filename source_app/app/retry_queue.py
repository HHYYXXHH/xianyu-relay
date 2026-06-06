"""重试队列 —— 基于本地文件的生产级重试逻辑。

特性:
- 指数退避: 延迟 = base_delay * (2 ** retry_count)
- 最大重试次数: 超限后移入死信队列
- 持久化: JSON 文件存储，重启不丢失
- 定时触发: process_retry_queue 由外部定时任务驱动
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from source_app.app.config import RETRY_DIR
from source_app.app.upload_client import upload_event

MAX_RETRIES = 5
BASE_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 300


@dataclass
class RetryItem:
    event: dict[str, Any]
    retry_count: int = 0
    first_failure: float = field(default_factory=time.time)
    last_failure: float = field(default_factory=time.time)
    next_retry_at: float = 0


def ensure_queue_dir() -> None:
    RETRY_DIR.mkdir(parents=True, exist_ok=True)


def _queue_path() -> Path:
    ensure_queue_dir()
    return RETRY_DIR / "queue.json"


def _dead_letter_path() -> Path:
    ensure_queue_dir()
    return RETRY_DIR / "dead_letter.json"


def _load_items(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_items(path: Path, items: dict[str, dict[str, Any]]) -> None:
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def enqueue_retry(event: dict[str, Any]) -> str:
    """将失败事件加入重试队列。"""
    ensure_queue_dir()
    event_id = event.get("event_id", "")
    items = _load_items(_queue_path())

    existing = items.get(event_id, {})
    retry_count = existing.get("retry_count", 0)
    first_failure = existing.get("first_failure", time.time())

    delay = min(BASE_DELAY_SECONDS * (2 ** retry_count), MAX_DELAY_SECONDS)
    items[event_id] = {
        "event": event,
        "retry_count": retry_count,
        "first_failure": first_failure,
        "last_failure": time.time(),
        "next_retry_at": time.time() + delay,
    }
    _save_items(_queue_path(), items)
    return event_id


def process_retry_queue() -> list[dict[str, Any]]:
    """处理所有到期的重试任务。返回本次处理成功的事件列表。"""
    ensure_queue_dir()
    items = _load_items(_queue_path())
    if not items:
        return []

    now = time.time()
    processed: list[dict[str, Any]] = []
    dead: dict[str, dict[str, Any]] = _load_items(_dead_letter_path())
    to_remove: list[str] = []

    for event_id, item_data in list(items.items()):
        if item_data["next_retry_at"] > now:
            continue

        event = item_data["event"]
        result = upload_event(event)

        if result.get("ok"):
            processed.append(event)
            to_remove.append(event_id)
            continue

        item_data["retry_count"] += 1
        item_data["last_failure"] = time.time()

        if item_data["retry_count"] >= MAX_RETRIES:
            dead[event_id] = item_data
            to_remove.append(event_id)
        else:
            delay = min(BASE_DELAY_SECONDS * (2 ** item_data["retry_count"]), MAX_DELAY_SECONDS)
            item_data["next_retry_at"] = now + delay

    for eid in to_remove:
        items.pop(eid, None)

    _save_items(_queue_path(), items)
    if dead:
        _save_items(_dead_letter_path(), dead)

    return processed


def remove_retry(event_id: str) -> None:
    """从重试队列移除已成功项。"""
    items = _load_items(_queue_path())
    if event_id in items:
        items.pop(event_id)
        _save_items(_queue_path(), items)


def get_retry_status(event_id: str) -> dict[str, Any] | None:
    """查询某个事件的重试状态。"""
    items = _load_items(_queue_path())
    return items.get(event_id)


def get_queue_stats() -> dict[str, int]:
    """返回重试队列统计信息。"""
    items = _load_items(_queue_path())
    dead = _load_items(_dead_letter_path())
    return {
        "pending": len(items),
        "dead_letter": len(dead),
    }
