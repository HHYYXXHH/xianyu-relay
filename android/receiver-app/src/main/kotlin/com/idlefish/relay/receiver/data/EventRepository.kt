package com.idlefish.relay.receiver.data

import android.content.Context
import com.idlefish.relay.receiver.data.entity.EventEntity
import com.idlefish.relay.shared.model.EventRecord
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class EventRepository {

    private val events = LinkedHashMap<String, EventUiModel>()
    private val handledSet = mutableSetOf<String>()
    private val _eventsFlow = MutableStateFlow<List<EventUiModel>>(emptyList())
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var db: AppDatabase? = null

    val eventsFlow: StateFlow<List<EventUiModel>> = _eventsFlow.asStateFlow()

    fun init(context: Context) {
        db = AppDatabase.getInstance(context)
        scope.launch {
            val saved = db!!.eventDao().getAll()
            for (entity in saved) {
                val record = try {
                    EventRecord.fromJson(org.json.JSONObject(entity.eventJson))
                } catch (e: Exception) {
                    continue
                }
                events[record.eventId] = EventUiModel.from(record, handledSet.contains(record.eventId))
            }
            _eventsFlow.value = events.values.toList()
        }
    }

    @Synchronized
    fun addEvent(event: EventRecord) {
        val uiModel = EventUiModel.from(event, handledSet.contains(event.eventId))
        events[event.eventId] = uiModel
        _eventsFlow.value = events.values.toList()

        // 持久化到 Room
        val currentDb = db ?: return
        scope.launch {
            currentDb.eventDao().insert(
                EventEntity(
                    eventId = event.eventId,
                    eventJson = org.json.JSONObject().apply {
                        put("event_id", event.eventId)
                        put("event_type", event.eventType)
                        put("content_type", event.contentType)
                        put("source", event.source)
                        put("timestamp", event.timestamp)
                        put("thread_key", event.threadKey)
                        put("message_key", event.messageKey)
                        put("summary", event.summary)
                        put("ocr_status", event.ocrStatus)
                        put("upload_status", event.uploadStatus)
                        put("need_receiver_attention", event.needReceiverAttention)
                        put("notify_receiver", event.notifyReceiver)
                        put("checksum", event.checksum)
                        put("content_text", event.contentText)
                        put("image_ocr_text", event.imageOcrText)
                        put("ocr_error", event.ocrError)
                        put("error_code", event.errorCode)
                        put("error_message", event.errorMessage)
                        val arr = org.json.JSONArray()
                        event.imageRefs.forEach { arr.put(it) }
                        put("image_refs", arr)
                    }.toString()
                )
            )
        }
    }

    @Synchronized
    fun markHandled(eventId: String) {
        handledSet.add(eventId)
        events[eventId]?.let {
            events[eventId] = it.copy(isHandled = true)
        }
        _eventsFlow.value = events.values.toList()
    }

    @Synchronized
    fun getEvent(eventId: String): EventUiModel? = events[eventId]

    @Synchronized
    fun clear() {
        events.clear()
        handledSet.clear()
        _eventsFlow.value = emptyList()
    }
}

data class EventUiModel(
    val eventId: String,
    val eventType: String,
    val contentType: String,
    val summary: String,
    val needAttention: Boolean,
    val isHandled: Boolean,
    val ocrStatus: String,
    val uploadStatus: String,
    val imageRefs: List<String>,
    val contentText: String,
    val imageOcrText: String,
    val ocrError: String,
    val errorCode: String,
    val errorMessage: String,
    val timestamp: String,
    val threadKey: String,
) {
    companion object {
        fun from(event: EventRecord, isHandled: Boolean = false): EventUiModel = EventUiModel(
            eventId = event.eventId,
            eventType = event.eventType,
            contentType = event.contentType,
            summary = event.summary,
            needAttention = event.needReceiverAttention,
            isHandled = isHandled,
            ocrStatus = event.ocrStatus,
            uploadStatus = event.uploadStatus,
            imageRefs = event.imageRefs,
            contentText = event.contentText,
            imageOcrText = event.imageOcrText,
            ocrError = event.ocrError,
            errorCode = event.errorCode,
            errorMessage = event.errorMessage,
            timestamp = event.timestamp,
            threadKey = event.threadKey,
        )
    }
}
