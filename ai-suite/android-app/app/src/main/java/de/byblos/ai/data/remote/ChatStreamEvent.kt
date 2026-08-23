package de.byblos.ai.data.remote

sealed interface ChatStreamEvent {
    data class Delta(val text: String) : ChatStreamEvent
    data object Completed : ChatStreamEvent
    data class Failure(val message: String) : ChatStreamEvent
}
