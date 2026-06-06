package com.idlefish.relay.shared.schema

import com.idlefish.relay.shared.model.EventRecord
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

object EventValidator {

    private val json = Json { ignoreUnknownKeys = true; coerceInputValues = true }

    fun validate(payload: JsonObject): Pair<Boolean, List<String>> {
        val missing = mutableListOf<String>()
        for (field in Constants.REQUIRED_FIELDS) {
            if (!payload.containsKey(field)) {
                missing.add(field)
            }
        }
        if (missing.isNotEmpty()) return false to missing

        val contentType = payload["content_type"]?.jsonPrimitive?.content ?: ""
        if (contentType !in Constants.SUPPORTED_CONTENT_TYPES) {
            return false to listOf("content_type 不合法: $contentType")
        }
        val ocrStatus = payload["ocr_status"]?.jsonPrimitive?.content ?: ""
        if (ocrStatus !in Constants.SUPPORTED_OCR_STATUS) {
            return false to listOf("ocr_status 不合法: $ocrStatus")
        }
        val uploadStatus = payload["upload_status"]?.jsonPrimitive?.content ?: ""
        if (uploadStatus !in Constants.SUPPORTED_UPLOAD_STATUS) {
            return false to listOf("upload_status 不合法: $uploadStatus")
        }
        return true to emptyList()
    }

    fun normalize(payload: JsonObject): EventRecord {
        val obj = payload.toMutableMap()

        obj.putIfAbsent("image_refs", JsonPrimitive(""))
        obj.putIfAbsent("content_text", JsonPrimitive(""))
        obj.putIfAbsent("image_ocr_text", JsonPrimitive(""))
        obj.putIfAbsent("error_code", JsonPrimitive(""))
        obj.putIfAbsent("error_message", JsonPrimitive(""))
        obj.putIfAbsent("ocr_error", JsonPrimitive(""))
        obj.putIfAbsent("retry_count", JsonPrimitive(0))
        obj.putIfAbsent("attention_status", JsonPrimitive(""))
        obj.putIfAbsent("handled_at", JsonPrimitive(""))

        // 规范化 boolean 字段
        val notify = obj["notify_receiver"]?.jsonPrimitive?.boolean ?: false
        val attention = obj["need_receiver_attention"]?.jsonPrimitive?.boolean ?: false

        return EventRecord(
            eventId = obj["event_id"]?.jsonPrimitive?.content ?: "",
            eventType = obj["event_type"]?.jsonPrimitive?.content ?: "message",
            contentType = obj["content_type"]?.jsonPrimitive?.content ?: "text",
            source = obj["source"]?.jsonPrimitive?.content ?: "chat_page",
            timestamp = obj["timestamp"]?.jsonPrimitive?.content ?: "",
            threadKey = obj["thread_key"]?.jsonPrimitive?.content ?: "",
            messageKey = obj["message_key"]?.jsonPrimitive?.content ?: "",
            summary = obj["summary"]?.jsonPrimitive?.content ?: "",
            ocrStatus = obj["ocr_status"]?.jsonPrimitive?.content ?: "not_needed",
            uploadStatus = obj["upload_status"]?.jsonPrimitive?.content ?: "pending",
            needReceiverAttention = attention,
            notifyReceiver = notify,
            checksum = obj["checksum"]?.jsonPrimitive?.content ?: "",
            imageRefs = emptyList(), // 从 array 中提取
            contentText = obj["content_text"]?.jsonPrimitive?.content ?: "",
            imageOcrText = obj["image_ocr_text"]?.jsonPrimitive?.content ?: "",
            ocrError = obj["ocr_error"]?.jsonPrimitive?.content ?: "",
            errorCode = obj["error_code"]?.jsonPrimitive?.content ?: "",
            errorMessage = obj["error_message"]?.jsonPrimitive?.content ?: "",
            retryCount = obj["retry_count"]?.jsonPrimitive?.content?.toIntOrNull() ?: 0,
            attentionStatus = obj["attention_status"]?.jsonPrimitive?.content ?: "",
            handledAt = obj["handled_at"]?.jsonPrimitive?.content ?: "",
        )
    }
}
