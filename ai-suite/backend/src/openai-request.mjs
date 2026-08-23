import { createHash } from "node:crypto";

const SYSTEM_INSTRUCTIONS =
  "You are the professional assistant inside the Byblos application. " +
  "Reply in the user's language, be precise, and never claim to have performed actions you did not perform. " +
  "Do not request passwords, secret keys, payment credentials, or unnecessary sensitive personal data.";

export function hashClientIdentifier(clientId) {
  if (!clientId) return "";
  return createHash("sha256").update(clientId, "utf8").digest("hex");
}

export function buildOpenAIRequest({
  model,
  messages,
  maxOutputTokens,
  clientId = "",
}) {
  const hashedClientId = hashClientIdentifier(clientId);
  const request = {
    model,
    instructions: SYSTEM_INSTRUCTIONS,
    input: messages,
    stream: true,
    store: false,
    max_output_tokens: maxOutputTokens,
  };

  if (hashedClientId) {
    const opaqueIdentifier = `byblos_${hashedClientId}`;
    request.safety_identifier = opaqueIdentifier;
    request.prompt_cache_key = opaqueIdentifier;
  }

  return request;
}
