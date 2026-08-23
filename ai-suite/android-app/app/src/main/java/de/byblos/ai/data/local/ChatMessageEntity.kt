package de.byblos.ai.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import de.byblos.ai.data.model.ChatMessage
import de.byblos.ai.data.model.ChatRole
import de.byblos.ai.data.model.ContextMessage
import de.byblos.ai.data.model.DeliveryStatus

@Entity(
    tableName = "messages",
    indices = [Index(value = ["conversationId"])],
)
data class ChatMessageEntity(
    @PrimaryKey val id: String,
    val conversationId: String,
    val role: String,
    val content: String,
    val status: String,
    val createdAt: Long,
    val errorMessage: String?,
)

fun ChatMessageEntity.toDomain(): ChatMessage = ChatMessage(
    id = id,
    conversationId = conversationId,
    role = ChatRole.valueOf(role),
    content = content,
    status = DeliveryStatus.valueOf(status),
    createdAt = createdAt,
    errorMessage = errorMessage,
)

fun ChatMessageEntity.toContextMessage(): ContextMessage = ContextMessage(
    role = ChatRole.valueOf(role),
    content = content,
)
