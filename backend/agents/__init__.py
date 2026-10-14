"""The Campus Customs agent team. Importing this package builds all five agents."""

from .accounting import accounting_agent
from .base import REGISTRY, run_agent
from .boss import boss_agent
from .customer_service import customer_service_agent
from .facilities import facilities_agent
from .inventory import inventory_agent
from .mcp import ALLOWED_TOOLS, HUMAN_ONLY_TOOLS, SHOP_MCP

__all__ = ["REGISTRY", "run_agent", "SHOP_MCP", "ALLOWED_TOOLS", "HUMAN_ONLY_TOOLS", "boss_agent",
           "inventory_agent", "accounting_agent", "facilities_agent", "customer_service_agent"]
