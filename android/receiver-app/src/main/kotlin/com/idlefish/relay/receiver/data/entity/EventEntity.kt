package com.idlefish.relay.receiver.data.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "received_events",
    indices = [Index(value = ["event_id"], unique = true)],
)
data class EventEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "event_id")
    val eventId: String,

    @ColumnInfo(name = "event_json")
    val eventJson: String,

    @ColumnInfo(name = "received_at")
    val receivedAt: Long = System.currentTimeMillis(),
)
