import { randomUUID } from "node:crypto";
import http from "node:http";

class HttpError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const CLIENT_ID_PATTERN = /^[A-Za-z0-9._:-]{8,128}$/;

function firstHeaderValue(value) {
  return Array.isArray(value) ? value[0] : value;
}

function requestIdFor(request) {
  const candidate = firstHeaderValue(request.headers["x-request-id"]);
  if (typeof candidate === "string" && REQUEST_ID_PATTERN.test(candidate)) {
    return candidate;
  }
  return randomUUID();
}

function clientIdFor(request) {
  const value = firstHeaderValue(request.headers["x-client-id"]);
  if (value == null || value === "") return "";
  if (typeof value !== "string" || !CLIENT_ID_PATTERN.test(value)) {
    throw new HttpError(
      400,
      "invalid_client_id",
      "X-Client-Id must contain 8 to 128 ASCII identifier characters",
    );
  }
  return value;
}

function applySecurityHeaders(response) {
  response.setHeader("Content-Security-Policy", "default-src 'none'");
  response.setHeader("Cross-Origin-Resource-Policy", "same-site");
  response.setHeader("Referrer-Policy", "no-referrer");
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader("X-Frame-Options", "DENY");
  response.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
}

function configureCors(request, response, allowedOrigins) {
  const origin = request.headers.origin;
  if (!origin) return true;

  if (allowedOrigins.includes(origin)) {
    response.setHeader("Access-Control-Allow-Origin", origin);
    response.setHeader("Vary", "Origin");
    response.setHeader(
      "Access-Control-Allow-Headers",
      "content-type,x-api-token,x-client-id,x-request-id",
    );
    response.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
    return true;
  }

  return false;
}

function sendJson(response, status, payload) {
  const body = JSON.stringify(payload);
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    "Cache-Control": "no-store",
  });
  response.end(body);
}

function sendSse(response, event, payload) {
  response.write(`event: ${event}\n`);
  response.write(`data: ${JSON.stringify(payload)}\n\n`);
}

async function readJson(request, maxBytes = 32 * 1024) {
  const chunks = [];
  let size = 0;

  for await (const chunk of request) {
    size += chunk.length;
    if (size > maxBytes) {
      throw new HttpError(413, "payload_too_large", "Request body is too large");
    }
    chunks.push(chunk);
  }

  if (chunks.length === 0) {
    throw new HttpError(400, "invalid_json", "Request body is required");
  }

  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new HttpError(400, "invalid_json", "Request body is not valid JSON");
  }
}

function validateChatRequest(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new HttpError(400, "invalid_request", "Request must be an object");
  }

  const conversationId =
    typeof value.conversationId === "string" ? value.conversationId.trim() : "";
  if (conversationId.length < 1 || conversationId.length > 100) {
    throw new HttpError(
      400,
      "invalid_request",
      "conversationId must contain 1 to 100 characters",
    );
  }

  if (!Array.isArray(value.messages) || value.messages.length < 1 || value.messages.length > 20) {
    throw new HttpError(400, "invalid_request", "messages must contain 1 to 20 items");
  }

  const messages = value.messages.map((message, index) => {
    if (!message || typeof message !== "object" || Array.isArray(message)) {
      throw new HttpError(400, "invalid_request", `messages.${index} must be an object`);
    }

    if (message.role !== "user" && message.role !== "assistant") {
      throw new HttpError(
        400,
        "invalid_request",
        `messages.${index}.role must be user or assistant`,
      );
    }

    const content = typeof message.content === "string" ? message.content.trim() : "";
    if (content.length < 1 || content.length > 8_000) {
      throw new HttpError(
        400,
        "invalid_request",
        `messages.${index}.content must contain 1 to 8000 characters`,
      );
    }

    return { role: message.role, content };
  });

  return { conversationId, messages };
}

function createRateLimiter({ limit, windowMs }) {
  const clients = new Map();

  return function checkRateLimit(key, response) {
    const now = Date.now();
    let entry = clients.get(key);

    if (!entry || entry.resetAt <= now) {
      entry = { count: 0, resetAt: now + windowMs };
      clients.set(key, entry);
    }

    entry.count += 1;
    const remaining = Math.max(0, limit - entry.count);
    const retryAfterSeconds = Math.max(1, Math.ceil((entry.resetAt - now) / 1000));
    response.setHeader("RateLimit-Limit", String(limit));
    response.setHeader("RateLimit-Remaining", String(remaining));
    response.setHeader("RateLimit-Reset", String(Math.ceil(entry.resetAt / 1000)));

    if (clients.size > 10_000) {
      for (const [clientKey, clientEntry] of clients) {
        if (clientEntry.resetAt <= now) clients.delete(clientKey);
      }
    }

    return {
      allowed: entry.count <= limit,
      retryAfterSeconds,
    };
  };
}

