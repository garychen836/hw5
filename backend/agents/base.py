"""Shared machinery for the five agents: building them, the delegation tool
that gives the team full connectivity, and the agent loop that writes every
step to the audit trail.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (RetryPromptPart, TextPart, ThinkingPart, ToolCallPart, ToolReturnPart,
                                  UserPromptPart)
from pydantic_ai.usage import UsageLimits

import audit
from llm import MODEL_NAME, MODEL_SETTINGS, build_model
from models import AGENT_NAMES, AgentName, AgentReport, TeamDeps

from .mcp import toolset_for

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

# Per-agent caps (on top of the shared per-ticket Budget in models.py).
REQUEST_LIMITS = {"boss": 12, "default": 8}
MAX_OUTPUT_TOKENS = 1_200
SETTINGS = {**MODEL_SETTINGS, "max_tokens": MAX_OUTPUT_TOKENS}

REGISTRY: dict[str, Agent] = {}
_MODEL = build_model()  # gpt-6-luna, the only model any agent may use


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text()


def build_agent(name: str, output_type: type) -> Agent:
    """One team member: its prompt file, its MCP tools, and ask_teammate."""
    agent = Agent(
        _MODEL,
        name=name,
        deps_type=TeamDeps,
        output_type=output_type,
        instructions=load_prompt(name),  # fully static, so the provider can cache it
        toolsets=[toolset_for(name)],
        model_settings=SETTINGS,
        retries=2,
    )
    agent.tool(ask_teammate)
    REGISTRY[name] = agent
    return agent


def _run_context(deps: TeamDeps) -> str:
    """Run facts that change per call. They go in the task message, not the
    system prompt, so the static prompt stays identical and cacheable."""
    b = deps.budget
    return (f"[Run context: ticket {deps.ticket_id}. You are '{deps.agent}'. Delegation chain: "
            f"{' > '.join(deps.chain)}. Team budget left: {b.tokens_left():,} tokens, "
            f"{b.max_delegations - b.delegations} delegations, depth {deps.depth} of {b.max_depth}.]")


# ---------------------------------------------------------------------------
# Delegation: any agent may ask any other agent (full connectivity)
# ---------------------------------------------------------------------------

async def ask_teammate(ctx: RunContext[TeamDeps], teammate: AgentName, task: str) -> dict:
    """Hand a task to a teammate and wait for their report.

    Args:
        teammate: one of boss, inventory, accounting, facilities, customer_service.
        task: what you need, with the ticket id and the exact ids / SKU / size / qty involved.
    """
    d, b = ctx.deps, ctx.deps.budget
    refusal = None
    if teammate not in AGENT_NAMES:
        refusal = f"No teammate called '{teammate}'."
    elif teammate == d.agent:
        refusal = "You cannot delegate to yourself."
    elif teammate in d.chain:
        refusal = (f"'{teammate}' is already waiting on this chain ({' > '.join(d.chain)}). "
                   "Return your report to them instead of asking back (prevents loops).")
    elif d.depth + 1 > b.max_depth:
        refusal = f"Delegation depth limit ({b.max_depth}) reached. Finish with what you have."
    elif b.delegations >= b.max_delegations:
        refusal = f"Team delegation limit ({b.max_delegations}) reached for this ticket. Finish with what you have."
    elif b.tokens_left() < 6_000:
        refusal = "Team token budget almost used up. Finish with what you have."

    if refusal:
        audit.record("delegation_refused", run_id=d.run_id, ticket_id=d.ticket_id, agent=d.agent, chain=d.chain,
                     teammate=teammate, task=task, reason=refusal)
        return {"ok": False, "message": refusal}

    b.delegations += 1
    first = len(d.handoffs)
    d.handoffs.append({"no": b.delegations, "from": d.agent, "to": teammate, "task": task})
    audit.record("handoff", run_id=d.run_id, ticket_id=d.ticket_id, agent=d.agent, chain=d.chain,
                 teammate=teammate, task=task, delegation_no=b.delegations)
    report = await run_agent(teammate, task, d.child(teammate))
    # Everyone who worked under this delegation, including onward handoffs.
    involved = [teammate] + [h["to"] for h in d.handoffs[first + 1:]]
    onward = [f"{h['from']} -> {h['to']}" for h in d.handoffs[first + 1:]]
    return {"ok": True, "from": teammate, "agents_involved": involved, "onward_handoffs": onward, "report": report}


# ---------------------------------------------------------------------------
# The agent loop, with one audit entry per step
# ---------------------------------------------------------------------------

async def run_agent(name: str, task: str, deps: TeamDeps) -> dict:
    """Run one agent's loop to completion and return its output as a dict."""
    agent = REGISTRY[name]
    b = deps.budget
    limits = UsageLimits(
        request_limit=REQUEST_LIMITS.get(name, REQUEST_LIMITS["default"]),
        total_tokens_limit=max(b.tokens_left(), 1),
    )
    log = lambda event, **kw: audit.record(event, run_id=deps.run_id, ticket_id=deps.ticket_id, agent=name,
                                           chain=deps.chain, **kw)
    log("agent_start", task=task, model=MODEL_NAME)
    step = 0
    try:
        async with agent.iter(f"{task}\n\n{_run_context(deps)}", deps=deps, usage_limits=limits) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            log("tool_result", step=step, tool=part.tool_name, tool_call_id=part.tool_call_id,
                                result=part.content)
                        elif isinstance(part, RetryPromptPart):
                            log("retry", step=step, tool=part.tool_name, text=str(part.content))
                        elif isinstance(part, UserPromptPart) and step == 0:
                            pass  # already logged as agent_start
                elif Agent.is_call_tools_node(node):
                    step += 1
                    resp = node.model_response
                    u = resp.usage
                    b.tokens_used += u.input_tokens + u.output_tokens
                    tally = deps.usage_by_agent.setdefault(name, {"requests": 0, "input_tokens": 0,
                                                                  "cached_tokens": 0, "output_tokens": 0})
                    tally["requests"] += 1
                    tally["input_tokens"] += u.input_tokens
                    tally["cached_tokens"] += u.cache_read_tokens
                    tally["output_tokens"] += u.output_tokens
                    calls = [p for p in resp.parts if isinstance(p, ToolCallPart)]
                    text = " ".join(p.content for p in resp.parts if isinstance(p, TextPart)).strip()
                    log("model_step", step=step, model=resp.model_name or MODEL_NAME,
                        tokens={"input": u.input_tokens, "cached": u.cache_read_tokens, "output": u.output_tokens},
                        text=text or None,
                        tool_calls=[{"tool": c.tool_name, "args": c.args_as_dict()} for c in calls],
                        thinking=any(isinstance(p, ThinkingPart) for p in resp.parts),
                        team_tokens_used=b.tokens_used)
            output = run.result.output
    except UsageLimitExceeded as exc:
        log("limit_hit", error=str(exc))
        if name == "boss":
            raise
        return AgentReport(summary=f"{name} stopped: {exc}. Partial work may be in the database.",
                           open_questions=["Ran out of budget before finishing."]).model_dump()
    except Exception as exc:  # report, never crash the whole team on one agent
        log("agent_error", error=f"{type(exc).__name__}: {exc}")
        if name == "boss":
            raise
        return AgentReport(summary=f"{name} hit an error: {type(exc).__name__}: {exc}",
                           open_questions=["Error before finishing."]).model_dump()

    result: dict[str, Any] = output.model_dump()
    log("agent_done", step=step, output=result)
    return result
