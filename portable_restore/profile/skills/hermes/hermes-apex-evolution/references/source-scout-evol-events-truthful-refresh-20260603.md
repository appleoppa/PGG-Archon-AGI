# Truthful source_scout + evol_events refresh — 2026-06-03

## Use case

Rust `hermes_apex_evolution` evaluates:

- `lambda_phi` from freshness of `~/.hermes/workspace/evolution/super_evolution13/source_scout.json`
- `evol_code` from line activity in `~/.hermes/workspace/evolution/super_evolution13/evol_events.jsonl`

When those are low/stale, do not write empty files or synthetic lines just to raise scores. Refresh them only with real research/evolution events backed by evidence.

## Real source_scout pattern

1. Query authoritative/read-only sources (GitHub API, README snapshots, arXiv via `py_scout`, or other public docs).
2. Store raw evidence paths under the task workspace.
3. Write `source_scout.json` with:
   - `generated_at`
   - source/query list
   - repository/doc metadata
   - README/API evidence paths/hashes
   - absorbed patterns
   - blocked items
   - truth boundary (“read-only scout; no code imported/executed”)
4. If GitHub API rate-limits, record the blocker and do not fabricate tree/source evidence.

## Real evol_events pattern

Append JSONL events only for actual tool-backed steps, e.g.:

- file corpus indexed with SHA256
- LLM call completed with visible output or correctly downgraded
- GitHub scout search completed
- README evidence fetched
- health/convergence/Rust evaluate verified
- provider compatibility fix verified
- benchmark smoke passed

Each event should include:

```json
{
  "timestamp": "...",
  "event_id": "stable_unique_id",
  "description": "actual event",
  "evidence_root": "...",
  "truth_boundary": "real event ledger entry; no capability claim by itself"
}
```

## Verification

After refresh:

```bash
apex13 eval --workspace ~/.hermes/workspace --output <json>
python -m apex_god.middleware.convergence_bridge --cycle
python -m apex_god.health
```

Report both the improved scores and the evidence paths. Do not claim AGI capability from these metrics alone.
