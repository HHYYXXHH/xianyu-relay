package com.idlefish.relay.source.handler

import android.graphics.Bitmap
import com.idlefish.relay.shared.model.ErrorCodes
import com.idlefish.relay.source.parser.NotificationParser.ParsedMessage
import com.idlefish.relay.source.upload.EventUploader
import com.idlefish.relay.source.upload.ImageUploader
import org.json.JSONObject

class NormalImageHandler(
    private val eventBuilder: EventBuilder,
    private val eventUploader: EventUploader,
    private val imageUploader: ImageUploader,
) {

    suspend fun handle(message: ParsedMessage, bitmap: Bitmap, filename: String): JSONObject {
        val imageResult = imageUploader.uploadImage(bitmap, filename)

        if (!imageResult.ok) {
            val errorCode = if (imageResult.status in setOf(408, 429, 500, 502, 503, 504)) {
                ErrorCodes.UPLOAD_TIMEOUT
            } else {
                ErrorCodes.UPLOAD_FAILED
            }
            val failedEvent = eventBuilder.buildUploadFailureEvent(message, listOf(filename), errorCode)
            eventUploader.uploadEvent(failedEvent)
            return failedEvent
        }

        val event = eventBuilder.buildNormalEvent(message, listOf(filename))
        eventUploader.uploadEvent(event)
        return event
    }
}
