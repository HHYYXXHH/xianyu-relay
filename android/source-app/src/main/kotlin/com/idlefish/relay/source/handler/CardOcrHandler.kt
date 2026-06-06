package com.idlefish.relay.source.handler

import android.graphics.Bitmap
import com.idlefish.relay.source.ocr.OcrResultParser
import com.idlefish.relay.source.ocr.TesseractOcrEngine
import com.idlefish.relay.source.parser.NotificationParser.ParsedMessage
import com.idlefish.relay.source.upload.EventUploader
import org.json.JSONObject

class CardOcrHandler(
    private val ocrEngine: TesseractOcrEngine,
    private val eventBuilder: EventBuilder,
    private val uploader: EventUploader,
) {

    suspend fun handle(
        message: ParsedMessage,
        bitmap: Bitmap,
        imageRefs: List<String>,
    ): JSONObject {
        return try {
            val ocrResult = ocrEngine.recognize(bitmap)

            if (!ocrResult.success || ocrResult.text.isBlank()) {
                val failedEvent = eventBuilder.buildOcrFailedEvent(
                    message, imageRefs, ocrResult.error.ifBlank { "no_text_detected" }
                )
                uploader.uploadEvent(failedEvent)
                failedEvent
            } else {
                val parsed = OcrResultParser.parse(ocrResult.text)
                val cardEvent = eventBuilder.buildCardEvent(message, parsed, imageRefs)
                uploader.uploadEvent(cardEvent)
                cardEvent
            }
        } catch (e: Exception) {
            val failedEvent = eventBuilder.buildOcrFailedEvent(
                message, imageRefs, e.message ?: "ocr_exception"
            )
            uploader.uploadEvent(failedEvent)
            failedEvent
        }
    }
}
