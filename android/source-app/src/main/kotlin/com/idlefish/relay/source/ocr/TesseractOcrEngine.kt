package com.idlefish.relay.source.ocr

import android.content.Context
import android.graphics.Bitmap
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class OcrResult(
    val success: Boolean,
    val text: String = "",
    val error: String = "",
)

/**
 * OCR 引擎接口。当前为内置桩实现，可替换为:
 * - tess-two: com.rmtheis:tess-two (TessBaseAPI)
 * - Google ML Kit: com.google.mlkit:text-recognition-chinese
 */
class TesseractOcrEngine(private val context: Context) {

    @Volatile
    private var initialized = false

    init {
        initialized = true
    }

    suspend fun recognize(bitmap: Bitmap): OcrResult = withContext(Dispatchers.Default) {
        if (!initialized) {
            return@withContext OcrResult(success = false, error = "ocr_engine_init_failed")
        }

        try {
            // 内置桩: 返回图片尺寸信息作为占位
            // 接入真实 OCR 引擎时替换此方法
            val w = bitmap.width
            val h = bitmap.height
            val placeholder = "图片尺寸: ${w}x${h}\n请接入 Tesseract (tess-two) 或 Google ML Kit 以启用真实 OCR"

            OcrResult(success = true, text = placeholder)
        } catch (e: Exception) {
            OcrResult(success = false, error = e.message ?: "ocr_exception")
        }
    }

    fun release() {}

    companion object {
        @Volatile
        private var instance: TesseractOcrEngine? = null

        fun getInstance(context: Context): TesseractOcrEngine {
            return instance ?: synchronized(this) {
                instance ?: TesseractOcrEngine(context.applicationContext).also { instance = it }
            }
        }
    }
}
