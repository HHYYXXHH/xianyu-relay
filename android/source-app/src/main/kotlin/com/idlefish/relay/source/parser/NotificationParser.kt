package com.idlefish.relay.source.parser

import android.net.Uri
import android.service.notification.StatusBarNotification
import com.idlefish.relay.shared.util.TimestampUtil
import com.idlefish.relay.source.service.NotificationMonitorService

class NotificationParser {

    data class ParsedMessage(
        val messageKey: String,
        val threadKey: String,
        val timestamp: String,
        val source: String,
        val title: String,
        val text: String,
        val imageUris: List<Uri>,
        val rawKey: String,
    )

    fun parse(sbn: StatusBarNotification): ParsedMessage? {
        val extras = sbn.notification.extras

        // 诊断：输出所有 extras key
        val allKeys = extras.keySet()
        val extrasLog = StringBuilder("Extras: ")
        for (key in allKeys) {
            val value = extras.get(key)
            val valueStr = when (value) {
                is CharSequence -> value.toString().take(60)
                else -> value?.toString()?.take(60) ?: "null"
            }
            extrasLog.append("$key=$valueStr; ")
        }
        NotificationMonitorService.addLog(extrasLog.toString())

        val title = extras.getCharSequence("android.title")?.toString() ?: ""
        val text = extras.getCharSequence("android.text")?.toString() ?: ""
        val bigText = extras.getCharSequence("android.bigText")?.toString() ?: ""
        val summaryText = extras.getCharSequence("android.summaryText")?.toString() ?: ""
        val subText = extras.getCharSequence("android.subText")?.toString() ?: ""
        val infoText = extras.getCharSequence("android.infoText")?.toString() ?: ""
        val template = extras.getString("android.template") ?: ""
        val allLines = extras.getCharSequenceArray("android.textLines")?.joinToString("\n") ?: ""

        val fullText = buildString {
            if (title.isNotBlank()) { append("标题:"); appendLine(title) }
            if (text.isNotBlank()) { append("内容:"); appendLine(text) }
            if (bigText.isNotBlank()) { append("大文本:"); appendLine(bigText) }
            if (summaryText.isNotBlank()) { append("摘要:"); appendLine(summaryText) }
            if (subText.isNotBlank()) { append("副标题:"); appendLine(subText) }
            if (allLines.isNotBlank()) { append("多行:"); appendLine(allLines) }
        }.trim()

        if (title.isBlank() && fullText.isBlank()) return null

        val whenMs = sbn.notification.`when`
        val timestamp = if (whenMs > 0) TimestampUtil.format(whenMs) else TimestampUtil.now()

        val messageKey = sbn.key?.split("|")?.lastOrNull() ?: System.currentTimeMillis().toString()
        val imageUris = extractImageUris(sbn)

        return ParsedMessage(
            messageKey = "notif_$messageKey",
            threadKey = sbn.packageName,
            timestamp = timestamp,
            source = "notification_bar",
            title = title,
            text = fullText,
            imageUris = imageUris,
            rawKey = sbn.key ?: "",
        )
    }

    private fun extractImageUris(sbn: StatusBarNotification): List<Uri> {
        val uris = mutableListOf<Uri>()
        val extras = sbn.notification.extras

        // 尝试从 EXTRA_PICTURE 获取大图
        val picture = extras.get("android.picture")
        if (picture != null) {
            // 大图以 Bitmap 形式传递，需单独处理
            // 此处记录，Bitmap 由 MessageDispatcher 处理
        }

        // 尝试从 Wearable 扩展获取图片
        val pages = extras.get("android.wearable.EXTENSIONS")
        // 简化处理：通过 content URI scheme 搜索
        return uris
    }
}
