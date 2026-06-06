"""上传客户端 —— 向中转服务器上传事件与图片。

- upload_event: 发送 JSON 事件到 POST /events
- upload_image: 发送图片二进制到 POST /images（multipart）
- 区分可重试错误与不可重试错误
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from shared.api_client import post as api_post
from source_app.app.config import EVENT_API_URL, IMAGE_API_URL

RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}


def _is_retryable(result: dict[str, Any]) -> bool:
    """判断上传失败是否可重试。"""
    status = result.get("status", 0)
    return isinstance(status, int) and status in RETRYABLE_STATUSES


def upload_event(event: dict[str, Any]) -> dict[str, Any]:
    """上传事件 JSON 到 POST /events。"""
    return api_post(EVENT_API_URL, event)


def upload_image(image_ref: str) -> dict[str, Any]:
    """上传图片文件到 POST /images。

    使用 multipart/form-data 编码发送图片二进制数据。
    返回格式与 upload_event 一致: {"ok": bool, "status": int, "body": dict}
    """
    from pathlib import Path

    img_path = Path(image_ref)
    if not img_path.exists():
        return {"ok": False, "status": 404, "body": {"error": f"图片文件不存在: {image_ref}"}}

    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    image_data = img_path.read_bytes()
    file_name = img_path.name

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + image_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        IMAGE_API_URL,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            resp_body = response.read().decode("utf-8")
            return {"ok": True, "status": response.status, "body": json.loads(resp_body) if resp_body else {}}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "body": {"error": exc.reason}, "retryable": exc.code in RETRYABLE_STATUSES}
    except (urllib.error.URLError, OSError) as exc:
        return {"ok": False, "status": 500, "body": {"error": str(exc)}, "retryable": True}


def upload_event_with_images(event: dict[str, Any]) -> dict[str, Any]:
    """上传事件并附带所有图片引用。

    先上传每张图片，再上传事件（事件中携带已上传的图片 URL）。
    """
    image_refs = event.get("image_refs", [])
    uploaded_urls: list[str] = []

    for ref in image_refs:
        result = upload_image(ref)
        if result.get("ok"):
            uploaded_urls.append(result.get("body", {}).get("url", ref))
        else:
            return {
                "ok": False,
                "status": result.get("status", 500),
                "body": {"error": f"图片上传失败: {ref}", "detail": result},
            }

    event_with_urls = {**event, "image_refs": uploaded_urls or image_refs}
    return upload_event(event_with_urls)
