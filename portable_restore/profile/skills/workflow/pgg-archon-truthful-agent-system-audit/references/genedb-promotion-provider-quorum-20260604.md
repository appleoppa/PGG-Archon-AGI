# GeneDB Promotion Gate + Provider Quorum Pattern — 2026-06-04

## Trigger

Use when PGG Archon / Hermes evolution work reaches GeneDB candidate review, promotion gates, LLM quorum evidence, or lifecycle cleanup of duplicate/low-score candidates.

## Durable lessons

1. Candidate exists ≠ promoted. `gene_lifecycle.state='candidate'` and `promoted_at=null` must stay candidate-only until a separate audited transaction runs.
2. All-candidate audit is different from single-gene promotion. First classify every candidate with blockers, then promote exactly one candidate per transaction.
3. LLM quorum must classify the model-level verdict, not nested candidate decisions. If model output is JSON with top-level `model_verdict: PASS` but `candidate_decisions[].decision: BLOCKED`, the quorum classifier should count the top-level verdict only.
4. Reasoning models can return HTTP 200 with `reasoning_content` but empty `content` when token budget is too small. Increase `max_tokens` and require visible final `content`; do not count reasoning-only output as visible PASS.
5. Provider repair is part of the promotion gate when quorum is blocked by transport/config issues. Re-test with real HTTP calls and record HTTP status, visible chars, raw hash, verdict, and error for failed channels.
6. User authorization for a high-risk candidate should remove only the explicit authorization blocker. It must not remove unrelated blockers such as unresolved safety holds, low score, duplicate/stale state, or missing quorum.
7. Promotion transaction must be single-gene, backed up, conditional, and read back: update exactly one lifecycle row, insert one `promotion_chain` row, verify state/timestamp/chain, and store artifact hashes.
8. Duplicate/low-score/safety-hold leftovers should be retired/archived via lifecycle metadata transactions, not deleted or silently ignored.

## Recommended ladder

1. Read DB state distribution and candidate rows.
2. Run all-candidate read-only gate with LLM quorum evidence.
3. If providers fail, repair provider config/call shape and rerun evidence; failed channels remain `ERROR` or `SKIPPED`, never hidden PASS.
4. Recompute quorum using saved evidence and a top-level verdict parser.
5. For each ready candidate, run a per-gene quorum pack. Require at least two visible PASS outputs for that gene.
6. Run dry-run promotion transaction.
7. Run real promotion transaction for exactly one gene.
8. Read back `gene_lifecycle` and `promotion_chain`.
9. Repeat per candidate only if each candidate has separate quorum evidence.
10. For remaining blocked candidates, use bounded lifecycle cleanup transaction (`retired`/`archived`) with reason and evidence; never delete.

## Provider notes from this session

- DeepSeek-V4-Flash: use `max_tokens >= 4096` for nontrivial reasoning audits; extract final `choices[0].message.content`; `reasoning_content` alone is diagnostic but not visible PASS.
- MiMo v2.5 Pro in this setup: working endpoint was `https://token-plan-cn.xiaomimimo.com/v1`; the official `https://api.xiaomimimo.com/v1` returned 401 for the available key.
- Agnes in this setup: working endpoint was `https://apihub.agnes-ai.com/v1` with model `agnes-2.0-flash`.
- Claude was intentionally not repaired when the user said so; record as `skipped_by_user_request` or actual HTTP error, not as quorum pass.

## Evidence fields to preserve

- provider label/name/model/api_mode/key_env name only
- HTTP status
- visible output chars
- reasoning chars if present
- raw response sha256
- classified model verdict
- parsed top-level JSON verdict
- evidence file path
- DB backup path
- DB sha256 after transaction
- lifecycle before/after rows
- promotion_chain row and decision hash

## Boundaries

This pattern proves bounded GeneDB lifecycle governance only. It does not prove full AGI, external AGI benchmark performance, legal correctness, or safe unsupervised production takeover.
