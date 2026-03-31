"""Payments backend stub — simulates refund processing with idempotency."""

import os
from datetime import datetime, timezone
from uuid import uuid4

from backend.types.models import ErrorCode, ProcessRefundOutput, RefundReason

# Module-level idempotency tracking
_processed_keys: dict[str, ProcessRefundOutput] = {}


async def process_refund(
    order_id: str,
    customer_id: str,
    reason: RefundReason,
    idempotency_key: str,
) -> ProcessRefundOutput | ErrorCode:
    """Process a refund with idempotency protection.

    Maintains a module-level dict to track processed idempotency keys.
    Enforces a refund limit from the REFUND_LIMIT environment variable (default $150).

    Args:
        order_id: Order to refund
        customer_id: Customer who owns the order
        reason: Reason for the refund
        idempotency_key: UUID v4 key to prevent duplicate refunds

    Returns:
        ProcessRefundOutput with refund details, or ErrorCode if processing fails
    """
    # Check for duplicate idempotency key - return cached result for true idempotency
    if idempotency_key in _processed_keys:
        return _processed_keys[idempotency_key]

    # Map order IDs to refund amounts (based on order fixtures)
    order_amounts = {
        "ORD-8842": 89.99,
        "ORD-9901": 49.00,
        "ORD-7771": 400.00,
    }

    # Get refund amount
    if order_id not in order_amounts:
        return ErrorCode.NOT_FOUND

    amount = order_amounts[order_id]

    # Check refund limit
    refund_limit = float(os.getenv("REFUND_LIMIT", "150"))
    if amount > refund_limit:
        return ErrorCode.LIMIT_EXCEEDED

    # Process refund
    result = ProcessRefundOutput(
        refund_id=f"REF-{uuid4().hex[:6].upper()}",
        status="processed",
        amount=amount,
        processed_at=datetime.now(timezone.utc).isoformat(),
    )

    # Store in idempotency map
    _processed_keys[idempotency_key] = result

    return result
