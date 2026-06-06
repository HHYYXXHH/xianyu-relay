package com.idlefish.relay.source.retry

import android.content.Context
import android.util.Log
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.idlefish.relay.source.data.AppDatabase
import com.idlefish.relay.source.upload.EventUploader
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class RetryWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    private val db = AppDatabase.getInstance(context)
    private val repository = RetryRepository(db)
    private val uploader = EventUploader()

    companion object {
        private const val TAG = "RetryWorker"
        private const val MAX_RETRIES = 5
        private const val WORK_NAME = "retry_upload_worker"
        private const val RETENTION_DAYS = 30L

        fun schedule(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val request = PeriodicWorkRequestBuilder<RetryWorker>(1, TimeUnit.HOURS)
                .setConstraints(constraints)
                .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
        }
    }

    override suspend fun doWork(): Result {
        Log.d(TAG, "开始处理重试队列")

        // 1. 重试旧的重试队列
        val items = repository.getDueItems()
        for (item in items) {
            try {
                val event = JSONObject(item.eventJson)
                val result = uploader.uploadEvent(event)

                if (result.ok) {
                    repository.remove(item.eventId)
                    Log.i(TAG, "重试成功: ${item.eventId}")
                } else {
                    val newCount = item.retryCount + 1
                    if (newCount >= MAX_RETRIES) {
                        repository.moveToDeadLetter(item)
                        Log.w(TAG, "移入死信: ${item.eventId}")
                    } else {
                        val delaySeconds = minOf(2L * (1L shl newCount), 300L)
                        repository.updateRetryInfo(
                            item.eventId,
                            newCount,
                            System.currentTimeMillis() + delaySeconds * 1000,
                        )
                        Log.d(TAG, "重试失败, 第${newCount}次: ${item.eventId}")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "重试异常: ${item.eventId}", e)
            }
        }

        // 2. 重试 messages 表中未上传的消息
        val unuploaded = db.messageDao().getUnuploaded()
        for (msg in unuploaded) {
            try {
                val event = JSONObject(msg.eventJson)
                val result = uploader.uploadEvent(event)
                if (result.ok) {
                    db.messageDao().markUploaded(msg.eventId, System.currentTimeMillis())
                    Log.i(TAG, "补传成功: ${msg.eventId}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "补传失败: ${msg.eventId}", e)
            }
        }

        // 3. 清理30天前的已上传消息
        val cutoff = System.currentTimeMillis() - RETENTION_DAYS * 24 * 3600 * 1000L
        db.messageDao().deleteUploadedBefore(cutoff)
        Log.d(TAG, "已清理 $RETENTION_DAYS 天前的消息")

        return Result.success()
    }
}
