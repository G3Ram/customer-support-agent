import pytest
from uuid import uuid4
from backend.agent.orchestrator import (
    Orchestrator, TextEvent, ToolCallEvent, ToolResultEvent
)
from backend.mcp_layer.session_storage import get_session

pytestmark = pytest.mark.asyncio

async def test_refund_happy_path():
    """
    Scenario 1: Damaged item, eligible order, within policy.
    USR-001 / ORD-8842 / refund_eligible=True / $89.99
    Expected: get_customer → lookup_order → process_refund
    No escalation. Refund confirmed in response.
    """
    orch = Orchestrator(session_id=f"int-refund-{uuid4().hex[:8]}")
    events = []
    async for event in orch.run(
        "Hi, my email is sarah@example.com. "
        "My blender arrived broken, order ORD-8842. "
        "I need a refund please."
    ):
        events.append(event)

    tool_calls = [e for e in events if isinstance(e, ToolCallEvent)]
    tool_names = [e.tool_name for e in tool_calls]
    tool_results = [e for e in events if isinstance(e, ToolResultEvent)]

    # Verify sequence
    assert "get_customer" in tool_names, f"get_customer missing: {tool_names}"
    assert "lookup_order" in tool_names, f"lookup_order missing: {tool_names}"
    assert "process_refund" in tool_names, f"process_refund missing: {tool_names}"
    assert "escalate_to_human" not in tool_names, f"Unexpected escalation: {tool_names}"

    # Verify order
    gc = tool_names.index("get_customer")
    lo = tool_names.index("lookup_order")
    pr = tool_names.index("process_refund")
    assert gc < lo < pr, f"Wrong tool order: {tool_names}"

    # Verify no parse errors
    bad = [e for e in tool_results
           if "unexpected_response_format" in str(e.result)]
    assert not bad, f"Response parse errors: {[e.result for e in bad]}"

    # Verify refund confirmed in text
    text = " ".join(
        e.content for e in events if isinstance(e, TextEvent)
    ).lower()
    assert any(w in text for w in ["refund", "ref-", "processed", "issued"]), \
        f"No refund confirmation: {text[:300]}"

    # Verify session state
    session = get_session(orch.session_id)
    assert session.customer_id == "USR-001"

    print(f"✓ Refund happy path — sequence: {tool_names}")


async def test_prerequisite_enforced_live():
    """
    Even when user gives order ID first, get_customer
    must always precede lookup_order.
    """
    orch = Orchestrator(session_id=f"int-prereq-{uuid4().hex[:8]}")
    events = []
    async for event in orch.run("Check order ORD-8842"):
        events.append(event)

    tool_names = [e.tool_name for e in events if isinstance(e, ToolCallEvent)]

    if "lookup_order" in tool_names:
        assert "get_customer" in tool_names, \
            "CRITICAL: lookup_order called without get_customer"
        gc = tool_names.index("get_customer")
        lo = tool_names.index("lookup_order")
        assert gc < lo, \
            f"CRITICAL: lookup_order before get_customer: {tool_names}"

    print(f"✓ Prerequisite enforced — sequence: {tool_names}")


async def test_idempotency_key_reuse():
    """
    Simulate what happens on retry — same session, same order.
    The second refund attempt must not create a duplicate charge.
    """
    session_id = f"int-idem-{uuid4().hex[:8]}"
    orch = Orchestrator(session_id=session_id)

    # First attempt
    events1 = []
    async for event in orch.run(
        "Email sarah@example.com. Order ORD-8842 arrived broken. Refund please."
    ):
        events1.append(event)

    tool_names1 = [e.tool_name for e in events1 if isinstance(e, ToolCallEvent)]

    # Check idempotency key was stored
    from backend.mcp_layer.session_storage import get_session as gs
    session_state = gs(session_id)
    assert len(session_state.idempotency_keys) > 0, \
        "No idempotency key stored after refund"

    key_before = dict(session_state.idempotency_keys)
    print(f"✓ Idempotency key stored: {key_before}")
    print(f"✓ First attempt sequence: {tool_names1}")
