"""发射端启动入口。

模式:
  (默认)  ADB 通知监控
  --file  文件监听模式（监控 data/watch/*.json）
  --poll  轮询模式
  --test  单次模拟消息测试
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time

from source_app.app.card_ocr_handler import handle_card_image
from source_app.app.config import DATA_DIR
from source_app.app.event_builder import build_event
from source_app.app.image_classifier import classify_images
from source_app.app.local_storage import ensure_dirs
from source_app.app.message_listener import (
    ListenerConfig,
    check_adb_available,
    check_device_connected,
    set_message_handler,
    start_listener,
)
from source_app.app.normal_image_handler import handle_normal_image
from source_app.app.upload_client import upload_event


def handle_incoming_message(message: dict[str, Any]) -> dict[str, Any]:
    """处理标准化消息的主入口。"""
    images = message.get("images", [])
    text = message.get("text", "")
    msg_key = message.get("message_key", str(int(time.time() * 1000)))

    if not images and not text:
        return {"status": "skipped", "reason": "empty_message"}

    # 纯文本
    if not images:
        event = build_event(message, {
            "event_id": f"evt_{msg_key}",
            "event_type": "message", "content_type": "text",
            "summary": text[:80] if text else "空消息", "content_text": text,
            "checksum": hashlib.md5(text.encode()).hexdigest()[:8] if text else "",
        })
        upload_event(event)
        return {"status": "ok", "event_id": event.get("event_id"), "type": "text"}

    # 图片 + 文本
    classifications = classify_images(images)
    results = []
    for i, (image, classification) in enumerate(zip(images, classifications)):
        single_msg = {**message, "images": [image],
            "image_refs": [image.get("path", image.get("image_ref", ""))]}
        if classification == "normal_image":
            results.append(handle_normal_image(single_msg))
        else:
            results.append(handle_card_image(single_msg))

    if text:
        text_event = build_event(message, {
            "event_id": f"evt_{msg_key}_text",
            "event_type": "message", "content_type": "text",
            "summary": text[:80], "content_text": text,
            "checksum": hashlib.md5(text.encode()).hexdigest()[:8] if text else "",
        })
        upload_event(text_event)

    return {"status": "ok", "results": results}


def main() -> None:
    ensure_dirs()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    set_message_handler(handle_incoming_message)

    # 模式选择
    if "--test" in sys.argv:
        _run_test_message()
        return

    if "--file" in sys.argv:
        config = ListenerConfig(mode="file_watcher", poll_interval=1.0,
            watch_dir=str(DATA_DIR / "watch"))
    elif "--poll" in sys.argv:
        config = ListenerConfig(mode="polling", poll_interval=2.0)
    else:
        # 默认 ADB 模式
        print("=" * 50)
        print("  闲鱼消息转发 - 发射端 (ADB 模式)")
        print("=" * 50)
        config = ListenerConfig(mode="adb_bridge", poll_interval=2.0)

    start_listener(config)


def _run_test_message() -> None:
    """发送一条模拟消息，验证完整管线。"""
    print("[测试] 模拟发送闲鱼消息...\n")

    test_msg = {
        "message_key": f"test_{int(time.time()*1000)}",
        "thread_key": "com.taobao.idlefish",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "notification_bar",
        "text": "买家已付款\n订单号: order_2026052615001234\n金额: 1299.00元",
        "images": [],
        "image_refs": [],
    }

    result = handle_incoming_message(test_msg)
    print(f"[测试] 处理结果: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    import json
    main()
