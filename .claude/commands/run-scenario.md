---
description: Run one of the 3 canonical test scenarios end-to-end
---
Run the integration test for scenario: $ARGUMENTS

Valid values: refund | billing | escalate

Steps:
1. Check if backend/tests/integration/test_$ARGUMENTS_flow.py exists
2. If not, use the test-writer subagent to create it using the scenario definitions in CLAUDE.md
3. Run: pytest backend/tests/integration/test_$ARGUMENTS_flow.py -v --tb=short
4. Show the full tool call sequence that was executed
5. Report pass/fail and any assertion errors

If ANTHROPIC_API_KEY is not set, stop and tell me before running.