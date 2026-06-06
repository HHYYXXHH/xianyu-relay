"""普通图片处理骨架。"""

from __future__ import annotations

from typing import Any

from shared.error_codes import get_error_message
from source_app.app.event_builder import build_event
from source_app.app.retry_queue import enqueue_retry
from source_app.app.upload_client import upload_event


def handle_normal_image(message: dict[str, Any]) -> dict[str, Any]:
    """处理普通图片消息。"""
    event = build_normal_event(message)
    upload_result = upload_event(event)

    if upload_result.get("ok"):
        return event

    return handle_upload_failure(message, upload_result)


def build_normal_event(message: dict[str, Any]) -> dict[str, Any]:
    """构造普通图片事件。"""
    return build_event(
        message,
        {
            "event_type": "image",
            "content_type": "image",
            "summary": "用户发送了图片",
            "ocr_status": "not_needed",
            "upload_status": "pending",
        },
    )


def handle_upload_failure(message: dict[str, Any], error: dict[str, Any]) -> dict[str, Any]:
    """处理上传失败并构建失败事件。"""
    event = build_upload_failure_event(message, error)
    enqueue_retry(event)
    return event


def build_upload_failure_event(message: dict[str, Any], error: dict[str, Any]) -> dict[str, Any]:
    """构造普通图片上传失败事件。"""
    code = error.get("body", {}).get("error", "upload_failed")
    return build_event(
        message,
        {
            "event_type": "image",
            "content_type": "image",
            "summary": "普通图片上传失败",
            "upload_status": "failed",
            "error_code": code,
            "error_message": get_error_message(code),
            "need_receiver_attention": True,
            "notify_receiver": True,
        },
    )
