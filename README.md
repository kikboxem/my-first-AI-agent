# ValuePilot — Commercial AI Agent

A public, responsive AI portfolio project that demonstrates **measurable business reasoning** using Hugging Face `smolagents`, Groq's hosted GPT-OSS 120B, and deterministic Python tools.

**[Try the live website](https://my-first-ai-agent-8sea.onrender.com)**

## What it demonstrates

- **Automation ROI:** model labor capacity unlocked by automation, annual software/setup costs, net first-year value, ROI and setup payback.
- **Sales pipeline uplift:** model incremental expected deals, revenue and gross profit from a hypothetical change in conversion rate.
- **Lead prioritization:** compute probability-weighted gross profit per estimated selling hour to compare opportunities.
- **International coordination:** retrieve local time in **12-hour AM/PM format with full time-zone names**, taking daylight saving time into account.

All outputs are illustrative **scenarios, not verified financial outcomes or guaranteed savings**. Tools use explicitly supplied inputs, not invented customer or company data. The application does not send emails, scrape private accounts, or make purchases.

## Architecture

**UI:** Custom responsive HTML/CSS/JavaScript served by FastAPI rather than Gradio's default interface.

**Orchestration:** Hugging Face `ToolCallingAgent` selects one of four deterministic Python tools. A Groq-compatible model adapter selects exactly one custom Python tool. A specialized smolagents subclass returns the verified tool's result directly, avoiding a fragile second model call.

**Security & availability:**
- Public site without a username/password challenge.
- Redis atomic rolling-window quotas: **5 queries/visitor/hour**, **5 total queries/minute**, and **30 total queries/24 hours**.
- Fails closed if Redis is missing or unavailable, preventing unmetered model calls.
- Basic IP pseudonymization, input validation (300 characters), 2 concurrent requests and 3 agent steps maximum.
- Private `GROQ_API_KEY` and `REDIS_URL` server-side environment variables; no secrets in GitHub.
- No CAPTCHA; legitimate automated access is allowed within the same budgets.
- These protections are appropriate for a small portfolio demonstration but do **not** replace WAF protections or provider-side spend limits.

## Deploy on Render

Create a **Python** web service connected to this repository:

- Build command: `pip install -r requirements.txt`
- Start command: `python app.py`
- Region: select the nearest supported region
- Environment variables:
  - `GROQ_API_KEY`: Groq API key authorized for `openai/gpt-oss-120b`
  - `REDIS_URL`: full Redis URL. For Upstash TCP/TLS, use `rediss://...` (never commit the password)

The `app.py` file is the entrypoint; `server.py` contains the agent/API; `index.html` contains the polished public interface.

## Test examples

1. "What time is it in Tokyo?"
2. "We have 200 qualified leads monthly, current win rate 10%, target 12%, average deal USD 3,000 and gross margin 35%. Estimate additional revenue and gross profit."
3. "12 staff save 3 hours weekly each, loaded labor cost USD 35/h, 50% realized economic value, USD 300 monthly software fee, USD 2,000 setup cost. Calculate year-one ROI."
4. "Evaluate a USD 20,000 opportunity, 35% gross margin, 60% win probability, requiring 10 sales hours."

**The purpose:** showcase how reliable business rules and agent-driven tool selection can assist customer-facing and operations teams. Financial benefits are hypothetical until validated using real company data.

MIT licensed.
