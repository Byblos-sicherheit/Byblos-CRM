package de.byblos.ai.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.StopCircle
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.byblos.ai.R
import de.byblos.ai.data.model.ChatMessage
import de.byblos.ai.data.model.ChatRole
import de.byblos.ai.data.model.DeliveryStatus

@Composable
fun ChatRoute(viewModel: ChatViewModel) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    ChatScreen(
        state = state,
        onInputChanged = viewModel::onInputChanged,
        onSend = viewModel::send,
        onCancel = viewModel::cancelSend,
        onClear = viewModel::clearConversation,
        onDismissError = viewModel::dismissError,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    state: ChatUiState,
    onInputChanged: (String) -> Unit,
    onSend: () -> Unit,
    onCancel: () -> Unit,
    onClear: () -> Unit,
    onDismissError: () -> Unit,
) {
    val snackbarHostState = remember { SnackbarHostState() }
    val listState = rememberLazyListState()
    val errorMessage = when (state.error) {
        ChatUiError.SEND_FAILED -> stringResource(R.string.error_send_failed)
        null -> null
    }

    LaunchedEffect(state.error, errorMessage) {
        if (errorMessage != null) {
            snackbarHostState.showSnackbar(errorMessage)
            onDismissError()
        }
    }

    val lastContentLength = state.messages.lastOrNull()?.content?.length ?: 0
    LaunchedEffect(state.messages.size, lastContentLength) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.lastIndex)
        }
    }

    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding(),
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.chat_title)) },
                actions = {
                    IconButton(
                        onClick = onClear,
                        enabled = state.messages.isNotEmpty() && !state.isSending,
                    ) {
                        Icon(
                            imageVector = Icons.Default.DeleteOutline,
                            contentDescription = stringResource(R.string.delete_conversation),
                        )
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            MessageComposer(
                input = state.input,
                isSending = state.isSending,
                onInputChanged = onInputChanged,
                onSend = onSend,
                onCancel = onCancel,
            )
        },
    ) { padding ->
        if (state.messages.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(24.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = stringResource(R.string.empty_state),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.bodyLarge,
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .testTag("message_list"),
                state = listState,
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(
                    items = state.messages,
                    key = ChatMessage::id,
                ) { message ->
                    MessageBubble(message)
                }
            }
        }
    }
}

@Composable
private fun MessageComposer(
    input: String,
    isSending: Boolean,
    onInputChanged: (String) -> Unit,
    onSend: () -> Unit,
    onCancel: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface)
            .imePadding()
            .navigationBarsPadding(),
    ) {
        HorizontalDivider()
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.Bottom,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedTextField(
                value = input,
                onValueChange = onInputChanged,
                modifier = Modifier
                    .weight(1f)
                    .testTag("message_input"),
                enabled = !isSending,
                label = { Text(stringResource(R.string.message_label)) },
                minLines = 1,
                maxLines = 6,
            )

            IconButton(
                modifier = Modifier.testTag("send_button"),
                onClick = if (isSending) onCancel else onSend,
                enabled = isSending || input.isNotBlank(),
            ) {
                if (isSending) {
                    Icon(
                        imageVector = Icons.Default.StopCircle,
                        contentDescription = stringResource(R.string.cancel_generation),
                    )
                } else {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.Send,
                        contentDescription = stringResource(R.string.send_message),
                    )
                }
            }
        }
    }
}

@Composable
private fun MessageBubble(message: ChatMessage) {
    val isUser = message.role == ChatRole.USER
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        Column(
            modifier = Modifier
                .widthIn(max = 340.dp)
                .background(
                    color = if (isUser) {
                        MaterialTheme.colorScheme.primaryContainer
                    } else {
                        MaterialTheme.colorScheme.secondaryContainer
                    },
                    shape = RoundedCornerShape(18.dp),
                )
                .padding(horizontal = 16.dp, vertical = 12.dp),
        ) {
            if (message.content.isNotEmpty()) {
                Text(
                    text = message.content,
                    style = MaterialTheme.typography.bodyLarge,
                )
            }

            when (message.status) {
                DeliveryStatus.SENDING -> Text(
                    text = stringResource(R.string.generating_answer),
                    style = MaterialTheme.typography.labelSmall,
                )

                DeliveryStatus.FAILED -> Text(
                    text = stringResource(R.string.delivery_failed),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.labelSmall,
                )

                DeliveryStatus.CANCELLED -> Text(
                    text = stringResource(R.string.generation_cancelled),
                    style = MaterialTheme.typography.labelSmall,
                )

                DeliveryStatus.COMPLETED -> Unit
            }
        }
    }
}
