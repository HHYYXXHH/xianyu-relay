package com.idlefish.relay.source.data.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.idlefish.relay.source.data.entity.MessageEntity

@Dao
interface MessageDao {

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(message: MessageEntity)

    @Query("SELECT * FROM messages ORDER BY created_at DESC")
    suspend fun getAll(): List<MessageEntity>

    @Query("SELECT * FROM messages WHERE event_id = :eventId LIMIT 1")
    suspend fun getByEventId(eventId: String): MessageEntity?

    @Query("UPDATE messages SET uploaded = 1, uploaded_at = :uploadedAt WHERE event_id = :eventId")
    suspend fun markUploaded(eventId: String, uploadedAt: Long)

    @Query("DELETE FROM messages WHERE uploaded = 1 AND created_at < :before")
    suspend fun deleteUploadedBefore(before: Long)

    @Query("SELECT * FROM messages WHERE uploaded = 0 ORDER BY created_at ASC")
    suspend fun getUnuploaded(): List<MessageEntity>

    @Query("SELECT COUNT(*) FROM messages WHERE uploaded = 0")
    suspend fun getUnuploadedCount(): Int

    @Query("SELECT COUNT(*) FROM messages")
    suspend fun getTotalCount(): Int
}
