"""状态回传骨架。"""

from __future__ import annotations

from shared.api_client import post
from receiver_app.app.config import ATTENTION_STATUS_URL


def report_handled(event_id: str) -> dict[str, str]:
    """上报已处理状态。"""
    return post(ATTENTION_STATUS_URL, {"event_id": event_id, "status": "handled"})
