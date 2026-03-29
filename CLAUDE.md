# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Customer Support Resolution Agent

## What this project is
A Claude-powered agentic customer support system using the Claude Agent SDK.
Handles returns, billing disputes, and account issues via 4 MCP tools.
Target: ≥80% first-contact resolution (FCR).

## Request lifecycle (3-layer architecture)
1. **API layer** (`backend/api/`) — FastAPI receives chat requests, streams SSE responses
2. **Agent layer** (`backend/agent/`) — Orchestrator manages conversation state, calls Claude API with MCP tools
3. **MCP layer** (`backend/mcp/`) — MCP server exposes tools, middleware enforces prerequisites/idempotency
4. **Backend layer** (`backend/backends/`) — Stub implementations return fixture data (no real API calls)

## Architecture non-negotiables — enforced in CODE, not just prompts

**Middleware pattern**: All MCP tool calls pass through middleware decorators that enforce these rules BEFORE the tool executes.

1. `get_customer` MUST be called before `lookup_order` or `process_refund`
   → Enforced in: `backend/mcp/middleware/prerequisites.py` (tracks tool call sequence in session state)
2. `process_refund` requires `refund_eligible: True` from `lookup_order`
   → Enforced in: `backend/mcp/middleware/prerequisites.py` (validates previous tool outputs)
3. Idempotency keys are UUID v4, generated ONCE per refund attempt, REUSED on retry
   → Enforced in: `backend/mcp/middleware/idempotency.py` (stores key in session, regenerates on new order)
4. `OWNERSHIP_MISMATCH` from `lookup_order` → escalate P1 immediately, NEVER retry
   → This is a prompt-level rule (no middleware enforcement)
5. Internal error codes and the $150 refund limit NEVER appear in user-facing text
   → Enforced in prompts + agent response validation

## The 4 MCP tools (in required call order)
1. `get_customer`       — READ, no side effects, always first
2. `lookup_order`       — READ, requires customer_id from step 1
3. `process_refund`     — WRITE, irreversible, requires refund_eligible=True from step 2
4. `escalate_to_human`  — ESCALATE, available any time

MCP tools are defined in `backend/mcp/tools/` and exposed via `backend/mcp/server.py`. The MCP server runs as part of the agent orchestrator, not as a separate process.

## Agent & prompts architecture
- `backend/agent/orchestrator.py` — Main agent loop, manages Claude API calls with MCP tool integration
- `backend/agent/session.py` — Tracks conversation history, tool call state, idempotency keys
- `backend/agent/classifier.py` — Pre-processes user input to detect escalation triggers before agent responds
- `backend/prompts/system_prompt.py` — Core system prompt defining agent behavior, tool usage patterns
- `backend/prompts/few_shot_examples.py` — Example conversations demonstrating correct tool sequencing

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

## Backend stubs pattern
The `backend/backends/` directory contains stub implementations that return fixture data:
- `crm.py` — get_customer_by_email() returns mock customer records
- `orders.py` — get_order_by_id() returns mock order data with refund eligibility
- `payments.py` — process_refund_internal() simulates refund processing (always succeeds)
- `tickets.py` — create_escalation_ticket() simulates ticket creation

These stubs allow end-to-end testing without external dependencies. In production, these would be replaced with real API clients.

## Test structure
- **Unit tests** (`backend/tests/unit/`) — Test middleware in isolation (prerequisites, idempotency, error handlers)
- **Integration tests** (`backend/tests/integration/`) — Test multi-tool workflows (refund flow, escalation, cross-account scenarios)
- **Evaluation tests** (`backend/tests/evals/`) — Measure FCR rate against benchmark scenarios

## Setup & dependencies
```bash
# Install dependencies (from backend/ directory)
pip install -e .

# Or using uv (faster)
uv pip install -e .

# Key dependencies:
# - anthropic>=0.40.0 — Claude API SDK
# - fastapi>=0.115.0 — API framework
# - mcp>=1.0.0 — Model Context Protocol SDK
# - pydantic>=2.0 — Data validation
# - python-ulid — Sortable UUIDs for idempotency
```

