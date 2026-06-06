"""Tesseract 中文 OCR 测试。
验证: 中文截图 → card_ocr_handler.run_local_ocr → 结构化解析 → 事件构建
"""

import os, sys
sys.path.insert(0, ".")
os.makedirs("data/test_images", exist_ok=True)
os.makedirs("data/tessdata", exist_ok=True)

# 检查中文包
has_cn = os.path.exists("data/tessdata/chi_sim.traineddata")
print(f"中文语言包: {'已安装 (data/tessdata/)' if has_cn else '未安装'}")

# ── 生成中文闲鱼卡片 ──
from PIL import Image, ImageDraw, ImageFont

W, H = 420, 720
img = Image.new("RGB", (W, H), color=(248, 248, 248))
draw = ImageDraw.Draw(img)

try:
    font_title = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 26)
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 20)
    font_s = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 15)
except Exception:
    font_title = font = font_s = ImageFont.load_default()

draw.rectangle([0, 0, W, 55], fill=(255, 80, 0))
draw.text((25, 14), "闲鱼 - 交易详情", fill="white", font=font_title)

draw.rectangle([20, 75, W-20, 140], fill="white", outline=(230, 230, 230))
draw.text((35, 85), "交易状态: 买家已付款", fill=(0, 160, 0), font=font)
draw.text((35, 112), "等待卖家发货", fill=(140, 140, 140), font=font_s)

y = 160
draw.rectangle([20, y, W-20, y+175], fill="white", outline=(230, 230, 230))
draw.text((35, y+10), "订单信息", fill=(60, 60, 60), font=font)
draw.text((35, y+42), "订单编号: order_2026052615005678", fill=(90, 90, 90), font=font_s)
draw.text((35, y+68), "商品名称: Apple AirPods Pro 第二代", fill=(90, 90, 90), font=font_s)
draw.text((35, y+94), "商品价格: 1299.00元", fill=(90, 90, 90), font=font_s)
draw.text((35, y+120), "购买数量: 1件", fill=(90, 90, 90), font=font_s)
draw.text((35, y+146), "运费: 免运费", fill=(90, 90, 90), font=font_s)

y = 355
draw.rectangle([20, y, W-20, y+80], fill="white", outline=(230, 230, 230))
draw.text((35, y+10), "支付信息", fill=(60, 60, 60), font=font)
draw.text((35, y+38), "实付款: 1299.00元", fill=(220, 40, 40), font=font_title)
draw.text((35, y+62), "支付时间: 2026年5月26日 15:30", fill=(120, 120, 120), font=font_s)

y = 455
draw.rectangle([20, y, W-20, y+85], fill="white", outline=(230, 230, 230))
draw.text((35, y+10), "收货地址", fill=(60, 60, 60), font=font)
draw.text((35, y+38), "张三  13812345678", fill=(90, 90, 90), font=font_s)
draw.text((35, y+60), "浙江省杭州市余杭区五常街道", fill=(90, 90, 90), font=font_s)

path_cn = "data/test_images/xianyu_card_cn.png"
img.save(path_cn, "PNG")

# ── 用 card_ocr_handler 的 OCR 链路 ──
print("=" * 55)
print("  Tesseract 中文 OCR 测试")
print("=" * 55)

from source_app.app.card_ocr_handler import run_local_ocr, parse_ocr_result, build_card_event

ocr_text = run_local_ocr(path_cn)
print(f"\nOCR 原始输出 ({len(ocr_text)} 字符):")
print(ocr_text[:500])

# ── 结构化解析 ──
parsed = parse_ocr_result(ocr_text)
print(f"\n─── 解析结果 ───")
print(f"  状态:    {parsed['status']}")
print(f"  订单号:  {parsed['order_id']}")
print(f"  金额:    {parsed['amount']}")
print(f"  时间:    {parsed['trade_time']}")
print(f"  退款号:  {parsed['refund_id']}")
print(f"  摘要:    {parsed['summary']}")

# ── 验证 ──
print(f"\n─── 验证 ───")
checks = [
    ("订单号正确", "order_2026052615005678" in parsed["order_id"]),
    ("金额有值", parsed["amount"] != ""),
    ("时间正确", "2026" in parsed["trade_time"]),
    ("摘要非空", len(parsed["summary"]) > 0),
]
all_ok = True
for label, ok in checks:
    mark = "PASS" if ok else "FAIL"
    if not ok: all_ok = False
    print(f"  [{mark}] {label}")

# ── 语言检测 ──
cn_chars = sum(1 for c in ocr_text if '一' <= c <= '鿿')
print(f"\n  检测到中文字符: {cn_chars} 个")
if cn_chars > 5:
    print(f"  中文识别: 正常")
else:
    print(f"  中文识别: 较少（可能需要完整版 chi_sim）")

print(f"\n{'='*55}")
print(f"  {'中文 OCR 测试通过!' if all_ok else '部分字段待优化'}")
print(f"{'='*55}")
