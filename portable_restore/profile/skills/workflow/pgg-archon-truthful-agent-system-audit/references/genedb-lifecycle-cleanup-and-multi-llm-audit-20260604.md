# GeneDB Lifecycle Cleanup + Multi-LLM System Audit Pattern — 2026-06-04

## Trigger

Use this reference when PGG Archon / Hermes work enters any of:

- A GeneDB candidate audit needs to graduate from "all-candidate read-only gate" to actual lifecycle mutation.
- The remaining GeneDB pool mixes promotable rows, duplicate/stale rows, low-score rows, and rows with unresolved safety holds; you must decide the action for each.
- A user asks for a "全面审计本系统的所有/模块/配置/技能/cron/后台" style review and wants every configured LLM channel tried honestly (not role-played).

## Durable lessons

### 1. GeneDB lifecycle is not only promotion

The bounded promotion transaction (`agent/pgg_archon_gene_promotion_transaction.py`) handles candidate → promoted with backup/readback. It does NOT retire, archive, or downgrade. When the audit reveals duplicates, low-score, or safety-hold candidates that should leave `state='candidate'`, you need a separate bounded lifecycle transition.

Pattern: `agent/pgg_archon_gene_lifecycle_transaction.py`

- `to_state ∈ {"retired", "archived"}` only (no deletion).
- Single-gene update guarded by `from_state` predicate.
- One DB backup, one `promotion_chain` row, one readback check.
- `idempotent`: already-in-target-state returns `ALREADY_IN_TARGET_STATE_VERIFIED` without a duplicate chain row.
- `--dry-run` produces a real backup + decision sha256, no mutation.

Audit-action mapping (from real multi-LLM verdicts, 2026-06-04):

| Gate blocker | Lifecycle action |
|---|---|
| `duplicate_candidate_group` | `retired` (or `archived` if you want to keep a non-promoted trail) |
| `phase3_ars_cycle_candidate_requires_duplicate_staleness_review` | `retired` |
| `quality_score_below_threshold` (no fresh DB rescore) | `retired` |
| `candidate_contains_unresolved_safety_hold` | `retired` |
| `core_takeover_requires_explicit_human_authorization` (only) | keep in `candidate` until human auth token supplied |

### 2. Human authorization token — narrow and auditable

The all-candidate gate exposes `--human-authorization-token STRING`. The token:

- Only removes the specific blocker `core_takeover_requires_explicit_human_authorization`.
- Does NOT bypass `candidate_contains_unresolved_safety_hold`, `quality_score_below_threshold`, or `duplicate_candidate_group`.
- Result field `human_authorization_token_present: bool` is part of the audit JSON, so the absence of a token is itself an evidence record.

Use it only for the explicitly authorized row(s). Always log the token's user authorization event in the manifest external ledger.

### 3. Per-gene LLM quorum when the global pack is too coarse

The all-candidate gate's quorum is global. If a decision is needed for one specific gene, a single shared evidence pack can be misread by models (the model picks the "best representative" gene and reclassifies siblings as duplicates). For per-gene audit:

- Build a per-gene evidence pack containing only that gene's row + the cross-row conflict map.
- Run a separate quorum gate (`evaluate_llm_quorum_gate` with per-gene evidence files).
- Required pass count is still `>= 2`, but counts come from per-gene LLM verdicts.

A successful per-gene quorum is the legitimate input to a `promote_gene_transaction` call with `trigger_phase=..._per_gene_quorum`. The transaction itself does NOT re-run the LLM gate — it only validates the saved summary JSON.

### 4. Multi-LLM system audit pattern (audit the system, not just the gene pool)

For a "全面审计" request:

