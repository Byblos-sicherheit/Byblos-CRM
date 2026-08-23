import OpenAI from "openai";
import { buildOpenAIRequest } from "./openai-request.mjs";

export function createOpenAITextStreamer({
  apiKey,
  model,
  maxOutputTokens,
  baseURL = "",
}) {
  const client = new OpenAI({
    apiKey,
    ...(baseURL ? { baseURL } : {}),
  });

  return async function* streamText({ messages, signal, clientId, requestId }) {
    const stream = await client.responses.create(
      buildOpenAIRequest({
        model,
        messages,
        maxOutputTokens,
        clientId,
      }),
      {
        signal,
        ...(requestId
          ? {
              headers: {
                "X-Client-Request-Id": requestId,
              },
            }
          : {}),
      },
    );

    let completed = false;

    for await (const event of stream) {
      if (event.type === "response.output_text.delta" && event.delta) {
        yield event.delta;
        continue;
      }

      if (event.type === "response.completed") {
        completed = true;
        continue;
      }

      if (event.type === "response.failed" || event.type === "response.incomplete") {
        const message =
          event.response?.error?.message ||
          event.response?.incomplete_details?.reason ||
          `OpenAI response ended with ${event.type}`;
        throw new Error(message);
      }

      if (event.type === "error") {
        throw new Error(event.error?.message || event.message || "OpenAI streaming error");
      }
    }

    if (!completed && !signal?.aborted) {
      throw new Error("OpenAI stream ended before response.completed");
    }
  };
}
