"""First AI agent: time-zone assistant using smolagents and Groq."""

import datetime
import os

import gradio as gr
import pytz
from smolagents import OpenAIServerModel, ToolCallingAgent, tool
from collections import deque
from threading import Lock
from time import monotonic

@tool
def get_current_time_in_timezone(timezone: str) -> str:
    """Get the current local date and time for an IANA time zone.

    Args:
        timezone: Time-zone identifier, for example Asia/Tokyo or Europe/Copenhagen.
    """
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        return f"Unknown time zone: {timezone}. Use an IANA name like Asia/Tokyo."
    return datetime.datetime.now(tz).strftime("%A, %d %B %Y, %H:%M:%S %Z")


def ask_agent(message: str, request: gr.Request) -> str:
    message = (message or "").strip()

    if not message or len(message) > 300:
        return "Enter a question of up to 300 characters."

    limit_message = check_rate_limit(request)
    if limit_message:
        return limit_message

    # Keep your existing try/except and agent code below.

    try:
        model = OpenAIServerModel(
            model_id="openai/gpt-oss-120b",
            api_base="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
        )
        agent = ToolCallingAgent(
            tools=[get_current_time_in_timezone],
            model=model,
            max_steps=3,
        )
        return str(agent.run(message))
    except Exception:
        return "The request could not be completed. Please try again, or check the Render logs."


if __name__ == "__main__":
    
    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError("Set GROQ_API_KEY in Render environment variables.")
    if not username or not password:
        raise RuntimeError("Set APP_USERNAME and APP_PASSWORD in Render environment variables.")

    demo = gr.Interface(
        
# Basic in-memory request limits
PER_IP_LIMIT = 5
PER_IP_WINDOW = 3600
GLOBAL_LIMIT = 30
GLOBAL_WINDOW = 86400

ip_requests = {}
global_requests = deque()
rate_lock = Lock()

def check_rate_limit(request: gr.Request):
    forwarded = (
        request.headers.get("x-forwarded-for", "")
        if request else ""
    )
    ip = forwarded.split(",")[0].strip() or (
        request.client.host
        if request and request.client else "unknown"
    )

    now = monotonic()

    with rate_lock:
        while global_requests and global_requests[0] <= now - GLOBAL_WINDOW:
            global_requests.popleft()

        # Remove expired visitors
        for key, times in list(ip_requests.items()):
            while times and times[0] <= now - PER_IP_WINDOW:
                times.popleft()
            if not times:
                del ip_requests[key]

        if len(global_requests) >= GLOBAL_LIMIT:
            return "Daily demo limit reached. Try again later."

        times = ip_requests.setdefault(ip, deque())

        if len(times) >= PER_IP_LIMIT:
            return "Hourly limit reached. Try again later."

        times.append(now)
        global_requests.append(now)

    return None

        fn=ask_agent,
        inputs=gr.Textbox(label="Your question", placeholder="What time is it in Tokyo?", lines=2),
        outputs=gr.Textbox(label="Agent answer"),
        title="My First AI Agent",
        description="A small smolagents project that uses a custom tool to answer time-zone questions.",
        examples=["What time is it in Tokyo?", "What is the current time in Copenhagen?"],
    )
    demo.queue(default_concurrency_limit=1, max_size=10).launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "10000")),
        show_error=False,
    )