function log(logger, level, event, fields) {
  const method = typeof logger?.[level] === "function" ? logger[level] : logger?.log;
  if (typeof method === "function") {
    method.call(logger, JSON.stringify({ event, ...fields }));
  }
}

export function createHttpServer({
  streamText,
  appApiToken = "",
  allowedOrigins = [],
  maxRequestsPer15Minutes = 60,
  maxConcurrentStreams = 20,
  streamTimeoutMs = 120_000,
  logger = console,
}) {
  if (typeof streamText !== "function") {
    throw new TypeError("streamText must be a function");
  }

  const checkRateLimit = createRateLimiter({
    limit: maxRequestsPer15Minutes,
    windowMs: 15 * 60 * 1000,
  });
  let activeStreams = 0;

  return http.createServer(async (request, response) => {
    const requestId = requestIdFor(request);
    const startedAt = Date.now();
    response.setHeader("X-Request-Id", requestId);
    applySecurityHeaders(response);

    try {
      if (!configureCors(request, response, allowedOrigins)) {
        sendJson(response, 403, { error: "origin_not_allowed", requestId });
        return;
      }

      if (request.method === "OPTIONS") {
        response.writeHead(204);
        response.end();
        return;
      }

      const url = new URL(request.url || "/", "http://localhost");

      if (request.method === "GET" && url.pathname === "/health") {
        sendJson(response, 200, { status: "ok" });
        return;
      }

      if (request.method === "GET" && url.pathname === "/ready") {
        sendJson(response, 200, { status: "ready" });
        return;
      }

      if (request.method !== "POST" || url.pathname !== "/v1/chat/stream") {
        sendJson(response, 404, { error: "not_found", requestId });
        return;
      }

      const contentType = firstHeaderValue(request.headers["content-type"]) || "";
      if (!contentType.toLowerCase().startsWith("application/json")) {
        sendJson(response, 415, { error: "unsupported_media_type", requestId });
        return;
      }

      const clientId = clientIdFor(request);
      const rateLimitKey = clientId || request.socket.remoteAddress || "unknown";
      const rateLimit = checkRateLimit(rateLimitKey, response);
      if (!rateLimit.allowed) {
        response.setHeader("Retry-After", String(rateLimit.retryAfterSeconds));
        sendJson(response, 429, { error: "rate_limited", requestId });
        return;
      }

      if (appApiToken && request.headers["x-api-token"] !== appApiToken) {
        sendJson(response, 401, { error: "unauthorized", requestId });
        return;
      }

      if (activeStreams >= maxConcurrentStreams) {
        response.setHeader("Retry-After", "5");
        sendJson(response, 503, { error: "server_busy", requestId });
        return;
      }

      const body = validateChatRequest(await readJson(request));
      activeStreams += 1;

      response.writeHead(200, {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      });
      response.flushHeaders();
      sendSse(response, "started", { requestId });

      const abortController = new AbortController();
      let timedOut = false;
      const timeout = setTimeout(() => {
        timedOut = true;
        abortController.abort(new Error("stream_timeout"));
      }, streamTimeoutMs);
      timeout.unref?.();

      request.on("aborted", () => abortController.abort(new Error("client_aborted")));
      response.on("close", () => {
        if (!response.writableEnded) {
          abortController.abort(new Error("client_disconnected"));
        }
      });

      try {
        for await (const delta of streamText({
          messages: body.messages,
          conversationId: body.conversationId,
          signal: abortController.signal,
          clientId,
          requestId,
        })) {
          if (abortController.signal.aborted) break;
          if (typeof delta === "string" && delta.length > 0) {
            sendSse(response, "delta", { delta });
          }
        }

        if (timedOut && !response.destroyed) {
          sendSse(response, "error", { code: "stream_timeout", requestId });
        } else if (!abortController.signal.aborted) {
          sendSse(response, "completed", { ok: true, requestId });
          log(logger, "info", "chat_stream_completed", {
            requestId,
            durationMs: Date.now() - startedAt,
          });
        }
      } catch (error) {
        if (timedOut && !response.destroyed) {
          sendSse(response, "error", { code: "stream_timeout", requestId });
        } else if (!abortController.signal.aborted && !response.destroyed) {
          sendSse(response, "error", { code: "generation_failed", requestId });
          log(logger, "error", "chat_stream_failed", {
            requestId,
            name: error?.name,
            message: error?.message,
          });
        }
      } finally {
        clearTimeout(timeout);
        activeStreams -= 1;
        if (!response.writableEnded && !response.destroyed) {
          response.end();
        }
      }
    } catch (error) {
      if (response.headersSent) {
        if (!response.writableEnded && !response.destroyed) response.end();
        return;
      }

      if (error instanceof HttpError) {
        sendJson(response, error.status, {
          error: error.code,
          message: error.message,
          requestId,
        });
        return;
      }

      log(logger, "error", "unhandled_request_error", {
        requestId,
        name: error?.name,
        message: error?.message,
      });
      sendJson(response, 500, { error: "internal_error", requestId });
    }
  });
}
