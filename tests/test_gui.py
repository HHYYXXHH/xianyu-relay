"""GUI 端到端测试 —— 模拟发射事件 → WebSocket → GUI 接收。"""
import json, os, shutil, sys, threading, time, urllib.request

sys.path.insert(0, ".")

for d in ["relay_server/data", "data"]:
    if os.path.exists(d): shutil.rmtree(d)

# 启动服务器
from relay_server.demo_server import main as http_main, HOST, PORT
server_thread = threading.Thread(target=http_main, daemon=True)
server_thread.start()
time.sleep(1.5)

# 启动 GUI（隐藏窗口，仅测试数据流）
from receiver_app.app.gui import ReceiverGUI
import tkinter as tk

gui = ReceiverGUI()
gui.root.withdraw()  # 隐藏窗口

# 等待 WebSocket 连接
time.sleep(1)

# 模拟发射端发送事件
HOST_URL = f"http://{HOST}:{PORT}"

def post(path, payload):
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(f"{HOST_URL}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())

events_to_send = [
    ("普通图片", {"event_id":"gui_001","event_type":"image","content_type":"image",
     "source":"chat_page","timestamp":"2026-05-26 15:00:00","thread_key":"t1",
     "message_key":"m1","image_refs":["product.jpg"],"summary":"买家发送了商品图片",
     "ocr_status":"not_needed","upload_status":"success",
     "need_receiver_attention":False,"notify_receiver":False,"checksum":"gc1"}),
    ("图片上传超时", {"event_id":"gui_002","event_type":"image","content_type":"image",
     "source":"chat_page","timestamp":"2026-05-26 15:01:00","thread_key":"t1",
     "message_key":"m2","image_refs":["large_img.jpg"],"summary":"图片上传超时",
     "ocr_status":"not_needed","upload_status":"failed",
     "error_code":"upload_timeout","error_message":"图片上传超时，请检查网络或稍后重试",
     "need_receiver_attention":True,"notify_receiver":True,"checksum":"gc2"}),
    ("OCR识别失败", {"event_id":"gui_003","event_type":"image","content_type":"image",
     "source":"chat_page","timestamp":"2026-05-26 15:02:00","thread_key":"t1",
     "message_key":"m3","image_refs":["payment_card.jpg"],"summary":"图片识别失败，已保留原图",
     "ocr_status":"failed","ocr_error":"no_text_detected","upload_status":"success",
     "need_receiver_attention":True,"notify_receiver":True,"checksum":"gc3"}),
]

print("=" * 55)
print("  GUI 端到端测试")
print("=" * 55)

# 发送事件
print("\n[发射端] 发送事件...")
for label, evt in events_to_send:
    r = post("/events", evt)
    print(f"  [{r['status']}] {label}  ws_delivered={r.get('ws_delivered',False)}")

# 等待 GUI 通过 WebSocket 接收
time.sleep(2)

# 验证 GUI EventStore
print(f"\n[GUI] EventStore 事件数: {gui.store.count}")

events = gui.store.get_all()
checks = [
    ("收到2条事件(普通图片不推送)", len(events) == 2, f"实际 {len(events)}"),
    ("gui_001 不在(notify=false不推送)", not any(e["event_id"]=="gui_001" for e in events)),
    ("gui_002 存在", any(e["event_id"]=="gui_002" for e in events)),
    ("gui_003 存在", any(e["event_id"]=="gui_003" for e in events)),
    ("需关注事件红色标记", any(
        e.get("need_receiver_attention") and not e.get("_handled")
        for e in events
    )),
]

all_ok = True
for label, ok, *detail in checks:
    d = detail[0] if detail else ""
    mark = "PASS" if ok else "FAIL"
    if not ok: all_ok = False
    print(f"  [{mark}] {label} {d}")

# 测试标记已处理
gui.store.mark_handled("gui_002")
handled = gui.store.get("gui_002")
checks2 = [
    ("标记已处理成功", handled is not None and handled.get("_handled") == True),
]
for label, ok in checks2:
    mark = "PASS" if ok else "FAIL"
    if not ok: all_ok = False
    print(f"  [{mark}] {label}")

# 清理
gui._on_close()
print(f"\n{'='*55}")
print(f"  {'全部通过!' if all_ok else '存在失败项'}")
print(f"{'='*55}")
