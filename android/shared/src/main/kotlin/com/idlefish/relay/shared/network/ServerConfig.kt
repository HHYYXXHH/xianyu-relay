package com.idlefish.relay.shared.network

import android.content.SharedPreferences

object ServerConfig {
    private const val KEY_HOST = "server_host"
    private const val KEY_HTTP_PORT = "server_http_port"
    private const val KEY_WS_PORT = "server_ws_port"

    const val DEFAULT_HOST = "139.199.11.252"
    const val DEFAULT_HTTP_PORT = 9006
    const val DEFAULT_WS_PORT = 9007

    var host: String = DEFAULT_HOST
    var httpPort: Int = DEFAULT_HTTP_PORT
    var wsPort: Int = DEFAULT_WS_PORT

    fun httpBaseUrl(): String = "http://$host:$httpPort"

    fun loadFromPreferences(prefs: SharedPreferences) {
        host = prefs.getString(KEY_HOST, DEFAULT_HOST) ?: DEFAULT_HOST
        httpPort = prefs.getInt(KEY_HTTP_PORT, DEFAULT_HTTP_PORT)
        wsPort = prefs.getInt(KEY_WS_PORT, DEFAULT_WS_PORT)
    }

    fun saveToPreferences(prefs: SharedPreferences) {
        prefs.edit()
            .putString(KEY_HOST, host)
            .putInt(KEY_HTTP_PORT, httpPort)
            .putInt(KEY_WS_PORT, wsPort)
            .apply()
    }
}
