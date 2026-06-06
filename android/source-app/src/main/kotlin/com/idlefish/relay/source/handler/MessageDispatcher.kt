package com.idlefish.relay.source.handler

import android.content.Context
import android.graphics.BitmapFactory
import com.idlefish.relay.source.classifier.ImageClassifier
import com.idlefish.relay.source.data.AppDatabase
import com.idlefish.relay.source.data.entity.MessageEntity
import com.idlefish.relay.source.ocr.TesseractOcrEngine
import com.idlefish.relay.source.parser.NotificationParser.ParsedMessage
import com.idlefish.relay.source.service.NotificationMonitorService
import com.idlefish.relay.source.upload.EventUploader
import com.idlefish.relay.source.upload.ImageUploader
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

class MessageDispatcher {

    private val eventBuilder = EventBuilder()
    private val eventUploader = EventUploader()
    private val imageUploader = ImageUploader()
    private var cardHandler: CardOcrHandler? = null

    private fun getCardHandler(context: Context): CardOcrHandler {
        if (cardHandler == null) {
            val ocrEngine = TesseractOcrEngine.getInstance(context)
            cardHandler = CardOcrHandler(ocrEngine, eventBuilder, eventUploader)
        }
        return cardHandler!!
    }

    suspend fun dispatch(message: ParsedMessage) = withContext(Dispatchers.IO) {
        val context = com.idlefish.relay.source.IdlefishRelayApp.instance
        val dao = AppDatabase.getInstance(context).messageDao()

        if (message.imageUris.isEmpty() && message.text.isBlank()) {
            NotificationMonitorService.addLog("空消息，跳过")
            return@withContext
        }

        // 仅文本（无图片）
        if (message.imageUris.isEmpty()) {
            val event = eventBuilder.buildFromBase(message, mapOf(
                "event_type" to "message",
                "content_type" to "text",
                "content_text" to message.text,
            ))
            uploadEvent(dao, event)
            return@withContext
        }

        // 有图片 → 逐一分类处理
        for ((index, uri) in message.imageUris.withIndex()) {
            val bitmap = try {
                val stream = context.contentResolver.openInputStream(uri)
                BitmapFactory.decodeStream(stream)
            } catch (e: Exception) {
                android.util.Log.e(TAG, "无法加载图片: $uri", e)
                continue
            }

            if (bitmap == null) continue

            val classification = ImageClassifier.classify(bitmap)
            val filename = "${message.messageKey}_${index}.jpg"

            when (classification) {
                ImageClassifier.Classification.NORMAL_IMAGE -> {
                    val result = imageUploader.uploadImage(bitmap, filename)
                    if (!result.ok) {
                        val errorCode = if (result.status in setOf(408, 429, 500, 502, 503, 504)) {
                            com.idlefish.relay.shared.model.ErrorCodes.UPLOAD_TIMEOUT
                        } else {
                            com.idlefish.relay.shared.model.ErrorCodes.UPLOAD_FAILED
                        }
                        val failed = eventBuilder.buildUploadFailureEvent(message, listOf(filename), errorCode)
                        uploadEvent(dao, failed)
                    } else {
                        val event = eventBuilder.buildNormalEvent(message, listOf(filename))
                        uploadEvent(dao, event)
                    }
                }
                else -> {
                    val handler = getCardHandler(context)
                    val result = handler.handle(message, bitmap, listOf(filename))
                    uploadEvent(dao, result)
                }
            }
            bitmap.recycle()
        }

        if (message.text.isNotBlank()) {
            val textEvent = eventBuilder.buildFromBase(message, mapOf(
                "event_type" to "message",
                "content_type" to "text",
                "content_text" to message.text,
            ))
            uploadEvent(dao, textEvent)
        }
    }

    private suspend fun uploadEvent(dao: com.idlefish.relay.source.data.dao.MessageDao, event: JSONObject) {
        val eventId = event.optString("event_id")
        val now = System.currentTimeMillis()

        // 先存本地 (uploaded=false)
        dao.insert(
            MessageEntity(
                eventId = eventId,
                eventJson = event.toString(),
                uploaded = false,
                createdAt = now,
            )
        )

        NotificationMonitorService.addLog("上传: $eventId")
        val result = eventUploader.uploadEvent(event)
        NotificationMonitorService.addLog("上传结果: ok=${result.ok}, status=${result.status}")

        if (result.ok) {
            dao.markUploaded(eventId, System.currentTimeMillis())
            NotificationMonitorService.addLog("已标记上传成功: $eventId")
        } else {
            NotificationMonitorService.addLog("上传失败: ${result.body.take(100)}")
        }
    }

    companion object {
        private const val TAG = "MsgDispatcher"
    }
}
