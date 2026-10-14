"""Campus Customs desk API (FastAPI).

Start it from the backend/ folder:

    uvicorn main:app --reload --port 8000        (with the project .venv active)

The React board (frontend/, http://localhost:5173) calls these routes.

Every shop fact and every change goes through the Campus Customs MCP server,
the same tools the agents use, so the API has no back door into the
database. The routes for a human (approve / reject a payment, confirm a
quote) call the human-only MCP tools. No agent can reach those, and this API
never runs them on an agent's behalf.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
for p in (BACKEND, ROOT / "mcp_server"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastmcp import Client  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import audit  # noqa: E402
from llm import MODEL_NAME, key_source  # noqa: E402
from models import AGENT_NAMES, AGENT_TITLES  # noqa: E402
from server import DB_PATH, mcp as shop_server  # noqa: E402
from team import new_run_id, run_ticket  # noqa: E402

ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
TICKET_IDS = (101, 102, 103)

_shop: Client | None = None          # MCP client the human routes use
RUNS: dict[str, dict] = {}          # run_id -> {"ticket_id", "status", "result"}
_active_run: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _shop
    async with Client(shop_server) as client:  # in-process MCP session over the same server code
        _shop = client
        yield
    _shop = None


app = FastAPI(title="Campus Customs desk", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


async def shop(tool: str, **args: Any) -> dict:
    """Call one Campus Customs MCP tool and return its result."""
    if _shop is None:
        raise HTTPException(503, "MCP server not connected yet")
    result = await _shop.call_tool(tool, args, raise_on_error=False)
    if result.is_error:
        raise HTTPException(500, f"{tool} failed: {result.content[0].text if result.content else 'unknown error'}")
    return result.data if result.data is not None else json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# request bodies
# ---------------------------------------------------------------------------

class HumanDecision(BaseModel):
    name: str = Field(..., min_length=1, description="The human approving, e.g. 'Gary Chen'.")
    note: str = ""


def _human_name(name: str) -> str:
    """Approvals must carry a real person's name, never an agent's."""
    clean = name.strip()
    if not clean:
        raise HTTPException(400, "A human name is required.")
    if clean.lower().replace(" ", "_") in AGENT_NAMES or clean.lower() in ("agent", "ai", "bot", "system"):
        raise HTTPException(403, f"'{clean}' is an agent, not a human. Payments need a person's approval.")
    return clean


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health() -> dict:
    db = DB_PATH.relative_to(ROOT) if DB_PATH.is_relative_to(ROOT) else DB_PATH
    return {"ok": True, "model": MODEL_NAME, "key_source": key_source(), "database": str(db),
            "active_run": _active_run}


@app.get("/api/tickets")
async def list_tickets() -> dict:
    """The three tickets, with open / resolved state and what is waiting on a human."""
    board = await shop("list_tickets")
    tickets = []
    for t in board["tickets"]:
        detail = await shop("get_ticket", ticket_id=t["id"])
        pending = [r for r in detail["payment_requests"] if r["status"] == "pending"]
        draft_quotes = [q for q in detail["quotes"] if q["status"] == "draft"]
        tickets.append({
            **detail["ticket"],
            "resolved": t["status"] == "resolved",
            "state": "resolved" if t["status"] == "resolved" else "open",
            "pending_payments": pending,
            "draft_quotes": draft_quotes,
            "message_drafts": detail["message_drafts"],
            "status_history": detail["status_history"],
            "running": any(r["ticket_id"] == t["id"] and r["status"] == "running" for r in RUNS.values()),
        })
    return {"today": board["today"], "tickets": tickets}


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: int) -> dict:
    detail = await shop("get_ticket", ticket_id=ticket_id)
    if not detail.get("found"):
        raise HTTPException(404, detail.get("message", "No such ticket"))
    return detail


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_team(ticket_id: int) -> dict:
    """Start the agent team on one ticket. Returns at once with a run_id;
    poll /api/events?run_id=... to watch, and /api/runs/{run_id} for the result."""
    global _active_run
    if ticket_id not in TICKET_IDS:
        raise HTTPException(404, f"No open ticket {ticket_id}")
    if _active_run:
        raise HTTPException(409, f"Run {_active_run} is still going; one ticket at a time (they share one cash account).")
    run_id = new_run_id()
    RUNS[run_id] = {"run_id": run_id, "ticket_id": ticket_id, "status": "running", "result": None}
    _active_run = run_id

    async def work() -> None:
        global _active_run
        try:
            result = await run_ticket(ticket_id, run_id=run_id)
            RUNS[run_id].update(status="done" if result["status"] == "ok" else "error", result=result)
        except Exception as exc:  # never leave the board stuck on "running"
            RUNS[run_id].update(status="error", result={"error": f"{type(exc).__name__}: {exc}"})
        finally:
            _active_run = None

    asyncio.create_task(work())
    return {"run_id": run_id, "ticket_id": ticket_id, "status": "running"}


def _board_event(e: dict) -> dict:
    """A compact view of one audit entry: who, what they said, which tools."""
    out = {k: e.get(k) for k in ("seq", "ts", "run_id", "ticket_id", "agent", "chain", "event")}
    out["agent_title"] = AGENT_TITLES.get(e.get("agent"), e.get("agent"))
    kind = e.get("event")
    if kind == "model_step":
        out["said"] = e.get("text")
        out["tools"] = [c["tool"] for c in e.get("tool_calls") or []]
        out["tool_args"] = e.get("tool_calls")
        out["tokens"] = e.get("tokens")
    elif kind == "tool_result":
        out["tool"], out["result"] = e.get("tool"), e.get("result")
    elif kind in ("handoff", "delegation_refused"):
        out["to"], out["task"], out["reason"] = e.get("teammate"), e.get("task"), e.get("reason")
    elif kind == "agent_start":
        out["task"] = e.get("task")
    elif kind == "agent_done":
        out["output"] = e.get("output")
    elif kind == "run_end":
        out.update({k: e.get(k) for k in ("status", "error", "handoffs", "usage_by_agent", "usage_total")})
    elif kind in ("limit_hit", "agent_error"):
        out["error"] = e.get("error")
    elif kind == "human_action":
        out.update({k: e.get(k) for k in ("action", "target", "by", "outcome")})
    return out


def _trail(run_id: str | None = None) -> list[dict]:
    """All audit entries (file on disk), optionally for one run."""
    path = audit.AUDIT_PATH
    entries = json.loads(path.read_text()) if path.exists() and path.stat().st_size else []
    return [e for e in entries if run_id is None or e.get("run_id") == run_id]


@app.get("/api/events")
async def events(since: int = 0, run_id: str | None = None, limit: int = 200) -> dict:
    """Recent agent events (what each agent said, which tools they used), newest last.
    Pass the last seq you saw as `since` to get only new ones."""
    live = audit.recent(since_seq=since, run_id=run_id)
    entries = live if live or since else [e for e in _trail(run_id) if e.get("seq", 0) > since]
    entries = entries[-limit:]
    return {"events": [_board_event(e) for e in entries],
            "last_seq": entries[-1]["seq"] if entries else since,
            "active_run": _active_run}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    """A run's status, the Boss's resolution, and a short summary per agent."""
    trail = _trail(run_id)
    if run_id not in RUNS and not trail:
        raise HTTPException(404, f"No run {run_id}")
    per_agent: dict[str, list[dict]] = {}
    tools_by_agent: dict[str, list[str]] = {}
    for e in trail:
        if e["event"] == "agent_done":
            per_agent.setdefault(e["agent"], []).append(e.get("output"))
        if e["event"] == "model_step":
            tools_by_agent.setdefault(e["agent"], []).extend(c["tool"] for c in e.get("tool_calls") or [])
    end = next((e for e in reversed(trail) if e["event"] == "run_end"), None)
    info = RUNS.get(run_id, {"run_id": run_id, "status": "done" if end else "unknown", "result": None})
    return {
        **{k: info.get(k) for k in ("run_id", "status")},
        "ticket_id": info.get("ticket_id") or (trail[0]["ticket_id"] if trail else None),
        "resolution": (info.get("result") or {}).get("resolution") or (per_agent.get("boss") or [None])[-1],
        "agents": {a: {"title": AGENT_TITLES.get(a, a), "outputs": outs, "tools_used": tools_by_agent.get(a, [])}
                   for a, outs in per_agent.items()},
        "handoffs": (end or {}).get("handoffs"),
        "usage_by_agent": (end or {}).get("usage_by_agent"),
        "usage_total": (end or {}).get("usage_total"),
    }


@app.get("/api/runs")
async def list_runs() -> dict:
    ends = {e["run_id"]: e for e in _trail() if e["event"] == "run_end"}
    starts = [e for e in _trail() if e["event"] == "run_start"]
    return {"runs": [{"run_id": s["run_id"], "ticket_id": s["ticket_id"], "started": s["ts"],
                      "status": RUNS.get(s["run_id"], {}).get("status") or ("done" if s["run_id"] in ends else "unknown")}
                     for s in starts]}


@app.get("/api/payments")
async def payment_requests(status: str | None = "pending") -> dict:
    """Payment / purchase-order requests the agents prepared (pending by default)."""
    return await shop("list_payment_requests", status=status)


@app.post("/api/payments/{request_id}/approve")
async def approve_payment(request_id: int, body: HumanDecision) -> dict:
    """HUMAN ONLY. The one route that moves cash: pays a prepared request after a person clicks approve."""
    who = _human_name(body.name)
    outcome = await shop("approve_payment_request", request_id=request_id, approved_by=who)
    audit.record("human_action", run_id="human", ticket_id=None, agent="human", action="approve_payment",
                 target=request_id, by=who, outcome=outcome)
    if not outcome.get("ok"):
        raise HTTPException(409, outcome.get("message", "Approval refused"))
    return {**outcome, "cash": await shop("get_cash_balance")}


@app.post("/api/payments/{request_id}/reject")
async def reject_payment(request_id: int, body: HumanDecision) -> dict:
    """HUMAN ONLY. Reject a prepared request; no money moves."""
    who = _human_name(body.name)
    outcome = await shop("reject_payment_request", request_id=request_id, decided_by=who, note=body.note)
    audit.record("human_action", run_id="human", ticket_id=None, agent="human", action="reject_payment",
                 target=request_id, by=who, outcome=outcome)
    if not outcome.get("ok"):
        raise HTTPException(409, outcome.get("message", "Reject refused"))
    return outcome


@app.post("/api/quotes/{quote_id}/confirm")
async def confirm_quote(quote_id: int, body: HumanDecision) -> dict:
    """HUMAN ONLY. Confirm a draft price quote (e.g. ticket 103's bulk discount); no money moves."""
    who = _human_name(body.name)
    outcome = await shop("confirm_price_quote", quote_id=quote_id, confirmed_by=who)
    audit.record("human_action", run_id="human", ticket_id=outcome.get("ticket_id"), agent="human",
                 action="confirm_quote", target=quote_id, by=who, outcome=outcome)
    if not outcome.get("ok"):
        raise HTTPException(409, outcome.get("message", "Confirm refused"))
    return outcome


@app.post("/api/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: int, body: HumanDecision) -> dict:
    """HUMAN ONLY. A person marks a ticket resolved (e.g. after reviewing the drafts).
    Refused while a payment request on it is still pending."""
    who = _human_name(body.name)
    outcome = await shop("update_ticket_status", ticket_id=ticket_id, status="resolved",
                         note=body.note or f"Marked resolved by {who}.", updated_by=who)
    audit.record("human_action", run_id="human", ticket_id=ticket_id, agent="human", action="resolve_ticket",
                 target=ticket_id, by=who, outcome=outcome)
    if not outcome.get("ok"):
        raise HTTPException(409, outcome.get("message", "Resolve refused"))
    return outcome


@app.get("/api/cash")
async def cash() -> dict:
    """Current checking balance from cash_accounts (plus pending requests)."""
    return await shop("get_cash_balance")


@app.post("/api/reset")
async def reset() -> dict:
    """Copy the original database over the working copy for a fresh run.
    The audit trail is kept (it is append-only); a reset entry is added."""
    if _active_run:
        raise HTTPException(409, f"Run {_active_run} is in progress; wait for it to finish before resetting.")
    shutil.copyfile(ORIGINAL_DB, DB_PATH)
    RUNS.clear()
    after = await shop("get_cash_balance")
    audit.record("db_reset", run_id="human", ticket_id=None, agent="human",
                 outcome={"copied": f"{ORIGINAL_DB.name} -> {DB_PATH.name}", "checking_balance": after["balance"]})
    return {"ok": True, "message": f"Reset {DB_PATH.name} from {ORIGINAL_DB.name}.", "cash": after,
            "tickets": (await shop("list_tickets"))["tickets"]}
