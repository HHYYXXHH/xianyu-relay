"""图片加载器 —— 支持本地文件、URL 和 base64 编码图片的加载。

特性:
- 本地文件: 直接读取并可选缩略图
- URL: 下载并缓存到本地
- 返回 PIL Image 对象供渲染使用
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from receiver_app.app.config import IMAGE_CACHE_DIR


def ensure_cache_dir() -> None:
    IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_image(image_ref: str) -> dict[str, Any]:
    """加载图片，返回统一结构。

    返回:
        {
            "ok": bool,
            "path": str,        # 本地路径
            "width": int,
            "height": int,
            "format": str,
            "error": str,       # 仅失败时
        }
    """
    ref = image_ref.strip()

    if not ref:
        return {"ok": False, "path": "", "error": "empty_ref"}

    if ref.startswith(("http://", "https://")):
        return _load_from_url(ref)

    if ref.startswith("data:"):
        return _load_from_base64(ref)

    return _load_from_file(ref)


def _load_from_file(path_str: str) -> dict[str, Any]:
    """从本地文件加载图片。"""
    path = Path(path_str)
    if not path.exists():
        return {"ok": False, "path": str(path), "error": "file_not_found"}

    info = _get_image_info(path)
    if info is None:
        return {"ok": False, "path": str(path), "error": "invalid_image"}

    return {"ok": True, "path": str(path), **info}


def _load_from_url(url: str) -> dict[str, Any]:
    """从 URL 下载图片并缓存。"""
    import hashlib
    import urllib.request

    ensure_cache_dir()
    cache_name = hashlib.sha256(url.encode()).hexdigest()[:16] + ".jpg"
    cache_path = IMAGE_CACHE_DIR / cache_name

    if cache_path.exists():
        info = _get_image_info(cache_path)
        if info:
            return {"ok": True, "path": str(cache_path), "cached": True, **info}

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            cache_path.write_bytes(resp.read())
    except (urllib.error.URLError, OSError) as exc:
        return {"ok": False, "path": "", "error": str(exc)}

    info = _get_image_info(cache_path)
    if info is None:
        return {"ok": False, "path": str(cache_path), "error": "download_invalid_image"}

    return {"ok": True, "path": str(cache_path), "cached": False, **info}


def _load_from_base64(data_uri: str) -> dict[str, Any]:
    """解码 base64 数据 URI 并保存。"""
    import base64

    ensure_cache_dir()

    try:
        header, b64_data = data_uri.split(",", 1)
        image_bytes = base64.b64decode(b64_data)
    except (ValueError, base64.binascii.Error) as exc:
        return {"ok": False, "path": "", "error": f"base64_decode_failed: {exc}"}

    import hashlib

    cache_name = hashlib.sha256(image_bytes).hexdigest()[:16] + ".jpg"
    cache_path = IMAGE_CACHE_DIR / cache_name
    cache_path.write_bytes(image_bytes)

    info = _get_image_info(cache_path)
    if info is None:
        return {"ok": False, "path": str(cache_path), "error": "base64_invalid_image"}

    return {"ok": True, "path": str(cache_path), **info}


def _get_image_info(path: Path) -> dict[str, Any] | None:
    """读取图片基础信息。"""
    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format or "unknown",
            }
    except (ImportError, OSError):
        pass

    try:
        import imghdr

        fmt = imghdr.what(str(path))
        if fmt:
            return {"width": 0, "height": 0, "format": fmt}
    except ImportError:
        pass

    return None


def load_thumbnail(image_ref: str, max_size: int = 200) -> dict[str, Any]:
    """加载图片缩略图。"""
    result = load_image(image_ref)
    if not result["ok"]:
        return result

    try:
        from PIL import Image as PILImage

        with PILImage.open(result["path"]) as img:
            img.thumbnail((max_size, max_size))
            thumb_path = Path(result["path"]).with_suffix(".thumb.jpg")
            img.save(str(thumb_path), "JPEG")
            result["thumb_path"] = str(thumb_path)
    except ImportError:
        result["thumb_path"] = result["path"]

    return result
