package com.idlefish.relay.source

import android.app.Application
import android.app.PendingIntent
import android.content.SharedPreferences
import androidx.preference.PreferenceManager
import com.idlefish.relay.shared.network.ServerConfig

class IdlefishRelayApp : Application() {

    lateinit var prefs: SharedPreferences
        private set

    /** 待处理的OCR任务：无障碍服务就绪时自动消费 */
    data class OcrTask(
        val contentIntent: PendingIntent?,
        val sellerName: String,
        val createdAt: Long = System.currentTimeMillis(),
    )

    @Volatile
    var pendingOcrTask: OcrTask? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        prefs = PreferenceManager.getDefaultSharedPreferences(this)
        ServerConfig.loadFromPreferences(prefs)
    }

    companion object {
        lateinit var instance: IdlefishRelayApp
            private set
    }
}
