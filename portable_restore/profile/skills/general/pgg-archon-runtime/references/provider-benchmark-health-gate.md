# Provider benchmark / health gate lessons

Session-derived reusable pattern for PGG Archon evolution work.

## Trigger

Use when verifying or integrating configured LLM providers into PGG Archon / AGI evolution loops, especially when the task involves provider routing, benchmark scoring, or health status.

## Durable workflow

1. Do not stop at raw API connectivity. After a provider returns HTTP 200, connect it to the existing PGG benchmark path when low-risk:
   - provider call
   - deterministic benchmark tasks
   - PGG integrated scoring
   - Rust status / Rust ECC / Delta-G / APEX evidence
   - ranking
   - evolution queue
   - provider health gate
2. Preserve raw provider evidence without printing secrets:
   - HTTP status
   - returned model
   - usage/token fields
   - finish reason
   - response preview
   - prediction preview
   - error text for failed transport
3. Separate failure classes:
   - transport failure: HTTP error, gateway failure, missing key, empty output, provider timeout
   - capability failure: provider responded normally but failed deterministic task scoring
4. Health gate routing pattern:
   - first HEALTHY provider = primary candidate
   - other HEALTHY providers = healthy fallback candidates
   - degraded providers = fallback/specialized candidates
   - transport-down providers = blocked until recovered
5. For chat_completions providers, accept both base_url and full endpoint:
   - if URL ends with `/chat/completions`, use it as-is
   - otherwise append `/chat/completions`
6. For reasoning-style providers, score deterministic outputs after stripping harmless reasoning wrappers, while preserving raw prediction evidence.

## MiniMax-M3 specific notes

- Config shape observed in default profile:
  - provider id: `minimax_m3`
  - model: `MiniMax-M3`
  - api_mode: `chat_completions`
  - base_url: `https://api.minimax.chat/v1`
  - key_env: `MINIMAX_API_KEY`
- MiniMax-M3 may return `<think>...</think>` before the final answer.
- Deterministic scorers should ignore `<think>` blocks for exact/contains/JSON scoring, but evidence should retain the raw prediction.
- MiniMax-M3 connectivity is not enough; verify it inside the PGG provider benchmark and health gate.

## User workflow preference embedded

For PGG Archon / AGI evolution tasks, do not stop after writing “next step should be…”. If the next step has >75% necessity, is low-risk, and is rollback-friendly, continue through tests, real smoke, audit where appropriate, commit, ledger/manifest update, and readback.

Always pre-announce approximate duration before tool calls, but then act immediately.

## Boundary language

Provider benchmark and health gate evidence is internal engineering verification. It is not an external benchmark, not full AGI proof, and not legal correctness proof.
