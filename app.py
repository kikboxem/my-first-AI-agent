"""ValuePilot entry point: cloud Render mode or private, offline Ollama mode."""
import os
from server import app

if __name__ == "__main__":
    import uvicorn
    local = os.getenv("VALUEPILOT_LOCAL_MODE") == "1"
    if not local and not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Configure GROQ_API_KEY in Render environment variables.")
    uvicorn.run(
        app,
        host="127.0.0.1" if local else "0.0.0.0",
        port=int(os.getenv("PORT", "8765" if local else "10000")),
    )
