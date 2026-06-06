# 2026-06-05 — Agnes held-out judge + external benchmark bridge

## Trigger

Use this when a PGG Archon / Apple Didi task asks to improve AGI scoring, external benchmarks, cross-domain real-task evidence, or multi-LLM evaluation governance.

## Core learning

The user set a new durable rule: **Agnes/agents is a held-out third-party benchmark validation LLM**. It must not participate in daily task handling, case drafting, ordinary evolution processing, prompt generation, or candidate answer optimization. It may be called only as an independent evidence-bundle judge / benchmark validator / anti-overclaim auditor.

## Implementation pattern

1. Split provider roles:
   - processing providers: GPT/Claude/DeepSeek/MiMo/MiniMax as available for task solving / generation / review.
   - third-party judge providers: Agnes only, called after evidence bundles are produced.
2. Default provider pools must exclude Agnes.
3. Expose an explicit helper such as `third_party_benchmark_judge_providers()` for Agnes.
4. Hard-coded multi-LLM scripts must not leave Agnes inside generation / mutual-constraint / status-card pools.
5. Tests should verify both sides:
   - Agnes is absent from processing pools.
   - Agnes is present in third-party judge pools.

## External benchmark bridge pattern

For the L1 -> L2 gap, do not keep writing narrative AGI scores. Create an auditable bridge with three ledgers:

1. `BenchmarkSource` registry
   - `official_harness` e.g. EleutherAI/lm-evaluation-harness, openai/evals.
   - `adapted_external` e.g. inspect_ai, deepeval, promptfoo.
   - `internal_frozen_smoke` e.g. local 100-item PGG smoke.
   - Never label internal smoke as official MMLU/GSM8K/BigBench/LegalBench.
2. `CrossDomainTask` registry
   - fields: domain, real_or_synthetic, source_of_truth, input_artifacts, output_artifacts, acceptance_criteria, verifier, status, evidence_paths, human_review_required.
   - no task is PASS without readback/verifier evidence.
3. `EvolutionGainReport`
   - before/after fixed task set.
   - fields: before_status, after_status, before_score, after_score, delta, evidence_path, regression_reason.
   - if regressions exist or evidence is only LLM prose, status must remain WATCH.

## 0006 case lesson

Case `PGG-MS-20260605-0006` can be used as real-world legal landing evidence only at **WATCH** level unless its open gaps are closed. Positive evidence: P0-P7 ledger, FINAL v2, v1 fact-error correction, 15/15 true-fact and 0/8 false-fact self-check records. Open gaps: CMS guard recorded BLOCKED, constructed cases must be replaced by real cases, party details are pending, and the exact grassroots court is pending.

Do not count this case as fully verified or externally file-ready until those gaps are closed.

## Truth boundary

This pattern improves evidence governance and evaluator contamination control. It is **not** an official external benchmark pass, not L2 proof, and not full AGI proof.
