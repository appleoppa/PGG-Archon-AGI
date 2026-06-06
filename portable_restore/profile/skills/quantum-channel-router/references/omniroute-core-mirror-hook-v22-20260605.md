# OmniRoute core mirror-only hook v2.2 — 2026-06-05

## Purpose

Add a low-risk mirror-only hook around `AIAgent.run_conversation()` without changing the Hermes answer path.

## Implementation

- `run_agent.py` forwarder now calls original `agent.conversation_loop.run_conversation(...)` first.
- It then checks `~/.hermes/data/omniroute_auto_evidence_bridge.json`.
- If `enabled=true`, it calls `record_omniroute_core_mirror(...)`.
- The hook is wrapped in `try/except` and always returns the original result unchanged.

## Mirror ledger

File:

```text
~/.hermes/data/omniroute_core_mirror_events.jsonl
```

Schema:

```text
PGGArchonOmniRouteCoreMirror/v1
```

Recorded fields:

- task_id
- session_id
- provider
- model
- platform
- user_sha256 + user_preview
- final_response_sha256 + final_response_preview
- completed
- api_calls
- result_keys
- boundary

## Verification observed

- Direct smoke recorded `mirror_smoke_task`.
- A real core conversation was mirrored:
  - session `20260606_011707_eedfd1`
  - provider `custom`
  - model `gpt-5.5`
  - completed `true`
  - final preview `FINAL_ANSWER: $460`
- WebUI `Core mirror evidence` panel displayed recent mirror events.

## Boundary

Mirror-only means:

- no route enforcement
- no provider substitution
- no extra model call
- no answer mutation
- fail-open if recording fails

Next stage, if authorized, is route-suggest mode, not enforce mode.
