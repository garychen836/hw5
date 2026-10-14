"""Facilities — the shop space: lease, rent, landlord.

Prompt: backend/prompts/facilities.md. MCP tools: see ALLOWED_TOOLS["facilities"] in agents/mcp.py.
"""

from models import AgentReport

from .base import build_agent

facilities_agent = build_agent("facilities", output_type=AgentReport)
