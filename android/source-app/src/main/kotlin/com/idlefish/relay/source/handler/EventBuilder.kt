package com.idlefish.relay.source.handler

import com.idlefish.relay.shared.model.ErrorCodes
import com.idlefish.relay.shared.util.ChecksumUtil
import com.idlefish.relay.source.ocr.OcrResultParser
import com.idlefish.relay.source.parser.NotificationParser.ParsedMessage
import org.json.JSONArray
import org.json.JSONObject

class EventBuilder {

    fun buildFromBase(message: ParsedMessage, overrides: Map<String, Any?> = emptyMap()): JSONObject {
        return JSONObject().apply {
            put("event_id", overrides["event_id"] ?: "evt_${message.messageKey}")
            put("event_type", overrides["event_type"] ?: "message")
            put("content_type", overrides["content_type"] ?: "text")
            put("source", message.source)
            put("title", overrides["title"] ?: message.title)
            put("timestamp", message.timestamp)
            put("thread_key", message.threadKey)
            put("message_key", message.messageKey)
            put("summary", overrides["summary"] ?: message.text.take(80))
            put("ocr_status", overrides["ocr_status"] ?: "not_needed")
            put("upload_status", overrides["upload_status"] ?: "pending")
            put("need_receiver_attention", overrides["need_receiver_attention"] ?: false)
            put("notify_receiver", overrides["notify_receiver"] ?: true)
            put("checksum", overrides["checksum"] ?: ChecksumUtil.md5Short(message.text))
            put("image_refs", JSONArray((overrides["image_refs"] as? List<*>) ?: emptyList<String>()))
            put("content_text", overrides["content_text"] ?: "")
            put("image_ocr_text", overrides["image_ocr_text"] ?: "")
            put("ocr_error", overrides["ocr_error"] ?: "")
            put("error_code", overrides["error_code"] ?: "")
            put("error_message", overrides["error_message"] ?: "")
        }
    }

    fun buildNormalEvent(message: ParsedMessage, imageRefs: List<String>): JSONObject {
        return buildFromBase(message, mapOf(
            "event_type" to "image",
            "content_type" to "image",
            "summary" to "用户发送了图片",
            "ocr_status" to "not_needed",
            "need_receiver_attention" to false,
            "notify_receiver" to false,
            "image_refs" to imageRefs,
        ))
    }

    fun buildUploadFailureEvent(message: ParsedMessage, imageRefs: List<String>, errorCode: String): JSONObject {
        return buildFromBase(message, mapOf(
            "event_type" to "image",
            "content_type" to "image",
            "summary" to "普通图片上传失败",
            "ocr_status" to "not_needed",
            "upload_status" to "failed",
            "error_code" to errorCode,
            "error_message" to ErrorCodes.getMessage(errorCode),
            "need_receiver_attention" to true,
            "notify_receiver" to true,
            "image_refs" to imageRefs,
        ))
    }

    fun buildCardEvent(message: ParsedMessage, ocrResult: OcrResultParser.ParsedOcr, imageRefs: List<String>): JSONObject {
        return buildFromBase(message, mapOf(
            "event_type" to "trade_card",
            "content_type" to "card",
            "summary" to ocrResult.summary,
            "image_ocr_text" to ocrResult.text,
            "content_text" to ocrResult.text.take(200),
            "ocr_status" to "success",
            "need_receiver_attention" to false,
            "notify_receiver" to false,
            "image_refs" to imageRefs,
        ))
    }

    fun buildOcrFailedEvent(message: ParsedMessage, imageRefs: List<String>, error: String): JSONObject {
        return buildFromBase(message, mapOf(
            "event_type" to "image",
            "content_type" to "image",
            "summary" to "图片识别失败，已保留原图",
            "ocr_status" to "failed",
            "ocr_error" to error,
            "error_code" to ErrorCodes.OCR_FAILED,
            "error_message" to ErrorCodes.getMessage(ErrorCodes.OCR_FAILED),
            "need_receiver_attention" to true,
            "notify_receiver" to true,
            "image_refs" to imageRefs,
        ))
    }
}
