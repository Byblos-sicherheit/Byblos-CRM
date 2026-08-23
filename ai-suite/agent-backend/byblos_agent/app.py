from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
import json
import logging
import re
import time
from typing import Any
from uuid import uuid4

from .config import Settings
from .contracts import ContractError, validate_chat_request
from .provider import TextStreamer

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
MAX_BODY_BYTES = 32 * 1024
LOGGER = logging.getLogger("byblos_agent")


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int = 900) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._entries: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> tuple[bool, int, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            entries = self._entries[key]
            while entries and entries[0] <= cutoff:
                entries.popleft()
            allowed = len(entries) < self.limit
            if allowed:
                entries.append(now)
            remaining = max(0, self.limit - len(entries))
            retry_after = max(1, int(self.window_seconds - (now - entries[0]))) if entries else 1
            if len(self._entries) > 10000:
                empty = [client for client, values in self._entries.items() if not values]
                for client in empty:
                    self._entries.pop(client, None)
            return allowed, remaining, retry_after


class AgentApplication:
    def __init__(self, settings: Settings, streamer: TextStreamer) -> None:
        self.settings = settings
        self.streamer = streamer
        self.limiter = SlidingWindowLimiter(settings.max_requests_per_15_minutes)
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_streams)

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if scope.get("type") != "http":
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        request_id = headers.get("x-request-id", "")
        if not REQUEST_ID_RE.fullmatch(request_id):
            request_id = str(uuid4())

        response_headers = self._security_headers(request_id)
        origin = headers.get("origin", "")
        if origin:
            if origin not in self.settings.allowed_origins:
                await self._json(send, 403, {"error": "origin_not_allowed", "requestId": request_id}, response_headers)
                return
            response_headers.extend(
                [
                    (b"access-control-allow-origin", origin.encode("latin-1")),
                    (b"vary", b"Origin"),
                    (b"access-control-allow-headers", b"content-type,x-api-token,x-client-id,x-request-id"),
                    (b"access-control-allow-methods", b"GET,POST,OPTIONS"),
                ]
            )

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "/")

        if method == "OPTIONS":
            await self._empty(send, 204, response_headers)
            return
        if method == "GET" and path == "/health":
            await self._json(send, 200, {"status": "ok"}, response_headers)
            return
        if method == "GET" and path == "/ready":
            status = 200 if self.settings.provider_ready else 503
            state = "ready" if status == 200 else "credentials_missing"
            await self._json(send, status, {"status": state}, response_headers)
            return
        if method != "POST" or path != "/v1/chat/stream":
            await self._json(send, 404, {"error": "not_found", "requestId": request_id}, response_headers)
            return

        if not headers.get("content-type", "").lower().startswith("application/json"):
            await self._json(send, 415, {"error": "unsupported_media_type", "requestId": request_id}, response_headers)
            return

        if self.settings.app_api_token and headers.get("x-api-token") != self.settings.app_api_token:
            await self._json(send, 401, {"error": "unauthorized", "requestId": request_id}, response_headers)
            return

        client_id = headers.get("x-client-id", "")
        if client_id and not CLIENT_ID_RE.fullmatch(client_id):
            await self._json(send, 400, {"error": "invalid_client_id", "requestId": request_id}, response_headers)
            return

        rate_key = client_id or (scope.get("client") or ("unknown", 0))[0]
        allowed, remaining, retry_after = await self.limiter.check(rate_key)
        response_headers.extend(
            [
                (b"ratelimit-limit", str(self.limiter.limit).encode("ascii")),
                (b"ratelimit-remaining", str(remaining).encode("ascii")),
            ]
        )
        if not allowed:
            response_headers.append((b"retry-after", str(retry_after).encode("ascii")))
            await self._json(send, 429, {"error": "rate_limited", "requestId": request_id}, response_headers)
            return

        try:
            raw_body = await self._read_body(receive)
            payload = json.loads(raw_body.decode("utf-8"))
            chat_request = validate_chat_request(payload)
        except UnicodeDecodeError:
            await self._json(send, 400, {"error": "invalid_json", "requestId": request_id}, response_headers)
            return
        except json.JSONDecodeError:
            await self._json(send, 400, {"error": "invalid_json", "requestId": request_id}, response_headers)
            return
        except ContractError as exc:
            await self._json(send, exc.status, {"error": exc.code, "requestId": request_id}, response_headers)
            return
        except ValueError as exc:
            code = str(exc)
            status = 413 if code == "payload_too_large" else 400
            await self._json(send, status, {"error": code, "requestId": request_id}, response_headers)
            return

        try:
            await asyncio.wait_for(self.semaphore.acquire(), timeout=0.001)
        except TimeoutError:
            response_headers.append((b"retry-after", b"5"))
            await self._json(send, 503, {"error": "server_busy", "requestId": request_id}, response_headers)
            return

        cancelled = asyncio.Event()
        disconnect_task = asyncio.create_task(self._watch_disconnect(receive, cancelled))
        started_at = time.monotonic()

        try:
            sse_headers = response_headers + [
                (b"content-type", b"text/event-stream; charset=utf-8"),
                (b"cache-control", b"no-cache, no-transform"),
                (b"x-accel-buffering", b"no"),
            ]
            await send({"type": "http.response.start", "status": 200, "headers": sse_headers})
            await self._sse(send, "started", {"requestId": request_id})

            async with asyncio.timeout(self.settings.stream_timeout_seconds):
                async for delta in self.streamer.stream_text(
                    messages=chat_request.messages,
                    conversation_id=chat_request.conversation_id,
                    request_id=request_id,
                    client_id=client_id,
                    cancelled=cancelled,
                ):
                    if cancelled.is_set():
                        break
                    if delta:
                        await self._sse(send, "delta", {"delta": delta})

            if not cancelled.is_set():
                await self._sse(send, "completed", {"ok": True, "requestId": request_id})
                LOGGER.info(
                    "chat_stream_completed request_id=%s duration_ms=%d",
                    request_id,
                    int((time.monotonic() - started_at) * 1000),
                )
        except TimeoutError:
            cancelled.set()
            await self._sse(send, "error", {"code": "stream_timeout", "requestId": request_id})
        except Exception:
            LOGGER.exception("chat_stream_failed request_id=%s", request_id)
            if not cancelled.is_set():
                await self._sse(send, "error", {"code": "provider_error", "requestId": request_id})
        finally:
            cancelled.set()
            disconnect_task.cancel()
            await asyncio.gather(disconnect_task, return_exceptions=True)
            self.semaphore.release()
            try:
                await send({"type": "http.response.body", "body": b"", "more_body": False})
            except Exception:
                pass

    @staticmethod
    async def _read_body(receive) -> bytes:
        chunks: list[bytes] = []
        size = 0
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                raise ValueError("client_disconnected")
            if message["type"] != "http.request":
                continue
            body = message.get("body", b"")
            size += len(body)
            if size > MAX_BODY_BYTES:
                raise ValueError("payload_too_large")
            chunks.append(body)
            more = bool(message.get("more_body", False))
        if not chunks:
            raise ValueError("invalid_json")
        return b"".join(chunks)

    @staticmethod
    async def _watch_disconnect(receive, cancelled: asyncio.Event) -> None:
        while not cancelled.is_set():
            message = await receive()
            if message["type"] == "http.disconnect":
                cancelled.set()
                return

    @staticmethod
    def _security_headers(request_id: str) -> list[tuple[bytes, bytes]]:
        return [
            (b"x-request-id", request_id.encode("ascii")),
            (b"content-security-policy", b"default-src 'none'"),
            (b"cross-origin-resource-policy", b"same-site"),
            (b"referrer-policy", b"no-referrer"),
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", b"DENY"),
            (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
        ]

    @staticmethod
    async def _json(send, status: int, payload: dict[str, Any], headers) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": headers
                + [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"cache-control", b"no-store"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})

    @staticmethod
    async def _empty(send, status: int, headers) -> None:
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    @staticmethod
    async def _sse(send, event: str, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        body = f"event: {event}\ndata: {data}\n\n".encode("utf-8")
        await send({"type": "http.response.body", "body": body, "more_body": True})


def create_app(settings: Settings, streamer: TextStreamer) -> AgentApplication:
    return AgentApplication(settings=settings, streamer=streamer)
