---
description: Verify the programmatic enforcement layer is working correctly
---
Run a quick verification that the prerequisites enforcement is solid:

1. Run: pytest backend/tests/unit/test_prerequisites.py -v
2. Run: pytest backend/tests/unit/test_idempotency.py -v
3. Write and run a quick inline test:
   python -c "
   from backend.mcp.middleware.prerequisites import check_prerequisites, PrerequisiteError
   from backend.types.models import ToolName, SessionState
   s = SessionState()
   try:
       check_prerequisites(ToolName.PROCESS_REFUND, s)
       print('FAIL: should have raised PrerequisiteError')
   except PrerequisiteError as e:
       print(f'PASS: {e}')
   "

Report: all passing / any failures with details.
This must pass before any session that touches the orchestrator.