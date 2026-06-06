package com.idlefish.relay.shared.schema

object Constants {
    val SUPPORTED_CONTENT_TYPES = setOf("text", "image", "card")
    val SUPPORTED_OCR_STATUS = setOf("not_needed", "pending", "success", "failed")
    val SUPPORTED_UPLOAD_STATUS = setOf("pending", "success", "failed")

    val REQUIRED_FIELDS = listOf(
        "event_id", "event_type", "content_type", "source", "timestamp",
        "thread_key", "message_key", "summary", "ocr_status",
        "notify_receiver", "need_receiver_attention", "upload_status", "checksum",
    )
}
