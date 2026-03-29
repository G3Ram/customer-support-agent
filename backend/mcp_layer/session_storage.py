"""Centralized session storage for MCP tools.

This module provides a shared session storage that all tools use to track
state across tool calls. Each session is identified by a session_id string.
"""

from backend.types.models import SessionState

# Module-level session storage shared across all tools
_sessions: dict[str, SessionState] = {}


def get_session(session_id: str) -> SessionState:
    """Get an existing session or create a new one.
    
    Args:
        session_id: Unique identifier for the session
        
    Returns:
        SessionState for this session
    """
    if session_id not in _sessions:
        _sessions[session_id] = SessionState()
    return _sessions[session_id]


def update_session(session_id: str, session: SessionState) -> None:
    """Update a session in storage.
    
    Args:
        session_id: Unique identifier for the session
        session: Updated SessionState to store
    """
    _sessions[session_id] = session


def clear_session(session_id: str) -> None:
    """Clear a session from storage.
    
    Args:
        session_id: Unique identifier for the session to clear
    """
    if session_id in _sessions:
        del _sessions[session_id]


def clear_all_sessions() -> None:
    """Clear all sessions from storage.
    
    Useful for testing or cleanup.
    """
    _sessions.clear()
