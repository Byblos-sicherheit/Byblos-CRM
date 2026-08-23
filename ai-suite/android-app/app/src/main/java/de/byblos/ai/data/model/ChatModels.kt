package de.byblos.ai.data.model

enum class ChatRole {
    USER,
    ASSISTANT,
}

enum class DeliveryStatus {
    SENDING,
    COMPLETED,
    FAILED,
    CANCELLED,
}

data class ChatMessage(
    val id: String,
    val conversationId: String,
    val role: ChatRole,
    val content: String,
    val status: DeliveryStatus,
    val createdAt: Long,
    val errorMessage: String? = null,
)

data class ContextMessage(
    val role: ChatRole,
    val content: String,
)
