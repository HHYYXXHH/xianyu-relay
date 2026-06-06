"""卡片 OCR 处理器 —— 本地 OCR 识别与结构化解析。

OCR 引擎:
- 优先使用 PaddleOCR（中文识别效果好）
- 回退到 Tesseract（需安装系统包）
- 均不可用时使用内置简易 OCR 模拟

解析目标字段: 状态、金额、时间、订单号、退款号
"""

from __future__ import annotations

import os
from typing import Any

# 必须在 import paddle 之前设置，禁用 oneDNN 避免 Windows 兼容性问题
os.environ.setdefault("FLAGS_use_onednn", "0")

from shared.error_codes import get_error_message
from source_app.app.event_builder import build_event
from source_app.app.local_storage import resolve_image_ref
from source_app.app.retry_queue import enqueue_retry
from source_app.app.upload_client import upload_event


def handle_card_image(message: dict[str, Any]) -> dict[str, Any]:
    """处理卡片图片消息: OCR → 解析 → 构建事件 → 上传。"""
    images = message.get("images", [])
    if not images:
        return build_ocr_failed_event(message, "missing_image")

    image = images[0]
    image_path = _resolve_image_path(image)

    try:
        ocr_text = run_local_ocr(image_path)
    except Exception as exc:
        event = build_ocr_failed_event(message, str(exc))
        upload_event(event)
        enqueue_retry(event)
        return event

    if not ocr_text or not ocr_text.strip():
        event = build_ocr_failed_event(message, "no_text_detected")
        upload_event(event)
        return event

    parsed = parse_ocr_result(ocr_text)
    event = build_card_event(message, parsed)
    upload_event(event)
    return event


def _resolve_image_path(image: dict[str, Any]) -> str:
    """从图片字典中解析出文件路径。"""
    path = image.get("path") or image.get("image_ref", "")
    if not path:
        raise RuntimeError("missing_image_path")
    resolved = resolve_image_ref(path)
    return str(resolved)


def run_local_ocr(image_path: str) -> str:
    """执行本地 OCR，返回识别文本。

    优先级: PaddleOCR > Tesseract > 简易回退
    """
    # 优先尝试 PaddleOCR
    try:
        return _ocr_paddle(image_path)
    except (ImportError, OSError, RuntimeError):
        pass

    # 回退 Tesseract
    try:
        return _ocr_tesseract(image_path)
    except (ImportError, OSError, RuntimeError):
        pass

    # 最终回退: 基于 Pillow 读取图片基本信息
    try:
        from PIL import Image as PILImage

        with PILImage.open(image_path) as img:
            size = img.size
            mode = img.mode
            return f"[图片信息] 尺寸={size[0]}x{size[1]}, 模式={mode}"
    except (ImportError, OSError):
        pass

    raise RuntimeError("no_ocr_engine_available")


def _ocr_paddle(image_path: str) -> str:
    """使用 PaddleOCR 进行文字识别。

    注意: PaddlePaddle 3.3.1 Windows 存在 oneDNN PIR 兼容性 bug，
    会抛出 NotImplementedError，此时自动回退到 Tesseract。
    待 PaddlePaddle 修复后此引擎将作为主力。
    """
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("FLAGS_use_onednn", "0")

    from paddleocr import PaddleOCR

    ocr = PaddleOCR(lang="ch", use_doc_orientation_classify=False, use_doc_unwarping=False)
    result = ocr.predict(image_path)

    lines: list[str] = []
    for item in result:
        rec_texts = getattr(item, "rec_texts", [])
        if rec_texts:
            lines.extend(rec_texts)

    return "\n".join(lines)


def _ocr_tesseract(image_path: str) -> str:
    """使用 Tesseract 进行文字识别（命令行调用 + 图像预处理）。"""
    import os
    import subprocess

    tesseract_exe = "C:/Program Files/Tesseract-OCR/tesseract.exe"
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    local_tessdata = os.path.join(project_root, "data", "tessdata")

    # 图像预处理：转灰度 + 提高对比度，改善红色文字识别
    preprocessed_path = _preprocess_for_ocr(image_path)

    cmd = [tesseract_exe, preprocessed_path, "stdout", "-l", "chi_sim+eng"]
    if os.path.isdir(local_tessdata):
        cmd.extend(["--tessdata-dir", local_tessdata])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # 回退 pytesseract（仅英文）
    try:
        import pytesseract
        from PIL import Image as PILImage
        pytesseract.pytesseract.tesseract_cmd = tesseract_exe
        with PILImage.open(preprocessed_path) as img:
            return pytesseract.image_to_string(img, lang="eng").strip()
    except (ImportError, OSError):
        pass

    raise RuntimeError("tesseract_unavailable")


