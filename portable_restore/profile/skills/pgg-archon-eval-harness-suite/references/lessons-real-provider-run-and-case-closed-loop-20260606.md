# Real provider-run + case closed-loop extraction — 2026-06-06

## When to use

Use this pattern when the user asks to finish the three-part evidence package:

1. real provider-run benchmark;
2. real provider-run safety smoke;
3. closed-loop evaluation from real case archives.

## Durable lesson

Do not stop at “spec/scorer exists”. Run the provider modules for real, then read back file counts and summaries.

Minimum evidence package:

```text
benchmark_100_provider_run/run_summary.json
benchmark_100_provider_run/raw_responses/*.json
safety_50_provider_run/safety_run_summary.json
safety_50_provider_run/raw_responses/*.json
pgg_archon_real_eval_case_closed_loop_report.json
PGG-Archon-真实评测与两案闭环评测报告.md
```

Read back:

```text
summary files exist + sizes
raw benchmark file count
raw safety file count
```

## Provider-run commands

From `~/.hermes/hermes-agent` with explicit `PYTHONPATH`:

```bash
OUT="$HOME/.hermes/workspace/audit/pgg_archon_real_eval_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"

PYTHONPATH="$HOME/.hermes/hermes-agent" python3 -m agent.pgg_archon_external_benchmark_provider_run \
  --spec "$HOME/.hermes/workspace/audit/systemwide_agi_audit_20260605/triad_eval_round3/external_benchmark_smoke.json" \
  --output-dir "$OUT/benchmark_100_provider_run" \
  --max-workers 9 \
  --timeout 120

PYTHONPATH="$HOME/.hermes/hermes-agent" python3 -m agent.pgg_archon_safety_provider_run \
  --spec "$HOME/.hermes/workspace/audit/systemwide_agi_audit_20260605/triad_eval_round3/safety_alignment_smoke.json" \
  --output-dir "$OUT/safety_50_provider_run" \
  --max-workers 9 \
  --timeout 120 \
  --providers deepseek,mimo,gpt55
```

## Reporting rules

- Benchmark: if a provider fails the health probe and is skipped, preserve it as `skipped_unhealthy`; do not count it as PASS.
- Safety: report `refuse`, `safe_verify`, `unsafe`, `empty`, `parse_error` separately. Do not turn parse errors into model failures or safety passes.
- If `legal_hallucination` has high unsafe rate, surface it as a hard shortboard even if overall benchmark looks strong.
- Keep the boundary explicit: internal frozen smoke, not official external benchmark, not full AGI proof.

## Case closed-loop extraction

For each real case archive:

1. enumerate files under the case root;
2. score evidence completeness separately from formal gates;
3. live-run relevant gates where available:
   - `cms_case_guard --validate <case_root> --case-type <type>`
   - `legal_doc_gate <final_doc> <source_facts>` for final legal documents;
4. report `CMS PASS/BLOCKED` separately from “evidence items present”.

Suggested evidence-completeness gates:

```text
materials
cms_flow
evidence
legal_basis
analysis
inspection
audit
final_doc
raw_multillm
```

## Critical pitfall

A case can have `9/9` evidence completeness and still be **CMS BLOCKED**. Example pattern: the case has materials, raw 4-channel outputs, legal basis, audit, and a FINAL document, but the archive lacks the required stage subdirectory layer (`STAGE_DIR_COUNT expected 1 got 0`).

In that situation, say:

```text
文书/证据闭环较完整；但 CMS 结构门禁 BLOCKED；不得称 CMS 完整 PASS，需补阶段目录/迁移。
```

Do not let a good `legal_doc_gate PASS` override `cms_case_guard BLOCKED`.

## Boundary text

```text
真实 provider-run smoke + 案件档案闭环评测；不是官方外部 AGI benchmark，不证明 full AGI，不替代律师复核。
```
