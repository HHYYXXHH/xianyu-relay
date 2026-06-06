"""尝试各种方式绕过 PaddlePaddle 3.x oneDNN 问题。"""
import os
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

# 方案1: 设置 KMP 环境变量
os.environ["KMP_SETTINGS"] = "0"
os.environ["OMP_NUM_THREADS"] = "1"

# 方案2: 在 import paddle 之前设置 FLAGS
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

import sys
sys.path.insert(0, ".")

from PIL import Image, ImageDraw, ImageFont
os.makedirs("data/test_images", exist_ok=True)

img = Image.new("RGB", (300, 200), color=(248, 248, 248))
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 20)
except:
    font = ImageFont.load_default()
draw.text((20, 80), "闲鱼交易 1299.00元", fill=(0, 0, 0), font=font)
img_path = "data/test_images/paddle_test.png"
img.save(img_path)

print("方案: KMP_SETTINGS=0 + FLAGS_use_onednn=0")

import paddle
print(f"Paddle version: {paddle.__version__}")

# 尝试通过 Config 禁用
try:
    config = paddle.inference.Config()
    config.disable_gpu()
    config.disable_glog_info()
    # 尝试禁用 MKLDNN/oneDNN
    try:
        config.disable_mkldnn()
        print("MKLDNN disabled via Config")
    except:
        print("disable_mkldnn not available")
    try:
        config.enable_mkldnn_int8({})
    except:
        pass
    print("Config approach attempted")
except Exception as e:
    print(f"Config error: {e}")

# 尝试 set_device
try:
    paddle.device.set_device('cpu')
    print("set_device('cpu') done")
except Exception as e:
    print(f"set_device error: {e}")

from paddleocr import PaddleOCR
print("Initializing PaddleOCR...")
ocr = PaddleOCR(lang="ch", use_doc_orientation_classify=False, use_doc_unwarping=False)
print("Running OCR...")

try:
    result = ocr.predict(os.path.abspath(img_path))
    lines = []
    for item in result:
        texts = getattr(item, "rec_texts", [])
        if texts:
            lines.extend(texts)
    if lines:
        print(f"PaddleOCR 成功! {len(lines)} 行: {lines[:5]}")
    else:
        print("无识别结果")
except Exception as e:
    print(f"OCR 失败: {type(e).__name__}: {e}")
