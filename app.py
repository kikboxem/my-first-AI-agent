"""First AI agent: time-zone assistant using smolagents and Groq."""

import datetime
import os

import gradio as gr
import pytz
from smolagents import OpenAIServerModel, ToolCallingAgent, tool


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


def ask_agent(message: str) -> str:
    """Accept a short time-zone question and run the agent."""
    message = (message or "").strip()
    if not message or len(message) > 300:
        return "Please enter a time-zone question of at most 300 characters."

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
    username = os.environ.get("APP_USERNAME")
    password = os.environ.get("APP_PASSWORD")
    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError("Set GROQ_API_KEY in Render environment variables.")
    if not username or not password:
        raise RuntimeError("Set APP_USERNAME and APP_PASSWORD in Render environment variables.")

    demo = gr.Interface(
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
        auth=(username, password),
        show_error=False,
    )
