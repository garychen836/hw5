"""Boss — reads each ticket, decides who works on it, makes the final call.

Prompt: backend/prompts/boss.md. MCP tools: see ALLOWED_TOOLS["boss"] in agents/mcp.py.
"""

from models import TicketResolution

from .base import build_agent

boss_agent = build_agent("boss", output_type=TicketResolution)
