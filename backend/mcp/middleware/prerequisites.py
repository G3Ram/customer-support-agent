"""Prerequisite checking middleware for MCP tools.

This module enforces tool call ordering at the code level:
- lookup_order requires get_customer to have been called first
- process_refund requires both get_customer AND refund_eligible=True from lookup_order
- escalate_to_human requires get_customer to have been called first

These rules prevent tool misuse and ensure data consistency.
"""

from dataclasses import replace

from backend.types.models import SessionState, ToolName


class PrerequisiteError(Exception):
    """Raised when a tool is called without satisfying its prerequisites."""

    pass


def check_prerequisites(tool_name: ToolName, session: SessionState) -> None:
    """Check if prerequisites are satisfied for calling the given tool.

    Args:
        tool_name: The tool being called
        session: Current session state containing customer_id, refund_eligible, etc.

    Raises:
        PrerequisiteError: If prerequisites are not satisfied
    """
    if tool_name == ToolName.LOOKUP_ORDER:
        if session.customer_id is None:
            raise PrerequisiteError(
                "lookup_order requires get_customer to be called first. "
                "customer_id is not set in session."
            )

    elif tool_name == ToolName.PROCESS_REFUND:
        if session.customer_id is None:
            raise PrerequisiteError(
                "process_refund requires get_customer to be called first. "
                "customer_id is not set in session."
            )
        if not session.refund_eligible:
            raise PrerequisiteError(
                "process_refund requires refund_eligible=True from lookup_order. "
                "The order is not eligible for refund."
            )

    elif tool_name == ToolName.ESCALATE_TO_HUMAN:
        if session.customer_id is None:
            raise PrerequisiteError(
                "escalate_to_human requires get_customer to be called first. "
                "customer_id is not set in session."
            )

    # GET_CUSTOMER has no prerequisites


def update_session_state(
    tool_name: ToolName, result: dict, session: SessionState
) -> SessionState:
    """Update session state after a successful tool call.

    Args:
        tool_name: The tool that was called
        result: The result returned by the tool (as a dict)
        session: Current session state

    Returns:
        New SessionState instance with updated values (never mutates in place)
    """
    if tool_name == ToolName.GET_CUSTOMER:
        return replace(
            session,
            customer_id=result.get("customer_id"),
            open_case_count=result.get("open_case_count", 0),
        )

    elif tool_name == ToolName.LOOKUP_ORDER:
        return replace(session, refund_eligible=result.get("refund_eligible", False))

    elif tool_name == ToolName.ESCALATE_TO_HUMAN:
        return replace(session, escalation_triggered=True)

    # PROCESS_REFUND doesn't update session state
    return session
