"""事件服务骨架。"""

from __future__ import annotations

from typing import Any

from relay_server.models.event import EventRecord
from relay_server.storage.local_store import mark_handled, upsert_event, update_event_images


class EventService:
    """事件存储服务。"""

    def create_event(self, payload: dict[str, Any]) -> EventRecord:
        """创建事件记录并落盘。"""
        upsert_event(payload)
        return EventRecord(
            event_id=payload["event_id"],
            event_type=payload["event_type"],
            content_type=payload["content_type"],
            source=payload["source"],
            timestamp=payload["timestamp"],
            thread_key=payload["thread_key"],
            message_key=payload["message_key"],
            summary=payload["summary"],
            ocr_status=payload["ocr_status"],
            upload_status=payload["upload_status"],
            checksum=payload["checksum"],
            image_refs=payload.get("image_refs", []),
            metadata=payload.get("metadata", {}),
        )

    def update_attention_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        """更新处理状态。"""
        event_id = payload.get("event_id")
        if event_id:
            mark_handled(event_id)
        return {"event_id": event_id, "status": "handled"}

    def save_event_images(self, event_id: str, image_refs: list[str]) -> list[str]:
        """保存图片引用。"""
        update_event_images(event_id, image_refs)
        return image_refs

    def mark_event_handled(self, event_id: str) -> dict[str, Any]:
        """标记事件已处理。"""
        mark_handled(event_id)
        return {"event_id": event_id, "handled": True}


EVENT_SERVICE = EventService()
