package com.idlefish.relay.shared.model

import kotlinx.serialization.Serializable
import org.json.JSONObject

@Serializable
data class EventRecord(
    val eventId: String,
    val eventType: String,
    val contentType: String,
    val source: String,
    val timestamp: String,
    val threadKey: String,
    val messageKey: String,
    val summary: String,
    val ocrStatus: String = "not_needed",
    val uploadStatus: String = "pending",
    val needReceiverAttention: Boolean = false,
    val notifyReceiver: Boolean = false,
    val checksum: String = "",
    val imageRefs: List<String> = emptyList(),
    val contentText: String = "",
    val imageOcrText: String = "",
    val ocrError: String = "",
    val errorCode: String = "",
    val errorMessage: String = "",
    val retryCount: Int = 0,
    val attentionStatus: String = "",
    val handledAt: String = "",
) {
    companion object {
        fun fromJson(json: JSONObject): EventRecord {
            val imageRefsList = mutableListOf<String>()
            val arr = json.optJSONArray("image_refs")
            if (arr != null) {
                for (i in 0 until arr.length()) {
                    arr.optString(i)?.let { imageRefsList.add(it) }
                }
            }

            return EventRecord(
                eventId = json.optString("event_id"),
                eventType = json.optString("event_type"),
                contentType = json.optString("content_type"),
                source = json.optString("source"),
                timestamp = json.optString("timestamp"),
                threadKey = json.optString("thread_key"),
                messageKey = json.optString("message_key"),
                summary = json.optString("summary"),
                ocrStatus = json.optString("ocr_status", "not_needed"),
                uploadStatus = json.optString("upload_status", "pending"),
                needReceiverAttention = json.optBoolean("need_receiver_attention"),
                notifyReceiver = json.optBoolean("notify_receiver"),
                checksum = json.optString("checksum"),
                imageRefs = imageRefsList,
                contentText = json.optString("content_text"),
                imageOcrText = json.optString("image_ocr_text"),
                ocrError = json.optString("ocr_error"),
                errorCode = json.optString("error_code"),
                errorMessage = json.optString("error_message"),
                retryCount = json.optInt("retry_count", 0),
                attentionStatus = json.optString("attention_status"),
                handledAt = json.optString("handled_at"),
            )
        }
    }
}
