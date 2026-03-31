import pytest
from uuid import uuid4
from backend.agent.orchestrator import Orchestrator, TextEvent, ToolCallEvent

pytestmark = pytest.mark.asyncio


async def test_distress_trigger_p1():
    """
    'Unacceptable' trigger phrase → immediate P1 escalation.
    """
    orch = Orchestrator(session_id=f"int-p1-{uuid4().hex[:8]}")
    events = []
    async for event in orch.run(
        "Email james@example.com. "
        "This is absolutely unacceptable. "
        "I want to speak to a manager RIGHT NOW."
    ):
        events.append(event)

    tool_calls = [e for e in events if isinstance(e, ToolCallEvent)]
    tool_names = [e.tool_name for e in tool_calls]

    assert "escalate_to_human" in tool_names, \
        f"Must escalate on distress trigger. Got: {tool_names}"

    escalate = next(
        e for e in tool_calls if e.tool_name == "escalate_to_human"
    )
    assert escalate.tool_input.get("priority") == "P1", \
        f"Must be P1. Got: {escalate.tool_input.get('priority')}"
    assert escalate.tool_input.get("reason") == "customer_distress", \
        f"Wrong reason: {escalate.tool_input}"

    context = escalate.tool_input.get("context", "")
    assert len(context) > 20, f"Context too short: '{context}'"

    text = " ".join(
        e.content for e in events if isinstance(e, TextEvent)
    ).lower()
    assert any(w in text for w in ["ticket", "tkt", "agent", "team", "specialist"]), \
        f"Response must reference escalation: {text[:200]}"

    print(f"✓ P1 escalation — reason: {escalate.tool_input.get('reason')}, "
          f"priority: {escalate.tool_input.get('priority')}")
    print(f"  Context: '{context[:80]}'")


async def test_human_request_honored():
    """Explicit request for human must always be honored."""
    orch = Orchestrator(session_id=f"int-human-{uuid4().hex[:8]}")
    events = []
    async for event in orch.run(
        "Email sarah@example.com. "
        "I want to speak to a real person please."
    ):
        events.append(event)

    tool_names = [e.tool_name for e in events if isinstance(e, ToolCallEvent)]
    assert "escalate_to_human" in tool_names, \
        f"Must honor human request. Got: {tool_names}"

    print(f"✓ Human request honored — sequence: {tool_names}")


async def test_ineligible_order_escalation():
    """
    Order outside return window → explained or escalated P2.
    Must NOT silently fail or give wrong info.
    """
    orch = Orchestrator(session_id=f"int-inelig-{uuid4().hex[:8]}")
    events = []
    async for event in orch.run(
        "Email marcus@example.com. "
        "I want to return order ORD-9901. "
        "I know it has been a while but I really need this refund."
    ):
        events.append(event)

    tool_names = [e.tool_name for e in events if isinstance(e, ToolCallEvent)]
    text = " ".join(
        e.content for e in events if isinstance(e, TextEvent)
    ).lower()

    # Must have checked the order
    assert "lookup_order" in tool_names, \
        f"Must look up order before deciding. Got: {tool_names}"

    # Either escalates or explains policy clearly
    if "escalate_to_human" in tool_names:
        escalate = next(
            e for e in events
            if isinstance(e, ToolCallEvent) and e.tool_name == "escalate_to_human"
        )
        priority = escalate.tool_input.get("priority")
        assert priority in ["P2", "P3"], \
            f"Ineligible order should be P2/P3, got: {priority}"
        print(f"✓ Ineligible order → escalated {priority}")
    else:
        assert any(w in text for w in ["policy", "eligible", "window", "30"]), \
            f"Must explain policy. Got: {text[:300]}"
        print(f"✓ Ineligible order → policy explained")
