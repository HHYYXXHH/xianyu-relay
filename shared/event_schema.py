"""事件结构、校验与归一化。"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from shared.constants import SUPPORTED_CONTENT_TYPES, SUPPORTED_OCR_STATUS, SUPPORTED_UPLOAD_STATUS


REQUIRED_FIELDS = {
    "event_id",
    "event_type",
    "content_type",
    "source",
    "timestamp",
    "thread_key",
    "message_key",
    "summary",
    "ocr_status",
    "notify_receiver",
    "need_receiver_attention",
    "upload_status",
    "checksum",
}


def validate_event(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """校验事件结构。"""
    errors: list[str] = []
    missing = REQUIRED_FIELDS.difference(payload.keys())
    if missing:
        errors.append(f"缺少字段: {sorted(missing)}")

    content_type = payload.get("content_type")
    if content_type not in SUPPORTED_CONTENT_TYPES:
        errors.append("content_type 不合法")

    ocr_status = payload.get("ocr_status")
    if ocr_status not in SUPPORTED_OCR_STATUS:
        errors.append("ocr_status 不合法")

    upload_status = payload.get("upload_status")
    if upload_status not in SUPPORTED_UPLOAD_STATUS:
        errors.append("upload_status 不合法")

    return len(errors) == 0, errors


def normalize_event(payload: dict[str, Any]) -> dict[str, Any]:
    """把事件对象归一化为统一结构。"""
    normalized = deepcopy(payload)
    normalized.setdefault("image_refs", [])
    normalized.setdefault("content_text", "")
    normalized.setdefault("image_ocr_text", "")
    normalized.setdefault("error_code", "")
    normalized.setdefault("error_message", "")
    normalized.setdefault("ocr_error", "")
    normalized.setdefault("metadata", {})

    if not normalized.get("timestamp"):
        normalized["timestamp"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    if normalized.get("notify_receiver") is None:
        normalized["notify_receiver"] = False
    if normalized.get("need_receiver_attention") is None:
        normalized["need_receiver_attention"] = False

    return normalized
