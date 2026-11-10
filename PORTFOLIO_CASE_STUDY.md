# ValuePilot — Private Sales Opportunity Audit (Case Study)

## Problem

Sales teams can lose track of opportunities when task dates are missed or CRM contact histories become stale. An ordinary chatbot can analyze a CSV, but repeated manual uploads, variable reasoning, privacy questions, and a lack of reproducible scoring may create operational friction.

**Opportunity, not a validated market claim:** provide a repeatable local-first audit that transforms an authorized CRM export into a reviewable action list without sending business records to a model provider.

## Implemented solution

**Default mode:** A single-screen CSV audit with:

- Input validation and explicit required schema.
- Deterministic scoring and explainable flags (overdue tasks, 14+ day stale contact, missing due date, no contact recorded).
- Ranked opportunities and separate metrics for weighted pipeline and flagged opportunities.
- Human-readable recommended next steps, always subject to approval.
- Exportable CSV report with formula-injection protection.
- Entire processing in browser memory: no upload, cookies, third-party frontend packages or inference calls for CSV analysis.
- Cloud-hosted demo and local-only alternative.

**Optional AI mode:** A model selects one of four Python tools for simplified ROI, sales uplift, lead priority, or international time. A tool result is returned directly rather than trusting the model to recalculate. The public endpoint is Redis rate-limited; the private local instance can use Ollama.

## Why this instead of an ordinary chatbot?

| Business requirement | ValuePilot implementation |
|---|---|
| Avoid sharing CRM rows with a cloud model | CSV never leaves the browser |
| Repeated review of similar records | Same deterministic algorithm for each run |
| Explain why an opportunity was flagged | Visible status/rule and explicit scoring formula |
| Turn analysis into a business action | Downloadable, human-reviewable next-action CSV |
| Control inference expenses | No AI model tokens in CSV mode |
| Preserve business oversight | No automatic emails or changes to the CRM |
| Audit changes to the algorithm | Public source, reproducible fixtures and CI tests |

This is a prototype, not a claim that the product is uniquely capable or commercially validated. Existing CRM platforms may offer comparable or superior features.

## Reproducible demonstration

1. Open the public URL or run locally.
2. Select **CSV lead audit** (the default tab).
3. Choose **Load synthetic sample**.
4. Review the ranked records and flags.
5. Select **Export ranked report** and inspect the added decision columns.
6. Review the algorithm in `csv_audit.js` and the automated tests under `tests/`.

The synthetic example contains **8 opportunity rows** and deliberately includes missed follow-ups and closed deals. It proves the workflow produces deterministic output, not that it increases actual sales.

## Architecture and operating costs

- **Data processing:** Browser JavaScript. Zero inference API calls per CSV audit, zero server storage of uploaded data.
- **Frontend:** Self-hosted HTML/CSS/JS, no third-party browser bundles.
- **Backend (optional AI demo):** Python, FastAPI, Hugging Face smolagents.
- **Public AI inference:** Groq API (plan allowances and provider terms apply).
- **Private AI inference:** Ollama with an installed open-weight model, on a loopback-only server.
- **Public host:** Render Free; Redis limiter on a free database tier (subject to provider limitations).
- **Local deployment:** Existing Windows machine; no new cloud account or cloud inference fee for CSV processing. Electricity, equipment and time are real costs.

## Quality and responsibility

- **Security:** Strict same-origin CSP; no inline JS/CSS; CSV formula-injection mitigation; fixed data limits and validation; no personal-data upload endpoint.
- **Privacy:** Local-in-browser analysis and no persistence by default; any real CRM processing requires organizational authorization and applicable notices.
- **Accessibility:** Keyboard-operable controls, semantic headings/table, status announcements, visible focus, responsive fallback. A formal WCAG 2.2 AA audit has **not** been performed.
- **Sustainability:** Models are not invoked for work that deterministic code can solve. Energy consumption and emissions are **not measured**, so no carbon savings are claimed.
- **Transparency:** Lead priority is a business-rule heuristic; win probability is user-supplied. Scores are not estimates of causal revenue recovery.
- **SDGs:** Design principles are relevant to Goals 8, 9, 12, 13 and 16, but this prototype does not claim certified SDG compliance or quantified impact.

## Evidence and honest limitations

- Local Node tests for CSV parsing, scoring, data validation and safe export.
- Python HTTP tests for routes, local access restrictions and browser security headers.
- CI pipeline in GitHub Actions.
- Browser-level proof that the synthetic CSV renders and the desktop application does not require page scrolling at 1440×900.

**Not implemented:** automated CRM synchronization, automatic lead contact, validated conversion uplift, audit trails for approvals, enterprise authentication, real production users, legal compliance certification, independently measured sustainability outcomes.

## Next validation stage

Run a permissioned pilot with anonymized historical opportunity data. Compare generated flags against manually reviewed ground truth; measure precision, recall, staff review time, accepted actions, follow-up completion, actual outcomes and total cost. Only then consider claims about revenue impact or environmental efficiency.

This portfolio project was developed with substantial AI coding assistance. It demonstrates an end-to-end collaborative implementation and testing workflow, **not independent authorship of all code**.
