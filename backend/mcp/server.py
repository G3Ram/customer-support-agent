"""MCP server for customer support agent tools.

Exposes 4 tools via FastMCP:
- get_customer
- lookup_order
- process_refund
- escalate_to_human

All tools share a single MCP instance and use session-based state tracking
to enforce prerequisites and idempotency.
"""

from mcp.server import FastMCP  # pyright: ignore[reportMissingImports]

# Create the MCP instance that all tools will register with
mcp = FastMCP("customer-support-agent")

# Import tools to register them with the MCP server
# These imports must come after mcp creation to avoid circular imports
from backend.mcp.tools import (  # noqa: E402
    escalate_to_human,
    get_customer,
    lookup_order,
    process_refund,
)


def list_tools():
    """List registered tools for verification."""
    return [
        "get_customer",
        "lookup_order",
        "process_refund",
        "escalate_to_human",
    ]
