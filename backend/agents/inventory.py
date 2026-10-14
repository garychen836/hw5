"""Inventory — stock by SKU and size, shortfalls, which vendor can restock and how fast.

Prompt: backend/prompts/inventory.md. MCP tools: see ALLOWED_TOOLS["inventory"] in agents/mcp.py.
"""

from models import AgentReport

from .base import build_agent

inventory_agent = build_agent("inventory", output_type=AgentReport)
