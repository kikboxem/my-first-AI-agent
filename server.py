"""ValuePilot — a public, Redis-protected agent for commercial decision modeling."""
import datetime
import hashlib
import hmac
import ipaddress
import logging
import os
import re
import threading
import uuid
from pathlib import Path

import pytz
import redis
from babel.dates import get_timezone_name
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from smolagents import OpenAIServerModel, ToolCallingAgent, tool
from smolagents.agents import ActionOutput, ToolOutput

app = FastAPI(title="ValuePilot", docs_url=None, redoc_url=None, openapi_url=None)
log = logging.getLogger("valuepilot")
gate = threading.BoundedSemaphore(2)
root = Path(__file__).resolve().parent
_redis = None
_redis_lock = threading.Lock()

# Rolling limits: visitor/hour, everyone/minute, everyone/24 hours.
LIMITS = ((5, 3600000), (5, 60000), (30, 86400000))
LUA = """
local t=redis.call('TIME')
local n=tonumber(t[1])*1000+math.floor(tonumber(t[2])/1000)
local limits={tonumber(ARGV[1]),tonumber(ARGV[3]),tonumber(ARGV[5])}
local periods={tonumber(ARGV[2]),tonumber(ARGV[4]),tonumber(ARGV[6])}
for i=1,3 do
 redis.call('ZREMRANGEBYSCORE',KEYS[i],'-inf',n-periods[i])
 if redis.call('ZCARD',KEYS[i])>=limits[i] then return i end
end
for i=1,3 do
 redis.call('ZADD',KEYS[i],n,ARGV[7])
 redis.call('PEXPIRE',KEYS[i],periods[i])
end
return 0
"""

def redis_client():
    global _redis
    if _redis is None:
        with _redis_lock:
            if _redis is None:
                url = os.getenv("REDIS_URL")
                if not url:
                    raise RuntimeError("No REDIS_URL")
                _redis = redis.Redis.from_url(url, decode_responses=True,
                                             socket_connect_timeout=2, socket_timeout=2)
    return _redis

def visitor_id(request: Request):
    addresses = []
    for raw in request.headers.get("x-forwarded-for", "").split(","):
        try:
            address = ipaddress.ip_address(raw.strip())
            if address.is_global:
                addresses.append(str(address))
        except ValueError:
            pass
    ip = addresses[-1] if addresses else (request.client.host if request.client else "unknown")
    return hmac.new(os.environ["GROQ_API_KEY"].encode(), ip.encode(), hashlib.sha256).hexdigest()[:32]

def quota(request: Request):
    try:
        keys = [f"valuepilot:v1:ip:{visitor_id(request)}",
                "valuepilot:v1:global:minute", "valuepilot:v1:global:day"]
        args = [LIMITS[0][0], LIMITS[0][1], LIMITS[1][0], LIMITS[1][1],
                LIMITS[2][0], LIMITS[2][1], uuid.uuid4().hex]
        return int(redis_client().eval(LUA, len(keys), *keys, *args))
    except (redis.RedisError, OSError, ValueError, TypeError, RuntimeError):
        log.warning("REDIS_QUOTA_UNAVAILABLE")
        return -1

def checks(currency, fields):
    code = currency.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise ValueError("Currency must be a 3-letter label such as USD, INR or EUR.")
    for label, value, minimum, maximum in fields:
        if not minimum <= value <= maximum:
            raise ValueError(f"{label}: must be between {minimum:g} and {maximum:g}.")
    return code

def fmt(value, code):
    return f"{code} {value:,.2f}"

@tool
def get_current_time_in_timezone(timezone: str) -> str:
    """Get current time in AM/PM with the full local time-zone name.

    Args:
        timezone: An IANA time-zone name, such as Asia/Tokyo, Asia/Kolkata, or Europe/Copenhagen.
    """
    if len(timezone) > 128:
        return "Time-zone name too long."
    try:
        now = datetime.datetime.now(pytz.timezone(timezone))
    except pytz.UnknownTimeZoneError:
        return "Unknown time zone; try Asia/Tokyo."
    hour = now.strftime("%I").lstrip("0") or "12"
    long_name = get_timezone_name(now, width="long", locale="en_US")
    offset = now.strftime("%z")
    return (f"{now.strftime('%A, %d %B %Y')} at {hour}:{now.strftime('%M %p')} — "
            f"{long_name} (UTC{offset[:3]}:{offset[3:]}).")

