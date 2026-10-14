"""The one connection from the agent team to the Campus Customs MCP server.

All shop facts reach the agents through this MCP toolset (stdio, running
mcp_server/server.py over data/campus_customs_new.db). There is no other
shop-tools layer.

Each agent sees only the MCP tools on its own allow-list (least privilege).
The human-only tools (approve / reject a payment) are on no list, and the
call hook below refuses them even if a model somehow names them. The same
hook stamps the real agent name into "who did this" arguments, so the
database records who acted, not who the model claims to be.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastmcp.client.transports import PythonStdioTransport
from pydantic_ai import RunContext
from pydantic_ai.mcp import MCPToolset

ROOT = Path(__file__).resolve().parent.parent.parent
SERVER = ROOT / "mcp_server" / "server.py"

HUMAN_ONLY_TOOLS = frozenset({"approve_payment_request", "reject_payment_request", "confirm_price_quote"})

# Which MCP tools each agent may call.
ALLOWED_TOOLS: dict[str, frozenset[str]] = {
    "boss": frozenset({"list_tickets", "get_ticket", "get_cash_balance", "list_payment_requests",
                       "update_ticket_status"}),
    "inventory": frozenset({"get_ticket", "check_stock", "find_vendors", "get_invoice_status"}),
    "accounting": frozenset({"get_ticket", "get_cash_balance", "list_payment_requests", "get_invoice_status",
                             "get_lease_status", "check_stock", "find_vendors", "prepare_payment",
                             "prepare_purchase_order", "prepare_price_quote"}),
    "facilities": frozenset({"get_ticket", "get_lease_status", "get_cash_balance"}),
    "customer_service": frozenset({"get_ticket", "check_stock", "draft_customer_message"}),
}
assert not any(HUMAN_ONLY_TOOLS & tools for tools in ALLOWED_TOOLS.values())

# Arguments that say who acted; always overwritten with the real agent name.
IDENTITY_ARGS = ("requested_by", "prepared_by", "written_by", "updated_by")


async def _guard(ctx: RunContext[Any], call_tool, name: str, args: dict[str, Any]):
    agent = ctx.deps.agent
    if name in HUMAN_ONLY_TOOLS or name not in ALLOWED_TOOLS.get(agent, ()):
        # Shown to the model as the tool's answer, so it can carry on.
        why = ("Payments are approved only by a human on the dashboard." if name in HUMAN_ONLY_TOOLS
               else "Ask the teammate whose job it is with ask_teammate.")
        return {"ok": False, "message": f"'{agent}' is not allowed to call {name}. {why}"}
    for key in IDENTITY_ARGS:
        if key in args:
            args[key] = agent
    return await call_tool(name, args)


def _server_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "CAMPUS_DB")}
    env["FASTMCP_SHOW_SERVER_BANNER"] = "false"
    env["FASTMCP_LOG_LEVEL"] = "WARNING"
    return env


# One server process for the whole team, opened per ticket run in team.py.
SHOP_MCP = MCPToolset(
    PythonStdioTransport(str(SERVER), python_cmd=sys.executable, env=_server_env(), cwd=str(ROOT)),
    process_tool_call=_guard,
)


def toolset_for(agent: str):
    """The MCP tools this agent may see."""
    allowed = ALLOWED_TOOLS[agent]
    return SHOP_MCP.filtered(lambda ctx, tool_def: tool_def.name in allowed)
