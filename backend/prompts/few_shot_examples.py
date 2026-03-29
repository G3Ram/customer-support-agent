"""Few-shot examples demonstrating correct tool usage patterns.

These examples show the agent how to handle different customer support scenarios
with the correct tool sequencing, escalation logic, and reasoning.
"""

EXAMPLES: list[dict] = [
    # Example 1 — AUTO-RESOLVE (damage claim, within policy)
    {
        "user": "My blender arrived broken, order ORD-8842. I want a refund.",
        "assistant_reasoning": (
            "Call get_customer to verify identity, then lookup_order "
            "to confirm refund_eligible, then process_refund with reason=damaged. "
            "Confirm with reference ID."
        ),
        "expected_tool_sequence": ["get_customer", "lookup_order", "process_refund"],
        "outcome": "auto_resolved",
    },
    # Example 2 — ESCALATE (outside return window, policy exception)
    {
        "user": "I want to return something I bought 45 days ago.",
        "assistant_reasoning": (
            "get_customer, lookup_order returns refund_eligible=False. "
            "Cannot override policy. escalate_to_human with reason=policy_exception, priority=P2."
        ),
        "expected_tool_sequence": ["get_customer", "lookup_order", "escalate_to_human"],
        "outcome": "escalated_P2",
    },
    # Example 3 — ESCALATE (customer distress, P1)
    {
        "user": "This is absolutely unacceptable. I've been waiting 3 weeks. I want a manager NOW.",
        "assistant_reasoning": (
            "Trigger phrase detected: 'unacceptable'. get_customer to gather "
            "context, then immediately escalate_to_human with reason=customer_distress, priority=P1. "
            "Do not attempt to resolve autonomously."
        ),
        "expected_tool_sequence": ["get_customer", "escalate_to_human"],
        "outcome": "escalated_P1",
    },
]
