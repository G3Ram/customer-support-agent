"""Tickets backend stub — simulates escalation ticket creation."""

from uuid import uuid4

from backend.types.models import (
    EscalateToHumanOutput,
    EscalationPriority,
    EscalationReason,
)


async def escalate_to_human(
    customer_id: str,
    reason: EscalationReason,
    summary: str,
    priority: EscalationPriority,
) -> EscalateToHumanOutput:
    """Create an escalation ticket for human agent review.

    Always succeeds. Returns different queue positions and wait times based on priority.

    Args:
        customer_id: Customer who needs assistance
        reason: Category explaining why escalation is needed
        summary: Detailed context about the issue
        priority: Urgency level (P1/P2/P3)

    Returns:
        EscalateToHumanOutput with ticket details
    """
    # Generate ticket ID
    ticket_id = f"TKT-{uuid4().hex[:6].upper()}"

    # Priority-based queue positioning
    if priority == EscalationPriority.P1:
        queue_position = 1
        estimated_wait_mins = 2
    elif priority == EscalationPriority.P2:
        queue_position = 3
        estimated_wait_mins = 10
    else:  # P3
        queue_position = 8
        estimated_wait_mins = 25

    # Format estimated response time
    if estimated_wait_mins < 60:
        estimated_response = f"{estimated_wait_mins} minutes"
    else:
        hours = estimated_wait_mins // 60
        estimated_response = f"{hours} hour{'s' if hours > 1 else ''}"

    return EscalateToHumanOutput(
        ticket_id=ticket_id,
        status="created",
        estimated_response_time=estimated_response,
    )
