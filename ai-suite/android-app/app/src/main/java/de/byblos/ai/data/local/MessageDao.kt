package de.byblos.ai.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface MessageDao {
    @Query(
        """
        SELECT * FROM messages
        WHERE conversationId = :conversationId
        ORDER BY createdAt ASC
        """,
    )
    fun observeMessages(conversationId: String): Flow<List<ChatMessageEntity>>

    @Query(
        """
        SELECT * FROM messages
        WHERE conversationId = :conversationId
          AND content != ''
          AND status = 'COMPLETED'
        ORDER BY createdAt DESC
        LIMIT :limit
        """,
    )
    suspend fun getRecentCompletedMessages(
        conversationId: String,
        limit: Int,
    ): List<ChatMessageEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(message: ChatMessageEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(messages: List<ChatMessageEntity>)

    @Query(
        """
        UPDATE messages
        SET content = :content,
            status = :status,
            errorMessage = :errorMessage
        WHERE id = :id
        """,
    )
    suspend fun updateAssistant(
        id: String,
        content: String,
        status: String,
        errorMessage: String?,
    )


    @Query(
        """
        UPDATE messages
        SET status = 'FAILED',
            errorMessage = 'interrupted'
        WHERE conversationId = :conversationId
          AND status = 'SENDING'
        """,
    )
    suspend fun markInterruptedMessages(conversationId: String)

    @Query("DELETE FROM messages WHERE conversationId = :conversationId")
    suspend fun clearConversation(conversationId: String)
}
