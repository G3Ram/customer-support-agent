---
description: Summarize current state before compacting or ending a session
---
Read the following files and produce a status report:

1. backend/mcp/middleware/prerequisites.py — does it exist? are tests passing?
2. backend/mcp/middleware/idempotency.py — same
3. backend/mcp/tools/ — which of the 4 tools are implemented vs stub?
4. backend/agent/orchestrator.py — implemented? wired to prerequisites?
5. backend/tests/ — how many tests exist, how many pass?

Then:
- Update the status checklist in CLAUDE.md to reflect current reality
- List any assumptions made in this session that I should review
- Output a 5-bullet summary: done / in-progress / blocked / next step / risks