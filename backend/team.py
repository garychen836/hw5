"""Run the whole team on one ticket: Boss first, specialists as the Boss (or
each other) delegate. This is what the backend route calls.

    cd backend && ../.venv/bin/python team.py 102     # try one ticket from the terminal
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime

import os

import audit
from agents import SHOP_MCP, run_agent
from llm import MODEL_NAME, key_source
from models import Budget, TeamDeps

_one_run_at_a_time = asyncio.Lock()  # tickets share one cash account; never race two runs


def new_run_id() -> str:
    return f"run-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"


async def run_ticket(ticket_id: int, budget: Budget | None = None, run_id: str | None = None) -> dict:
    budget = budget or Budget()
    run_id = run_id or new_run_id()
    deps = TeamDeps(run_id=run_id, ticket_id=ticket_id, agent="boss", chain=["boss"], budget=budget)
    async with _one_run_at_a_time:
        audit.record("run_start", run_id=run_id, ticket_id=ticket_id, agent="team", model=MODEL_NAME,
                     key_source=key_source(), database=os.getenv("CAMPUS_DB", "data/campus_customs_new.db"),
                     limits={"max_total_tokens": budget.max_total_tokens, "max_delegations": budget.max_delegations,
                             "max_depth": budget.max_depth})
        status, resolution, error = "ok", None, None
        try:
            async with SHOP_MCP:
                resolution = await run_agent(
                    "boss", f"Work ticket {ticket_id}. Read it, delegate only to who it needs, and make the final call.",
                    deps)
        except Exception as exc:
            status, error = "error", f"{type(exc).__name__}: {exc}"
        totals = {k: sum(u[k] for u in deps.usage_by_agent.values())
                  for k in ("requests", "input_tokens", "cached_tokens", "output_tokens")}
        audit.record("run_end", run_id=run_id, ticket_id=ticket_id, agent="team", status=status, error=error,
                     delegations=budget.delegations, handoffs=deps.handoffs, usage_by_agent=deps.usage_by_agent, usage_total=totals)
    return {"run_id": run_id, "ticket_id": ticket_id, "status": status, "error": error, "resolution": resolution,
            "delegations": budget.delegations, "handoffs": deps.handoffs, "usage_by_agent": deps.usage_by_agent, "usage_total": totals}


if __name__ == "__main__":
    out = asyncio.run(run_ticket(int(sys.argv[1])))
    print(json.dumps(out, indent=2, default=str))
