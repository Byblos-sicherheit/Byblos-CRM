package de.byblos.ai.data

import de.byblos.ai.data.local.ChatMessageEntity
import de.byblos.ai.data.local.MessageDao
import de.byblos.ai.data.local.toContextMessage
import de.byblos.ai.data.local.toDomain
import de.byblos.ai.data.model.ChatMessage
import de.byblos.ai.data.model.ChatRole
import de.byblos.ai.data.model.DeliveryStatus
import de.byblos.ai.data.remote.ChatStreamSource
import de.byblos.ai.data.remote.ChatStreamEvent
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.map
import java.io.IOException
import java.util.UUID

interface ChatRepository {
    fun observeMessages(conversationId: String): Flow<List<ChatMessage>>
    suspend fun recoverInterruptedMessages(conversationId: String)
    suspend fun sendMessage(conversationId: String, text: String)
    suspend fun clearConversation(conversationId: String)
}

class DefaultChatRepository(
    private val dao: MessageDao,
    private val remote: ChatStreamSource,
    private val nowMillis: () -> Long = System::currentTimeMillis,
) : ChatRepository {
    override fun observeMessages(conversationId: String): Flow<List<ChatMessage>> =
        dao.observeMessages(conversationId).map { entities ->
            entities.map(ChatMessageEntity::toDomain)
        }

    override suspend fun recoverInterruptedMessages(conversationId: String) {
        dao.markInterruptedMessages(conversationId)
    }

    override suspend fun sendMessage(conversationId: String, text: String) {
        val normalized = text.trim()
        require(normalized.isNotEmpty()) { "Message must not be empty" }
        require(normalized.length <= MAX_MESSAGE_LENGTH) {
            "Message exceeds $MAX_MESSAGE_LENGTH characters"
        }

        val now = nowMillis()
        val assistantId = UUID.randomUUID().toString()

        dao.insertAll(
            listOf(
                ChatMessageEntity(
                    id = UUID.randomUUID().toString(),
                    conversationId = conversationId,
                    role = ChatRole.USER.name,
                    content = normalized,
                    status = DeliveryStatus.COMPLETED.name,
                    createdAt = now,
                    errorMessage = null,
                ),
                ChatMessageEntity(
                    id = assistantId,
                    conversationId = conversationId,
                    role = ChatRole.ASSISTANT.name,
                    content = "",
                    status = DeliveryStatus.SENDING.name,
                    createdAt = now + 1,
                    errorMessage = null,
                ),
            ),
        )

        val context = dao.getRecentCompletedMessages(
            conversationId = conversationId,
            limit = MAX_CONTEXT_MESSAGES,
        )
            .asReversed()
            .map(ChatMessageEntity::toContextMessage)

        val answer = StringBuilder()
        var completed = false
        var lastPartialWriteAt = 0L
        var hasPersistedPartial = false

        suspend fun persistPartialIfNeeded(force: Boolean = false) {
            val currentTime = nowMillis()
            if (force || !hasPersistedPartial || currentTime - lastPartialWriteAt >= PARTIAL_WRITE_INTERVAL_MS) {
                dao.updateAssistant(
                    id = assistantId,
                    content = answer.toString(),
                    status = DeliveryStatus.SENDING.name,
                    errorMessage = null,
                )
                lastPartialWriteAt = currentTime
                hasPersistedPartial = true
            }
        }

        try {
            remote.streamChat(conversationId, context).collect { event ->
                when (event) {
                    is ChatStreamEvent.Delta -> {
                        answer.append(event.text)
                        persistPartialIfNeeded()
                    }

                    ChatStreamEvent.Completed -> {
                        completed = true
                        dao.updateAssistant(
                            id = assistantId,
                            content = answer.toString(),
                            status = DeliveryStatus.COMPLETED.name,
                            errorMessage = null,
                        )
                    }

                    is ChatStreamEvent.Failure -> {
                        throw IOException(event.message)
                    }
                }
            }

            if (!completed) {
                throw IOException("Stream closed before completion")
            }
        } catch (cancelled: CancellationException) {
            dao.updateAssistant(
                id = assistantId,
                content = answer.toString(),
                status = DeliveryStatus.CANCELLED.name,
                errorMessage = ERROR_CANCELLED,
            )
            throw cancelled
        } catch (error: Throwable) {
            dao.updateAssistant(
                id = assistantId,
                content = answer.toString(),
                status = DeliveryStatus.FAILED.name,
                errorMessage = ERROR_COMMUNICATION,
            )
            throw error
        }
    }

    override suspend fun clearConversation(conversationId: String) {
        dao.clearConversation(conversationId)
    }

    private companion object {
        const val MAX_MESSAGE_LENGTH = 8_000
        const val MAX_CONTEXT_MESSAGES = 20
        const val PARTIAL_WRITE_INTERVAL_MS = 100L
        const val ERROR_CANCELLED = "cancelled"
        const val ERROR_COMMUNICATION = "communication_failed"
    }
}
