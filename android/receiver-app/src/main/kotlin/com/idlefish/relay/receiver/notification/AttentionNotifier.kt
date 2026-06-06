package com.idlefish.relay.receiver.notification

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import com.idlefish.relay.receiver.IdlefishReceiverApp
import com.idlefish.relay.receiver.R
import com.idlefish.relay.receiver.ui.MainActivity
import com.idlefish.relay.shared.model.EventRecord

object AttentionNotifier {

    private var notificationId = 2000

    fun notify(context: Context, event: EventRecord) {
        val intent = Intent(context, MainActivity::class.java).apply {
            putExtra("event_id", event.eventId)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            notificationId,
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

        val title = buildString {
            append("需要人工处理")
            if (event.ocrStatus == "failed") append(" - OCR识别失败")
            if (event.uploadStatus == "failed") append(" - 图片上传失败")
        }

        val notification = NotificationCompat.Builder(context, IdlefishReceiverApp.CHANNEL_ATTENTION)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title)
            .setContentText(event.summary)
            .setStyle(NotificationCompat.BigTextStyle().bigText(event.summary))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(notificationId++, notification)
    }
}