@tool
def calculate_automation_roi(employees: int, weekly_hours_saved_each: float,
                             fully_loaded_hourly_cost: float, realization_percent: float,
                             monthly_software_cost: float, setup_cost: float,
                             currency: str = "USD") -> str:
    """Model first-year labor-automation value with explicit costs and realization assumptions.

    Args:
        employees: Number of staff affected.
        weekly_hours_saved_each: Estimated weekly hours saved per employee.
        fully_loaded_hourly_cost: Labor cost per hour including overhead.
        realization_percent: Share of saved time that creates economic value, between 0 and 100.
        monthly_software_cost: Monthly cost of automation software.
        setup_cost: One-time implementation cost.
        currency: Three-letter label like USD or INR. No currency conversion is performed.
    """
    try:
        c = checks(currency, [("employees",employees,1,100000),
                             ("weekly hours",weekly_hours_saved_each,0,80),
                             ("hourly cost",fully_loaded_hourly_cost,0,1e7),
                             ("realization",realization_percent,0,100),
                             ("monthly cost",monthly_software_cost,0,1e9),
                             ("setup cost",setup_cost,0,1e9)])
    except ValueError as exc:
        return str(exc)
    annual_hours = employees * weekly_hours_saved_each * 52
    value = annual_hours * fully_loaded_hourly_cost * realization_percent / 100
    costs = monthly_software_cost * 12 + setup_cost
    net = value - costs
    roi = f"{net / costs * 100:,.1f}%" if costs else "Undefined when cost is zero"
    monthly_margin = value / 12 - monthly_software_cost
    payback = f"{setup_cost / monthly_margin:,.1f} months" if monthly_margin > 0 else "Not achieved"
    return (f"ILLUSTRATIVE AUTOMATION ROI — FIRST YEAR\n"
            f"Hours recovered: {annual_hours:,.1f}/year\n"
            f"Realized capacity value: {fmt(value,c)}/year\n"
            f"First-year total cost: {fmt(costs,c)}\n"
            f"Modeled net value: {fmt(net,c)}\n"
            f"Modeled ROI: {roi}\n"
            f"Setup payback: {payback}\n"
            "Important: capacity released is NOT guaranteed cash savings; "
            "real-world economic value depends on how recovered time is used.")

@tool
def forecast_sales_uplift(qualified_leads_per_month: int, current_win_rate_percent: float,
                          target_win_rate_percent: float, average_deal_value: float,
                          gross_margin_percent: float, currency: str = "USD") -> str:
    """Calculate incremental revenue and gross profit from a hypothetical sales win-rate change.

    Args:
        qualified_leads_per_month: Monthly number of qualified sales leads.
        current_win_rate_percent: Current percentage of leads converted to customers.
        target_win_rate_percent: Hypothetical target conversion percentage.
        average_deal_value: Average revenue of a closed deal.
        gross_margin_percent: Percentage of revenue counted as gross profit.
        currency: Three-letter label like USD or INR; no exchange-rate conversion.
    """
    try:
        c = checks(currency, [("leads",qualified_leads_per_month,1,1e8),
                             ("current rate",current_win_rate_percent,0,100),
                             ("target rate",target_win_rate_percent,0,100),
                             ("deal value",average_deal_value,0,1e9),
                             ("gross margin",gross_margin_percent,0,100)])
    except ValueError as exc:
        return str(exc)
    delta_deals = qualified_leads_per_month * (target_win_rate_percent-current_win_rate_percent)/100
    revenue = delta_deals * average_deal_value
    profit = revenue * gross_margin_percent / 100
    return (f"ILLUSTRATIVE SALES UPSIDE\n"
            f"Incremental expected deals: {delta_deals:+,.1f}/month\n"
            f"Incremental revenue: {fmt(revenue,c)}/month\n"
            f"Incremental gross profit: {fmt(profit,c)}/month\n"
            f"Annualized gross profit: {fmt(profit*12,c)}\n"
            "Important: these figures are scenario arithmetic, not a prediction of actual performance.")

@tool
def prioritize_sales_lead(deal_value: float, gross_margin_percent: float,
                          win_probability_percent: float, expected_sales_hours: float,
                          currency: str = "USD") -> str:
    """Estimate a sales opportunity's probability-weighted gross profit per selling hour.

    Args:
        deal_value: Revenue if the deal closes.
        gross_margin_percent: Gross profit margin percent.
        win_probability_percent: Estimated percentage chance the opportunity closes.
        expected_sales_hours: Estimated selling effort in hours.
        currency: Three-letter label such as USD or INR; no FX conversion.
    """
    try:
        c = checks(currency, [("deal value",deal_value,0,1e9),
                             ("gross margin",gross_margin_percent,0,100),
                             ("win probability",win_probability_percent,0,100),
                             ("selling hours",expected_sales_hours,0.1,1e5)])
    except ValueError as exc:
        return str(exc)
    gross = deal_value*gross_margin_percent/100
    expected = gross*win_probability_percent/100
    return (f"ILLUSTRATIVE OPPORTUNITY VALUE\n"
            f"Gross profit if won: {fmt(gross,c)}\n"
            f"Probability-adjusted gross profit: {fmt(expected,c)}\n"
            f"Expected gross profit per selling hour: {fmt(expected/expected_sales_hours,c)}\n"
            "Compare opportunities using consistent inputs; this excludes sales costs, "
            "and win probability is subjective.")

