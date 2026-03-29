"""Tool: escalate_to_human - Create an escalation ticket for human agent review.

This tool creates a support ticket for a human agent to take over the conversation.
It should be used when the issue cannot be resolved through automated tools or when
the customer explicitly requests human assistance.

USE THIS TOOL when: Issue requires policy exception, customer is distressed, tools fail
after retries, fraud is suspected, or customer explicitly requests human help.
DO NOT use for: Issues that can be resolved with other tools.
REQUIRES: Verified customer_id from get_customer must be in session first.
On success: Always succeeds and returns ticket details with estimated response time.
"""

from backend.backends.tickets import escalate_to_human as escalate_to_human_backend
from backend.mcp_layer.middleware.prerequisites import (
    PrerequisiteError,
    check_prerequisites,
    update_session_state,
)
from backend.mcp_layer.mcp_server import mcp
from backend.mcp_layer.session_storage import get_session, update_session
from backend.types.models import (
    EscalationPriority,
    EscalationReason,
    ToolName,
)


@mcp.tool()
async def escalate_to_human(
    session_id: str,
    reason: str,
    priority: str,
    context: str,
    customer_id: str,
    order_id: str | None = None,
) -> dict:
    """Create an escalation ticket for human agent review.

    This tool transfers the conversation to a human agent by creating a support
    ticket with all relevant context. The ticket is prioritized based on urgency.

    Args:
        session_id: Session identifier for state tracking across tool calls
        reason: Category explaining why human intervention is needed. Must be one of:
                policy_exception, customer_distress, tool_failure, fraud_suspected, complexity
        priority: Urgency level. Must be one of: P1 (urgent), P2 (high), P3 (normal)
        context: Detailed context about the customer issue (2-3 sentences covering what
                 customer wants, what was tried, and why it couldn't be resolved)
        customer_id: Customer ID from get_customer
        order_id: Optional order ID if the issue is related to a specific order

    Returns:
        Dict containing ticket details (ticket_id, status, estimated_response_time)
    """
    # Get or create session
    session = get_session(session_id)

    # Check prerequisites FIRST
    try:
        check_prerequisites(ToolName.ESCALATE_TO_HUMAN, session)
    except PrerequisiteError as e:
        return {"error": "prerequisite_failed", "message": str(e)}

    # Validate reason enum
    try:
        escalation_reason = EscalationReason(reason)
    except ValueError:
        return {
            "error": "invalid_reason",
            "message": f"Invalid escalation reason. Must be one of: {', '.join([r.value for r in EscalationReason])}",
        }

    # Validate priority enum
    try:
        escalation_priority = EscalationPriority(priority)
    except ValueError:
        return {
            "error": "invalid_priority",
            "message": f"Invalid priority. Must be one of: {', '.join([p.value for p in EscalationPriority])}",
        }

    # Call backend (note: backend uses "summary" instead of "context")
    result = await escalate_to_human_backend(
        customer_id=customer_id,
        reason=escalation_reason,
        summary=context,
        priority=escalation_priority,
    )

    # Update session state
    result_dict = result.model_dump()
    updated_session = update_session_state(ToolName.ESCALATE_TO_HUMAN, result_dict, session)
    update_session(session_id, updated_session)

    # Return dict (not Pydantic model)
    return result_dict
