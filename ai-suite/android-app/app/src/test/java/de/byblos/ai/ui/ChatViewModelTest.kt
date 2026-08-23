package de.byblos.ai.ui

import de.byblos.ai.data.ChatRepository
import de.byblos.ai.data.model.ChatMessage
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ChatViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @Test
    fun send_trimsInputAndDelegatesToRepository() = runTest {
        val repository = FakeChatRepository()
        val viewModel = ChatViewModel(repository)

        viewModel.onInputChanged("  اختبار  ")
        viewModel.send()
        advanceUntilIdle()

        assertEquals(listOf("اختبار"), repository.sentMessages)
        assertFalse(viewModel.uiState.value.isSending)
    }

    private class FakeChatRepository : ChatRepository {
        private val messages = MutableStateFlow<List<ChatMessage>>(emptyList())
        val sentMessages = mutableListOf<String>()

        override fun observeMessages(conversationId: String): Flow<List<ChatMessage>> = messages

        override suspend fun recoverInterruptedMessages(conversationId: String) = Unit

        override suspend fun sendMessage(conversationId: String, text: String) {
            sentMessages += text
        }

        override suspend fun clearConversation(conversationId: String) {
            messages.value = emptyList()
        }
    }
}