TOOLS = [get_current_time_in_timezone, calculate_automation_roi,
         forecast_sales_uplift, prioritize_sales_lead]

class SelectToolModel(OpenAIServerModel):
    """Require selection of one custom Python tool, not a generated final answer."""
    def generate(self, messages, **kwargs):
        available = kwargs.get("tools_to_call_from") or []
        kwargs["tools_to_call_from"] = [
            item for item in available if item.name != "final_answer"
        ]
        kwargs["tool_choice"] = "required"
        reply = super().generate(messages, **kwargs)
        if reply.tool_calls:
            reply.tool_calls = reply.tool_calls[:1]
        return reply


class ToolResultAgent(ToolCallingAgent):
    """Return the trusted Python tool's result directly, avoiding unreliable second model calls."""
    def _step_stream(self, memory_step):
        for event in super()._step_stream(memory_step):
            if isinstance(event, ToolOutput) and not event.is_final_answer:
                memory_step.tool_calls = [event.tool_call]
                memory_step.observations = event.observation
                yield event
                yield ActionOutput(output=event.output, is_final_answer=True)
                return
            yield event


class AskPayload(BaseModel):
    message: str = Field(min_length=1, max_length=300)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self' data:; font-src 'self'; "
        "base-uri 'none'; object-src 'none'; frame-ancestors 'none'; "
        "form-action 'self'"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/")
def home():
    return FileResponse(root/"index.html", media_type="text/html",
                        headers={"Cache-Control": "no-store"})

@app.get("/styles.css", include_in_schema=False)
def stylesheet():
    return FileResponse(root / "styles.css", media_type="text/css",
                        headers={"Cache-Control": "public, max-age=300"})


@app.get("/agent_ui.js", include_in_schema=False)
def agent_interface():
    return FileResponse(root / "agent_ui.js", media_type="text/javascript",
                        headers={"Cache-Control": "public, max-age=300"})


@app.get("/csv_audit.js", include_in_schema=False)
def csv_engine():
    return FileResponse(
        root / "csv_audit.js", media_type="text/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/csv_ui.js", include_in_schema=False)
def csv_interface():
    return FileResponse(
        root / "csv_ui.js", media_type="text/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/ask")
def ask(payload: AskPayload, request: Request):
    message = payload.message.strip()
    if not message:
        return JSONResponse({"error": "Enter a question."}, status_code=422)
    local_mode = os.getenv("VALUEPILOT_LOCAL_MODE") == "1"
    if local_mode:
        # Explicitly disallow access from non-loopback interfaces.
        host = request.client.host if request.client else ""
        inside_container = os.getenv("VALUEPILOT_CONTAINER_LOCAL") == "1"
        try:
            parsed = ipaddress.ip_address(host)
            allowed = parsed.is_loopback or (inside_container and parsed.is_private)
        except ValueError:
            allowed = False
        if not allowed:
            return JSONResponse({"error": "Local mode only accepts loopback or container-network requests."}, status_code=403)
        origin = request.headers.get("origin")
        if origin and origin not in ("http://127.0.0.1:8765", "http://localhost:8765"):
            return JSONResponse({"error": "Cross-site requests are disabled."}, status_code=403)
    if not gate.acquire(blocking=False):
        return JSONResponse({"error": "The demo is busy. Try again shortly."},
                            status_code=503, headers={"Retry-After": "10"})
    try:
        decision = 0 if local_mode else quota(request)
        if decision != 0:
            errors = {
                -1: "Rate-limit storage is unavailable. Try again later.",
                1: "You've reached five demo requests in the last hour.",
                2: "The public demo is busy. Try again in a minute.",
                3: "Today's shared demo quota has been used. Try again later.",
            }
            return JSONResponse({"error": errors.get(decision,"Please try again later.")},
                                status_code=503 if decision == -1 else 429)
        try:
            # Browser-local CSV audit never invokes this model endpoint.
            # Optional local agent mode uses Ollama with no paid cloud inference.
            model = SelectToolModel(
                model_id=os.getenv("OLLAMA_MODEL", "llama3.2:3b") if local_mode else "openai/gpt-oss-120b",
                api_base=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1") if local_mode else "https://api.groq.com/openai/v1",
                api_key="ollama" if local_mode else os.environ["GROQ_API_KEY"],
                max_tokens=700,
            )
            agent = ToolResultAgent(model=model, tools=TOOLS, max_steps=3,
                                     verbosity_level=0)
            answer = agent.run(
                "Call the one relevant Python tool to answer the request using supplied facts. "
                "Tool results are returned directly, with clear assumptions. Request: " + message
            )
            return {"answer": str(answer)}
        except Exception as exc:
            log.warning("AGENT_FAILURE type=%s status=%s",type(exc).__name__,
                        getattr(exc,"status_code","unknown"))
            return JSONResponse({"error": "The model couldn't complete the request. Try again."},
                                status_code=502)
    finally:
        gate.release()
