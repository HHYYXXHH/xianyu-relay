"""去重服务骨架。"""

from __future__ import annotations

from typing import Any

from relay_server.storage.local_store import has_event_key


class DedupeService:
    """用于判断事件是否为重复事件。"""

    def build_dedupe_key(self, payload: dict[str, Any]) -> str:
        """生成去重键。"""
        return payload.get("checksum") or payload.get("event_id") or payload.get("message_key") or ""

    def should_dedupe(self, payload: dict[str, Any]) -> bool:
        """判断是否需要去重。"""
        key = self.build_dedupe_key(payload)
        return has_event_key(key)


DEDUPE_SERVICE = DedupeService()
