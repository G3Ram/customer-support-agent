"""Unit tests for prerequisite checking middleware.

Tests verify that tool ordering violations are caught at the code level:
- lookup_order requires customer_id
- process_refund requires customer_id AND refund_eligible
- escalate_to_human requires customer_id
- update_session_state correctly updates session after tool calls
"""

import pytest

from backend.mcp.middleware.prerequisites import (
    PrerequisiteError,
    check_prerequisites,
    update_session_state,
)
from backend.types.models import SessionState, ToolName


class TestCheckPrerequisites:
    """Test that prerequisite violations raise PrerequisiteError."""

    def test_lookup_order_without_customer_id_raises_error(self):
        """lookup_order requires get_customer to be called first."""
        session = SessionState()  # customer_id is None
        with pytest.raises(
            PrerequisiteError, match="lookup_order requires get_customer"
        ):
            check_prerequisites(ToolName.LOOKUP_ORDER, session)

    def test_process_refund_without_customer_id_raises_error(self):
        """process_refund requires get_customer to be called first."""
        session = SessionState()  # customer_id is None
        with pytest.raises(
            PrerequisiteError, match="process_refund requires get_customer"
        ):
            check_prerequisites(ToolName.PROCESS_REFUND, session)

    def test_process_refund_with_customer_id_but_not_eligible_raises_error(self):
        """process_refund requires refund_eligible=True from lookup_order."""
        session = SessionState(customer_id="cust_123", refund_eligible=False)
        with pytest.raises(
            PrerequisiteError, match="process_refund requires refund_eligible=True"
        ):
            check_prerequisites(ToolName.PROCESS_REFUND, session)

    def test_escalate_to_human_without_customer_id_raises_error(self):
        """escalate_to_human requires get_customer to be called first."""
        session = SessionState()  # customer_id is None
        with pytest.raises(
            PrerequisiteError, match="escalate_to_human requires get_customer"
        ):
            check_prerequisites(ToolName.ESCALATE_TO_HUMAN, session)

    def test_get_customer_has_no_prerequisites(self):
        """get_customer can be called anytime, no prerequisites."""
        session = SessionState()
        # Should not raise
        check_prerequisites(ToolName.GET_CUSTOMER, session)

    def test_lookup_order_with_customer_id_succeeds(self):
        """lookup_order succeeds when customer_id is set."""
        session = SessionState(customer_id="cust_123")
        # Should not raise
        check_prerequisites(ToolName.LOOKUP_ORDER, session)

    def test_process_refund_with_all_prerequisites_succeeds(self):
        """process_refund succeeds when customer_id is set and refund_eligible=True."""
        session = SessionState(customer_id="cust_123", refund_eligible=True)
        # Should not raise
        check_prerequisites(ToolName.PROCESS_REFUND, session)

    def test_escalate_to_human_with_customer_id_succeeds(self):
        """escalate_to_human succeeds when customer_id is set."""
        session = SessionState(customer_id="cust_123")
        # Should not raise
        check_prerequisites(ToolName.ESCALATE_TO_HUMAN, session)


class TestUpdateSessionState:
    """Test that session state is correctly updated after tool calls."""

    def test_get_customer_sets_customer_id(self):
        """get_customer updates customer_id in session."""
        session = SessionState()
        result = {"customer_id": "cust_456", "open_case_count": 3}

        updated = update_session_state(ToolName.GET_CUSTOMER, result, session)

        assert updated.customer_id == "cust_456"
        assert updated.open_case_count == 3
        # Original session is not mutated
        assert session.customer_id is None

    def test_lookup_order_sets_refund_eligible(self):
        """lookup_order updates refund_eligible in session."""
        session = SessionState(customer_id="cust_123")
        result = {"refund_eligible": True}

        updated = update_session_state(ToolName.LOOKUP_ORDER, result, session)

        assert updated.refund_eligible is True
        # Original session is not mutated
        assert session.refund_eligible is False

    def test_lookup_order_with_refund_eligible_false(self):
        """lookup_order correctly handles refund_eligible=False."""
        session = SessionState(customer_id="cust_123")
        result = {"refund_eligible": False}

        updated = update_session_state(ToolName.LOOKUP_ORDER, result, session)

        assert updated.refund_eligible is False

    def test_escalate_to_human_sets_escalation_triggered(self):
        """escalate_to_human updates escalation_triggered in session."""
        session = SessionState(customer_id="cust_123")
        result = {"ticket_id": "ticket_789"}

        updated = update_session_state(ToolName.ESCALATE_TO_HUMAN, result, session)

        assert updated.escalation_triggered is True
        # Original session is not mutated
        assert session.escalation_triggered is False

    def test_process_refund_does_not_update_session(self):
        """process_refund doesn't update session state."""
        session = SessionState(customer_id="cust_123", refund_eligible=True)
        result = {"refund_id": "refund_xyz", "status": "processed"}

        updated = update_session_state(ToolName.PROCESS_REFUND, result, session)

        # Session should be returned unchanged
        assert updated.customer_id == session.customer_id
        assert updated.refund_eligible == session.refund_eligible

    def test_update_session_state_never_mutates_in_place(self):
        """Verify that update_session_state returns a new instance."""
        session = SessionState()
        result = {"customer_id": "cust_789", "open_case_count": 1}

        updated = update_session_state(ToolName.GET_CUSTOMER, result, session)

        # Should be different objects
        assert updated is not session
        assert id(updated) != id(session)
