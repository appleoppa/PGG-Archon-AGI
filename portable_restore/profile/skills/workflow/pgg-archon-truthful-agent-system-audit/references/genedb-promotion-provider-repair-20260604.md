# GeneDB Promotion Gate Provider Repair Pattern — 2026-06-04

## When to use

Use when GeneDB candidate promotion is blocked by provider evidence, LLM quorum, or candidate audit gates.

## Durable lessons

1. Candidate exists is not promotion. `gene_lifecycle.state='candidate'` and `promoted_at=null` require a separate promotion gate and transaction.
2. Call every configured provider separately. Active chat model does not count as independent audit evidence.
3. Respect explicit user scope: if the user says Claude is temporarily not to be repaired, mark it `skipped_by_user_request` and do not count it as PASS.
4. Reasoning models need enough visible-output budget. For DeepSeek-V4-Flash and MiMo-v2.5-Pro, use `max_tokens>=4096` for real audits and record both visible `content` length and `reasoning_content` length. Reasoning-only text is diagnostic evidence, not visible PASS.
5. MiMo with the user's current audit key works via `https://token-plan-cn.xiaomimimo.com/v1`; the generic `https://api.xiaomimimo.com/v1` may return 401 with the same key.
6. Agnes works via `https://apihub.agnes-ai.com/v1` with model `agnes-2.0-flash`.
7. LLM quorum classifiers must parse top-level `model_verdict` + `feasibility_ok`. Do not let nested candidate-level `"decision":"BLOCKED"` inside `candidate_decisions` override a top-level `model_verdict: PASS`.
8. If quorum passes after provider/config/classifier repair, promote at most one candidate per transaction: dry-run first, then backup DB, update exactly one lifecycle row, insert one `promotion_chain` row, read back DB state, and update manifest with artifact hashes.

## Verification checklist

- Provider smoke: HTTP status, visible output chars, reasoning chars where applicable.
- Quorum gate: `visible_pass_count >= required_pass_count`.
- Candidate gate: all-candidate read-only audit returns review-ready candidates.
- Transaction dry-run: `DRY_RUN_READY` before mutation.
- Real transaction: `PROMOTED_VERIFIED`, DB state readback, promotion_chain row readback.
- Manifest readback: artifact paths and sha256 recorded.

## Boundaries

A GeneDB lifecycle promotion proves exactly one bounded candidate passed the local promotion transaction. It does not prove full AGI, external AGI benchmark success, legal correctness, or production takeover safety.
