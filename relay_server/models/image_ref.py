"""图片引用模型骨架。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ImageRef:
    """图片引用模型。"""

    image_ref: str
    event_id: str
    storage_path: str
