package com.idlefish.relay.shared.model

object ErrorCodes {
    const val UPLOAD_TIMEOUT = "upload_timeout"
    const val UPLOAD_FAILED = "upload_failed"
    const val OCR_FAILED = "ocr_failed"
    const val INVALID_PAYLOAD = "invalid_payload"
    const val SERVER_ERROR = "server_error"

    fun getMessage(code: String): String = when (code) {
        UPLOAD_TIMEOUT -> "图片上传超时，请检查网络或稍后重试"
        UPLOAD_FAILED -> "图片上传失败，请检查网络或稍后重试"
        OCR_FAILED -> "图片识别失败，已保留原图"
        INVALID_PAYLOAD -> "请求体不合法"
        SERVER_ERROR -> "服务端处理异常"
        else -> "未知错误"
    }
}
