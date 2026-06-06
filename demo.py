"""WebSocket 实时推送全流程演示。"""
import json, os, shutil, sys, threading, time, urllib.request

sys.path.insert(0, ".")

for d in ["relay_server/data", "data"]:
    if os.path.exists(d): shutil.rmtree(d)

# 启动服务
from relay_server.demo_server import main as http_main, HOST, PORT, WS_PORT
server_thread = threading.Thread(target=http_main, daemon=True)
server_thread.start()
time.sleep(1.5)

import websockets.sync.client as ws_sync

HOST_URL = f"http://{HOST}:{PORT}"

print("=" * 55)
print("  WebSocket 实时推送 —— 全流程演示")
print("=" * 55)
print(f"  HTTP:       {HOST_URL}")
print(f"  WebSocket:  ws://{HOST}:{WS_PORT}")
print()

# ── 1. 接收端通过 WebSocket 连接 ──
print("[接收端] 通过 WebSocket 连接服务器...")
ws = ws_sync.connect(f"ws://{HOST}:{WS_PORT}", close_timeout=2)
connected = json.loads(ws.recv())
print(f"[接收端] {connected['message']}")

# ── 2. 发射端发送事件 ──
print("\n[发射端] 模拟发送3条闲鱼消息...\n")

def post(path, payload):
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(f"{HOST_URL}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())

scenarios = [
    ("买家发来商品图", "正常转发，不推送通知", False, {
        "event_id":"evt_001","event_type":"image","content_type":"image",
        "source":"chat_page","timestamp":"2026-05-26 14:00:00","thread_key":"th_123",
        "message_key":"m1","image_refs":["product.jpg"],"summary":"买家发送了商品图片",
        "ocr_status":"not_needed","upload_status":"success",
        "need_receiver_attention":False,"notify_receiver":False,"checksum":"c1"}),
    ("图片上传超时", "上传失败，需通知接收端处理", True, {
        "event_id":"evt_002","event_type":"image","content_type":"image",
        "source":"chat_page","timestamp":"2026-05-26 14:01:00","thread_key":"th_123",
        "message_key":"m2","image_refs":["large_img.jpg"],"summary":"图片上传失败",
        "ocr_status":"not_needed","upload_status":"failed",
        "error_code":"upload_timeout","error_message":"图片上传超时，请检查网络或稍后重试",
        "need_receiver_attention":True,"notify_receiver":True,"checksum":"c2"}),
    ("交易卡片OCR失败", "OCR识别失败，保留原图并通知", True, {
        "event_id":"evt_003","event_type":"image","content_type":"image",
        "source":"chat_page","timestamp":"2026-05-26 14:02:00","thread_key":"th_123",
        "message_key":"m3","image_refs":["payment_card.jpg"],"summary":"图片识别失败，已保留原图",
        "ocr_status":"failed","ocr_error":"no_text_detected","upload_status":"success",
        "need_receiver_attention":True,"notify_receiver":True,"checksum":"c3"}),
]

for label, desc, should_push, evt in scenarios:
    r = post("/events", evt)
    ws_info = f"WS客户端={r.get('ws_clients',0)}  实时送达={r.get('ws_delivered',False)}"
    print(f"  [{r['status']}] {label}")
    print(f"         {desc}")
    print(f"         {ws_info}")
    time.sleep(0.5)

# ── 3. 接收端实时收到事件 ──
print("\n[接收端] 实时接收推送事件...\n")

received = []
deadline = time.time() + 2
while time.time() < deadline:
    try:
        raw = ws.recv(timeout=1.0)
        msg = json.loads(raw)
        if msg.get("type") == "event":
            evt = msg["event"]
            received.append(evt)
            attention = "需要人工处理" if evt.get("need_receiver_attention") else "正常消息"
            print(f"  >> [{evt['ocr_status']}/{evt['upload_status']}] {evt['summary']}")
            print(f"     event_id={evt['event_id']}  [{attention}]")
            if evt.get("error_code"):
                print(f"     错误码={evt['error_code']}  错误信息={evt['error_message']}")
            if evt.get("ocr_error"):
                print(f"     OCR错误={evt['ocr_error']}")
            print()
        elif msg.get("type") == "ping":
            ws.send(json.dumps({"type": "pong"}))
    except TimeoutError:
        break

ws.close()

# ── 4. 汇总 ──
print("─" * 55)
print(f"  发射: 3条  |  WebSocket实时推送: {len(received)}条  |  HTTP轮询队列: {len(received)}条")
print()

checks = [
    ("收到上传失败事件", any(e["event_id"]=="evt_002" for e in received)),
    ("收到OCR失败事件", any(e["event_id"]=="evt_003" for e in received)),
    ("普通图片未推送(节省带宽)", not any(e["event_id"]=="evt_001" for e in received)),
]
all_ok = True
for label, ok in checks:
    print(f"  [{'OK' if ok else 'FAIL'}] {label}")
    if not ok: all_ok = False

print()
print(f"  HTTP 服务:    {HOST_URL}")
print(f"  WebSocket 服务: ws://{HOST}:{WS_PORT}")
print(f"  接收端启动:   python receiver_app/app/main.py")
print()
print("=" * 55)
print(f"  {'演示成功！' if all_ok else '存在失败项'}")
print("=" * 55)
