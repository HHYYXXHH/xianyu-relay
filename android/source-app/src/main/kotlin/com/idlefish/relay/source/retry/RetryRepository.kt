package com.idlefish.relay.source.retry

import com.idlefish.relay.source.data.AppDatabase
import com.idlefish.relay.source.data.entity.DeadLetterEntity
import com.idlefish.relay.source.data.entity.RetryItemEntity
import org.json.JSONObject

class RetryRepository(private val db: AppDatabase) {

    suspend fun enqueue(event: JSONObject, retryCount: Int = 0) {
        val eventId = event.optString("event_id") ?: return

        val delaySeconds = minOf(2L * (1L shl retryCount), 300L)
        val now = System.currentTimeMillis()

        db.retryItemDao().insert(
            RetryItemEntity(
                eventId = eventId,
                eventJson = event.toString(),
                retryCount = retryCount,
                firstFailure = now,
                lastFailure = now,
                nextRetryAt = now + delaySeconds * 1000,
            )
        )
    }

    suspend fun getDueItems(): List<RetryItemEntity> {
        return db.retryItemDao().getDueItems()
    }

    suspend fun getAllItems(): List<RetryItemEntity> {
        return db.retryItemDao().getAll()
    }

    suspend fun updateRetryInfo(eventId: String, count: Int, nextRetryAt: Long) {
        db.retryItemDao().updateRetryInfo(eventId, count, System.currentTimeMillis(), nextRetryAt)
    }

    suspend fun remove(eventId: String) {
        val items = db.retryItemDao().getAll()
        val item = items.find { it.eventId == eventId } ?: return
        db.retryItemDao().delete(item)
    }

    suspend fun moveToDeadLetter(entity: RetryItemEntity) {
        db.deadLetterDao().insert(
            DeadLetterEntity(
                eventId = entity.eventId,
                eventJson = entity.eventJson,
                retryCount = entity.retryCount,
                lastFailure = entity.lastFailure,
            )
        )
        db.retryItemDao().delete(entity)
    }

    suspend fun getStats(): Pair<Int, Int> {
        val pending = db.retryItemDao().getPendingCount()
        val dead = db.deadLetterDao().getDeadLetterCount()
        return pending to dead
    }
}
