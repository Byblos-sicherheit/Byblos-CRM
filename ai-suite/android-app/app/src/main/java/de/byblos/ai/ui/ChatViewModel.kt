package de.byblos.ai.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import de.byblos.ai.data.ChatRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class ChatViewModel(
    private val repository: ChatRepository,
) : ViewModel() {
    private val input = MutableStateFlow("")
    private val isSending = MutableStateFlow(false)
    private val error = MutableStateFlow<ChatUiError?>(null)
    private var sendJob: Job? = null

    val uiState: StateFlow<ChatUiState> = combine(
        repository.observeMessages(CONVERSATION_ID),
        input,
        isSending,
        error,
    ) { messages, currentInput, sending, currentError ->
        ChatUiState(
            messages = messages,
            input = currentInput,
            isSending = sending,
            error = currentError,
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = ChatUiState(),
    )

    init {
        viewModelScope.launch {
            repository.recoverInterruptedMessages(CONVERSATION_ID)
        }
    }

    fun onInputChanged(value: String) {
        input.value = value.take(MAX_MESSAGE_LENGTH)
        error.value = null
    }

    fun send() {
        val message = input.value.trim()
        if (message.isEmpty() || isSending.value) return

        input.value = ""
        isSending.value = true
        error.value = null

        sendJob = viewModelScope.launch {
            try {
                repository.sendMessage(CONVERSATION_ID, message)
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (_: Throwable) {
                error.value = ChatUiError.SEND_FAILED
            } finally {
                isSending.value = false
                sendJob = null
            }
        }
    }

    fun cancelSend() {
        sendJob?.cancel()
    }

    fun clearConversation() {
        if (isSending.value) return
        viewModelScope.launch {
            repository.clearConversation(CONVERSATION_ID)
            error.value = null
        }
    }

    fun dismissError() {
        error.value = null
    }

    companion object {
        private const val CONVERSATION_ID = "default"
        private const val MAX_MESSAGE_LENGTH = 8_000

        fun factory(repository: ChatRepository): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    require(modelClass.isAssignableFrom(ChatViewModel::class.java))
                    return ChatViewModel(repository) as T
                }
            }
    }
}
