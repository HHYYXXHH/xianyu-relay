"""事件 API 骨架。"""

from __future__ import annotations

from typing import Any

from relay_server.services.dedupe_service import DEDUPE_SERVICE
from relay_server.services.event_service import EVENT_SERVICE
from relay_server.services.push_service import PUSH_SERVICE


def validate_event(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """验证事件请求体。"""
    required = {"event_id", "event_type", "content_type", "source", "timestamp", "thread_key", "message_key", "summary", "ocr_status", "notify_receiver", "need_receiver_attention", "upload_status", "checksum"}
    missing = sorted(required.difference(payload))
    return len(missing) == 0, missing


def create_event(request: dict[str, Any]) -> dict[str, Any]:
    """接收事件并写入存储层，需要推送时广播。"""
    ok, missing = validate_event(request)
    if not ok:
        return {"status": "rejected", "missing_fields": missing}

    if DEDUPE_SERVICE.should_dedupe(request):
        return {"status": "duplicate", "event_id": request["event_id"]}

    event = EVENT_SERVICE.create_event(request)
    EVENT_SERVICE.save_event_images(event.event_id, request.get("image_refs", []))

    result = PUSH_SERVICE.dispatch_event(request)
    return {"status": "accepted", "event_id": event.event_id, **result}
