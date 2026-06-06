# Source scout + evol_events refresh pattern

Use when Rust APEX ΔE shows real gaps in `lambda_phi` or `evol_code`.

## Signal

`apex13 eval --workspace ~/.hermes/workspace --output <json>` reports:

- `lambda_phi < 1.0`: `workspace/evolution/super_evolution13/source_scout.json` is missing or stale.
- `evol_code < 1.0`: `workspace/evolution/super_evolution13/evol_events.jsonl` is missing or has fewer than 10 real event lines.

## Truthful repair pattern

1. Do **not** hand-edit scores.
2. Build real evidence first:
   - query GitHub/API/arXiv/other open sources read-only;
   - fetch bounded README/API metadata where relevant;
   - store raw scout evidence under a workspace evidence directory.
3. Rewrite or refresh `~/.hermes/workspace/evolution/super_evolution13/source_scout.json` with the actual scout evidence, timestamp, queries, source URLs, and a truth boundary such as: “read-only scout; no external code imported or executed”.
4. Append `~/.hermes/workspace/evolution/super_evolution13/evol_events.jsonl` only with real events that occurred in the session. Each line should include timestamp, event_id, description, evidence_root, and a boundary note. Do not create synthetic “activity” events.
5. Re-run:
   - `apex13 eval --workspace /Users/appleoppa/.hermes/workspace --output <json>`
   - background cycle if status.json should reflect the new eval;
   - `python -m apex_god.middleware.convergence_bridge --cycle`
   - `python -m apex_god.health`
6. Report the before/after component scores and preserve remaining gaps.

## Pitfalls

- This pattern is legitimate only when the scout file and event log contain real evidence. Empty/touch-only updates are score gaming.
- GitHub scout is reference learning, not code absorption. Do not claim external repo code was imported, run, or verified unless that actually happened.
- If an LLM provider returns HTTP 200 but no visible text, record that separately and do not count it as substantive model advice.
