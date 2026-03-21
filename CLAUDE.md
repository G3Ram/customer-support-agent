# Customer Support Resolution Agent

## What this project is
A Claude-powered agentic customer support system using the Claude Agent SDK.
Handles returns, billing disputes, and account issues via 4 MCP tools.
Target: ≥80% first-contact resolution (FCR).

## Architecture non-negotiables — enforced in CODE, not just prompts
1. `get_customer` MUST be called before `lookup_order` or `process_refund`
   → Enforced in: `backend/mcp/middleware/prerequisites.py`
2. `process_refund` requires `refund_eligible: True` from `lookup_order`
   → Enforced in: `backend/mcp/middleware/prerequisites.py`
3. Idempotency keys are UUID v4, generated ONCE per refund attempt, REUSED on retry
   → Enforced in: `backend/mcp/middleware/idempotency.py`
4. `OWNERSHIP_MISMATCH` from `lookup_order` → escalate P1 immediately, NEVER retry
5. Internal error codes and the $150 refund limit NEVER appear in user-facing text

## The 4 MCP tools (in required call order)
1. `get_customer`       — READ, no side effects, always first
2. `lookup_order`       — READ, requires customer_id from step 1
3. `process_refund`     — WRITE, irreversible, requires refund_eligible=True from step 2
4. `escalate_to_human`  — ESCALATE, available any time

## Escalation triggers (non-negotiable)
- Customer says: "lawyer", "fraud", "scam", "unacceptable", "sue" → P1
- Refund amount > $150 (LIMIT_EXCEEDED) → P2
- Tool failure after 2 retries → P2
- OWNERSHIP_MISMATCH → P1
- Customer requests human → P1, honor immediately
- 2+ failed clarification rounds → P3

## Code conventions
- Python 3.11+, Pydantic v2 throughout
- All error codes are in `backend/types/models.py` ErrorCode enum — never raw strings
- All tool inputs/outputs are Pydantic models — never plain dicts at the boundary
- Async everywhere in agent/, api/, and mcp/ layers
- Backend stubs live in backend/backends/ — no real API calls, fixture data only
- Tests required before any implementation is considered done

## Commands
- Run tests:      pytest backend/tests/ -v
- Run server:     uvicorn backend.api.main:app --reload
- Type check:     pyright backend/
- Lint:           ruff check backend/

## Current implementation status
<!-- Update this after every session -->
- [ ] backend/types/models.py
- [ ] backend/mcp/middleware/prerequisites.py
- [ ] backend/mcp/middleware/idempotency.py
- [ ] backend/mcp/tools/ (all 4 tools)
- [ ] backend/mcp/server.py
- [ ] backend/prompts/system_prompt.py
- [ ] backend/prompts/few_shot_examples.py
- [ ] backend/backends/ (all 4 stubs)
- [ ] backend/agent/orchestrator.py
- [ ] backend/api/ (FastAPI routes + SSE)
- [ ] backend/tests/unit/ (prerequisites, idempotency)
- [ ] backend/tests/integration/ (3 canonical scenarios)

## Session rules
- Scope every session to ONE directory at a time
- Run tests at the end of every session before stopping
- Update the status checklist above before ending any session
- Never modify prerequisites.py without running its tests immediately after