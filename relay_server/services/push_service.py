"""推送服务 —— WebSocket 实时推送 + 队列轮询双模式。"""

from __future__ import annotations

from typing import Any


class PushService:
    """事件推送服务。"""

    def should_push(self, event: dict[str, Any]) -> bool:
        return bool(event.get("notify_receiver"))

    def dispatch_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event_id = event.get("event_id", "")
        ws_delivered = False
        ws_count = 0

        if self.should_push(event):
            try:
                from relay_server.ws_server import broadcast_event, get_connection_count
                ws_count = get_connection_count()
                if ws_count > 0:
                    ws_delivered = broadcast_event(event)
            except ImportError:
                pass

        return {
            "event_id": event_id,
            "pushed": ws_delivered,
            "ws_clients": ws_count,
            "ws_delivered": ws_delivered,
        }


PUSH_SERVICE = PushService()
