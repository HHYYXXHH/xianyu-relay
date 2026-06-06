package com.idlefish.relay.shared.network

object ApiEndpoints {
    fun eventsUrl(baseUrl: String) = "$baseUrl/events"
    fun imagesUrl(baseUrl: String) = "$baseUrl/images"
    fun imageDownloadUrl(baseUrl: String, filename: String) = "$baseUrl/images/$filename"
    fun attentionStatusUrl(baseUrl: String) = "$baseUrl/attention-status"
    fun wsUrl(host: String, wsPort: Int) = "ws://$host:$wsPort"
}
