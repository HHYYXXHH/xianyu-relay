"""事件模型骨架。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventRecord:
    """事件记录模型。"""

    event_id: str
    event_type: str
    content_type: str
    source: str
    timestamp: str
    thread_key: str
    message_key: str
    summary: str
    ocr_status: str
    upload_status: str
    checksum: str
    image_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
