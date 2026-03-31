"""Unit tests for error message mappings.

Ensures that internal error codes and sensitive information are never exposed
to customers through error messages.
"""

import pytest

from backend.types.models import ErrorCode

# Forbidden strings that must NEVER appear in user-facing error messages
FORBIDDEN_IN_USER_MESSAGES = [
    "LIMIT_EXCEEDED",
    "OWNERSHIP_MISMATCH",
    "NOT_FOUND",
    "AUTH_FAILURE",
    "SUSPENDED",
    "RATE_LIMITED",
    "SERVER_ERROR",
    "INELIGIBLE",
    "DUPLICATE",
    "$150",
    "150.00",
    "150",
]


def test_process_refund_error_messages_no_internal_codes():
    """process_refund error messages must not leak internal codes."""
    # Import the error mapping function directly
    from backend.mcp_layer.tools.process_refund import _map_error_to_dict

    # Test all critical error codes
    test_cases = [
        ErrorCode.NOT_FOUND,
        ErrorCode.INELIGIBLE,
        ErrorCode.DUPLICATE,
        ErrorCode.LIMIT_EXCEEDED,
        ErrorCode.SUSPENDED,
    ]

    for error_code in test_cases:
        result = _map_error_to_dict(error_code)
        message = result.get("message", "")

        # Check that no forbidden strings appear in the message
        for forbidden in FORBIDDEN_IN_USER_MESSAGES:
            assert forbidden not in message, (
                f"process_refund error mapping for {error_code.name} "
                f"leaks forbidden string '{forbidden}' in message: '{message}'"
            )


def test_lookup_order_error_messages_no_internal_codes():
    """lookup_order error messages must not leak internal codes."""
    from backend.mcp_layer.tools.lookup_order import _map_error_to_dict

    test_cases = [
        ErrorCode.NOT_FOUND,
        ErrorCode.OWNERSHIP_MISMATCH,
    ]

    for error_code in test_cases:
        result = _map_error_to_dict(error_code)
        message = result.get("message", "")

        for forbidden in FORBIDDEN_IN_USER_MESSAGES:
            assert forbidden not in message, (
                f"lookup_order error mapping for {error_code.name} "
                f"leaks forbidden string '{forbidden}' in message: '{message}'"
            )


def test_get_customer_error_messages_no_internal_codes():
    """get_customer error messages must not leak internal codes."""
    from backend.mcp_layer.tools.get_customer import _map_error_to_dict

    test_cases = [
        ErrorCode.NOT_FOUND,
        ErrorCode.SUSPENDED,
    ]

    for error_code in test_cases:
        result = _map_error_to_dict(error_code)
        message = result.get("message", "")

        for forbidden in FORBIDDEN_IN_USER_MESSAGES:
            assert forbidden not in message, (
                f"get_customer error mapping for {error_code.name} "
                f"leaks forbidden string '{forbidden}' in message: '{message}'"
            )


def test_all_critical_error_codes_have_mappings():
    """All critical error codes must have user-safe message mappings."""
    from backend.mcp_layer.tools.process_refund import _map_error_to_dict

    # process_refund handles the most error codes — verify key ones
    critical_codes = [
        ErrorCode.INELIGIBLE,
        ErrorCode.DUPLICATE,
        ErrorCode.LIMIT_EXCEEDED,
    ]

    for code in critical_codes:
        result = _map_error_to_dict(code)
        assert "error" in result, f"ErrorCode.{code.name} has no error field"
        assert "message" in result, f"ErrorCode.{code.name} has no message field"
        assert len(result["message"]) > 0, f"ErrorCode.{code.name} has empty message"


def test_limit_exceeded_never_mentions_amount():
    """LIMIT_EXCEEDED error must not mention the $150 limit."""
    from backend.mcp_layer.tools.process_refund import _map_error_to_dict

    result = _map_error_to_dict(ErrorCode.LIMIT_EXCEEDED)
    message = result.get("message", "")

    # Check for various ways $150 could be mentioned
    forbidden_patterns = ["$150", "150", "$", "limit", "amount"]

    # Only check for explicit mentions of 150, not the word "limit"
    assert "150" not in message, (
        f"LIMIT_EXCEEDED error leaks the refund limit amount: '{message}'"
    )
    assert "$150" not in message, (
        f"LIMIT_EXCEEDED error leaks the refund limit amount: '{message}'"
    )


def test_ownership_mismatch_never_mentions_code():
    """OWNERSHIP_MISMATCH must not use the term 'ownership' in user message."""
    from backend.mcp_layer.tools.lookup_order import _map_error_to_dict

    result = _map_error_to_dict(ErrorCode.OWNERSHIP_MISMATCH)
    message = result.get("message", "").lower()

    # Should not mention "ownership", "mismatch", or the specific error code
    forbidden = ["ownership", "mismatch", "ownership_mismatch"]
    for term in forbidden:
        assert term not in message, (
            f"OWNERSHIP_MISMATCH error message contains '{term}': '{message}'"
        )


def test_error_messages_are_user_friendly():
    """All error messages should be polite, clear, and actionable."""
    from backend.mcp_layer.tools.process_refund import (
        _map_error_to_dict as refund_errors,
    )
    from backend.mcp_layer.tools.lookup_order import (
        _map_error_to_dict as order_errors,
    )
    from backend.mcp_layer.tools.get_customer import (
        _map_error_to_dict as customer_errors,
    )

    # Test a sample of errors from each tool
    all_mappings = [
        (refund_errors, ErrorCode.DUPLICATE),
        (order_errors, ErrorCode.NOT_FOUND),
        (customer_errors, ErrorCode.SUSPENDED),
    ]

    for error_fn, error_code in all_mappings:
        result = error_fn(error_code)
        message = result.get("message", "")

        # Basic quality checks
        assert len(message) > 10, f"Message too short: '{message}'"
        assert message[0].isupper() or message[0] in "\"'", (
            f"Message should start with capital letter: '{message}'"
        )

        # Should not contain technical jargon
        technical_terms = ["null", "undefined", "exception", "traceback", "error code"]
        for term in technical_terms:
            assert term.lower() not in message.lower(), (
                f"Message contains technical jargon '{term}': '{message}'"
            )
