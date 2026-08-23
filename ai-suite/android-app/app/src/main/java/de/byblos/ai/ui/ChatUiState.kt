package de.byblos.ai.ui

import de.byblos.ai.data.model.ChatMessage

enum class ChatUiError {
    SEND_FAILED,
}

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val input: String = "",
    val isSending: Boolean = false,
    val error: ChatUiError? = null,
)
