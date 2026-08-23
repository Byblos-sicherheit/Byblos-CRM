import assert from "node:assert/strict";
import test from "node:test";
import { createHttpServer } from "../src/app.mjs";

const silentLogger = {
  info() {},
  error() {},
  log() {},
};

async function withServer(options, callback) {
  const server = createHttpServer({ logger: silentLogger, ...options });
  server.listen(0, "127.0.0.1");
  await new Promise((resolve) => server.once("listening", resolve));
  const address = server.address();
  try {
    await callback(`http://127.0.0.1:${address.port}`);
  } finally {
    await new Promise((resolve, reject) =>
      server.close((error) => (error ? reject(error) : resolve())),
    );
  }
}

function chatRequest(baseUrl, {
  clientId = "client-12345678",
  requestId,
  token,
  contentType = "application/json",
  body = {
    conversationId: "default",
    messages: [{ role: "user", content: "hello" }],
  },
} = {}) {
  const headers = {
    "content-type": contentType,
    "x-client-id": clientId,
  };
  if (requestId) headers["x-request-id"] = requestId;
  if (token) headers["x-api-token"] = token;

  return fetch(`${baseUrl}/v1/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
}

test("health endpoint responds and returns a correlation id", async () => {
  await withServer({ streamText: async function* () {} }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/health`);
    assert.equal(response.status, 200);
    assert.match(response.headers.get("x-request-id"), /^[0-9a-f-]{36}$/);
    assert.deepEqual(await response.json(), { status: "ok" });
  });
});

test("readiness endpoint responds", async () => {
  await withServer({ streamText: async function* () {} }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/ready`);
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { status: "ready" });
  });
});

test("browser origins are rejected unless allowlisted", async () => {
  await withServer({ streamText: async function* () {} }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/health`, {
      headers: { origin: "https://untrusted.example" },
    });
    assert.equal(response.status, 403);
  });
});

test("allowlisted browser origin receives narrow CORS headers", async () => {
  await withServer(
    {
      allowedOrigins: ["https://app.example"],
      streamText: async function* () {},
    },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/health`, {
        headers: { origin: "https://app.example" },
      });
      assert.equal(response.status, 200);
      assert.equal(response.headers.get("access-control-allow-origin"), "https://app.example");
    },
  );
});

test("private token is enforced when configured", async () => {
  await withServer(
    {
      appApiToken: "secret-test-token",
      streamText: async function* () {
        yield "ignored";
      },
    },
    async (baseUrl) => {
      const response = await chatRequest(baseUrl);
      assert.equal(response.status, 401);
    },
  );
});

test("chat endpoint streams events and forwards identifiers", async () => {
  const expectedRequestId = "request-12345678";
  await withServer(
    {
      streamText: async function* ({ messages, clientId, requestId }) {
        assert.equal(messages[0].content, "hello");
        assert.equal(clientId, "client-12345678");
        assert.equal(requestId, expectedRequestId);
        yield "مرحبا";
        yield " بك";
      },
    },
    async (baseUrl) => {
      const response = await chatRequest(baseUrl, { requestId: expectedRequestId });
      assert.equal(response.status, 200);
      assert.equal(response.headers.get("x-request-id"), expectedRequestId);
      const body = await response.text();
      assert.match(body, /event: started/);
      assert.match(body, /event: delta/);
      assert.match(body, /مرحبا/);
      assert.match(body, /event: completed/);
    },
  );
});

test("unsupported media type is rejected", async () => {
  await withServer({ streamText: async function* () {} }, async (baseUrl) => {
    const response = await chatRequest(baseUrl, { contentType: "text/plain" });
    assert.equal(response.status, 415);
  });
});

test("invalid client identifier is rejected", async () => {
  await withServer({ streamText: async function* () {} }, async (baseUrl) => {
    const response = await chatRequest(baseUrl, { clientId: "bad id" });
    assert.equal(response.status, 400);
    assert.equal((await response.json()).error, "invalid_client_id");
  });
});

test("invalid request is rejected before the provider is called", async () => {
  let called = false;
  await withServer(
    {
      streamText: async function* () {
        called = true;
      },
    },
    async (baseUrl) => {
      const response = await chatRequest(baseUrl, {
        body: { conversationId: "default", messages: [] },
      });
      assert.equal(response.status, 400);
      assert.equal(called, false);
    },
  );
});

test("request body size is limited", async () => {
  await withServer({ streamText: async function* () {} }, async (baseUrl) => {
    const response = await chatRequest(baseUrl, {
      body: {
        conversationId: "default",
        messages: [{ role: "user", content: "x".repeat(40_000) }],
      },
    });
    assert.equal(response.status, 413);
  });
});

test("rate limiting is keyed by client id", async () => {
  await withServer(
    {
      maxRequestsPer15Minutes: 1,
      streamText: async function* () {},
    },
    async (baseUrl) => {
      const first = await chatRequest(baseUrl, { clientId: "client-one-12345" });
      assert.equal(first.status, 200);
      await first.text();

      const second = await chatRequest(baseUrl, { clientId: "client-one-12345" });
      assert.equal(second.status, 429);
      assert.ok(Number(second.headers.get("retry-after")) >= 1);

      const otherClient = await chatRequest(baseUrl, { clientId: "client-two-12345" });
      assert.equal(otherClient.status, 200);
      await otherClient.text();
    },
  );
});

test("concurrent stream limit sheds excess load", async () => {
  let releaseStream;
  const gate = new Promise((resolve) => {
    releaseStream = resolve;
  });

  await withServer(
    {
      maxConcurrentStreams: 1,
      streamText: async function* () {
        yield "started";
        await gate;
      },
    },
    async (baseUrl) => {
      const first = await chatRequest(baseUrl, { clientId: "client-first-123" });
      assert.equal(first.status, 200);

      const second = await chatRequest(baseUrl, { clientId: "client-second-123" });
      assert.equal(second.status, 503);
      assert.equal((await second.json()).error, "server_busy");

      releaseStream();
      await first.text();
    },
  );
});

test("stream timeout returns a machine-readable SSE error", async () => {
  await withServer(
    {
      streamTimeoutMs: 20,
      streamText: async function* ({ signal }) {
        await new Promise((resolve) => {
          signal.addEventListener("abort", resolve, { once: true });
        });
      },
    },
    async (baseUrl) => {
      const response = await chatRequest(baseUrl);
      assert.equal(response.status, 200);
      const body = await response.text();
      assert.match(body, /stream_timeout/);
    },
  );
});
