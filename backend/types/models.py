"""Core data models for the customer support agent.

This module defines all enums, dataclasses, and Pydantic models used throughout
the application. All tool inputs and outputs must use these models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class ToolName(str, Enum):
    """MCP tool names in the required call order."""

    GET_CUSTOMER = "get_customer"
    LOOKUP_ORDER = "lookup_order"
    PROCESS_REFUND = "process_refund"
    ESCALATE_TO_HUMAN = "escalate_to_human"


class RefundReason(str, Enum):
    """Valid reasons for processing a refund."""

    DAMAGED = "damaged"
    NOT_RECEIVED = "not_received"
    WRONG_ITEM = "wrong_item"
    CHANGED_MIND = "changed_mind"
    BILLING_ERROR = "billing_error"


class EscalationReason(str, Enum):
    """Reasons for escalating to a human agent."""

    POLICY_EXCEPTION = "policy_exception"
    CUSTOMER_DISTRESS = "customer_distress"
    TOOL_FAILURE = "tool_failure"
    FRAUD_SUSPECTED = "fraud_suspected"
    COMPLEXITY = "complexity"


class EscalationPriority(str, Enum):
    """Priority levels for escalations."""

    P1 = "P1"  # Urgent: legal threats, fraud, ownership mismatch
    P2 = "P2"  # High: tool failures, limit exceeded
    P3 = "P3"  # Normal: complexity, failed clarifications


class ErrorCode(str, Enum):
    """Error codes returned by backend systems and tools.

    These codes are NEVER shown to customers — they're for internal use only.
    """

    # Customer/Account errors
    NOT_FOUND = "NOT_FOUND"
    SUSPENDED = "SUSPENDED"
    AUTH_FAILURE = "AUTH_FAILURE"

    # Authorization errors
    OWNERSHIP_MISMATCH = "OWNERSHIP_MISMATCH"  # Triggers P1 escalation
    ACCESS_DENIED = "ACCESS_DENIED"

    # Refund errors
    INELIGIBLE = "INELIGIBLE"
    DUPLICATE = "DUPLICATE"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"  # Amount > $150, triggers P2 escalation
    PAYMENT_FAILED = "PAYMENT_FAILED"

    # System errors
    RATE_LIMITED = "RATE_LIMITED"
    SERVER_ERROR = "SERVER_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


# ============================================================================
# Session State
# ============================================================================


@dataclass
class SessionState:
    """Tracks conversation state and tool call history for a single session.

    Used by middleware to enforce prerequisites and idempotency rules.
    """

    customer_id: Optional[str] = None
    """Customer ID from get_customer, required before lookup_order/process_refund."""

    refund_eligible: bool = False
    """Set to True by lookup_order when refund_eligible=True, required for process_refund."""

    escalation_triggered: bool = False
    """True if escalate_to_human has been called in this session."""

    open_case_count: int = 0
    """Number of open support cases for the current customer."""

    idempotency_keys: dict[str, str] = field(default_factory=dict)
    """Map of order_id -> idempotency_key for refund deduplication.

    Keys persist across retries for the same order, regenerate on new order.
    """


# ============================================================================
# Tool Input/Output Models
# ============================================================================


class GetCustomerInput(BaseModel):
    """Input for the get_customer tool."""

    email: str = Field(
        description="Customer email address to look up in the CRM system"
    )


class GetCustomerOutput(BaseModel):
    """Output from the get_customer tool."""

    customer_id: str = Field(
        description="Unique customer identifier for use in subsequent tool calls"
    )

    name: str = Field(description="Customer's full name")

    email: str = Field(description="Customer's email address")

    account_status: str = Field(
        description="Account status: 'active', 'suspended', or 'closed'"
    )

    open_case_count: int = Field(
        description="Number of open support cases for this customer"
    )

    error_code: Optional[ErrorCode] = Field(
        default=None, description="Error code if the lookup failed"
    )


class LookupOrderInput(BaseModel):
    """Input for the lookup_order tool."""

    order_id: str = Field(description="Order ID to look up in the order system")

    customer_id: str = Field(
        description="Customer ID from get_customer, used for ownership verification"
    )


class LookupOrderOutput(BaseModel):
    """Output from the lookup_order tool."""

    order_id: str = Field(description="Order ID that was looked up")

    customer_id: str = Field(description="Customer ID who owns this order")

    amount: float = Field(description="Order total amount in USD")

    order_date: str = Field(description="ISO 8601 formatted order date")

    status: str = Field(
        description="Order status: 'pending', 'shipped', 'delivered', 'cancelled'"
    )

    refund_eligible: bool = Field(
        description="True if this order can be refunded, False otherwise"
    )

    refund_reason: Optional[str] = Field(
        default=None,
        description="Reason why the order is ineligible for refund, if applicable",
    )

    error_code: Optional[ErrorCode] = Field(
        default=None, description="Error code if the lookup failed"
    )


class ProcessRefundInput(BaseModel):
    """Input for the process_refund tool."""

    order_id: str = Field(description="Order ID to refund")

    customer_id: str = Field(description="Customer ID who owns the order")

    amount: float = Field(description="Refund amount in USD (must match order amount)")

    reason: RefundReason = Field(description="Reason for the refund")

    idempotency_key: str = Field(
        description="UUID v4 idempotency key to prevent duplicate refunds. "
        "Generated once per refund attempt, reused on retry."
    )


class ProcessRefundOutput(BaseModel):
    """Output from the process_refund tool."""

    refund_id: str = Field(description="Unique identifier for this refund transaction")

    status: str = Field(
        description="Refund status: 'processed', 'pending', or 'failed'"
    )

    amount: float = Field(description="Amount that was refunded in USD")

    processed_at: str = Field(
        description="ISO 8601 timestamp when the refund was processed"
    )

    error_code: Optional[ErrorCode] = Field(
        default=None, description="Error code if the refund failed"
    )


class EscalateToHumanInput(BaseModel):
    """Input for the escalate_to_human tool."""

    reason: EscalationReason = Field(
        description="Category explaining why human intervention is needed"
    )

    priority: EscalationPriority = Field(
        description="Urgency level: P1 (urgent), P2 (high), P3 (normal)"
    )

    context: str = Field(
        description="Detailed context about the customer issue, conversation history, "
        "and any attempted resolutions. This helps the human agent understand the situation."
    )

    customer_id: Optional[str] = Field(
        default=None, description="Customer ID if available from get_customer"
    )

    order_id: Optional[str] = Field(
        default=None, description="Order ID if the issue is related to a specific order"
    )


class EscalateToHumanOutput(BaseModel):
    """Output from the escalate_to_human tool."""

    ticket_id: str = Field(
        description="Unique identifier for the escalation ticket in the ticketing system"
    )

    status: str = Field(
        description="Ticket status: 'created', 'assigned', or 'failed'"
    )

    estimated_response_time: str = Field(
        description="Human-readable estimate of when a human agent will respond"
    )

    error_code: Optional[ErrorCode] = Field(
        default=None, description="Error code if ticket creation failed"
    )
