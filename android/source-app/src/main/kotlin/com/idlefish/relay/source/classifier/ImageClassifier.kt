package com.idlefish.relay.source.classifier

import android.graphics.Bitmap

object ImageClassifier {

    enum class Classification {
        CARD_IMAGE,
        NORMAL_IMAGE,
        UNKNOWN_IMAGE,
    }

    fun classify(bitmap: Bitmap): Classification {
        val w = bitmap.width
        val h = bitmap.height
        if (w <= 0 || h <= 0) return Classification.UNKNOWN_IMAGE

        val ratio = w.toFloat() / h.toFloat()

        // 竖屏截图: 0.35 <= ratio <= 0.7 且高度 > 600
        if (ratio in 0.35f..0.7f && h > 600) {
            return Classification.CARD_IMAGE
        }

        // 正方形: 0.75 <= ratio <= 1.3
        if (ratio in 0.75f..1.3f) {
            return Classification.NORMAL_IMAGE
        }

        // 横屏: ratio > 1.5
        if (ratio > 1.5f) {
            return Classification.NORMAL_IMAGE
        }

        // 高窄图: height > 1000 且 ratio < 0.8
        if (h > 1000 && ratio < 0.8f) {
            return Classification.CARD_IMAGE
        }

        return Classification.UNKNOWN_IMAGE
    }
}
