"""处理回传 API 骨架。"""

from __future__ import annotations

from typing import Any

from relay_server.services.event_service import EVENT_SERVICE


def update_attention_status(request: dict[str, Any]) -> dict[str, Any]:
    """接收处理回传并更新状态。"""
    result = EVENT_SERVICE.update_attention_status(request)
    EVENT_SERVICE.mark_event_handled(request.get("event_id", ""))
    return result
