"""WebSocket 实时推送验证测试。"""
import json, os, shutil, sys, threading, time, urllib.request

sys.path.insert(0, ".")

for d in ["relay_server/data", "data"]:
    if os.path.exists(d): shutil.rmtree(d)

# 只启动 demo_server（内部自动启动 WS 服务）
from relay_server.demo_server import main as http_main, HOST, PORT, WS_PORT
http_thread = threading.Thread(target=http_main, daemon=True)
http_thread.start()
time.sleep(2)

print("=" * 55)
print("  WebSocket 实时推送测试")
print("=" * 55)

import websockets.sync.client as ws_sync

received = []

try:
    ws = ws_sync.connect(f"ws://{HOST}:{WS_PORT}", close_timeout=2)
    msg = json.loads(ws.recv())
    print(f"[WS] {msg['message']}")
except Exception as e:
    print(f"[错误] WebSocket 连接失败: {e}")
    sys.exit(1)

HOST_URL = f"http://{HOST}:{PORT}"

def post(path, payload):
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(f"{HOST_URL}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())

# 发送事件
print("\n[发射端] 发送3条事件...")
events_data = [
    ("普通图片(不推送)", {"event_id":"ws_001","event_type":"image","content_type":"image",
     "source":"chat_page","timestamp":"2026-05-26 14:00:00","thread_key":"t1",
     "message_key":"m1","image_refs":["a.jpg"],"summary":"买家发图",
     "ocr_status":"not_needed","upload_status":"success",
     "need_receiver_attention":False,"notify_receiver":False,"checksum":"c1"}),
    ("上传失败", {"event_id":"ws_002","event_type":"image","content_type":"image",
     "source":"chat_page","timestamp":"2026-05-26 14:01:00","thread_key":"t1",
     "message_key":"m2","image_refs":["b.jpg"],"summary":"上传失败",
     "ocr_status":"not_needed","upload_status":"failed",
     "error_code":"upload_timeout","error_message":"超时",
     "need_receiver_attention":True,"notify_receiver":True,"checksum":"c2"}),
    ("OCR失败", {"event_id":"ws_003","event_type":"image","content_type":"image",
     "source":"chat_page","timestamp":"2026-05-26 14:02:00","thread_key":"t1",
     "message_key":"m3","image_refs":["c.jpg"],"summary":"OCR识别失败",
     "ocr_status":"failed","ocr_error":"no_text","upload_status":"success",
     "need_receiver_attention":True,"notify_receiver":True,"checksum":"c3"}),
]

for label, evt in events_data:
    r = post("/events", evt)
    print(f"  [{r['status']}] {label}  ws={r.get('ws_clients',0)}  delivered={r.get('ws_delivered',False)}")
    time.sleep(0.3)

# 接收 WebSocket 事件
print("\n[WS] 等待事件...")
deadline = time.time() + 3
while time.time() < deadline:
    try:
        raw = ws.recv(timeout=1.0)
        msg = json.loads(raw)
        if msg.get("type") == "event":
            evt = msg["event"]
            received.append(evt)
            print(f"  >> {evt['event_id']} - {evt['summary']}")
        elif msg.get("type") == "ping":
            ws.send(json.dumps({"type": "pong"}))
    except TimeoutError:
        break
    except Exception:
        break

ws.close()

# 验证
print(f"\n[验证] 收到 {len(received)} 条事件")
checks = [
    ("收到上传失败事件", any(e["event_id"]=="ws_002" for e in received)),
    ("收到OCR失败事件", any(e["event_id"]=="ws_003" for e in received)),
    ("普通图片未推送(notify_receiver=false)", not any(e["event_id"]=="ws_001" for e in received)),
]
all_ok = True
for label, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if not ok: all_ok = False

status = json.loads(urllib.request.urlopen(f"{HOST_URL}/ws/status").read())
print(f"\n[服务] ws_clients={status['ws_clients']}")

print(f"\n{'='*55}")
print(f"  {'全部通过!' if all_ok else '存在失败项'}")
print(f"{'='*55}")
