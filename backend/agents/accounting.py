"""Accounting — cash, invoices, margins; prepares payments, purchase orders and quotes for human approval.

Prompt: backend/prompts/accounting.md. MCP tools: see ALLOWED_TOOLS["accounting"] in agents/mcp.py.
"""

from models import AgentReport

from .base import build_agent

accounting_agent = build_agent("accounting", output_type=AgentReport)