1. Build a compact **state card** JSON (≤20 KB) before any LLM call. Include: processes, launchd jobs, listening ports, custom_providers, profile skill counts + memory hash, cron jobs, rust fused-watcher PID/cmdline, git HEAD, rust `.so` list, evolution manifest headline, gene DB state, env key presence (presence only, no secrets), home pollution, AGENTS.md/SOUL.md/USER.md presence, desktop file list.
2. Hand the state card + both user outline files to each configured LLM as a single prompt that demands STRICT JSON output (no markdown fence).
3. Disclose channel reality in the report: HTTP 502 / 403 / 500 / empty visible output → that model is "ERROR" or "MISSING", never silently mapped to PASS.
4. Aggregate model scores with median (not mean) when the visible-model count is small and one model dominates.
5. Cross-check each model's module-level claim against the actual state card. Models will sometimes claim "absent" for things the state card shows as "present" (skill count, rust `.so`, etc.) — keep the disagreement, do not average it away.

Pitfall (real, hit on 2026-06-04): the `pgg_archon_llm_quorum_gate` classifier was matching `"BLOCKED"` anywhere in the model output. A response of `{"model_verdict":"PASS","feasibility_ok":true,"candidate_decisions":[{"gene_id":112,"decision":"BLOCKED"}]}` was misclassified as BLOCKED. Fix:

- In `_classify_from_text`, first try `json.loads` of the response.
- If a top-level dict parses, classify from `model_verdict` and `feasibility_ok`, not from nested `candidate_decisions`.
- In `_normalize_evidence`, reparse `text_preview` and prefer the reparsed verdict over the saved `classified_verdict` when the reparsed verdict is not UNKNOWN.

This classifier now lives in `agent/pgg_archon_llm_quorum_gate.py`. Same trap exists in any ad-hoc "classify verdict" script — write it once and test it against a fixture that contains a nested BLOCKED inside a top-level PASS.

### 5. Audit scoring boundary

Multi-LLM audit scores are NOT a real L0–L5 AGI grade. They reflect the visible models' interpretation of the state card. To honestly map scores:

- 0–30: L0
- 31–50: L1
- 51–70: L2
- 71–85: L3
- 86–94: L4
- 95–100: L5

But the audit can only say "models place us near L1–L2 boundary given the evidence", never "this system has reached L1". A real L-grade requires external benchmark runs (MMLU/GSM8K/BigBench/red-team) which this audit did not perform.

### 6. Output discipline for audit reports

- Land reports under `~/.hermes/workspace/audit/` (not Desktop, not repo root).
- Provide both `.json` and `.md` versions; `.md` for human reading, `.json` for tool readback.
- Always include `report_sha256` in the manifest external ledger.
- Never claim a model "passed" when its only output was a 4xx/5xx error or an empty visible output.

## Verified evidence (2026-06-04)

- gene 114 promoted: real DB readback, `promotion_chain` row id=3.
- gene 112/111/109/106/104/100 promoted: per-gene quorum + per-gene transaction, chain rows id=4–9.
- gene 99/98/97/96/169/343/344/345 retired: non-delete lifecycle transition, chain rows id=10–17.
- DB final: `active=1, promoted=8, retired=8, candidate=0`, `promotion_chain_count=17`.
- Multi-LLM audit: 4 visible models, median score 62, range 55–68, channel reality preserved (GPT 502, Claude 403 not mapped to PASS).

## Common pitfalls

- Do not let one model's "best representative" pick override the deterministic duplicate detector. The detector catches `name+pattern_type` exact match; the model can still mark one row as "representative" — record the disagreement, let the user decide.
- Do not retire a `state='active'` row through the bounded cleanup transaction. Only `candidate`, `promoted`, or already-`active` rows with the same from_state predicate can transition. Trying to retire a `state='archived'` row will fail loudly — do not "fix" by silently relaxing the predicate.
- Do not skip the `promotion_chain` row insert in cleanup transactions. The audit chain is the only way to prove why a row changed state; without it, future audits cannot tell cleanup from accidental overwrite.
- Do not record the human authorization token value in the audit JSON. Record only its presence and the user that supplied it.
- Do not include user authorization tokens in any commit, manifest field, or log line — they are credentials in context, not evidence.
