"""Orders backend stub — returns hardcoded order fixture data."""

from backend.types.models import ErrorCode, LookupOrderOutput


async def lookup_order(order_id: str, customer_id: str) -> LookupOrderOutput | ErrorCode:
    """Look up order by ID and verify customer ownership.

    CRITICAL: Returns OWNERSHIP_MISMATCH if order exists but belongs to a different customer.

    Args:
        order_id: Order identifier (e.g., "ORD-8842")
        customer_id: Customer ID for ownership verification

    Returns:
        LookupOrderOutput with order details, or ErrorCode if lookup fails
    """
    # Hardcoded fixtures with ownership mapping
    fixtures = {
        "ORD-8842": {
            "owner": "USR-001",
            "data": LookupOrderOutput(
                order_id="ORD-8842",
                customer_id="USR-001",
                amount=89.99,
                order_date="2026-03-14T10:00:00Z",
                status="delivered",
                refund_eligible=True,
            ),
        },
        "ORD-9901": {
            "owner": "USR-002",
            "data": LookupOrderOutput(
                order_id="ORD-9901",
                customer_id="USR-002",
                amount=49.00,
                order_date="2026-02-03T10:00:00Z",
                status="delivered",
                refund_eligible=False,
                refund_reason="Subscription orders are not refundable",
            ),
        },
        "ORD-7771": {
            "owner": "USR-VIP",
            "data": LookupOrderOutput(
                order_id="ORD-7771",
                customer_id="USR-VIP",
                amount=400.00,
                order_date="2026-03-01T10:00:00Z",
                status="lost_in_transit",
                refund_eligible=True,
            ),
        },
    }

    # Check if order exists
    if order_id not in fixtures:
        return ErrorCode.NOT_FOUND

    # CRITICAL: Verify ownership
    fixture = fixtures[order_id]
    if fixture["owner"] != customer_id:
        return ErrorCode.OWNERSHIP_MISMATCH

    # Return order data
    return fixture["data"]
