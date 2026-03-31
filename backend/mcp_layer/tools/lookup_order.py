"""Tool: lookup_order - Look up order details and verify ownership.

This tool retrieves order information and verifies that the order belongs to the
current customer. It sets refund_eligible in the session, which is required for
process_refund to work.

USE THIS TOOL when: Customer provides an order ID or order number to investigate.
DO NOT use for: Customer-level data - use get_customer instead.
REQUIRES: Verified customer_id from get_customer must be in session first.
On OWNERSHIP_MISMATCH: Escalate P1 immediately - NEVER retry, this is a critical security issue.
"""

from pydantic import ValidationError

from backend.backends.orders import lookup_order as lookup_order_backend
from backend.mcp_layer.middleware.prerequisites import (
    PrerequisiteError,
    check_prerequisites,
    update_session_state,
)
from backend.mcp_layer.mcp_server import mcp
from backend.mcp_layer.session_storage import get_session, update_session
from backend.types.models import ErrorCode, LookupOrderInput, ToolName


@mcp.tool()
async def lookup_order(session_id: str, order_id: str, customer_id: str) -> dict:
    """Look up order information and verify customer ownership.

    This tool retrieves order details from the order management system and verifies
    that the order belongs to the specified customer. It determines refund eligibility
    which is required before processing any refunds.

    Args:
        session_id: Session identifier for state tracking across tool calls
        order_id: Order ID to look up in the order system (e.g., "ORD-8842")
        customer_id: Customer ID from get_customer, used for ownership verification

    Returns:
        Dict containing order details (order_id, customer_id, amount, order_date, status,
        refund_eligible, refund_reason) or error information if lookup fails
    """
    # Validate inputs through Pydantic model
    try:
        validated = LookupOrderInput(
            order_id=order_id,
            customer_id=customer_id,
        )
    except ValidationError as e:
        return {
            "error": "invalid_input",
            "message": f"Invalid input: {str(e.errors()[0]['msg'])}",
        }

    # Get or create session
    session = get_session(session_id)

    # SECURITY: Validate customer_id matches session (prevent cross-account access)
    if session.customer_id and customer_id != session.customer_id:
        return {
            "error": "unauthorized",
            "message": "Unable to access this order. Please verify your account information.",
        }

    # Check prerequisites FIRST
    try:
        check_prerequisites(ToolName.LOOKUP_ORDER, session)
    except PrerequisiteError as e:
        return {"error": "prerequisite_failed", "message": str(e)}

    # Call backend
    result = await lookup_order_backend(order_id, customer_id)

    # Handle ErrorCode returns
    if isinstance(result, ErrorCode):
        return _map_error_to_dict(result)

    # Update session state
    result_dict = result.model_dump()
    updated_session = update_session_state(ToolName.LOOKUP_ORDER, result_dict, session)
    update_session(session_id, updated_session)

    # Return dict (not Pydantic model)
    return result_dict


def _map_error_to_dict(error_code: ErrorCode) -> dict:
    """Map ErrorCode to user-safe dict.

    CRITICAL: Never expose internal error code names to customers.
    OWNERSHIP_MISMATCH requires immediate P1 escalation - no retries.
    """
    mapping = {
        ErrorCode.NOT_FOUND: {
            "error": "not_found",
            "message": "We couldn't find that order number. Please verify the order ID and try again.",
        },
        ErrorCode.OWNERSHIP_MISMATCH: {
            "error": "ownership_mismatch",
            "message": "We need to verify this order with additional security checks.",
            "escalate": True,
            "priority": "P1",
        },
    }
    return mapping.get(
        error_code,
        {
            "error": "server_error",
            "message": "We encountered a system error. Please try again in a moment.",
        },
    )
