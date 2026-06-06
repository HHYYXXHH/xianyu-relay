package com.idlefish.relay.receiver.service

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.idlefish.relay.receiver.IdlefishReceiverApp
import com.idlefish.relay.receiver.R
import com.idlefish.relay.receiver.network.WebSocketManager
import com.idlefish.relay.receiver.notification.AttentionNotifier
import com.idlefish.relay.receiver.data.EventRepository
import com.idlefish.relay.receiver.ui.MainActivity
import com.idlefish.relay.shared.network.ServerConfig
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class WebSocketService : Service() {

    private var webSocketManager: WebSocketManager? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = createForegroundNotification()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(FOREGROUND_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(FOREGROUND_ID, notification)
        }

        val repository = getRepository()
        repository.init(this)

        webSocketManager = WebSocketManager(
            onEventReceived = { event ->
                repository.addEvent(event)
                if (event.needReceiverAttention) {
                    AttentionNotifier.notify(this, event)
                }
            },
            onConnectionChanged = { connected ->
                _connectionState.value = connected
            },
        )

        webSocketManager?.connect("ws://${ServerConfig.host}:${ServerConfig.wsPort}")

        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        webSocketManager?.disconnect()
        super.onDestroy()
    }

    private fun createForegroundNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

        return NotificationCompat.Builder(this, IdlefishReceiverApp.CHANNEL_ATTENTION)
            .setContentTitle("闲鱼转发接收端")
            .setContentText("正在监听消息…")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    companion object {
        const val FOREGROUND_ID = 1001

        private var repository: EventRepository? = null

        private val _connectionState = MutableStateFlow(false)
        val connectionState: StateFlow<Boolean> = _connectionState.asStateFlow()

        @Synchronized
        fun getRepository(): EventRepository {
            if (repository == null) {
                repository = EventRepository()
            }
            return repository!!
        }
    }
}
