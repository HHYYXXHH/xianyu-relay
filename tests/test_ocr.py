"""真实 OCR 测试脚本。

用 PIL 生成仿真闲鱼交易卡片截图，测试完整 OCR 链路:
  run_local_ocr → parse_ocr_result → build_card_event
"""

import os
import sys

sys.path.insert(0, ".")

# ── 1. 生成仿真闲鱼交易卡片 ──
print("=" * 55)
print("  PaddleOCR 真实测试 —— 闲鱼交易卡片识别")
print("=" * 55)

from PIL import Image, ImageDraw, ImageFont

W, H = 420, 680
img = Image.new("RGB", (W, H), color=(245, 245, 245))
draw = ImageDraw.Draw(img)

# 尝试加载中文字体
font_paths = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/simkai.ttf",
]
font = None
font_small = None
for fp in font_paths:
    if os.path.exists(fp):
        try:
            font = ImageFont.truetype(fp, 22)
            font_small = ImageFont.truetype(fp, 16)
            font_title = ImageFont.truetype(fp, 28)
            print(f"使用字体: {os.path.basename(fp)}")
            break
        except (OSError, IOError):
            continue

if font is None:
    font = ImageFont.load_default()
    font_small = font
    font_title = font
    print("使用默认字体（中文可能无法渲染）")

# ── 绘制卡片界面 ──
# 顶部标题栏
draw.rectangle([0, 0, W, 50], fill=(255, 102, 0))
draw.text((20, 12), "闲鱼 - 交易详情", fill=(255, 255, 255), font=font_title)

# 状态区
draw.rectangle([20, 70, W-20, 130], fill=(255, 255, 255), outline=(220, 220, 220))
draw.text((40, 82), "交易状态: 买家已付款", fill=(34, 139, 34), font=font)
draw.text((40, 108), "等待卖家发货", fill=(120, 120, 120), font=font_small)

# 订单信息区
draw.rectangle([20, 150, W-20, 310], fill=(255, 255, 255), outline=(220, 220, 220))
draw.text((40, 162), "订单信息", fill=(51, 51, 51), font=font)
draw.text((40, 195), "订单编号: order_2026052614001234", fill=(80, 80, 80), font=font_small)
draw.text((40, 220), "商品名称: Apple AirPods Pro 2代", fill=(80, 80, 80), font=font_small)
draw.text((40, 245), "商品价格: ¥1,299.00", fill=(80, 80, 80), font=font_small)
draw.text((40, 270), "购买数量: 1", fill=(80, 80, 80), font=font_small)
draw.text((40, 295), "运费: ¥0.00（包邮）", fill=(80, 80, 80), font=font_small)

# 金额区
draw.rectangle([20, 330, W-20, 400], fill=(255, 255, 255), outline=(220, 220, 220))
draw.text((40, 342), "支付信息", fill=(51, 51, 51), font=font)
draw.text((40, 372), "实付款: ¥1,299.00元", fill=(220, 50, 50), font=font_title)
draw.text((40, 392), "支付时间: 2026年5月26日 14:30", fill=(120, 120, 120), font=font_small)

# 收货地址
draw.rectangle([20, 420, W-20, 500], fill=(255, 255, 255), outline=(220, 220, 220))
draw.text((40, 432), "收货地址", fill=(51, 51, 51), font=font)
draw.text((40, 460), "张三  13812345678", fill=(80, 80, 80), font=font_small)
draw.text((40, 482), "浙江省杭州市余杭区五常街道", fill=(80, 80, 80), font=font_small)

