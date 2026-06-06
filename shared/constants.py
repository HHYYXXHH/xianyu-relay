"""共享常量定义。"""

from __future__ import annotations

DEFAULT_TIMEOUT = 10
DEFAULT_ENCODING = "utf-8"
DEFAULT_IMAGE_DIR = "data/images"
DEFAULT_EVENT_DIR = "data/events"
DEFAULT_RETRY_DIR = "data/retry"

SUPPORTED_CONTENT_TYPES = {"text", "image", "card"}
SUPPORTED_OCR_STATUS = {"not_needed", "pending", "success", "failed"}
SUPPORTED_UPLOAD_STATUS = {"pending", "success", "failed"}
