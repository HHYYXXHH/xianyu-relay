"""重试服务骨架。"""

from __future__ import annotations


class RetryService:
    """失败事件重试服务。"""

    def mark_retry_pending(self, event_id: str) -> dict[str, str]:
        """标记等待重试。"""
        return {"event_id": event_id, "status": "pending"}

    def requeue_failed_event(self, event_id: str) -> dict[str, str]:
        """重新入队失败事件。"""
        return {"event_id": event_id, "status": "requeued"}


RETRY_SERVICE = RetryService()
