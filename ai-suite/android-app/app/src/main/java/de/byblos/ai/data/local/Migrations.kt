package de.byblos.ai.data.local

import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

object Migrations {
    val MIGRATION_1_2 = object : Migration(1, 2) {
        override fun migrate(db: SupportSQLiteDatabase) {
            db.execSQL("ALTER TABLE messages ADD COLUMN errorMessage TEXT")
            db.execSQL(
                "CREATE INDEX IF NOT EXISTS index_messages_conversationId " +
                    "ON messages (conversationId)",
            )
        }
    }
}
