"""CRM backend stub — returns hardcoded customer fixture data."""

from backend.types.models import ErrorCode, GetCustomerOutput


async def get_customer(customer_id: str) -> GetCustomerOutput | ErrorCode:
    """Look up customer by ID in the CRM system.

    Returns fixture data for known customer IDs, error codes for special cases.

    Args:
        customer_id: Customer identifier (e.g., "USR-001")

    Returns:
        GetCustomerOutput with customer details, or ErrorCode if lookup fails
    """
    # Hardcoded fixtures
    fixtures = {
        "USR-001": GetCustomerOutput(
            customer_id="USR-001",
            name="Sarah Chen",
            email="sarah@example.com",
            account_status="active",
            open_case_count=0,
        ),
        "USR-002": GetCustomerOutput(
            customer_id="USR-002",
            name="Marcus Lee",
            email="marcus@example.com",
            account_status="active",
            open_case_count=0,
        ),
        "USR-VIP": GetCustomerOutput(
            customer_id="USR-VIP",
            name="James Wright",
            email="james@example.com",
            account_status="active",
            open_case_count=1,
        ),
    }

    # Special error cases
    if customer_id == "USR-SUSPENDED":
        return ErrorCode.SUSPENDED

    # Look up in fixtures
    if customer_id in fixtures:
        return fixtures[customer_id]

    # Not found
    return ErrorCode.NOT_FOUND
