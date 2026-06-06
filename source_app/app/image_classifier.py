"""图片分类器 —— 基于图像属性的启发式分类。

分类策略:
- normal_image: 普通聊天图片（照片、表情等）
- card_image: 卡片类图片（交易截图、转账截图等）
- unknown_image: 无法判定，走保守 OCR 兜底

分类依据:
1. 图片尺寸与宽高比 —— 手机截图通常有特定的宽高比（9:16~19.5:9）
2. 文件大小 —— 截图类通常较大
3. 无法判定时返回 unknown_image，触发保守 OCR 处理
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def classify_images(images: list[dict[str, Any]]) -> list[str]:
    """对图片列表进行分类。"""
    return [classify_single_image(img) for img in images]


def classify_single_image(image: dict[str, Any]) -> str:
    """对单张图片分类。

    优先级:
    1. 显式 type 标记（来自上游系统）
    2. 基于图片文件属性的启发式分析
    3. 兜底返回 unknown_image
    """
    # 显式标记优先
    explicit_type = image.get("type", "")
    if explicit_type == "card":
        return "card_image"
    if explicit_type == "normal":
        return "normal_image"

    # 基于文件路径的启发式分析
    path = image.get("path") or image.get("image_ref", "")
    if path:
        try:
            return _classify_by_file(Path(path))
        except (OSError, IOError):
            pass

    # 基于宽高比（如果上游传了尺寸信息）
    width = image.get("width", 0)
    height = image.get("height", 0)
    if width > 0 and height > 0:
        return _classify_by_dimensions(width, height)

    # 无法判定，走保守 OCR 兜底
    return "unknown_image"


def _classify_by_file(path: Path) -> str:
    """通过文件属性分类。"""
    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as img:
            width, height = img.size
            return _classify_by_dimensions(width, height)
    except ImportError:
        pass

    return "unknown_image"


def _classify_by_dimensions(width: int, height: int) -> str:
    """基于图片尺寸分类。

    手机截图特征: 宽高比通常小于 1（竖屏），且高度较大。
    聊天图片特征: 宽高比接近 1 或更随机。
    """
    if width <= 0 or height <= 0:
        return "unknown_image"

    aspect_ratio = width / height

    # 竖屏截图: 宽度远小于高度 (9:16 ~ 0.56, 9:19.5 ~ 0.46)
    # 降低高度阈值到 600 以覆盖更多截图
    if 0.35 <= aspect_ratio <= 0.7 and height > 600:
        return "card_image"

    # 接近正方形的可能是产品图/普通图片
    if 0.75 <= aspect_ratio <= 1.3:
        return "normal_image"

    # 横屏图片不太可能是卡片
    if aspect_ratio > 1.5:
        return "normal_image"

    # 灰色地带：偏高且较窄 → 卡片
    if height > 1000 and aspect_ratio < 0.8:
        return "card_image"

    return "unknown_image"


def is_card_image(image: dict[str, Any]) -> bool:
    """便捷方法：判断单张图片是否为卡片类型。"""
    return classify_single_image(image) == "card_image"


def is_normal_image(image: dict[str, Any]) -> bool:
    """便捷方法：判断单张图片是否为普通类型。"""
    return classify_single_image(image) == "normal_image"
