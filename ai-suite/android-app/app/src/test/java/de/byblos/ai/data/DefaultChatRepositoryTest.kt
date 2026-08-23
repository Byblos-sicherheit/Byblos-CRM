package de.byblos.ai.data

import de.byblos.ai.data.local.ChatMessageEntity
import de.byblos.ai.data.local.MessageDao
import de.byblos.ai.data.model.ChatRole
import de.byblos.ai.data.model.DeliveryStatus
import de.byblos.ai.data.remote.ChatStreamEvent
import de.byblos.ai.data.remote.ChatStreamSource
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DefaultChatRepositoryTest {
    @Test
    fun rapidStreamingDeltasArePersistedInBatches() = runTest {
        val dao = FakeMessageDao()
        val remote = object : ChatStreamSource {
            override fun streamChat(
                conversationId: String,
                messages: List<de.byblos.ai.data.model.ContextMessage>,
            ): Flow<ChatStreamEvent> = flow {
                repeat(100) { emit(ChatStreamEvent.Delta("x")) }
                emit(ChatStreamEvent.Completed)
            }
        }
        val repository = DefaultChatRepository(
            dao = dao,
            remote = remote,
            nowMillis = { 1_000L },
        )

        repository.sendMessage("default", "hello")

        val assistant = dao.rows.single {
            it.role == ChatRole.ASSISTANT.name &&
                it.status == DeliveryStatus.COMPLETED.name
        }
        assertEquals("x".repeat(100), assistant.content)
        assertEquals(2, dao.updateAssistantCalls)
    }

    @Test
    fun cancellingAStreamLeavesAnExplicitCancelledMessage() = runTest {
        val dao = FakeMessageDao()
        val remote = object : ChatStreamSource {
            override fun streamChat(
                conversationId: String,
                messages: List<de.byblos.ai.data.model.ContextMessage>,
            ): Flow<ChatStreamEvent> = flow {
                emit(ChatStreamEvent.Delta("partial"))
                awaitCancellation()
            }
        }
        val repository = DefaultChatRepository(
            dao = dao,
            remote = remote,
            nowMillis = { 1_000L },
        )

        val job = launch {
            repository.sendMessage("default", "hello")
        }
        runCurrent()
        job.cancelAndJoin()

        val assistant = dao.rows.single { it.status == DeliveryStatus.CANCELLED.name }
        assertEquals("partial", assistant.content)
    }

    @Test
    fun interruptedSendingRowsAreRecoveredAsFailed() = runTest {
        val dao = FakeMessageDao().apply {
            rows += ChatMessageEntity(
                id = "assistant",
                conversationId = "default",
                role = "ASSISTANT",
                content = "partial",
                status = DeliveryStatus.SENDING.name,
                createdAt = 1L,
                errorMessage = null,
            )
            publish()
        }
        val repository = DefaultChatRepository(
            dao = dao,
            remote = object : ChatStreamSource {
                override fun streamChat(
                    conversationId: String,
                    messages: List<de.byblos.ai.data.model.ContextMessage>,
                ): Flow<ChatStreamEvent> = flow { error("not used") }
            },
        )

        repository.recoverInterruptedMessages("default")

        assertTrue(dao.rows.single().status == DeliveryStatus.FAILED.name)
    }

    private class FakeMessageDao : MessageDao {
        val rows = mutableListOf<ChatMessageEntity>()
        private val observed = MutableStateFlow<List<ChatMessageEntity>>(emptyList())
        var updateAssistantCalls = 0

        fun publish() {
            observed.value = rows.sortedBy(ChatMessageEntity::createdAt)
        }

        override fun observeMessages(conversationId: String): Flow<List<ChatMessageEntity>> =
            observed

        override suspend fun getRecentCompletedMessages(
            conversationId: String,
            limit: Int,
        ): List<ChatMessageEntity> = rows
            .filter {
                it.conversationId == conversationId &&
                    it.content.isNotEmpty() &&
                    it.status == DeliveryStatus.COMPLETED.name
            }
            .sortedByDescending(ChatMessageEntity::createdAt)
            .take(limit)

        override suspend fun insert(message: ChatMessageEntity) {
            rows.removeAll { it.id == message.id }
            rows += message
            publish()
        }

        override suspend fun insertAll(messages: List<ChatMessageEntity>) {
            messages.forEach { message ->
                rows.removeAll { it.id == message.id }
                rows += message
            }
            publish()
        }

        override suspend fun updateAssistant(
            id: String,
            content: String,
            status: String,
            errorMessage: String?,
        ) {
            updateAssistantCalls += 1
            val index = rows.indexOfFirst { it.id == id }
            rows[index] = rows[index].copy(
                content = content,
                status = status,
                errorMessage = errorMessage,
            )
            publish()
        }

        override suspend fun markInterruptedMessages(conversationId: String) {
            rows.indices.forEach { index ->
                val row = rows[index]
                if (
                    row.conversationId == conversationId &&
                    row.status == DeliveryStatus.SENDING.name
                ) {
                    rows[index] = row.copy(
                        status = DeliveryStatus.FAILED.name,
                        errorMessage = "interrupted",
                    )
                }
            }
            publish()
        }

        override suspend fun clearConversation(conversationId: String) {
            rows.removeAll { it.conversationId == conversationId }
            publish()
        }
    }
}
