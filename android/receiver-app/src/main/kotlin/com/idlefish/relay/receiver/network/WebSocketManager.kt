package com.idlefish.relay.receiver.network

import android.os.Handler
import android.os.Looper
import android.util.Log
import com.idlefish.relay.shared.model.EventRecord
import com.idlefish.relay.shared.network.ServerConfig
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class WebSocketManager(
    private val onEventReceived: (EventRecord) -> Unit,
    private val onConnectionChanged: (Boolean) -> Unit,
) {
    private var webSocket: WebSocket? = null
    private var reconnectDelay = 1L
    private var shouldReconnect = true
    private val handler = Handler(Looper.getMainLooper())

    private val client = OkHttpClient.Builder()
        .pingInterval(30, TimeUnit.SECONDS)
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    fun connect(wsUrl: String) {
        shouldReconnect = true
        doConnect(wsUrl)
    }

    private fun doConnect(wsUrl: String) {
        val request = Request.Builder().url(wsUrl).build()
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                Log.i(TAG, "WS 已连接")
                reconnectDelay = 1L
                onConnectionChanged(true)
            }

            override fun onMessage(ws: WebSocket, text: String) {
                try {
                    val msg = JSONObject(text)
                    when (msg.optString("type")) {
                        "connected" -> Log.i(TAG, "已注册: ${msg.optString("client_id")}")
                        "event" -> {
                            val eventJson = msg.optJSONObject("event") ?: return
                            val event = EventRecord.fromJson(eventJson)
                            onEventReceived(event)
                            // 发送 ACK 回执
                            ws.send("""{"type":"ack","event_id":"${event.eventId}"}""")
                            Log.d(TAG, "ACK 已发送: ${event.eventId}")
                        }
                        "ping" -> ws.send("""{"type":"pong"}""")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "消息解析失败", e)
                }
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WS 连接失败: ${t.message}")
                onConnectionChanged(false)
                scheduleReconnect()
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "WS 已关闭: $code $reason")
                onConnectionChanged(false)
                scheduleReconnect()
            }
        })
    }

    private fun scheduleReconnect() {
        if (!shouldReconnect) return
        val delay = reconnectDelay
        Log.i(TAG, "${delay}s 后重连")
        handler.postDelayed({
            reconnectDelay = minOf(reconnectDelay * 2, 30)
            if (shouldReconnect) {
                doConnect(ServerConfig.host.let { "ws://${it}:${ServerConfig.wsPort}" })
            }
        }, delay * 1000)
    }

    fun disconnect() {
        shouldReconnect = false
        webSocket?.close(1000, "客户端关闭")
    }

    companion object {
        private const val TAG = "WebSocketMgr"
    }
}
