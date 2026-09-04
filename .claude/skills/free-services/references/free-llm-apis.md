# Free LLM APIs for Claude Code

453+ free models from 31 providers. All expose OpenAI-compatible endpoints.

Source: `awesome-free-llm-apis` (MIT) · Live data: freellm.net

## Claude Code Configuration

Claude Code reads `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` from the environment.
Set them to route calls through any free backend instead of the paid Anthropic API.

**⚠ Never commit API keys to git. Always set via environment variables or `.env` files.**

```bash
# Add to ~/.bashrc or ~/.zshrc (NOT to any repo file)
export ANTHROPIC_BASE_URL="https://api.groq.com/openai/v1"
export ANTHROPIC_AUTH_TOKEN="gsk_your_key_here"
```

---

## Provider Quick Reference

| Provider | Base URL | Free Tier | Card? | Key Link |
|---|---|---|---|---|
| **Groq** | `https://api.groq.com/openai/v1` | 14,400 req/day, 30 RPM | ❌ No | console.groq.com/keys |
| **OpenRouter** | `https://openrouter.ai/api/v1` | 35+ free models, 50 req/day | ❌ No | openrouter.ai/keys |
| **NVIDIA NIM** | `https://integrate.api.nvidia.com/v1` | No daily token cap, 40 RPM | ❌ No | build.nvidia.com |
| **Cloudflare AI** | `https://api.cloudflare.com/…/ai/v1` | 10,000 req/day | ❌ No | cloudflare.com/dashboard |
| **SiliconFlow** | `https://api.siliconflow.cn/v1` | Generous free tier | ❌ No | cloud.siliconflow.cn |
| **Google AI Studio** | `https://generativelanguage.googleapis.com/v1beta/openai` | Gemini 2.5 Flash free | ❌ No | aistudio.google.com/apikey |
| **Mistral** | `https://api.mistral.ai/v1` | Free tier (rate limited) | ❌ No | console.mistral.ai |
| **Cohere** | `https://api.cohere.ai/v1` | Trial key, 5 req/min | ❌ No | dashboard.cohere.com |

## Recommended Models per Provider

| Provider | Best Free Model | Context | Strength |
|---|---|---|---|
| Groq | `llama-3.3-70b-versatile` | 128K | Speed, general purpose |
| Groq | `qwen-3-32b` | 128K | Reasoning, coding |
| OpenRouter | `google/gemini-2.5-flash:free` | 1M | Long context |
| OpenRouter | `openai/gpt-oss-120b:free` | 128K | Coding |
| NVIDIA NIM | `meta/llama-3.3-70b-instruct` | 128K | General |
| NVIDIA NIM | `deepseek-ai/deepseek-r1` | 128K | Reasoning |
| Google AI Studio | `gemini-2.5-flash-preview` | 1M | Multimodal, long context |

## Per-Tool Setup

### Claude Code (cc)

```bash
# Groq (recommended start — no credit card)
export ANTHROPIC_BASE_URL="https://api.groq.com/openai/v1"
export ANTHROPIC_AUTH_TOKEN="gsk_your_groq_key"

# OpenRouter (most model variety)
export ANTHROPIC_BASE_URL="https://openrouter.ai/api/v1"
export ANTHROPIC_AUTH_TOKEN="sk-or-v1-your_openrouter_key"

# NVIDIA NIM (no daily token cap)
export ANTHROPIC_BASE_URL="https://integrate.api.nvidia.com/v1"
export ANTHROPIC_AUTH_TOKEN="nvapi-your_nvidia_key"
```

**Caveats:**
- Not all free backends support every Claude Code tool/capability
- If you hit errors, use Llama 3.3 70B+ or DeepSeek R1
- Rate limits apply: Groq 14,400/day · NIM 40 RPM · OpenRouter 50/day (free tier)

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="gsk_your_key",  # from env: os.getenv("GROQ_API_KEY")
)
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Hello"}],
)
```

### Cursor

```
Settings → Models → Add Model
  Model name: llama-3.3-70b-versatile
  Base URL:   https://api.groq.com/openai/v1
  API key:    your-groq-key
```

### Codex CLI

```bash
export OPENAI_BASE_URL="https://api.groq.com/openai/v1"
export OPENAI_API_KEY="your-groq-key"
codex --model "llama-3.3-70b-versatile"
```

## Getting Your Keys (< 2 minutes each)

1. **Groq** — groq.com → Sign up with email → Console → API Keys → Create
2. **OpenRouter** — openrouter.ai → Sign in → Keys → Create Key
3. **NVIDIA NIM** — build.nvidia.com → Sign up → Settings → API Keys → Generate
4. **Google AI Studio** — aistudio.google.com → Get API Key → Create in new project

## Security Rules

- ✅ Store keys in environment variables or a `.env` file (gitignored)
- ✅ Add `.env` to `.gitignore` before creating it
- ❌ Never paste a key directly into source code
- ❌ Never commit a file containing a key
- ❌ Never share keys in chat, issues, or pull requests

```bash
# .env (gitignored)
ANTHROPIC_BASE_URL=https://api.groq.com/openai/v1
ANTHROPIC_AUTH_TOKEN=gsk_your_key_here
```

```bash
# Load in your shell session
source .env
# or: set -a; source .env; set +a
```
