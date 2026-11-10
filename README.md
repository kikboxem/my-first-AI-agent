# My First AI Agent — Public Time-Zone Demo

A simple public AI-agent portfolio project built with Python, Gradio, [Hugging Face smolagents](https://github.com/huggingface/smolagents), and Groq-hosted GPT-OSS 120B.

The agent has one custom Python tool, `get_current_time_in_timezone`, which uses an IANA time-zone identifier (e.g., `Asia/Tokyo`) to return the local time.

## Security and budget controls

- The public demo has **no login requirement**.
- An atomic Redis Lua check enforces three **rolling-window** limits: **5 requests per visitor per hour**, **5 requests globally per minute**, and **30 requests globally per 24 hours**.
- Redis counters are shared across app instances and survive restarts of the **app**. They survive restarts of the Redis server only if the Redis provider has persistence enabled.
- **Fail closed**: if Redis is missing or unreachable, the app does **not** call Groq.
- The input is restricted to 300 characters; the agent has at most 3 steps per request; Gradio handles only one agent request at a time.
- Visitor identifiers are pseudonymized with a keyed SHA-256 HMAC rather than storing raw IP addresses in Redis.
- Redis rate limits are **not** a substitute for bot detection, provider-side budgets, or a WAF. Client IP identification is best-effort behind proxies.

## Deploying to Render

1. Create a Python web service from this GitHub repository.
2. Use build command: `pip install -r requirements.txt`
3. Use start command: `python app.py`
4. Set these **service environment variables** in Render (never commit secrets):
   - `GROQ_API_KEY`: a Groq API key authorized to use `openai/gpt-oss-120b`
   - `REDIS_URL`: connection URL to a Redis/Valkey service (e.g., a Render Key Value instance in the same region or Upstash Redis).
5. Deploy. Once Redis is reachable, public questions are accepted within the limits.

**Important:** Render Free Key Value instances can lose their contents if the Key Value instance restarts. For stronger quota continuity, choose a provider/plan offering persistence.

## Test prompts

- What time is it in Tokyo?
- What is the current time in Copenhagen?
- What time is it in Pune?

## Design notes

A `ToolCallingAgent` is used instead of allowing unrestricted AI-generated Python execution on a public server. Only one controlled custom tool is exposed. Rate limiting is performed before the model call, regardless of whether the request comes from the Gradio UI or its backend API.

MIT License.
