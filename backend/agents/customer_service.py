"""Customer Service — kind, honest drafts for customers; never sends.

Prompt: backend/prompts/customer_service.md. MCP tools: see ALLOWED_TOOLS["customer_service"] in agents/mcp.py.
"""

from models import AgentReport

from .base import build_agent

customer_service_agent = build_agent("customer_service", output_type=AgentReport)
