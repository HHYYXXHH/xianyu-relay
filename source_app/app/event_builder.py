"""事件构建器。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from shared.constants import SUPPORTED_CONTENT_TYPES


def build_event(base_message: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """根据基础消息与覆盖字段构造统一事件。"""
    event = deepcopy(base_message)
    event.setdefault("event_type", "message")
    event.setdefault("content_type", "text")
    event.setdefault("source", "chat_page")
    event.setdefault("image_refs", [])
    event.setdefault("summary", "")
    event.setdefault("ocr_status", "not_needed")
    event.setdefault("notify_receiver", False)
    event.setdefault("need_receiver_attention", False)
    event.setdefault("upload_status", "pending")
    event.setdefault("checksum", "")

    if event.get("content_type") not in SUPPORTED_CONTENT_TYPES:
        raise ValueError("content_type 不合法")

    if overrides:
        event.update(overrides)

    return event
