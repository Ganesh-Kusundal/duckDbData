# 4) AI Agent Execution

Principles
- Local execution: agents operate in your environment; no external data egress.
- Planned actions: agents follow the task card; no ad‑hoc edits.
- Safety: no destructive commands; respect sandbox; dry‑run where possible.

Execution Loop (Agentic Reasoning)
1. Plan: restate the task and intended changes.
2. Act: make minimal diffs; run targeted tests.
3. Observe: evaluate results; collect logs/coverage.
4. Reflect: decide next step or rollback.

Traceability
- Every change appears as a code diff for review before commit.

