"""Agent session management for customer support conversations.

This module provides session-level abstractions over the Orchestrator,
tracking conversation lifecycle, turn counts, escalation state, and
first-contact resolution (FCR) metrics.
"""

from collections.abc import AsyncIterator
from datetime import datetime

from backend.agent.orchestrator import AgentEvent, Orchestrator


class AgentSession:
    """Represents a single support conversation session.

    Wraps Orchestrator with session lifecycle management and tracks key metrics:
    - Turn count (for FCR calculation)
    - Escalation state (whether escalate_to_human was called)
    - Resolution state (whether the issue was resolved)

    Attributes:
        session_id: Unique identifier for this session
        orchestrator: Underlying Orchestrator instance
        created_at: UTC timestamp when the session was created
        turn_count: Number of user turns processed
        is_escalated: Whether escalate_to_human has been called
        is_resolved: Whether the issue has been marked as resolved
    """

    def __init__(self, session_id: str):
        """Initialize a new agent session.

        Args:
            session_id: Unique identifier for this conversation session
        """
        self.session_id = session_id
        self.orchestrator = Orchestrator(session_id)
        self.created_at = datetime.utcnow()
        self.turn_count: int = 0
        self.is_escalated: bool = False
        self.is_resolved: bool = False

    async def process_turn(self, message: str) -> AsyncIterator[AgentEvent]:
        """Process a single conversation turn.

        This method:
        1. Increments the turn counter
        2. Delegates to the orchestrator's run() method
        3. Tracks whether escalation or resolution occurred during this turn
        4. Yields all events from the orchestrator

        Args:
            message: User message to process

        Yields:
            AgentEvent instances from the orchestrator
        """
        self.turn_count += 1

        async for event in self.orchestrator.run(message):
            # Track escalation
            if hasattr(event, "tool_name") and event.tool_name == "escalate_to_human":
                self.is_escalated = True

            # Track successful refund (marks session as resolved)
            if (
                hasattr(event, "result")
                and isinstance(event.result, dict)
                and "refund_id" in event.result
                and event.result.get("status") == "processed"
                and not event.is_error
            ):
                self.is_resolved = True

            yield event

    @property
    def fcr_achieved(self) -> bool:
        """Check if first-contact resolution was achieved.

        First-contact resolution (FCR) is defined as:
        - Issue resolved in exactly 1 turn
        - No escalation to human required
        - Issue marked as resolved

        Returns:
            True if FCR was achieved, False otherwise
        """
        return self.is_resolved and not self.is_escalated and self.turn_count == 1


# Module-level session registry (in-memory for now)
_sessions: dict[str, AgentSession] = {}


def get_or_create_agent_session(session_id: str) -> AgentSession:
    """Get an existing agent session or create a new one.

    This function maintains a module-level registry of active sessions.
    Sessions persist for the lifetime of the process.

    Args:
        session_id: Unique identifier for the session

    Returns:
        AgentSession instance for the given session_id
    """
    if session_id not in _sessions:
        _sessions[session_id] = AgentSession(session_id)
    return _sessions[session_id]


def clear_all_sessions() -> None:
    """Clear all sessions from the registry.

    Useful for testing or cleanup between test runs.
    """
    _sessions.clear()