# 底部按钮区
draw.rectangle([20, 520, W-20, 570], fill=(255, 255, 255), outline=(220, 220, 220))
draw.rectangle([W//2+10, 530, W-40, 555], fill=(255, 102, 0))
draw.text((W//2+30, 533), "立即发货", fill=(255, 255, 255), font=font_small)

# 保存
os.makedirs("data/test_images", exist_ok=True)
card_path = "data/test_images/xianyu_card.png"
img.save(card_path, "PNG")
print(f"\n仿真闲鱼卡片已生成: {card_path} ({W}x{H})")

# ── 2. 生成普通聊天图片（不含文字，靠尺寸模拟） ──
chat_img = Image.new("RGB", (600, 800), color=(50, 50, 50))
chat_draw = ImageDraw.Draw(chat_img)
for i in range(20):
    y = 40 + i * 38
    w = [280, 350, 200, 400, 180, 320, 260, 380, 220, 310,
         290, 340, 240, 370, 210, 330, 270, 390, 250, 300][i]
    color = (70, 180, 120) if i % 2 == 0 else (60, 60, 60)
    chat_draw.rounded_rectangle([20 if i % 2 == 0 else W-20-w, y, (20+w) if i % 2 == 0 else W-20, y+28],
                                radius=10, fill=color)

chat_path = "data/test_images/chat_screenshot.png"
chat_img.save(chat_path, "PNG")
print(f"仿真聊天截图已生成: {chat_path} ({chat_img.width}x{chat_img.height})")

# ── 3. 图片分类测试 ──
print("\n─── 图片分类测试 ───")
from source_app.app.image_classifier import classify_single_image

r1 = classify_single_image({"path": card_path, "width": W, "height": H})
print(f"交易卡片: {r1}  (预期: card_image)")

r2 = classify_single_image({"path": chat_path, "width": 600, "height": 800})
print(f"聊天截图: {r2}  (预期: card_image, 因为竖屏>800)")

r3 = classify_single_image({"type": "normal", "width": 400, "height": 400})
print(f"普通图片: {r3}  (预期: normal_image)")

# ── 4. OCR 测试 ──
print("\n─── OCR 识别测试 ──")
from source_app.app.card_ocr_handler import run_local_ocr, parse_ocr_result, build_card_event, build_ocr_failed_event

try:
    ocr_text = run_local_ocr(card_path)
    print(f"OCR 引擎: PaddleOCR")
    print(f"识别结果:\n{ocr_text[:500]}")
except RuntimeError as e:
    print(f"OCR 引擎回退: {e}")
    ocr_text = ""

# ── 5. 结构化解析测试 ──
print("\n─── 结构化解析测试 ──")

test_text = """交易状态: 买家已付款
订单编号: order_2026052614001234
商品名称: Apple AirPods Pro 2代
实付款: ¥1,299.00元
支付时间: 2026年5月26日 14:30
收货地址: 浙江省杭州市余杭区五常街道"""

parsed = parse_ocr_result(test_text)
print(f"  状态:   {parsed['status']}")
print(f"  订单号: {parsed['order_id']}")
print(f"  金额:   {parsed['amount']}元")
print(f"  时间:   {parsed['trade_time']}")
print(f"  摘要:   {parsed['summary']}")

# ── 6. 事件构建测试 ──
print("\n─── 事件构建测试 ──")

base_msg = {
    "event_id": "evt_ocr_test_001",
    "message_key": "msg_ocr_001",
    "thread_key": "thread_buyer_123",
    "timestamp": "2026-05-26 14:30:00",
    "images": [{"path": card_path}],
    "image_refs": [card_path],
    "text": "",
}

if ocr_text and ocr_text.strip():
    event = build_card_event(base_msg, parse_ocr_result(ocr_text))
    print("OCR 成功事件:")
else:
    event = build_ocr_failed_event(base_msg, "no_text_detected" if ocr_text is not None else str(e))
    print("OCR 失败事件（兜底）:")

print(f"  event_type:      {event['event_type']}")
print(f"  ocr_status:      {event['ocr_status']}")
print(f"  notify_receiver: {event['notify_receiver']}")
print(f"  need_attention:  {event['need_receiver_attention']}")
print(f"  summary:         {event['summary']}")
if event.get("content_text"):
    print(f"  content_text:    {event['content_text'][:100]}")

# ── 7. 汇总 ──
print()
print("=" * 55)
print("  OCR 测试完成")
print("=" * 55)
