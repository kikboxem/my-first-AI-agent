"""Render entry point for the ValuePilot commercial AI agent."""
import os
from server import app

if __name__ == "__main__":
    import uvicorn
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Configure GROQ_API_KEY in Render environment variables.")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
