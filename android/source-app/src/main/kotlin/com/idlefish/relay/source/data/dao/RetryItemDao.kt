package com.idlefish.relay.source.data.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.idlefish.relay.source.data.entity.DeadLetterEntity
import com.idlefish.relay.source.data.entity.RetryItemEntity

@Dao
interface RetryItemDao {
    @Query("SELECT * FROM retry_queue WHERE next_retry_at <= :now ORDER BY next_retry_at ASC")
    suspend fun getDueItems(now: Long = System.currentTimeMillis()): List<RetryItemEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(item: RetryItemEntity)

    @Query("UPDATE retry_queue SET retry_count = :count, last_failure = :lastFailure, next_retry_at = :nextRetryAt WHERE eventId = :eventId")
    suspend fun updateRetryInfo(eventId: String, count: Int, lastFailure: Long, nextRetryAt: Long)

    @Delete
    suspend fun delete(item: RetryItemEntity)

    @Query("SELECT COUNT(*) FROM retry_queue")
    suspend fun getPendingCount(): Int

    @Query("SELECT * FROM retry_queue ORDER BY next_retry_at ASC")
    suspend fun getAll(): List<RetryItemEntity>
}

@Dao
interface DeadLetterDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(item: DeadLetterEntity)

    @Query("SELECT COUNT(*) FROM dead_letter")
    suspend fun getDeadLetterCount(): Int

    @Delete
    suspend fun delete(item: DeadLetterEntity)

    @Query("SELECT * FROM dead_letter ORDER BY created_at DESC")
    suspend fun getAll(): List<DeadLetterEntity>
}
