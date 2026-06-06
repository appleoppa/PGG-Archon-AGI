# Bounded cross-domain process smoke benchmark — 2026-06-03

## When to use

Use when a user asks to continue PGG/Hermes evolution after high readiness scores but the remaining gap is “cross-domain benchmark not run.” This pattern adds a truthful, local process-level smoke test across domains without claiming AGI benchmark results.

## Boundary

This is **not** MMLU, GSM8K, AgentBench, ClawProBench, or a full AGI benchmark. It validates that the local evolution workflow has evidence across multiple process domains:

- legal/governance boundaries
- provider/runtime health
- Rust evolution metrics
- open-source research evidence
- evidence/audit hashes
- formula/score semantics
- ops/runtime supervision

D5/cross-domain applicability can receive only a capped local-process uplift (e.g. 0.45 → 0.60), never a claim of L2/L3/L5 AGI.

## Minimal benchmark checks

A deterministic local script should check:

1. Reports contain explicit no-overclaim boundaries (`no full AGI`, `no 10x`, `no hidden activation`).
2. All required LLM providers have visible output evidence, not just HTTP 200 metadata.
3. Rust APEX evaluate remains healthy (`apex_delta_e`, `lambda_phi`, `evol_code`, etc.).
4. Open-source scout has real README/API evidence; no external code was imported or executed.
5. Input file hashes and evidence index exist.
6. Readiness score has `score_type` that prevents AGI-level misinterpretation.
7. Runtime supervisor/watcher is actually running.

## Output

Persist:

- `artifacts/cross_domain_process_smoke_benchmark.py`
- `artifacts/cross_domain_process_smoke_result.json`
- report section stating `benchmark_type=bounded_cross_domain_process_smoke_not_agi_benchmark`

## GitHub/open-source handling

If GitHub API tree calls hit 403/rate limits, do not fabricate tree evidence. Use already-fetched README/API metadata if available, or label the tree/source detail as blocked. This pattern absorbs benchmark design ideas only; it does not import external benchmark code.

## Scoring discipline

- Passing this smoke test can improve a bounded readiness/process score.
- It cannot remove the remaining truth boundary: “full external AGI benchmark not run.”
- Keep the remaining gap explicit in manifest/report.
