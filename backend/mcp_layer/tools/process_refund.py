"""Tool: process_refund - Process a refund with idempotency protection.

This is a WRITE tool with irreversible side effects. It processes refunds with
idempotency protection to prevent duplicate charges. Must only be called after
lookup_order confirms refund_eligible=True.

USE THIS TOOL when: Customer requests a refund AND lookup_order returned refund_eligible=True.
DO NOT use for: Checking refund eligibility - use lookup_order first.
REQUIRES: Both customer_id from get_customer AND refund_eligible=True from lookup_order.
On LIMIT_EXCEEDED: Escalate P2 - amount exceeds the $150 refund limit.
On DUPLICATE: Return the existing refund information, do not retry.
"""

from pydantic import ValidationError

from backend.backends.payments import process_refund as process_refund_backend
from backend.mcp_layer.middleware.idempotency import get_or_create_idempotency_key
from backend.mcp_layer.middleware.prerequisites import (
    PrerequisiteError,
    check_prerequisites,
    update_session_state,
)
from backend.mcp_layer.mcp_server import mcp
from backend.mcp_layer.session_storage import get_session, update_session
from backend.types.models import ErrorCode, ProcessRefundInput, RefundReason, ToolName


@mcp.tool()
async def process_refund(
    session_id: str,
    order_id: str,
    customer_id: str,
    amount: float,
    reason: str,
) -> dict:
    """Process a refund for an eligible order with idempotency protection.

    This tool initiates a refund transaction. It automatically handles idempotency
    to prevent duplicate refunds - retrying with the same order_id will reuse the
    same idempotency key.

    Args:
        session_id: Session identifier for state tracking across tool calls
        order_id: Order ID to refund (e.g., "ORD-8842")
        customer_id: Customer ID who owns the order
        amount: Refund amount in USD (must match the order amount)
        reason: Reason for the refund - must be one of: damaged, not_received,
                wrong_item, changed_mind, billing_error

    Returns:
        Dict containing refund details (refund_id, status, amount, processed_at)
        or error information if processing fails
    """
    # Validate inputs through Pydantic model
    try:
        # Note: ProcessRefundInput expects idempotency_key, which we'll generate later
        # For now, validate the other fields
        validated = ProcessRefundInput(
            order_id=order_id,
            customer_id=customer_id,
            amount=amount,
            reason=RefundReason(reason),
            idempotency_key="placeholder",  # Will be replaced with real key
        )
    except ValidationError as e:
        return {
            "error": "invalid_input",
            "message": f"Invalid input: {str(e.errors()[0]['msg'])}",
        }
    except ValueError:
        return {
            "error": "invalid_reason",
            "message": f"Invalid refund reason. Must be one of: {', '.join([r.value for r in RefundReason])}",
        }

    # Get or create session
    session = get_session(session_id)

    # SECURITY: Validate customer_id matches session (prevent cross-account access)
    if session.customer_id and customer_id != session.customer_id:
        return {
            "error": "unauthorized",
            "message": "Unable to process this request. Please verify your account information.",
        }

    # Check prerequisites FIRST
    try:
        check_prerequisites(ToolName.PROCESS_REFUND, session)
    except PrerequisiteError as e:
        return {"error": "prerequisite_failed", "message": str(e)}

    # Get or create idempotency key for this order
    idempotency_key, updated_session = get_or_create_idempotency_key(order_id, session)
    update_session(session_id, updated_session)

    # Call backend
    result = await process_refund_backend(
        order_id, customer_id, validated.reason, idempotency_key
    )

    # Handle ErrorCode returns
    if isinstance(result, ErrorCode):
        return _map_error_to_dict(result)

    # Update session state (process_refund doesn't update state per middleware)
    result_dict = result.model_dump()
    final_session = update_session_state(ToolName.PROCESS_REFUND, result_dict, updated_session)
    update_session(session_id, final_session)

    # Return dict (not Pydantic model)
    return result_dict


def _map_error_to_dict(error_code: ErrorCode) -> dict:
    """Map ErrorCode to user-safe dict.

    CRITICAL: Never expose internal error code names or the $150 limit to customers.
    """
    mapping = {
        ErrorCode.NOT_FOUND: {
            "error": "not_found",
            "message": "We couldn't find that order. Please verify the order ID.",
        },
        ErrorCode.INELIGIBLE: {
            "error": "ineligible",
            "message": "This order is not eligible for a refund under our current policy.",
        },
        ErrorCode.DUPLICATE: {
            "error": "duplicate",
            "message": "A refund has already been processed for this order.",
        },
        ErrorCode.LIMIT_EXCEEDED: {
            "error": "limit_exceeded",
            "message": "This refund requires additional approval. Let me connect you with a specialist.",
            "escalate": True,
            "priority": "P2",
        },
        ErrorCode.SUSPENDED: {
            "error": "suspended",
            "message": "We need to review your account before processing this refund. Let me connect you with our team.",
            "escalate": True,
            "priority": "P2",
        },
    }
    return mapping.get(
        error_code,
        {
            "error": "server_error",
            "message": "We encountered a system error while processing the refund. Please try again in a moment.",
        },
    )
