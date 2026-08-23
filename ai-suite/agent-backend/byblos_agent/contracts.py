from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ContractError(ValueError):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True, slots=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ChatRequest:
    conversation_id: str
    messages: tuple[Message, ...]


def validate_chat_request(value: Any) -> ChatRequest:
    if not isinstance(value, dict):
        raise ContractError("invalid_request", "Request must be an object")

    conversation_id = value.get("conversationId")
    if not isinstance(conversation_id, str):
        raise ContractError("invalid_request", "conversationId must be a string")
    conversation_id = conversation_id.strip()
    if not 1 <= len(conversation_id) <= 100:
        raise ContractError(
            "invalid_request", "conversationId must contain 1 to 100 characters"
        )

    raw_messages = value.get("messages")
    if not isinstance(raw_messages, list) or not 1 <= len(raw_messages) <= 20:
        raise ContractError("invalid_request", "messages must contain 1 to 20 items")

    messages: list[Message] = []
    for index, raw_message in enumerate(raw_messages):
        if not isinstance(raw_message, dict):
            raise ContractError(
                "invalid_request", f"messages.{index} must be an object"
            )
        role = raw_message.get("role")
        if role not in {"user", "assistant"}:
            raise ContractError(
                "invalid_request", f"messages.{index}.role must be user or assistant"
            )
        content = raw_message.get("content")
        if not isinstance(content, str):
            raise ContractError(
                "invalid_request", f"messages.{index}.content must be a string"
            )
        content = content.strip()
        if not 1 <= len(content) <= 8000:
            raise ContractError(
                "invalid_request",
                f"messages.{index}.content must contain 1 to 8000 characters",
            )
        messages.append(Message(role=role, content=content))

    if messages[-1].role != "user":
        raise ContractError("invalid_request", "The final message must have role user")

    return ChatRequest(conversation_id=conversation_id, messages=tuple(messages))
