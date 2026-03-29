"""Idempotency key management for preventing duplicate refunds.

This module ensures that:
- Each refund attempt gets a unique UUID v4 idempotency key
- Keys persist across retries for the same order_id (preventing double charges)
- Keys regenerate when processing a different order_id
"""

import uuid
from dataclasses import replace

from backend.types.models import SessionState


def get_or_create_idempotency_key(
    operation_id: str, session: SessionState
) -> tuple[str, SessionState]:
    """Get an existing idempotency key or create a new one.

    Args:
        operation_id: Unique identifier for the operation (e.g., order_id for refunds)
        session: Current session state

    Returns:
        Tuple of (idempotency_key, updated_session_state)
        - If operation_id already exists, returns the existing key
        - If operation_id is new, generates a new UUID v4 and stores it
    """
    # Check if we already have a key for this operation
    if operation_id in session.idempotency_keys:
        return session.idempotency_keys[operation_id], session

    # Generate a new UUID v4 key
    new_key = str(uuid.uuid4())

    # Store it in the session
    updated_keys = {**session.idempotency_keys, operation_id: new_key}
    updated_session = replace(session, idempotency_keys=updated_keys)

    return new_key, updated_session