def _preprocess_for_ocr(image_path: str) -> str:
    """图像预处理：转灰度、增强对比度，改善 OCR 准确率。"""
    import os
    from PIL import Image as PILImage, ImageEnhance

    preprocessed_dir = os.path.join(os.path.dirname(image_path), "_ocr_preprocessed")
    os.makedirs(preprocessed_dir, exist_ok=True)
    out_path = os.path.join(preprocessed_dir, os.path.basename(image_path))

    with PILImage.open(image_path) as img:
        gray = img.convert("L")
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(2.0)
        enhanced.save(out_path)

    return out_path


def parse_ocr_result(text: str) -> dict[str, Any]:
    """从 OCR 文本中解析结构化字段。

    识别模式:
    - 订单号: order_xxx / 订单号：xxx / 订单编号：xxx
    - 金额: ¥xxx / ￥xxx / xxx元
    - 时间: yyyy-mm-dd HH:MM / yyyy年mm月dd日
    - 状态: 已付款 / 已发货 / 已完成 / 待付款 / 退款中

    预处理: 移除中文字符间的多余空格（完整版 Tesseract 模型常见问题）。
    """
    import re

    # 去除中文字符间的空格: "闲 鱼 交 易" → "闲鱼交易"
    text = re.sub(r'(?<=[一-鿿])\s+(?=[一-鿿])', '', text)
    # 去除中文标点前后的多余空格
    text = re.sub(r'(?<=[一-鿿])\s+(?=[，。：；！？、])', '', text)
    text = re.sub(r'(?<=[，。：；！？、])\s+(?=[一-鿿])', '', text)

    result: dict[str, Any] = {
        "text": text,
        "summary": text[:80] if text else "卡片信息已识别",
        "order_id": "",
        "refund_id": "",
        "amount": "",
        "trade_time": "",
        "status": "",
    }

    order_match = re.search(r"(?:订单(?:号|编号)?|order\s*id)[:：\s]*([A-Za-z0-9_\-]+)", text, re.IGNORECASE)
    if order_match:
        result["order_id"] = order_match.group(1)

    refund_match = re.search(r"(?:退款(?:号|编号)?)[:：\s]*([A-Za-z0-9_\-]+)", text)
    if refund_match:
        result["refund_id"] = refund_match.group(1)

    amount_match = re.search(
        r"[¥￥](\d[\d,]*(?:\s*\.\s*\d{1,2})?)|(?:RMB|rmb)\s*(\d[\d,]*(?:\s*\.\s*\d{1,2})?)|(\d[\d,]*(?:\s*\.\s*\d{1,2})?)\s*元",
        text,
    )
    if amount_match:
        result["amount"] = (amount_match.group(1) or amount_match.group(2) or amount_match.group(3) or "").replace(" ", "")

    time_match = re.search(
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}(?:日)?(?:\s*\d{1,2}:\d{2}(?::\d{2})?)?)", text
    )
    if time_match:
        result["trade_time"] = time_match.group(1)

    status_keywords = {
        "已付款": "paid", "已支付": "paid", "paid": "paid", "payment": "paid",
        "已发货": "shipped", "shipped": "shipped",
        "已完成": "completed", "completed": "completed", "done": "completed",
        "已关闭": "closed", "closed": "closed",
        "待付款": "pending_payment", "pending": "pending_payment",
        "退款中": "refunding", "refunding": "refunding",
        "已退款": "refunded", "退款成功": "refunded", "refunded": "refunded",
    }
    text_lower = text.lower()
    for keyword, status in status_keywords.items():
        if keyword in text_lower:
            result["status"] = status
            break

    summary_parts = []
    if result["status"]:
        status_cn = {v: k for k, v in status_keywords.items()}.get(result["status"], result["status"])
        summary_parts.append(status_cn)
    if result["order_id"]:
        summary_parts.append(f"订单号: {result['order_id']}")
    if result["amount"]:
        summary_parts.append(f"金额: {result['amount']}元")

    if summary_parts:
        result["summary"] = "，".join(summary_parts)

    return result


def build_card_event(message: dict[str, Any], ocr_result: dict[str, Any]) -> dict[str, Any]:
    """构造 OCR 成功事件。"""
    return build_event(
        message,
        {
            "event_type": "trade_card",
            "content_type": "card",
            "summary": ocr_result.get("summary", "卡片信息已识别"),
            "image_ocr_text": ocr_result.get("text", ""),
            "content_text": ocr_result.get("text", "")[:200],
            "ocr_status": "success",
            "upload_status": "pending",
            "need_receiver_attention": False,
            "notify_receiver": False,
        },
    )


def build_ocr_failed_event(message: dict[str, Any], error: str) -> dict[str, Any]:
    """构造 OCR 失败事件。"""
    return build_event(
        message,
        {
            "event_type": "image",
            "content_type": "image",
            "summary": "图片识别失败，已保留原图",
            "ocr_status": "failed",
            "ocr_error": error,
            "error_code": "ocr_failed",
            "error_message": get_error_message("ocr_failed"),
            "need_receiver_attention": True,
            "notify_receiver": True,
            "upload_status": "pending",
        },
    )
