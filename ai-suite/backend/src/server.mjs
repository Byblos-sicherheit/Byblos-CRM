import { createHttpServer } from "./app.mjs";
import { loadConfig } from "./config.mjs";
import { createOpenAITextStreamer } from "./openai-provider.mjs";

const config = loadConfig();
const streamText = createOpenAITextStreamer({
  apiKey: config.openaiApiKey,
  model: config.openaiModel,
  maxOutputTokens: config.openaiMaxOutputTokens,
  baseURL: config.openaiBaseUrl,
});

const server = createHttpServer({
  streamText,
  appApiToken: config.appApiToken,
  allowedOrigins: config.allowedOrigins,
  maxRequestsPer15Minutes: config.maxRequestsPer15Minutes,
  maxConcurrentStreams: config.maxConcurrentStreams,
  streamTimeoutMs: config.streamTimeoutMs,
});

server.headersTimeout = 10_000;
server.requestTimeout = 30_000;
server.keepAliveTimeout = 5_000;
server.maxHeadersCount = 50;

server.listen(config.port, "0.0.0.0", () => {
  console.log(
    JSON.stringify({
      event: "server_started",
      port: config.port,
      nodeEnv: config.nodeEnv,
      model: config.openaiModel,
    }),
  );
});

function shutdown(signal) {
  console.log(JSON.stringify({ event: "shutdown_started", signal }));
  server.closeIdleConnections?.();
  server.close((error) => {
    if (error) {
      console.error(JSON.stringify({ event: "shutdown_failed", message: error.message }));
      process.exitCode = 1;
    }
  });

  const forceTimer = setTimeout(() => {
    console.error(JSON.stringify({ event: "shutdown_forced", signal }));
    server.closeAllConnections?.();
  }, 10_000);
  forceTimer.unref();
}

process.once("SIGINT", () => shutdown("SIGINT"));
process.once("SIGTERM", () => shutdown("SIGTERM"));
