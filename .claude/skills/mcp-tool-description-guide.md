---
name: mcp-tool-description-guide
description: Reference for writing high-quality MCP tool descriptions that guide correct LLM tool selection
user-invocable: false
---
# How to write MCP tool descriptions for this project

Tool descriptions are the PRIMARY mechanism Claude uses for tool selection.
Thin descriptions cause misroutes. This guide defines the standard.

## Required structure
Every tool description must answer 4 questions:
1. What does it do? (one sentence, action + data returned)
2. When should I use it? (trigger signals — user phrases, identifier types, intent)
3. When should I NOT use it? (differentiation from similar tools)
4. What are the preconditions? (what must be true before calling)

## The differentiation boundary (most important)
The "DO NOT use for" section prevents misroutes between similar tools.
get_customer vs lookup_order are the highest-confusion pair:
- get_customer: account-level data (tier, status, billing history, open cases)
- lookup_order: order-level data (status, items, refund eligibility, shipping)

If a user says "check my order #12345" → lookup_order (not get_customer)
If a user says "what's my account status" → get_customer (not lookup_order)

## Error handling in descriptions
For each tool, state what to do on its most dangerous error:
- lookup_order: "On OWNERSHIP_MISMATCH: escalate P1 immediately, do not retry"
- process_refund: "On DUPLICATE: surface existing refund_id, do not reprocess"
- process_refund: "On LIMIT_EXCEEDED: escalate P2, do not reveal the $150 limit"
```

---

## How these files work together — the flow for a typical session
```
You open Claude Code
    ↓
CLAUDE.md auto-loads → Claude knows architecture rules, current status, conventions
    ↓
You type: "Implement backend/mcp/middleware/prerequisites.py"
    ↓
Claude reads CLAUDE.md constraints, implements the file
    ↓
PostToolUse hook fires after each file edit → runs pyright, surfaces type errors immediately
    ↓
Claude self-corrects type errors without you asking
    ↓
You type: "/run-scenario refund"
    ↓
.claude/commands/run-scenario.md executes → checks for test file, runs it, reports results
    ↓
You type: "Use the security-reviewer subagent to audit the middleware"
    ↓
.claude/agents/security-reviewer.md runs in isolated context → reports findings
    ↓
At 70% context: you type "/context-dump"
    ↓
.claude/commands/context-dump.md reads all implementation files, updates CLAUDE.md checklist
    ↓
You run /compact → Claude summarizes with full status preserved in CLAUDE.md