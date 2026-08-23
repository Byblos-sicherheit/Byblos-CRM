package de.byblos.ai.data.local

import android.content.Context
import androidx.room.Room
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class Migration1To2Test {
    private lateinit var context: Context

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        context.deleteDatabase(TEST_DB)
    }

    @After
    fun tearDown() {
        context.deleteDatabase(TEST_DB)
    }

    @Test
    fun migrationPreservesRowsAndAddsNullableErrorColumn() = runBlocking {
        val helper = FrameworkSQLiteOpenHelperFactory().create(
            SupportSQLiteOpenHelper.Configuration.builder(context)
                .name(TEST_DB)
                .callback(
                    object : SupportSQLiteOpenHelper.Callback(1) {
                        override fun onCreate(db: androidx.sqlite.db.SupportSQLiteDatabase) {
                            db.execSQL(
                                """
                                CREATE TABLE IF NOT EXISTS messages (
                                    id TEXT NOT NULL,
                                    conversationId TEXT NOT NULL,
                                    role TEXT NOT NULL,
                                    content TEXT NOT NULL,
                                    status TEXT NOT NULL,
                                    createdAt INTEGER NOT NULL,
                                    PRIMARY KEY(id)
                                )
                                """.trimIndent(),
                            )
                        }

                        override fun onUpgrade(
                            db: androidx.sqlite.db.SupportSQLiteDatabase,
                            oldVersion: Int,
                            newVersion: Int,
                        ) = Unit
                    },
                )
                .build(),
        )

        helper.writableDatabase.execSQL(
            """
            INSERT INTO messages(id, conversationId, role, content, status, createdAt)
            VALUES('m1', 'default', 'USER', 'hello', 'COMPLETED', 1)
            """.trimIndent(),
        )
        helper.close()

        val room = Room.databaseBuilder(context, AppDatabase::class.java, TEST_DB)
            .addMigrations(Migrations.MIGRATION_1_2)
            .allowMainThreadQueries()
            .build()

        val row = room.messageDao().getRecentCompletedMessages("default", 10).single()
        assertEquals("hello", row.content)
        assertNull(row.errorMessage)
        room.close()
    }

    private companion object {
        const val TEST_DB = "migration-test.db"
    }
}
