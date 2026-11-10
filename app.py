"""Public time-zone agent with Redis-backed, fail-closed request limits."""

import datetime
import hashlib
import hmac
import ipaddress
import json
import os
import uuid

import gradio as gr
import pytz
import redis
from smolagents import OpenAIServerModel, ToolCallingAgent, tool
from smolagents.models import ChatMessageToolCall, ChatMessageToolCallFunction

# Sliding-window limits are checked and recorded atomically in Redis.
# Global limits cap usage even if someone rotates IP addresses.
LIMITS = (
    (5, 60 * 60 * 1000),        # 5 requests per IP per rolling hour
    (5, 60 * 1000),             # 5 requests globally per rolling minute
    (30, 24 * 60 * 60 * 1000),  # 30 requests globally per rolling 24 hours
)

RATE_LIMIT_LUA = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
local limits = { tonumber(ARGV[1]), tonumber(ARGV[3]), tonumber(ARGV[5]) }
local windows = { tonumber(ARGV[2]), tonumber(ARGV[4]), tonumber(ARGV[6]) }
for i = 1, 3 do
  redis.call('ZREMRANGEBYSCORE', KEYS[i], '-inf', now - windows[i])
  if redis.call('ZCARD', KEYS[i]) >= limits[i] then
    return i
  end
end
for i = 1, 3 do
  redis.call('ZADD', KEYS[i], now, ARGV[7])
  redis.call('PEXPIRE', KEYS[i], windows[i])
end
return 0
"""



class GroqCompatibleModel(OpenAIServerModel):
    """Handle Groq's tool-choice requirement during multi-step agent runs."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tool_ran = False

    def generate(self, messages, **kwargs):
        # A tool is required for the first step. Once a real tool has been
        # called, Groq may naturally produce a plain-language final response,
        # which its API rejects if tool_choice remains 'required'.
        kwargs["tool_choice"] = "auto" if self._tool_ran else "required"
        result = super().generate(messages, **kwargs)
        if result.tool_calls:
            if any(call.function.name != "final_answer" for call in result.tool_calls):
                self._tool_ran = True
            return result

        # smolagents ToolCallingAgent expects final answers to arrive as a
        # final_answer tool call; normalize a plain response after tool use.
        if self._tool_ran and isinstance(result.content, str) and result.content.strip():
            final_text = result.content.strip()
            # Groq sometimes emits a JSON tool-call envelope as ordinary text.
            # Decode it so visitors see the answer, not the envelope.
            candidate = final_text
            if candidate.startswith("```"):
                candidate = candidate.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            try:
                obj = json.loads(candidate)
                if (
                    isinstance(obj, dict)
                    and obj.get("name") == "final_answer"
                    and isinstance(obj.get("arguments"), dict)
                    and isinstance(obj["arguments"].get("answer"), str)
                ):
                    final_text = obj["arguments"]["answer"]
            except (ValueError, TypeError):
                pass

            result.tool_calls = [
                ChatMessageToolCall(
                    function=ChatMessageToolCallFunction(
                        name="final_answer",
                        arguments={"answer": final_text},
                    ),
                    id="call_final_response",
                    type="function",
                )
            ]
        return result

@tool
def get_current_time_in_timezone(timezone: str) -> str:
    """Get the current local date and time for an IANA time zone.

    Args:
        timezone: An IANA time-zone identifier such as Asia/Tokyo or Europe/Copenhagen.
    """
    try:
        zone = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        return "Unknown time zone. Try a name such as Asia/Tokyo."
    return datetime.datetime.now(zone).strftime("%A, %d %B %Y, %H:%M:%S %Z")


def visitor_identifier(request: gr.Request) -> str:
    """Best-effort IP identity; global quotas remain authoritative."""
    headers = getattr(request, "headers", {}) or {}
    forwarded = headers.get("x-forwarded-for", "")
    # Render adds forwarding information at its proxy. Prefer the last valid
    # forwarded address rather than trusting a caller-supplied first entry.
    candidates = [s.strip() for s in forwarded.split(",") if s.strip()]
    client = getattr(request, "client", None)
    # Per-IP identity is best-effort; global quotas cannot be evaded by IP rotation.
    addresses = []
    for candidate in candidates:
        try:
            addresses.append(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    if addresses:
        public = [addr for addr in addresses if addr.is_global]
        ip = str(public[-1] if public else addresses[-1])
    elif client is not None and getattr(client, "host", None):
        ip = str(client.host)
    else:
        ip = "unidentified"
    # Use a stable secret-keyed pseudonym instead of storing raw IP addresses.
    secret = os.environ["GROQ_API_KEY"].encode("utf-8")
    return hmac.new(secret, ip.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def check_rate_limit(request: gr.Request) -> str | None:
    """Return error text on denial. Failure of Redis always denies inference."""
    url = os.getenv("REDIS_URL")
    if not url:
        return "Demo temporarily unavailable: rate-limit storage is not configured."
    try:
        client = redis.Redis.from_url(
            url, decode_responses=True,
            socket_connect_timeout=2, socket_timeout=2,
        )
        ip_hash = visitor_identifier(request)
        keys = [
            f"portfolio:agent:ip:{ip_hash}",
            "portfolio:agent:global:minute",
            "portfolio:agent:global:day",
        ]
        argv = [
            LIMITS[0][0], LIMITS[0][1],
            LIMITS[1][0], LIMITS[1][1],
            LIMITS[2][0], LIMITS[2][1],
            uuid.uuid4().hex,
        ]
        decision = int(client.eval(RATE_LIMIT_LUA, len(keys), *keys, *argv))
    except (redis.RedisError, ValueError, TypeError, OSError):
        # Never call Groq if counters cannot be checked.
        return "Demo temporarily unavailable. Please try again later."
    return {
        0: None,
        1: "You've reached 5 requests in the last hour. Please try again later.",
        2: "The demo is busy. Please try again in a minute.",
        3: "The daily demo allowance has been used. Please try again tomorrow.",
    }.get(decision, "Demo temporarily unavailable. Please try again later.")


def ask_agent(message: str, request: gr.Request) -> str:
    """All UI and Gradio API requests pass through this same limiter."""
    message = (message or "").strip()
    if not message or len(message) > 300:
        return "Please enter a question of at most 300 characters."

    denied = check_rate_limit(request)
    if denied:
        return denied

    try:
        model = GroqCompatibleModel(
            model_id="openai/gpt-oss-120b",
            api_base="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
            max_tokens=512,
        )
        agent = ToolCallingAgent(
            tools=[get_current_time_in_timezone],
            model=model,
            max_steps=3,
        )
        return str(agent.run(message))
    except Exception as error:
        # Do not log credentials, exception bodies, user prompts or response data.
        print(
            "AGENT_FAILURE",
            type(error).__name__,
            "status", getattr(error, "status_code", "unknown"),
            flush=True,
        )
        return "The model request failed. Please try again later."


if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Set GROQ_API_KEY as a secret in Render.")

    demo = gr.Interface(
        fn=ask_agent,
        inputs=gr.Textbox(label="Your question", placeholder="What time is it in Tokyo?", lines=2),
        outputs=gr.Textbox(label="Agent answer"),
        title="My First AI Agent",
        description="Public demo with a custom time-zone tool and Redis-backed request limits (5/hour per visitor; 30/day total).",
        examples=["What time is it in Tokyo?", "What is the current time in Copenhagen?"],
        cache_examples=False,
        analytics_enabled=False,
        flagging_mode="never",
    )
    demo.queue(default_concurrency_limit=1, max_size=10).launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "10000")),
        show_error=False,
    )