## Commands
```bash
# Run all tests with verbose output
pytest backend/tests/ -v

# Run specific test types
pytest backend/tests/unit/ -v              # Unit tests (middleware, error handlers)
pytest backend/tests/integration/ -v       # Integration tests (multi-tool flows)
pytest backend/tests/evals/ -v             # Evaluation benchmarks (FCR metrics)

# Run a single test file
pytest backend/tests/unit/test_prerequisites.py -v

# Run a single test function
pytest backend/tests/unit/test_prerequisites.py::test_lookup_order_requires_get_customer -v

# Run server (FastAPI with hot reload)
uvicorn backend.api.main:app --reload --port 8000

# Type check
pyright backend/

# Lint
ruff check backend/

# Format code
ruff format backend/
```

## Current implementation status
<!-- Updated: 2026-03-29 -->
- [x] backend/types/models.py — COMPLETE (271 lines), all enums and Pydantic models defined
- [x] backend/mcp/middleware/prerequisites.py — COMPLETE (88 lines), 14/14 unit tests passing
- [x] backend/mcp/middleware/idempotency.py — COMPLETE (40 lines), 7/7 unit tests passing
- [x] backend/backends/ (all 4 stubs) — COMPLETE (crm:51, orders:66, payments:66, tickets:56), verified with fixtures
- [x] backend/mcp/tools/ (all 4 tools) — COMPLETE (get_customer:102, lookup_order:90, process_refund:129, escalate_to_human:97), all tools use middleware correctly
- [x] backend/mcp/server.py — COMPLETE (35 lines), FastMCP instance created, all 4 tools registered and verified, import path fixed
- [x] backend/prompts/system_prompt.py — COMPLETE (134 lines), 6 sections with env var interpolation, verified
- [x] backend/prompts/few_shot_examples.py — COMPLETE (40 lines), 3 examples covering auto-resolve and escalation patterns
- [x] backend/agent/orchestrator.py — COMPLETE (287 lines), fully wired to prerequisites/idempotency/session_storage, tool schema generation verified
- [ ] backend/agent/session.py — NOT STARTED (0 lines)
- [ ] backend/agent/classifier.py — NOT STARTED (0 lines)
- [ ] backend/api/main.py — NOT STARTED (0 lines)
- [ ] backend/api/schemas.py — NOT STARTED (0 lines)
- [x] backend/tests/unit/ — COMPLETE, 21/21 tests passing (prerequisites:14, idempotency:7)
- [ ] backend/tests/unit/test_error_handlers.py — NOT STARTED (0 lines)
- [ ] backend/tests/integration/ (3 canonical scenarios) — NOT STARTED (0 lines each)
- [ ] backend/tests/evals/ (FCR benchmarks) — NOT STARTED (0 lines)

## Working in this codebase

**Session rules**:
- Scope work to ONE directory at a time (e.g., complete `backend/mcp/tools/` before moving to `agent/`)
- Run relevant tests after any implementation (pytest <path> -v)
- Update the "Current implementation status" checklist before ending sessions
- NEVER modify `prerequisites.py` or `idempotency.py` without running their unit tests immediately

**Implementation order** (recommended):
1. Start with `backend/types/models.py` (defines all Pydantic models and ErrorCode enum)
2. Then `backend/backends/` (stubs return fixture data based on models)
3. Then `backend/mcp/middleware/` (enforce prerequisites and idempotency)
4. Then `backend/mcp/tools/` (use middleware, call backend stubs)
5. Then `backend/mcp/server.py` (expose tools via MCP)
6. Then `backend/prompts/` (define system prompt and few-shot examples)
7. Then `backend/agent/` (orchestrator integrates everything)
8. Finally `backend/api/` (FastAPI routes expose agent via REST/SSE)

**Key principles**:
- Middleware returns detailed error responses when prerequisites fail (don't just raise exceptions)
- Session state tracks: conversation history, tool call sequence, idempotency keys, customer_id
- Idempotency keys persist for the same order_id, regenerate when switching orders
- Escalation triggers must be detected BEFORE the agent responds (use classifier.py)