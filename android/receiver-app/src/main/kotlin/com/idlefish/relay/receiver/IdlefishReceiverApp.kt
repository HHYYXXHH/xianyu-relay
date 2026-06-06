package com.idlefish.relay.receiver

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.idlefish.relay.shared.network.ServerConfig

class IdlefishReceiverApp : Application() {

    override fun onCreate() {
        super.onCreate()
        instance = this
        ServerConfig.loadFromPreferences(getSharedPreferences("receiver_prefs", MODE_PRIVATE))
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ATTENTION,
                "需要关注的事件",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = "OCR失败或上传失败时提醒"
            }
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(channel)
        }
    }

    companion object {
        const val CHANNEL_ATTENTION = "attention_events"
        lateinit var instance: IdlefishReceiverApp
            private set
    }
}
