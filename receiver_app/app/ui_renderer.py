"""接收端 UI 渲染器 —— 负责将事件展示到终端/界面。

支持的事件类型与渲染方式:
- 普通图片: 显示图片路径与摘要
- OCR 失败: 显示原图路径与失败原因
- 上传失败: 显示错误码与错误信息
- 卡片事件: 显示结构化 OCR 结果
- 文本消息: 显示文本内容
"""

from __future__ import annotations

from typing import Any

from receiver_app.app.image_loader import load_image


def render_event(event: dict[str, Any]) -> dict[str, Any]:
    """渲染事件到终端。

    返回渲染摘要字典，供上层（如 GUI）使用。
    """
    content_type = event.get("content_type", "text")
    ocr_status = event.get("ocr_status", "not_needed")
    upload_status = event.get("upload_status", "pending")

    if ocr_status == "failed":
        return _render_ocr_failed(event)

    if upload_status == "failed":
        return _render_upload_failed(event)

    if content_type in ("image", "card"):
        return _render_image_event(event)

    return _render_text_event(event)


def _render_ocr_failed(event: dict[str, Any]) -> dict[str, Any]:
    """渲染 OCR 失败事件: 显示原图 + 失败原因。"""
    summary = event.get("summary", "图片识别失败，已保留原图")
    ocr_error = event.get("ocr_error", "未知OCR错误")

    print("=" * 50)
    print(f"[OCR 失败提醒] {summary}")
    print(f"[失败原因] {ocr_error}")

    image_refs = event.get("image_refs", [])
    image_results = []
    for ref in image_refs:
        result = load_image(ref)
        if result["ok"]:
            print(f"[原图] {result['path']} ({result['width']}x{result['height']})")
        else:
            print(f"[原图加载失败] {ref}: {result.get('error', '')}")
        image_results.append(result)

    print(f"[需要人工处理] event_id={event.get('event_id', '')}")
    print("=" * 50)

    return {
        "rendered": True,
        "type": "ocr_failed",
        "summary": summary,
        "ocr_error": ocr_error,
        "image_results": image_results,
    }


def _render_upload_failed(event: dict[str, Any]) -> dict[str, Any]:
    """渲染上传失败事件: 显示错误码与错误信息。"""
    error_code = event.get("error_code", "unknown")
    error_message = event.get("error_message", "未知上传错误")
    summary = event.get("summary", "普通图片上传失败")

    print("=" * 50)
    print(f"[上传失败提醒] {summary}")
    print(f"[错误码] {error_code}")
    print(f"[错误信息] {error_message}")

    image_refs = event.get("image_refs", [])
    for ref in image_refs:
        print(f"[图片引用] {ref}")

    print(f"[需要人工处理] event_id={event.get('event_id', '')}")
    print("=" * 50)

    return {
        "rendered": True,
        "type": "upload_failed",
        "summary": summary,
        "error_code": error_code,
        "error_message": error_message,
    }


def _render_image_event(event: dict[str, Any]) -> dict[str, Any]:
    """渲染普通图片/卡片事件。"""
    summary = event.get("summary", "")
    content_type = event.get("content_type", "image")
    image_refs = event.get("image_refs", [])

    label = "[卡片事件]" if content_type == "card" else "[图片事件]"
    print(f"{label} {summary}")

    image_results = []
    for ref in image_refs:
        result = load_image(ref)
        if result["ok"]:
            print(f"  [图片] {result['path']} ({result['width']}x{result['height']})")
        else:
            print(f"  [图片加载失败] {ref}: {result.get('error', '')}")
        image_results.append(result)

    ocr_text = event.get("image_ocr_text", "")
    if ocr_text:
        print(f"  [OCR 文本] {ocr_text[:200]}")

    return {
        "rendered": True,
        "type": "image",
        "summary": summary,
        "image_results": image_results,
    }


def _render_text_event(event: dict[str, Any]) -> dict[str, Any]:
    """渲染文本事件。"""
    summary = event.get("summary", "")
    content_text = event.get("content_text", "")

    print(f"[文本事件] {summary}")
    if content_text:
        print(f"  [内容] {content_text[:500]}")

    return {"rendered": True, "type": "text", "summary": summary, "content": content_text}


def render_error(event: dict[str, Any]) -> dict[str, Any]:
    """渲染通用失败事件。"""
    return render_event(event)


def render_text(event: dict[str, Any]) -> dict[str, Any]:
    """渲染文本事件。"""
    return _render_text_event(event)
