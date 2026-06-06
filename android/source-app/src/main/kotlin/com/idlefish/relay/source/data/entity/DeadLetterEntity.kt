package com.idlefish.relay.source.data.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "dead_letter")
data class DeadLetterEntity(
    @PrimaryKey
    val eventId: String,
    @ColumnInfo(name = "event_json")
    val eventJson: String,
    @ColumnInfo(name = "retry_count")
    val retryCount: Int,
    @ColumnInfo(name = "last_failure")
    val lastFailure: Long,
    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),
)
