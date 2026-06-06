---
name: session-logs
description: 搜索和分析历史会话日志
metadata: {"openclaw":{"emoji":"📜","requires":{"bins":["jq","rg"]}}}
---

# Session Logs — Compact

## Trigger

Use when the user asks what happened before, where a past task left off, or to search/analyze historical sessions.

## Workflow

1. Use session_search discovery before asking user to repeat.
2. Scroll only around relevant anchors.
3. Extract goal, decisions, evidence and final state.
4. Do not treat old state as current without verifying live files/config.

## Stuck-dialog / handoff pattern

When the user says another conversation/dialog is stuck, crashed, or lost context:

1. Search recent sessions by the product/task name plus the user's reported error text or last instruction.
2. Scroll around the most recent matching user correction, not just the earliest hit.
3. Identify the last actionable instruction, unresolved error, and any completed fixes from the prior dialog.
4. Verify current live state before reporting continuity: running processes/ports, key directories, config files, recent logs/reports, and browser/UI reachability where relevant.
5. Report clearly what is known from history versus what is currently verified. Offer to continue in the current dialog rather than waiting for the stuck one.

## Historical score/report provenance pattern

When the user asks “这个评分/报告/结论是怎么来的” about a past AGI/evolution/system score:

1. Start with session_search using exact report title and rare phrases; if no hit, broaden to distinctive numbers, arrows, component names, and Chinese labels from the report.
2. Cross-check against durable ledgers/manifests/report files, not session memory alone. For PGG/APEX/Hermes scores this usually means `EVOLUTION_MANIFEST.json`, audit JSON/JSONL, scorecard history, and relevant workspace governance reports.
3. Reconstruct the arithmetic source explicitly: identify whether the score is an average, weighted score, external audit, health check count, or narrative aggregation.
4. Separate three states in the answer: (a) directly verified historical evidence, (b) inferred/probable source, (c) not found / evidence insufficient.
5. Always compare historical score labels against later truth-governance corrections. If later ledgers say “infrastructure readiness, not external capability/audit,” report that boundary prominently.
6. If live state is probed, label it as current verification only; do not overwrite or silently reinterpret the historical state.

## Reference

Full session log analysis patterns archived at `references/full-skill-archive-20260601.md`.
