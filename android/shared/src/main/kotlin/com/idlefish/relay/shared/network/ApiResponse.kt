package com.idlefish.relay.shared.model

import kotlinx.serialization.Serializable

@Serializable
data class ApiResponse(
    val ok: Boolean,
    val status: Int,
    val body: String = "",
)

@Serializable
data class EventAcceptedResponse(
    val status: String,
    val eventId: String,
    val pushed: Boolean = false,
    val wsClients: Int = 0,
    val wsDelivered: Boolean = false,
)

@Serializable
data class EventRejectedResponse(
    val status: String,
    val eventId: String,
    val missingFields: List<String> = emptyList(),
)

@Serializable
data class ImageUploadResponse(
    val status: String,
    val url: String = "",
    val filename: String = "",
    val size: Long = 0,
    val checksum: String = "",
)
