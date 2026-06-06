package com.idlefish.relay.source.data.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "messages",
    indices = [Index(value = ["event_id"], unique = true),
        Index(value = ["uploaded"])],
)
data class MessageEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "event_id")
    val eventId: String,

    @ColumnInfo(name = "event_json")
    val eventJson: String,

    @ColumnInfo(name = "uploaded")
    val uploaded: Boolean = false,

    @ColumnInfo(name = "uploaded_at")
    val uploadedAt: Long? = null,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),
)
