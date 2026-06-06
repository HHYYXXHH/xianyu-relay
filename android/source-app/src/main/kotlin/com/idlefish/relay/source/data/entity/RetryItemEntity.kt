package com.idlefish.relay.source.data.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "retry_queue")
data class RetryItemEntity(
    @PrimaryKey
    val eventId: String,
    @ColumnInfo(name = "event_json")
    val eventJson: String,
    @ColumnInfo(name = "retry_count")
    val retryCount: Int = 0,
    @ColumnInfo(name = "first_failure")
    val firstFailure: Long = System.currentTimeMillis(),
    @ColumnInfo(name = "last_failure")
    val lastFailure: Long = System.currentTimeMillis(),
    @ColumnInfo(name = "next_retry_at")
    val nextRetryAt: Long = 0,
)
