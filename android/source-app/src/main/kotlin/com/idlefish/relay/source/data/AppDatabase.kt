package com.idlefish.relay.source.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.idlefish.relay.source.data.dao.DeadLetterDao
import com.idlefish.relay.source.data.dao.MessageDao
import com.idlefish.relay.source.data.dao.RetryItemDao
import com.idlefish.relay.source.data.entity.DeadLetterEntity
import com.idlefish.relay.source.data.entity.MessageEntity
import com.idlefish.relay.source.data.entity.RetryItemEntity

@Database(
    entities = [RetryItemEntity::class, DeadLetterEntity::class, MessageEntity::class],
    version = 2,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun retryItemDao(): RetryItemDao
    abstract fun deadLetterDao(): DeadLetterDao
    abstract fun messageDao(): MessageDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(context, AppDatabase::class.java, "idlefish_source.db")
                    .fallbackToDestructiveMigration()
                    .build()
                    .also { INSTANCE = it }
            }
        }
    }
}
