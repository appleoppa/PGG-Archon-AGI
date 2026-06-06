# Lessons — Outline1 AGI scoring + final 33-card ACTIVE closure (2026-06-04)

## Trigger

Use when the user asks to compare current PGG Archon / Apple Didi AGI progress against `总纲1-通用人工智能AGI框架.md`, especially with requested real multi-LLM scoring.

## Reusable workflow

1. Read `总纲1-通用人工智能AGI框架.md` from Desktop/Documents and extract the scoring scale:
   - L0 0–30
   - L1 31–50
   - L2 51–70
   - L3 71–85
   - L4 86–94
   - L5 95–100
   - Weights: 基础认知25 / 跨域通用22 / 自主智能体20 / 自主知识进化13 / 安全对齐12 / 现实落地8.
2. Read current evidence, not memory-only claims:
   - `~/.hermes/data/EVOLUTION_MANIFEST.json`
   - latest final report under `~/.hermes/workspace/audit/`
   - 33-card verifier facts, e.g. `verifier_friendly_facts_33_synced.json`.
3. Build a compact scoring prompt that explicitly says:
   - status surface 33/33 ACTIVE is engineering evidence, not AGI ability;
   - smoke benchmark/redteam is not official benchmark;
   - Claude may be excluded by user instruction;
   - output must be STRICT JSON with six dimensions.
4. Call requested LLMs independently. If one channel returns HTTP 200 but non-JSON visible output, record `http_status`, `visible_output_chars`, raw preview, and classify as `ERROR` / `unstructured`, not as a valid numeric score.
5. Aggregate only parsed structured scores. Do not invent a score from an unparseable model response unless the numeric score is explicitly visible and separately quoted with caveat.
6. Write a verifier-friendly report under `~/.hermes/workspace/audit/p3_outline1_score_<date>/` with:
   - valid_scores
   - invalid_or_unstructured_scores
   - objective_summary
   - boundary.

## Durable findings from this session

- DeepSeek produced valid STRICT JSON for Outline1 scoring: 34/100, L1.
- MiniMax-M3 returned HTTP 200 with visible long output twice but included `<think>` / explanatory text and failed JSON parse twice. Treat this as true participation but not a structured score.
- The objective interpretation: current PGG Archon is L1 cross-domain weak generality by evidence, not L2. 33/33 ACTIVE proves status-surface engineering closure, not full AGI.

## se_sync final closure pitfall

When 33-card verifier reports remaining SKELETON/ABSENT despite real surfaces existing, inspect id shapes. In this session, source card ids mixed:

- integers, e.g. `17`, `22`, `4`, `8`
- strings with prefix, e.g. `file_1`
- strings like `0.5`, `2.5`

`se_sync` must normalize via `str(raw_id)` and strip `file_` before matching PATCHES. Exact string matching can leave false SKELETON/ABSENT and hide real 33/33 ACTIVE closure.

## Boundary language

Recommended output wording:

> 33-card status surface full ACTIVE is not full AGI. It is engineering/status evidence. For 总纲1 scoring, count it under tool orchestration, autonomous-agent engineering, and governance maturity, but require real benchmark/safety/cross-domain evidence before L2.
