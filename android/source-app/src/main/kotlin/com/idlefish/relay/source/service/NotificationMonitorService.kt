package com.idlefish.relay.source.service

import android.content.Intent
import android.provider.Settings
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import com.idlefish.relay.source.handler.MessageDispatcher
import com.idlefish.relay.source.parser.NotificationParser
import kotlinx.coroutines.*

class NotificationMonitorService : NotificationListenerService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val parser = NotificationParser()
    private val dispatcher = MessageDispatcher()
    private val seenKeys = LinkedHashSet<String>(500)

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return
        val pkg = sbn.packageName.lowercase()
        if (!pkg.contains("idlefish") && !pkg.contains("taobao")) return

        val key = sbn.key ?: return
        synchronized(seenKeys) {
            if (key in seenKeys) return
            seenKeys.add(key)
            if (seenKeys.size > 500) seenKeys.take(300).forEach { seenKeys.remove(it) }
        }

        val parsed = parser.parse(sbn) ?: return
        val sellerName = parsed.title
        addLog("闲鱼: $sellerName | ${parsed.text.take(100)}")

        // 上传通知摘要
        scope.launch { dispatcher.dispatch(parsed) }

        // contentIntent打开闲鱼
        val contentIntent = sbn.notification.contentIntent
        addLog("打开闲鱼…")
        try {
            contentIntent?.send()
        } catch (_: Exception) {
            try {
                startActivity(packageManager.getLaunchIntentForPackage("com.taobao.idlefish")?.apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                })
            } catch (_: Exception) {}
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {}
    override fun onListenerConnected() { addLog("通知监听 ✓") }
    override fun onListenerDisconnected() {
        addLog("通知监听断连")
        requestRebind(android.content.ComponentName(this, NotificationMonitorService::class.java))
    }

    companion object {
        private const val MAX_LOG = 150
        private val _log = mutableListOf<String>()
        val log: List<String> @Synchronized get() = _log.toList()

        @Synchronized
        fun addLog(msg: String) {
            val ts = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault()).format(java.util.Date())
            _log.add("$ts $msg")
            if (_log.size > MAX_LOG) _log.removeAt(0)
            android.util.Log.d("NotifMonitor", msg)
        }

        fun isNotificationListenerEnabled(ctx: android.content.Context): Boolean {
            val s = Settings.Secure.getString(ctx.contentResolver, "enabled_notification_listeners") ?: return false
            return s.contains(ctx.packageName ?: "")
        }
    }
}
