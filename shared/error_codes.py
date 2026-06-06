"""错误码与错误文案映射。"""

from __future__ import annotations

ERROR_MESSAGES = {
    "upload_timeout": "图片上传超时，请检查网络或稍后重试",
    "upload_failed": "图片上传失败，请检查网络或稍后重试",
    "ocr_failed": "图片识别失败，已保留原图",
    "invalid_payload": "请求体不合法",
    "server_error": "服务端处理异常",
}


def get_error_message(code: str) -> str:
    """根据错误码返回文案。"""
    return ERROR_MESSAGES.get(code, "未知错误")
