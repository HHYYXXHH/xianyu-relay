"""PaddleOCR 修复测试 —— 验证 oneDNN 绕过方案。"""
import os, sys
sys.path.insert(0, ".")
os.environ["FLAGS_use_onednn"] = "0"

# 生成测试图
from PIL import Image, ImageDraw, ImageFont
os.makedirs("data/test_images", exist_ok=True)

img = Image.new("RGB", (420, 600), color=(248, 248, 248))
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 22)
    font_s = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 16)
except Exception:
    font = font_s = ImageFont.load_default()

draw.rectangle([0, 0, 420, 50], fill=(255, 80, 0))
draw.text((20, 12), "闲鱼 - 交易详情", fill="white", font=font)
draw.rectangle([20, 70, 400, 130], fill="white", outline=(220, 220, 220))
draw.text((35, 82), "交易状态: 买家已付款", fill=(0, 160, 0), font=font)
draw.rectangle([20, 150, 400, 300], fill="white", outline=(220, 220, 220))
draw.text((35, 165), "订单编号: order_2026052615009999", fill=(90, 90, 90), font=font_s)
draw.text((35, 195), "商品价格: 1299.00元", fill=(90, 90, 90), font=font_s)
draw.text((35, 225), "支付时间: 2026年5月26日 16:00", fill=(90, 90, 90), font=font_s)
draw.rectangle([20, 320, 400, 380], fill="white", outline=(220, 220, 220))
draw.text((35, 335), "实付款: 1299.00元", fill=(220, 40, 40), font=font)
draw.rectangle([20, 400, 400, 470], fill="white", outline=(220, 220, 220))
draw.text((35, 415), "收货地址: 浙江省杭州市余杭区", fill=(90, 90, 90), font=font_s)

img_path = "data/test_images/xianyu_card_paddle.png"
img.save(img_path)
print(f"测试图: {img_path}")

# PaddleOCR
print("初始化 PaddleOCR...")
from paddleocr import PaddleOCR
ocr = PaddleOCR(lang="ch", use_doc_orientation_classify=False, use_doc_unwarping=False)
print("识别中...")
result = ocr.predict(os.path.abspath(img_path))

lines = []
for item in result:
    rec_texts = getattr(item, "rec_texts", [])
    if rec_texts:
        lines.extend(rec_texts)

text = "\n".join(lines)
cn = sum(1 for c in text if "一" <= c <= "鿿")
print(f"\nPaddleOCR 识别: {len(text)} 字符, {cn} 个中文")
print(text[:600])

# 结构化解析
from source_app.app.card_ocr_handler import parse_ocr_result
parsed = parse_ocr_result(text)
print(f"\n解析: status={parsed['status']} order={parsed['order_id']} amount={parsed['amount']}")

checks = [
    ("中文识别成功", cn > 10),
    ("状态=paid", parsed["status"] == "paid"),
    ("订单号正确", "order_2026052615009999" in parsed.get("order_id", "")),
    ("金额有值", parsed["amount"] != ""),
]
all_ok = True
for label, ok in checks:
    mark = "PASS" if ok else "FAIL"
    if not ok: all_ok = False
    print(f"  [{mark}] {label}")

print(f"\n{'='*50}")
print(f"  {'PaddleOCR 修复成功!' if all_ok else '部分字段待优化'}")
print(f"{'='*50}")
