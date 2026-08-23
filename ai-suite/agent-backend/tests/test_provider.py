from __future__ import annotations

import asyncio
import unittest

from byblos_agent.contracts import Message
from byblos_agent.provider import AntigravityTextStreamer, render_prompt


class ProviderTests(unittest.TestCase):
    def test_prompt_preserves_roles_and_latest_message(self):
        prompt = render_prompt(
            (
                Message(role="user", content="Frage eins"),
                Message(role="assistant", content="Antwort eins"),
                Message(role="user", content="Frage zwei"),
            )
        )
        self.assertIn("User: Frage eins", prompt)
        self.assertIn("Assistant: Antwort eins", prompt)
        self.assertTrue(prompt.endswith("Respond only to the latest user message."))


class FakeResponse:
    def __init__(self, tokens):
        self._tokens = iter(tokens)
        self.cancelled = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.sleep(0)
        try:
            return next(self._tokens)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def cancel(self):
        self.cancelled = True


class FakeAgent:
    response = None

    def __init__(self, config):
        self.config = config

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def chat(self, prompt):
        self.prompt = prompt
        return self.response


class TestStreamer(AntigravityTextStreamer):
    def __init__(self, response):
        self._settings = object()
        self.response = response

    def _make_config(self, conversation_id, request_id):
        del conversation_id, request_id
        FakeAgent.response = self.response
        return FakeAgent, object()


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_yields_provider_tokens(self):
        response = FakeResponse(["A", "B"])
        streamer = TestStreamer(response)
        cancelled = asyncio.Event()
        output = []
        async for token in streamer.stream_text(
            messages=(Message(role="user", content="Hallo"),),
            conversation_id="c1",
            request_id="r1",
            client_id="client-1",
            cancelled=cancelled,
        ):
            output.append(token)
        self.assertEqual(output, ["A", "B"])
        self.assertFalse(response.cancelled)

    async def test_stream_cancels_provider(self):
        response = FakeResponse(["A"])
        streamer = TestStreamer(response)
        cancelled = asyncio.Event()
        cancelled.set()
        output = []
        async for token in streamer.stream_text(
            messages=(Message(role="user", content="Hallo"),),
            conversation_id="c1",
            request_id="r1",
            client_id="client-1",
            cancelled=cancelled,
        ):
            output.append(token)
        self.assertEqual(output, [])
        self.assertTrue(response.cancelled)


if __name__ == "__main__":
    unittest.main()
