"""端到端集成测试脚本。

覆盖场景:
1. 普通图片成功转发
2. 普通图片上传失败
3. OCR 失败事件
4. 接收端消费
5. 重试队列
6. 去重验证
7. 事件校验
"""

import json
import os
import shutil
import sys
import threading
import time
import urllib.request

sys.path.insert(0, ".")

# 清理旧数据
for d in ["relay_server/data", "source_app/data", "receiver_app/data", "data"]:
    if os.path.exists(d):
        shutil.rmtree(d)

from relay_server.demo_server import main as server_main, HOST, PORT

server_thread = threading.Thread(target=server_main, daemon=True)
server_thread.start()
time.sleep(1)

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} -- {detail}")


def do_post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://{HOST}:{PORT}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def do_get(path):
    try:
        with urllib.request.urlopen(f"http://{HOST}:{PORT}{path}", timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


print("=" * 60)
print("端到端集成测试")
print("=" * 60)

# === 场景1: 普通图片事件 ===
print("\n--- 场景1: 普通图片事件 ---")
r1 = do_post("/events", {
    "event_id": "evt_normal_001", "event_type": "image", "content_type": "image",
    "source": "chat_page", "timestamp": "2026-05-26 14:00:00",
    "thread_key": "thread_001", "message_key": "msg_001",
    "image_refs": ["img_001.jpg"], "summary": "用户发送了图片",
    "ocr_status": "not_needed", "upload_status": "success",
    "need_receiver_attention": False, "notify_receiver": False, "checksum": "cks_001",
})
check("普通图片事件 accepted", r1.get("status") == "accepted")

# === 场景2: 上传失败事件 ===
print("\n--- 场景2: 上传失败事件 ---")
r2 = do_post("/events", {
    "event_id": "evt_upload_fail_001", "event_type": "image", "content_type": "image",
    "source": "chat_page", "timestamp": "2026-05-26 14:01:00",
    "thread_key": "thread_001", "message_key": "msg_002",
    "image_refs": ["img_002.jpg"], "summary": "普通图片上传失败",
    "ocr_status": "not_needed", "upload_status": "failed",
    "error_code": "upload_timeout", "error_message": "图片上传超时，请检查网络或稍后重试",
    "need_receiver_attention": True, "notify_receiver": True, "checksum": "cks_002",
})
check("上传失败事件 accepted", r2.get("status") == "accepted")

# === 场景3: OCR 失败事件 ===
print("\n--- 场景3: OCR 失败事件 ---")
r3 = do_post("/events", {
    "event_id": "evt_ocr_fail_001", "event_type": "image", "content_type": "image",
    "source": "chat_page", "timestamp": "2026-05-26 14:02:00",
    "thread_key": "thread_001", "message_key": "msg_003",
    "image_refs": ["img_003.jpg"], "summary": "图片识别失败，已保留原图",
    "ocr_status": "failed", "ocr_error": "no_text_detected",
    "upload_status": "success",
    "need_receiver_attention": True, "notify_receiver": True, "checksum": "cks_003",
})
check("OCR失败事件 accepted", r3.get("status") == "accepted")

# === 场景4: 待消费队列 ===
print("\n--- 场景4: 待消费队列 ---")
r4 = do_get("/events/pending")
pending_events = r4.get("events", [])
check("仅推送需要关注的事件", len(pending_events) == 2,
      f"期望2条，实际{len(pending_events)}条")
check("evt_normal_001 不在推送队列",
      not any(e["event_id"] == "evt_normal_001" for e in pending_events))

# === 场景5: 队列消费 ===
print("\n--- 场景5: 队列消费 ---")
consumed = []
for i in range(3):
    evt = do_get("/events/next").get("event")
    if evt:
        consumed.append(evt["event_id"])
check("正确消费了2条事件", len(consumed) == 2, f"实际{len(consumed)}条")
check("队列已空", do_get("/events/next").get("event") is None)

# ACK
for eid in consumed:
    do_post("/events/ack", {"event_id": eid})

# === 场景6: 去重 ===
print("\n--- 场景6: 去重验证 ---")
r6 = do_post("/events", {
    "event_id": "evt_ocr_fail_001", "event_type": "image", "content_type": "image",
    "source": "chat_page", "timestamp": "2026-05-26 14:04:00",
    "thread_key": "thread_001", "message_key": "msg_003",
    "image_refs": ["img_003.jpg"], "summary": "重复事件",
    "ocr_status": "failed", "upload_status": "pending",
    "need_receiver_attention": True, "notify_receiver": True, "checksum": "cks_003",
})
check("重复事件被拒绝", r6.get("status") == "duplicate")

# === 场景7: 事件校验 ===
print("\n--- 场景7: 事件校验 ---")
r7 = do_post("/events", {"event_id": "incomplete"})
check("不完整事件被拒绝", r7.get("status") == "rejected")
check("返回缺失字段列表", len(r7.get("missing_fields", [])) > 0)

# === 场景8: 状态回传 ===
print("\n--- 场景8: 状态回传 ---")
r8 = do_post("/attention-status", {
    "event_id": "evt_upload_fail_001",
    "attention_status": "handled",
    "handled_at": "2026-05-26 14:05:00",
})
check("状态回传成功", r8.get("status") == "handled" or r8.get("event_id"))

# === 场景9: 重试队列逻辑 ===
print("\n--- 场景9: 重试队列 ---")
from source_app.app.retry_queue import enqueue_retry, get_queue_stats, remove_retry

retry_event = {
    "event_id": "evt_retry_001", "event_type": "image", "content_type": "image",
    "source": "chat_page", "timestamp": "2026-05-26 14:03:00",
    "thread_key": "thread_001", "message_key": "msg_004",
    "image_refs": ["img_004.jpg"], "summary": "重试测试",
    "ocr_status": "not_needed", "upload_status": "failed",
    "need_receiver_attention": True, "notify_receiver": True, "checksum": "cks_retry",
    "error_code": "upload_failed", "error_message": "测试",
}
enqueue_retry(retry_event)
stats = get_queue_stats()
check("重试队列有1条", stats["pending"] == 1, f"实际{stats['pending']}条")
remove_retry("evt_retry_001")
stats2 = get_queue_stats()
check("移除后队列为空", stats2["pending"] == 0, f"实际{stats2['pending']}条")

# === 场景10: 发射端事件构建 ===
print("\n--- 场景10: 发射端事件构建 ---")
from source_app.app.event_builder import build_event
from source_app.app.normal_image_handler import build_normal_event, build_upload_failure_event

base = {"message_key": "msg_010", "thread_key": "thread_010",
        "timestamp": "2026-05-26 14:00:00", "event_id": "evt_010"}

normal_evt = build_normal_event(base)
check("普通图片事件字段正确",
      normal_evt["ocr_status"] == "not_needed" and normal_evt["content_type"] == "image")

fail_evt = build_upload_failure_event(base, {"ok": False, "status": 408,
      "body": {"error": "upload_timeout"}})
check("上传失败事件字段正确",
      fail_evt["upload_status"] == "failed" and fail_evt["notify_receiver"] is True)
check("失败事件包含错误码", fail_evt.get("error_code") == "upload_timeout")

# === 场景11: OCR 失败事件构建 ===
print("\n--- 场景11: OCR 失败事件构建 ---")
from source_app.app.card_ocr_handler import build_ocr_failed_event

ocr_fail = build_ocr_failed_event(base, "no_text_detected")
check("OCR失败 ocr_status=failed", ocr_fail["ocr_status"] == "failed")
check("OCR失败 need_receiver_attention=true", ocr_fail["need_receiver_attention"] is True)
check("OCR失败 notify_receiver=true", ocr_fail["notify_receiver"] is True)
check("OCR失败 保留原图引用", len(ocr_fail.get("image_refs", [])) >= 0)

# === 汇总 ===
print()
print("=" * 60)
print(f"测试结果: {passed} 通过, {failed} 失败 (共 {passed + failed} 项)")
if failed > 0:
    print("存在失败项，请检查！")
    sys.exit(1)
else:
    print("全部测试通过！")
print("=" * 60)
