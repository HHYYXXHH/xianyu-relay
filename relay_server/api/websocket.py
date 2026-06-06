"""实时推送骨架。"""

from __future__ import annotations

from typing import Any


def push_event(event: dict[str, Any]) -> dict[str, Any]:
    """推送事件到接收端。"""
    return {"event_id": event.get("event_id"), "pushed": True}
