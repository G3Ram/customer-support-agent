"""MCP tools for customer support agent.

This package contains 4 tools that work together to handle customer support requests:
1. get_customer - Look up customer by email (must be called first)
2. lookup_order - Look up order and verify ownership (requires customer_id)
3. process_refund - Process refund with idempotency (requires refund_eligible=True)
4. escalate_to_human - Create escalation ticket (requires customer_id)
"""

from backend.mcp.tools.escalate_to_human import escalate_to_human
from backend.mcp.tools.get_customer import get_customer
from backend.mcp.tools.lookup_order import lookup_order
from backend.mcp.tools.process_refund import process_refund

__all__ = [
    "get_customer",
    "lookup_order",
    "process_refund",
    "escalate_to_human",
]
