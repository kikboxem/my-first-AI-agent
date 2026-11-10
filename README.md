# ValuePilot — Private Sales Opportunity Audit + AI Agent Demo

**[Public demo](https://my-first-ai-agent-8sea.onrender.com/)** · [Local installation](#run-entirely-on-your-own-computer) · [Security and sustainability](#privacy-security-accessibility-and-sustainability)

A single-screen demonstration of useful, reviewable business workflow automation. Unlike a generic chatbot, the default **CSV lead audit** processes a CRM export into a prioritized, downloadable action plan. It works entirely **inside the browser**, without uploading the file to any server or AI provider.

**Status:** portfolio prototype. Not an independently validated revenue recovery product; no customer savings or environmental reductions have been measured.

## What works

**CSV lead audit (free and offline):**
- Read up to 2,000 opportunity rows / 1 MB, including quoted CSV cells; validate required columns, dates, currency codes and numeric ranges.
- Reject duplicate lead IDs, malformed inputs and mixed currencies (we intentionally do not make up exchange rates).
- Identify overdue next actions, stale contacts (14+ days), missing action dates and missing contact history.
- Rank **open** opportunities using a documented **review heuristic** based on opportunity value × user-supplied win probability, with boosts for neglected follow-ups.
- Report counts and probability-weighted pipeline value, **not** proven incremental or recoverable revenue.
- Provide suggested next actions that **require human review**. No email or CRM write access is enabled.
- Export all ranked rows to a CSV with spreadsheet-formula injection mitigation. The table displays the first 100; export includes all records.
- Run with **zero network requests during analysis**, zero inference tokens, and no persistent storage.

**Agent demonstrations (separate):** tool selection for automation ROI, sales win-rate scenarios, single-lead prioritization and full-name AM/PM world time. Public inference uses Groq, guarded by Redis limits. Local inference can instead use Ollama.

### Input schema

Exact required CSV headers (order does not matter; additional columns are ignored):

\`\`\`csv
lead_id,company,deal_value,currency,stage,last_contact_date,owner,win_probability_percent,next_action_due_date
\`\`\`

- \`deal_value\`: nonnegative amount in the declared currency. \`win_probability_percent\`: 0–100, supplied by the business.
- Dates: ISO \`YYYY-MM-DD\`, or blank for unknown.
- Stages \`won\`, \`closed won\`, \`lost\`, \`closed lost\` and \`disqualified\` are treated as closed; other stages are open.
- All opportunities in a CSV must use one currency. No currency exchange assumptions are made.
- No emails or telephone numbers are required. Do not upload sensitive CRM exports without authorization.

**Priority formula** (for open opportunities only):

\`\`\`text
expected_revenue = deal_value × supplied_win_probability / 100
priority_score = expected_revenue × (1 + 0.30 if overdue
                                      + 0.15 if stale
                                      + 0.10 if missing_due_date)
\`\`\`

Closed opportunities have zero active ranking score and are excluded from the active pipeline metrics. This heuristic is intended for **triage**, not financial forecasting; boosts were chosen as transparent demonstration parameters, **not** learned/validated probabilities. The user should calibrate it with historical win/loss outcomes before production use.

## Ubuntu 26.04 Docker deployment

The project includes a tested **Ubuntu 26.04 LTS Dockerfile**, a loopback-only Docker Compose configuration, non-root runtime and a Docker build/smoke-test job in GitHub Actions. See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for secure WSL2 instructions and Render runtime migration.

## Run entirely on your own computer

### Fastest: CSV-only, no Python dependencies

1. Download/clone the repository.
2. Double-click \`index.html\` (with \`csv_audit.js\` and \`csv_ui.js\` in the same directory).
3. Select **CSV lead audit** and click **Load synthetic sample** to try it.

All CSV reading, scoring and exporting occurs in your browser's memory. Other tools call an API and need the server described below.

### Full local application on Windows

1. Install Python 3.11+ and clone/download this repo.
2. Double-click \`start-local.bat\`. First run creates \`.venv\` and installs dependencies; subsequent runs reuse it.
3. Open **http://127.0.0.1:8765/**. Only your computer can reach this server because it binds to \`127.0.0.1\`.

For **optional local AI inference** (no Groq key, no Redis required), install [Ollama](https://ollama.com/), pull a tool-capable model such as \`llama3.2:3b\`, and run Ollama. The local server tries \`http://127.0.0.1:11434/v1\`. Model tool-calling performance depends on the selected model and hardware. The **CSV audit requires no model and works without Ollama**.

Alternatively, run manually:

\`\`\`powershell
$env:VALUEPILOT_LOCAL_MODE="1"
$env:PORT="8765"
python app.py
\`\`\`

Local mode disables the external Redis and Groq dependency for requests served on loopback. The cloud mode still uses protected inference with Redis quotas. Do not set local mode on a public server.

### Public Render deployment

- Python web service: build \`pip install -r requirements.txt\`, start \`python app.py\`
- Environment: \`GROQ_API_KEY\` and \`REDIS_URL\` (Upstash \`rediss://...\` or internal Redis URL).
- CSV files are **never uploaded** even when the public demo is used.
- Non-CSV model calls use global/visitor rolling-window Redis limits (5/user/hour, 5/min globally, 30/24h globally); fail closed if Redis is unavailable.

## Automated tests

The core audit is dependency-free JavaScript. Run:

\`\`\`powershell
node tests/test_csv_audit.cjs
\`\`\`

Tests cover parsing, dates, duplicate IDs, currency consistency, ranking, closed opportunities, quoted fields, spreadsheet-formula injection, and a synthetic fixture. Review actual tests in \`tests/\`.

## Privacy, security, accessibility and sustainability

- **Privacy by design:** CSV input stays in browser memory. No CRM API token, cookies, cloud storage, external tracking, third-party UI libraries, upload endpoint, automated outreach or data retention for the audit.
- **Security:** 1 MB and 2,000-row constraints; strict schema; no HTML rendering of uploaded cell values; formula injection mitigation for CSV export; explicit opt-in file selection; restrictive Content Security Policy with self-hosted scripts/styles; server-side Redis rate limits for paid-model endpoints.
- **Accessible design:** labeled file controls, semantic table, keyboard-friendly buttons, live region for outcomes, visible focus indicators, responsive/mobile fallback, and reduced-motion support. These are implementation measures, **not a formal WCAG certification**.
- **Sustainable cost design:** no LLM inference for data analysis, no large frontend libraries, and local-first computation. **Energy and CO2 savings have not been measured**; local compute still consumes electricity.
- **Fairness and accountability:** uses business-supplied criteria only, no protected-attribute scoring, provides rationale, and requires a human decision before contacting anyone. Biased or inaccurate inputs can still bias outcomes.
- **SDG alignment (intent only, not verified impact):** SDG 8 (productivity and decent work), SDG 9 (responsible infrastructure), SDG 12 (resource efficiency), SDG 13 (measured energy awareness), SDG 16 (transparency/accountability). This product does **not** claim compliance with all 17 SDGs.
- **GDPR:** browser-local processing helps data minimization, but this prototype has **not been audited for legal compliance**; organizations must establish their own lawful basis, notices, retention policy and contracts.

## Trade-offs and next validation

This prototype cannot infer actual close probabilities, guarantee revenue recovery or causally attribute revenue gains to its recommendations. To validate against real customers, conduct a consented pilot with historical CRM data and measure precision of flags, recall of missed follow-ups, human acceptance of suggestions, closed-deal outcomes versus an appropriate baseline, operating cost per reviewed lead, and accessibility and security assessments.

**Development:** built with AI coding assistance and human review. Useful for demonstrating requirements decomposition, developer workflow, testing and responsible implementation, **not evidence of unaided coding or commercial revenue**.

MIT license.
