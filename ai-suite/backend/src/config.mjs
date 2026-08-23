function readInteger(name, fallback, { min = 1, max = Number.MAX_SAFE_INTEGER } = {}) {
  const raw = process.env[name];
  if (!raw) return fallback;

  const value = Number.parseInt(raw, 10);
  if (!Number.isFinite(value) || value < min || value > max) {
    throw new Error(`${name} must be an integer between ${min} and ${max}`);
  }
  return value;
}

function readCsv(name) {
  return (process.env[name] || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function validateOptionalUrl(name, value, { requireHttps = false } = {}) {
  if (!value) return;

  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`${name} must be a valid absolute URL`);
  }

  if (requireHttps && parsed.protocol !== "https:") {
    throw new Error(`${name} must use https in production`);
  }
}

export function loadConfig() {
  const nodeEnv = process.env.NODE_ENV || "development";
  const config = {
    nodeEnv,
    port: readInteger("PORT", 3000, { max: 65_535 }),
    openaiApiKey: process.env.OPENAI_API_KEY || "",
    openaiModel: process.env.OPENAI_MODEL || "gpt-5-mini",
    openaiBaseUrl: process.env.OPENAI_BASE_URL || "",
    openaiMaxOutputTokens: readInteger("OPENAI_MAX_OUTPUT_TOKENS", 1_200, {
      max: 32_000,
    }),
    appApiToken: process.env.APP_API_TOKEN || "",
    allowedOrigins: readCsv("ALLOWED_ORIGINS"),
    maxRequestsPer15Minutes: readInteger("MAX_REQUESTS_PER_15_MINUTES", 60, {
      max: 100_000,
    }),
    maxConcurrentStreams: readInteger("MAX_CONCURRENT_STREAMS", 20, {
      max: 10_000,
    }),
    streamTimeoutMs: readInteger("STREAM_TIMEOUT_MS", 120_000, {
      min: 5_000,
      max: 600_000,
    }),
  };

  if (!config.openaiApiKey) {
    throw new Error("OPENAI_API_KEY is required");
  }

  validateOptionalUrl("OPENAI_BASE_URL", config.openaiBaseUrl, {
    requireHttps: nodeEnv === "production",
  });

  if (nodeEnv === "production") {
    if (config.appApiToken.length < 32) {
      throw new Error(
        "APP_API_TOKEN must contain at least 32 characters for private production testing. " +
          "Replace this gate with real user authentication before a public release.",
      );
    }

    if (config.allowedOrigins.includes("*")) {
      throw new Error("ALLOWED_ORIGINS must not contain * in production");
    }
  }

  return config;
}
