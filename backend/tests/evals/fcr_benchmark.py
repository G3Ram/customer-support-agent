"""FCR (First-Contact Resolution) Benchmark — Measure agent effectiveness.

This evaluation measures whether the agent achieves ≥80% first-contact resolution.
FCR = resolved in one turn, without escalation, without clarification rounds.
"""

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from backend.agent.session import AgentSession
from backend.agent.orchestrator import ToolCallEvent, TextEvent

# Define the eval scenarios
SCENARIOS = [
    {
        "id": "fcr-001",
        "name": "Damaged item refund",
        "message": "Hi, email sarah@example.com. My blender arrived broken, order ORD-8842. I want a refund.",
        "expected_outcome": "auto_resolved",
        "expected_tools": ["get_customer", "lookup_order", "process_refund"],
        "must_not_escalate": True,
    },
    {
        "id": "fcr-002",
        "name": "Distress trigger escalation",
        "message": "Email james@example.com. This is absolutely unacceptable. I want a manager NOW.",
        "expected_outcome": "escalated",
        "expected_tools": ["get_customer", "escalate_to_human"],
        "must_not_escalate": False,
    },
    {
        "id": "fcr-003",
        "name": "Human request honored",
        "message": "Email sarah@example.com. I want to talk to a real person please.",
        "expected_outcome": "escalated",
        "expected_tools": ["escalate_to_human"],
        "must_not_escalate": False,
    },
    {
        "id": "fcr-004",
        "name": "Ineligible order — policy explained",
        "message": "Email marcus@example.com. I want to return order ORD-9901 from 45 days ago.",
        "expected_outcome": "escalated_or_explained",
        "expected_tools": ["get_customer", "lookup_order"],
        "must_not_escalate": False,
    },
    {
        "id": "fcr-005",
        "name": "Cross-account blocked",
        "message": "Email marcus@example.com. Check order ORD-8842 please.",
        "expected_outcome": "blocked_or_escalated",
        "expected_tools": ["get_customer", "lookup_order"],
        "must_not_escalate": False,
    },
]


async def run_scenario(scenario: dict) -> dict:
    """Run a single eval scenario and return result."""
    session = AgentSession(session_id=f"eval-{scenario['id']}-{uuid4().hex[:6]}")

    events = []
    async for event in session.process_turn(scenario["message"]):
        events.append(event)

    tool_names = [e.tool_name for e in events if isinstance(e, ToolCallEvent)]
    text = " ".join(
        e.content for e in events if isinstance(e, TextEvent)
    ).lower()

    # Determine outcome
    if session.is_escalated:
        outcome = "escalated"
    elif session.is_resolved:
        outcome = "auto_resolved"
    elif "?" in text:
        outcome = "clarification_requested"
    else:
        outcome = "explained"

    # FCR achieved if: resolved without escalation in 1 turn
    fcr = session.fcr_achieved

    # Check for internal code leakage
    forbidden = ["LIMIT_EXCEEDED", "OWNERSHIP_MISMATCH", "NOT_FOUND",
                 "AUTH_FAILURE", "$150", "RATE_LIMITED"]
    leaked = [f for f in forbidden if f in " ".join(
        e.content for e in events if isinstance(e, TextEvent)
    )]

    return {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "expected_outcome": scenario["expected_outcome"],
        "actual_outcome": outcome,
        "tool_sequence": tool_names,
        "fcr_achieved": fcr,
        "turn_count": session.turn_count,
        "is_escalated": session.is_escalated,
        "is_resolved": session.is_resolved,
        "internal_codes_leaked": leaked,
        "passed": (
            outcome == scenario["expected_outcome"] or
            (scenario["expected_outcome"] == "escalated_or_explained" and
             outcome in ["escalated", "explained", "clarification_requested"]) or
            (scenario["expected_outcome"] == "blocked_or_escalated" and
             outcome in ["escalated", "explained"])
        ) and not leaked,
    }


async def run_benchmark():
    """Run all scenarios and calculate FCR rate."""
    print(f"\n{'='*60}")
    print(f"FCR BENCHMARK — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: ≥80% first-contact resolution")
    print(f"{'='*60}\n")

    results = []
    for scenario in SCENARIOS:
        print(f"Running: {scenario['name']}...")
        result = await run_scenario(scenario)
        results.append(result)
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        print(f"  {status} | outcome: {result['actual_outcome']} | "
              f"tools: {result['tool_sequence']}")
        if result["internal_codes_leaked"]:
            print(f"  ⚠ LEAKED: {result['internal_codes_leaked']}")

    # Calculate metrics
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    fcr_eligible = [r for r in results if r["expected_outcome"] == "auto_resolved"]
    fcr_achieved = sum(1 for r in fcr_eligible if r["fcr_achieved"])
    fcr_rate = (fcr_achieved / len(fcr_eligible) * 100) if fcr_eligible else 0

    print(f"\n{'='*60}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Scenarios passed:     {passed}/{total}")
    print(f"FCR rate:             {fcr_rate:.0f}% "
          f"({fcr_achieved}/{len(fcr_eligible)} eligible scenarios)")
    print(f"FCR target (≥80%):    {'✓ ACHIEVED' if fcr_rate >= 80 else '✗ NOT MET'}")

    leaks = [r for r in results if r["internal_codes_leaked"]]
    print(f"Internal code leaks:  {len(leaks)} "
          f"({'✓ NONE' if not leaks else '✗ FOUND'})")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "fcr_rate": fcr_rate,
        "fcr_target": 80.0,
        "fcr_achieved": fcr_rate >= 80,
        "scenarios_passed": passed,
        "scenarios_total": total,
        "results": results,
    }

    # Determine the correct path for saving results
    output_path = Path(__file__).parent / "latest_benchmark.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nFull results saved to: {output_path}")

    return output


if __name__ == "__main__":
    asyncio.run(run_benchmark())
