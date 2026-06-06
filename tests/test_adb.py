"""ADB 通知解析测试 —— 使用模拟 dumpsys 输出验证完整链路。"""

import json, os, shutil, sys, threading, time, urllib.request

sys.path.insert(0, ".")

for d in ["relay_server/data"]:
    if os.path.exists(d): shutil.rmtree(d)

# ── 构建模拟 dumpsys 输出 ──
SIMULATED_DUMPSYS = """
  NotificationRecord(0x07f2a3e0: pkg=com.taobao.idlefish user=UserHandle{0} id=21001 tag=chat priority=2 key=0|com.taobao.idlefish|21001|chat|10086)
    uid=10123
    when=1779800000000
    flags=0x0010
    sound=default
    defaults=0x00000001
    flags=0x00000010
    color=0xff4a90d9
    vis=PRIVATE
    semFlags=0x00000000
    semanticAction=0
    category=msg
    groupKey=com.taobao.idlefish.chat
    channelId=chat_message
    android.title=买家已付款
    android.text=订单号: order_2026052615001234，金额: 1299.00元
    android.subText=闲鱼
    android.tickerText=买家已付款
    android.bigText=买家已付款，订单号: order_2026052615001234，金额: 1299.00元，等待卖家发货

  NotificationRecord(0x07f2a3e1: pkg=com.taobao.idlefish user=UserHandle{0} id=21002 tag=chat priority=2 key=0|com.taobao.idlefish|21002|chat|10087)
    uid=10123
    when=1779800001000
    flags=0x0010
    android.title=买家发来新消息
    android.text=你好，请问什么时候发货？
    android.subText=闲鱼
    android.bigText=你好，请问什么时候发货？我这边比较着急用。

  NotificationRecord(0x07f2a3e2: pkg=com.taobao.idlefish user=UserHandle{0} id=21003 tag=chat priority=2 key=0|com.taobao.idlefish|21003|chat|10088)
    uid=10123
    when=1779800002000
    android.title=退款申请
    android.text=买家申请退款: 订单 order_refund_20260526_001
    android.subText=闲鱼

  NotificationRecord(0x07f2a3e3: pkg=com.tencent.mm user=UserHandle{0} id=22001 tag=null priority=0 key=0|com.tencent.mm|22001|null|10089)
    android.title=微信消息
    android.text=你好
"""

print("=" * 55)
print("  ADB 通知解析测试")
print("=" * 55)

# ── 1. 测试 ADB 检测 ──
from source_app.app.message_listener import (
    check_adb_available, check_device_connected,
    _parse_notifications, on_message,
)

print("\n[1] ADB 环境检测:")
ok, msg = check_adb_available()
print(f"    ADB 可用: {ok} ({msg})")
if ok:
    ok2, info = check_device_connected()
    print(f"    设备连接: {ok2} ({info})")
else:
    print(f"    (无可用的 ADB，使用模拟数据进行测试)")

# ── 2. 解析模拟通知 ──
print("\n[2] 解析模拟通知 (3条闲鱼 + 1条微信):")
messages = _parse_notifications(SIMULATED_DUMPSYS, "idlefish")
print(f"    闲鱼消息: {len(messages)} 条")

for i, msg in enumerate(messages):
    print(f"\n    消息 {i+1}:")
    print(f"      thread_key: {msg['thread_key']}")
    print(f"      source:     {msg['source']}")
    print(f"      text:       {msg['text'][:60]}...")
    print(f"      message_key: {msg['message_key']}")

checks = [
    ("过滤微信消息(仅3条闲鱼)", len(messages) == 3),
    ("消息1包含'买家已付款'", "买家已付款" in messages[0]["text"]),
    ("消息2包含'什么时候发货'", "什么时候发货" in messages[1]["text"]),
    ("消息3包含'退款申请'", "退款申请" in messages[2]["text"]),
    ("所有消息 source=notification_bar", all(m["source"] == "notification_bar" for m in messages)),
]

all_ok = True
for label, ok in checks:
    mark = "PASS" if ok else "FAIL"
    if not ok: all_ok = False
    print(f"    [{mark}] {label}")

# ── 3. 去重验证 ──
print("\n[3] 去重验证:")
again = _parse_notifications(SIMULATED_DUMPSYS, "idlefish")
print(f"    再次解析: {len(again)} 条 (预期: 0)")
checks2 = [
    ("重复通知已过滤", len(again) == 0),
]
for label, ok in checks2:
    mark = "PASS" if ok else "FAIL"
    if not ok: all_ok = False
    print(f"    [{mark}] {label}")

# ── 4. 消息标准化 ──
print("\n[4] 消息标准化 (on_message):")
if messages:
    result = on_message(messages[0])
    print(f"    message_key: {result['message_key']}")
    print(f"    thread_key:  {result['thread_key']}")
    print(f"    text length: {len(result['text'])}")

# ── 5. 端到端: 标准化消息 → 处理 → 上传 ──
print("\n[5] 端到端流程 (消息 → 分类 → 上传):")

# 启动服务器
from relay_server.demo_server import main as http_main, HOST, PORT
t = threading.Thread(target=http_main, daemon=True)
t.start()

# 等待服务器就绪
for _ in range(10):
    try:
        urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=2)
        print("    服务器已就绪")
        break
    except Exception:
        time.sleep(0.5)
else:
    print("    服务器启动超时")

from source_app.app.main import handle_incoming_message

results = []
for msg in messages:
    r = handle_incoming_message(msg)
    results.append(r)

# 纯文本消息 -> 直接上传
text_results = [r for r in results if r.get("type") == "text"]
print(f"    纯文本事件: {len(text_results)} 条")

# 验证服务器接收
import urllib.request
resp = urllib.request.urlopen(f"http://{HOST}:{PORT}/stats").read()
stats = json.loads(resp.decode())
print(f"    服务器事件总数: {stats['total_events']}")

checks3 = [
    ("服务器收到事件", stats["total_events"] > 0, f"实际 {stats['total_events']}"),
    ("3条消息全部处理", len(results) == 3),
]
for label, ok, *detail in checks3:
    d = detail[0] if detail else ""
    mark = "PASS" if ok else "FAIL"
    if not ok: all_ok = False
    print(f"    [{mark}] {label} {d}")

print(f"\n{'='*55}")
print(f"  {'全部通过!' if all_ok else '存在失败项'}")
print(f"{'='*55}")
