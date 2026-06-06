package com.idlefish.relay.receiver.data.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.idlefish.relay.receiver.data.entity.EventEntity

@Dao
interface EventDao {

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(event: EventEntity)

    @Query("SELECT * FROM received_events ORDER BY received_at DESC")
    suspend fun getAll(): List<EventEntity>

    @Query("SELECT * FROM received_events WHERE event_id = :eventId LIMIT 1")
    suspend fun getByEventId(eventId: String): EventEntity?

    @Query("SELECT COUNT(*) FROM received_events")
    suspend fun getCount(): Int
}
