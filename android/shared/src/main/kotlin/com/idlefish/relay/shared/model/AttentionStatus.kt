package com.idlefish.relay.shared.model

import kotlinx.serialization.Serializable

@Serializable
data class AttentionStatusRequest(
    val eventId: String,
    val attentionStatus: String = "handled",
    val handledAt: String,
)

@Serializable
data class AttentionStatusResponse(
    val status: String,
)
