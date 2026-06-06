package com.idlefish.relay.receiver.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.idlefish.relay.receiver.data.dao.EventDao
import com.idlefish.relay.receiver.data.entity.EventEntity

@Database(
    entities = [EventEntity::class],
    version = 1,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun eventDao(): EventDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(context, AppDatabase::class.java, "idlefish_receiver.db")
                    .build()
                    .also { INSTANCE = it }
            }
        }
    }
}
