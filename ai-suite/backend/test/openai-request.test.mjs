import assert from "node:assert/strict";
import test from "node:test";
import { buildOpenAIRequest, hashClientIdentifier } from "../src/openai-request.mjs";

test("client identifier is irreversibly hashed before leaving the backend", () => {
  const raw = "client-12345678";
  const hash = hashClientIdentifier(raw);
  assert.equal(hash.length, 64);
  assert.notEqual(hash, raw);
  assert.match(hash, /^[0-9a-f]{64}$/);
});

test("OpenAI request disables application-state storage and caps output", () => {
  const request = buildOpenAIRequest({
    model: "gpt-5-mini",
    messages: [{ role: "user", content: "hello" }],
    maxOutputTokens: 1200,
    clientId: "client-12345678",
  });

  assert.equal(request.model, "gpt-5-mini");
  assert.equal(request.store, false);
  assert.equal(request.stream, true);
  assert.equal(request.max_output_tokens, 1200);
  assert.match(request.safety_identifier, /^byblos_[0-9a-f]{64}$/);
  assert.equal(request.prompt_cache_key, request.safety_identifier);
  assert.equal(JSON.stringify(request).includes("client-12345678"), false);
});
