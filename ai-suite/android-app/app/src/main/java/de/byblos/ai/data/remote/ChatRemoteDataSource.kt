package de.byblos.ai.data.remote

import de.byblos.ai.data.model.ChatRole
import de.byblos.ai.data.model.ContextMessage
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import org.json.JSONArray
import org.json.JSONObject

interface ChatStreamSource {
    fun streamChat(
        conversationId: String,
        messages: List<ContextMessage>,
    ): Flow<ChatStreamEvent>
}

class ChatRemoteDataSource(
    client: OkHttpClient,
    private val baseUrl: String,
    private val privateTestingToken: String,
    private val clientId: String,
) : ChatStreamSource {
    private val eventSourceFactory = EventSources.createFactory(client)

    override fun streamChat(
        conversationId: String,
        messages: List<ContextMessage>,
    ): Flow<ChatStreamEvent> = callbackFlow {
        val jsonMessages = JSONArray().apply {
            messages.forEach { message ->
                put(
                    JSONObject()
                        .put(
                            "role",
                            when (message.role) {
                                ChatRole.USER -> "user"
                                ChatRole.ASSISTANT -> "assistant"
                            },
                        )
                        .put("content", message.content),
                )
            }
        }

        val body = JSONObject()
            .put("conversationId", conversationId)
            .put("messages", jsonMessages)
            .toString()
            .toRequestBody(JSON_MEDIA_TYPE)

        val requestId = java.util.UUID.randomUUID().toString()

        val requestBuilder = Request.Builder()
            .url(baseUrl.trimEnd('/') + "/v1/chat/stream")
            .post(body)
            .header("Accept", "text/event-stream")
            .header("X-Client-Id", clientId)
            .header("X-Request-Id", requestId)

        if (privateTestingToken.isNotBlank()) {
            requestBuilder.header("X-Api-Token", privateTestingToken)
        }

        val listener = object : EventSourceListener() {
            override fun onEvent(
                eventSource: EventSource,
                id: String?,
                type: String?,
                data: String,
            ) {
                when (type) {
                    "delta" -> {
                        val delta = runCatching {
                            JSONObject(data).getString("delta")
                        }.getOrNull()
                        if (!delta.isNullOrEmpty()) {
                            trySend(ChatStreamEvent.Delta(delta))
                        }
                    }

                    "completed" -> trySend(ChatStreamEvent.Completed)
                    "error" -> {
                        val message = runCatching {
                            val payload = JSONObject(data)
                            payload.optString("code")
                                .ifBlank { payload.optString("message") }
                                .ifBlank { "backend_streaming_error" }
                        }.getOrDefault("backend_streaming_error")
                        trySend(ChatStreamEvent.Failure(message))
                    }
                }
            }

            override fun onFailure(
                eventSource: EventSource,
                throwable: Throwable?,
                response: Response?,
            ) {
                val message = when {
                    throwable?.message != null -> throwable.message.orEmpty()
                    response != null -> "HTTP ${response.code}"
                    else -> "Network stream failed"
                }
                trySend(ChatStreamEvent.Failure(message))
                close(throwable)
            }

            override fun onClosed(eventSource: EventSource) {
                close()
            }
        }

        val eventSource = eventSourceFactory.newEventSource(
            requestBuilder.build(),
            listener,
        )

        awaitClose {
            eventSource.cancel()
        }
    }

    private companion object {
        val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
    }
}
