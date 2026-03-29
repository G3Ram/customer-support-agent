"""Unit tests for idempotency key management.

Tests verify that:
- Same operation_id returns the same key (prevents double charges on retry)
- Different operation_ids get different keys
- Keys are valid UUID v4 format
- Session state is immutable (returns new instance)
"""

import re
import uuid

import pytest

from backend.mcp_layer.middleware.idempotency import get_or_create_idempotency_key
from backend.types.models import SessionState


# UUID v4 regex pattern
UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class TestGetOrCreateIdempotencyKey:
    """Test idempotency key generation and retrieval."""

    def test_first_call_generates_new_key(self):
        """First call for an operation_id generates a new UUID v4."""
        session = SessionState()
        operation_id = "order_123"

        key, updated_session = get_or_create_idempotency_key(operation_id, session)

        # Should generate a key
        assert key is not None
        assert len(key) > 0

        # Should be a valid UUID v4
        assert UUID_V4_PATTERN.match(key), f"Invalid UUID v4 format: {key}"

        # Should be parseable as UUID
        uuid.UUID(key)  # Raises ValueError if invalid

        # Should be stored in session
        assert operation_id in updated_session.idempotency_keys
        assert updated_session.idempotency_keys[operation_id] == key

    def test_same_operation_id_returns_same_key(self):
        """Calling with the same operation_id twice returns the same key."""
        session = SessionState()
        operation_id = "order_123"

        # First call
        key1, session1 = get_or_create_idempotency_key(operation_id, session)

        # Second call with updated session
        key2, session2 = get_or_create_idempotency_key(operation_id, session1)

        # Should return the same key
        assert key1 == key2

        # Session should still have the key
        assert session2.idempotency_keys[operation_id] == key1

    def test_different_operation_ids_get_different_keys(self):
        """Different operation_ids get different idempotency keys."""
        session = SessionState()

        key1, session1 = get_or_create_idempotency_key("order_123", session)
        key2, session2 = get_or_create_idempotency_key("order_456", session1)

        # Keys should be different
        assert key1 != key2

        # Both should be valid UUID v4
        assert UUID_V4_PATTERN.match(key1)
        assert UUID_V4_PATTERN.match(key2)

        # Both should be stored
        assert session2.idempotency_keys["order_123"] == key1
        assert session2.idempotency_keys["order_456"] == key2

    def test_session_state_is_immutable(self):
        """get_or_create_idempotency_key returns a new SessionState instance."""
        session = SessionState()
        operation_id = "order_123"

        key, updated_session = get_or_create_idempotency_key(operation_id, session)

        # Should return a different instance
        assert updated_session is not session
        assert id(updated_session) != id(session)

        # Original session should be unchanged
        assert operation_id not in session.idempotency_keys

        # Updated session should have the key
        assert operation_id in updated_session.idempotency_keys

    def test_key_persists_across_multiple_calls(self):
        """Key persists across multiple sequential calls with the same operation_id."""
        session = SessionState()
        operation_id = "order_789"

        # Generate key
        key1, session1 = get_or_create_idempotency_key(operation_id, session)

        # Retrieve it multiple times
        key2, session2 = get_or_create_idempotency_key(operation_id, session1)
        key3, session3 = get_or_create_idempotency_key(operation_id, session2)
        key4, session4 = get_or_create_idempotency_key(operation_id, session3)

        # All should be the same key
        assert key1 == key2 == key3 == key4

    def test_key_format_is_uuid_v4(self):
        """Generated keys are valid UUID v4 format."""
        session = SessionState()

        # Generate multiple keys
        keys = []
        for i in range(5):
            key, session = get_or_create_idempotency_key(f"order_{i}", session)
            keys.append(key)

        # All should be valid UUID v4
        for key in keys:
            assert UUID_V4_PATTERN.match(key), f"Invalid UUID v4: {key}"

            # Should be parseable as UUID
            parsed = uuid.UUID(key)

            # Should be version 4
            assert parsed.version == 4

    def test_empty_operation_id(self):
        """Function handles empty operation_id string."""
        session = SessionState()

        key, updated_session = get_or_create_idempotency_key("", session)

        # Should still generate a key
        assert key is not None
        assert UUID_V4_PATTERN.match(key)

        # Should be stored with empty string as key
        assert "" in updated_session.idempotency_keys
