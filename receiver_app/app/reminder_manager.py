"""接收端提醒管理。"""

from __future__ import annotations

from typing import Any


def evaluate(event: dict[str, Any]) -> None:
    """判定是否需要提醒。"""
    if event.get("need_receiver_attention"):
        show_notification(event.get("summary", "需要人工处理"))


def show_notification(message: str) -> None:
    """展示提醒。"""
    print(f"[提醒] {message}")
