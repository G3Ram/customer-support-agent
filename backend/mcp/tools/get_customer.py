"""Tool: get_customer - Look up customer by email address.

This tool retrieves customer information from the CRM system. It must be called
FIRST before any other tool in a session to verify customer identity and establish
the session context.

USE THIS TOOL when: Customer provides an email address for verification.
DO NOT use for: Order-level data - use lookup_order instead.
REQUIRES: No prerequisites (always available).
On NOT_FOUND: Ask customer to confirm email, do not proceed with other tools.
"""

from backend.backends.crm import get_customer as get_customer_backend
from backend.mcp.middleware.prerequisites import (
    PrerequisiteError,
    check_prerequisites,
    update_session_state,
)
from backend.mcp.server import mcp
from backend.mcp.session_storage import get_session, update_session
from backend.types.models import ErrorCode, ToolName

# Email to customer_id mapping based on CRM fixtures
EMAIL_TO_CUSTOMER_ID = {
    "sarah@example.com": "USR-001",
    "marcus@example.com": "USR-002",
    "james@example.com": "USR-VIP",
}


@mcp.tool()
async def get_customer(session_id: str, email: str) -> dict:
    """Look up customer information by email address.

    This is the first tool that must be called in any support session. It verifies
    the customer's identity and retrieves their account information from the CRM system.

    Args:
        session_id: Session identifier for state tracking across tool calls
        email: Customer email address to look up in the CRM system

    Returns:
        Dict containing customer details (customer_id, name, email, account_status, open_case_count)
        or error information if lookup fails
    """
    # Get or create session
    session = get_session(session_id)

    # Check prerequisites (get_customer has none, but we call for consistency)
    try:
        check_prerequisites(ToolName.GET_CUSTOMER, session)
    except PrerequisiteError as e:
        return {"error": "prerequisite_failed", "message": str(e)}

    # Map email to customer_id
    customer_id = EMAIL_TO_CUSTOMER_ID.get(email.lower())
    if not customer_id:
        return {
            "error": "not_found",
            "message": "We couldn't find an account with that email address. Please verify the email and try again.",
        }

    # Call backend
    result = await get_customer_backend(customer_id)

    # Handle ErrorCode returns
    if isinstance(result, ErrorCode):
        return _map_error_to_dict(result)

    # Update session state
    result_dict = result.model_dump()
    updated_session = update_session_state(ToolName.GET_CUSTOMER, result_dict, session)
    update_session(session_id, updated_session)

    # Return dict (not Pydantic model)
    return result_dict


def _map_error_to_dict(error_code: ErrorCode) -> dict:
    """Map ErrorCode to user-safe dict.

    CRITICAL: Never expose internal error code names to customers.
    """
    mapping = {
        ErrorCode.NOT_FOUND: {
            "error": "not_found",
            "message": "We couldn't find an account with that email address. Please verify the email and try again.",
        },
        ErrorCode.SUSPENDED: {
            "error": "suspended",
            "message": "This account has been suspended. Please contact our support team for assistance.",
            "escalate": True,
            "priority": "P2",
        },
    }
    return mapping.get(
        error_code,
        {
            "error": "server_error",
            "message": "We encountered a system error. Please try again in a moment.",
        },
    )
