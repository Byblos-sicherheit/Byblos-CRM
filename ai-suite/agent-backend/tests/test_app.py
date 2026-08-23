from __future__ import annotations

import asyncio
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from byblos_agent.app import create_app
from byblos_agent.config import Settings


class FakeStreamer:
    async def stream_text(self, **kwargs):
        del kwargs
        yield "Hallo "
        yield "Welt"


class SlowStreamer:
    async def stream_text(self, **kwargs):
        del kwargs
        await asyncio.sleep(2)
        yield "zu spaet"


def settings_for_test(**changes):
    base = Settings(
        host="127.0.0.1",
        port=3100,
        environment="test",
        gemini_api_key="test-key",
        use_vertex=False,
        google_cloud_project="",
        google_cloud_location="",
        model=None,
        app_api_token="test-token",
        allowed_origins=("https://example.test",),
        max_requests_per_15_minutes=3,
        max_concurrent_streams=2,
        stream_timeout_seconds=5,
        app_data_dir=Path(tempfile.gettempdir()) / "byblos-agent-tests",
        skills_paths=(),
        system_instructions="Test",
    )
    return replace(base, **changes)


async def invoke(app, method="GET", path="/health", headers=None, body=b""):
    sent = []
    incoming = asyncio.Queue()
    await incoming.put({"type": "http.request", "body": body, "more_body": False})

    async def receive():
        try:
            return incoming.get_nowait()
        except asyncio.QueueEmpty:
            await asyncio.sleep(3600)

    async def send(message):
        sent.append(message)

    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
    }
    await app(scope, receive, send)
    return sent


def response_status(messages):
    return next(message["status"] for message in messages if message["type"] == "http.response.start")


def response_body(messages):
    return b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")


class AppTests(unittest.IsolatedAsyncioTestCase):
    async def test_health(self):
        messages = await invoke(create_app(settings_for_test(), FakeStreamer()))
        self.assertEqual(response_status(messages), 200)
        self.assertEqual(json.loads(response_body(messages)), {"status": "ok"})

    async def test_ready_reports_credentials(self):
        messages = await invoke(
            create_app(settings_for_test(gemini_api_key=""), FakeStreamer()),
            path="/ready",
        )
        self.assertEqual(response_status(messages), 503)

    async def test_requires_token(self):
        body = json.dumps(
            {"conversationId": "c1", "messages": [{"role": "user", "content": "Hi"}]}
        ).encode()
        messages = await invoke(
            create_app(settings_for_test(), FakeStreamer()),
            method="POST",
            path="/v1/chat/stream",
            headers={"content-type": "application/json", "x-client-id": "client-123"},
            body=body,
        )
        self.assertEqual(response_status(messages), 401)

    async def test_stream_contract_matches_android_client(self):
        body = json.dumps(
            {"conversationId": "c1", "messages": [{"role": "user", "content": "Hi"}]}
        ).encode()
        messages = await invoke(
            create_app(settings_for_test(), FakeStreamer()),
            method="POST",
            path="/v1/chat/stream",
            headers={
                "content-type": "application/json",
                "x-client-id": "client-123",
                "x-api-token": "test-token",
                "x-request-id": "request-123",
            },
            body=body,
        )
        self.assertEqual(response_status(messages), 200)
        stream = response_body(messages).decode("utf-8")
        self.assertIn("event: started", stream)
        self.assertIn('data: {"delta":"Hallo "}', stream)
        self.assertIn('data: {"delta":"Welt"}', stream)
        self.assertIn("event: completed", stream)


    async def test_rejects_disallowed_origin(self):
        messages = await invoke(
            create_app(settings_for_test(), FakeStreamer()),
            headers={"origin": "https://attacker.test"},
        )
        self.assertEqual(response_status(messages), 403)

    async def test_allows_configured_origin(self):
        messages = await invoke(
            create_app(settings_for_test(), FakeStreamer()),
            headers={"origin": "https://example.test"},
        )
        self.assertEqual(response_status(messages), 200)
        response_start = next(
            message for message in messages if message["type"] == "http.response.start"
        )
        headers = dict(response_start["headers"])
        self.assertEqual(headers[b"access-control-allow-origin"], b"https://example.test")

    async def test_rate_limit_is_enforced(self):
        app = create_app(settings_for_test(max_requests_per_15_minutes=1), FakeStreamer())
        body = json.dumps(
            {"conversationId": "c1", "messages": [{"role": "user", "content": "Hi"}]}
        ).encode()
        headers = {
            "content-type": "application/json",
            "x-client-id": "client-123",
            "x-api-token": "test-token",
        }
        first = await invoke(app, method="POST", path="/v1/chat/stream", headers=headers, body=body)
        second = await invoke(app, method="POST", path="/v1/chat/stream", headers=headers, body=body)
        self.assertEqual(response_status(first), 200)
        self.assertEqual(response_status(second), 429)

    async def test_stream_timeout_is_machine_readable(self):
        app = create_app(settings_for_test(stream_timeout_seconds=1), SlowStreamer())
        body = json.dumps(
            {"conversationId": "c1", "messages": [{"role": "user", "content": "Hi"}]}
        ).encode()
        messages = await invoke(
            app,
            method="POST",
            path="/v1/chat/stream",
            headers={
                "content-type": "application/json",
                "x-client-id": "client-123",
                "x-api-token": "test-token",
            },
            body=body,
        )
        self.assertEqual(response_status(messages), 200)
        self.assertIn('event: error\ndata: {"code":"stream_timeout"', response_body(messages).decode())

    async def test_rejects_invalid_json(self):
        messages = await invoke(
            create_app(settings_for_test(), FakeStreamer()),
            method="POST",
            path="/v1/chat/stream",
            headers={
                "content-type": "application/json",
                "x-client-id": "client-123",
                "x-api-token": "test-token",
            },
            body=b"{invalid",
        )
        self.assertEqual(response_status(messages), 400)


if __name__ == "__main__":
    unittest.main()
