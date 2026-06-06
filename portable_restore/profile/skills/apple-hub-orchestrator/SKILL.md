---
name: apple-hub-orchestrator
version: "2.2.0"
description: 苹果中枢调度器：统一入口与流程控制（多LLM协作：delegate_task 3-LLM + direct-HTTP 4-channel）
metadata:
  {
    "openclaw": {
      "original_id": "main",
      "original_name": "苹果中枢",
      "timeout": "同步",
      "mode": "调度",
      "subagents": "*",
      "capabilities": ["统一入口", "调度中心", "轻桥层", "流程控制"]
    },
    "category": "apple-case-system",
    "tags": ["调度", "中枢", "入口", "协调", "办案", "多LLM协作"]
  }
---

# Apple Hub Orchestrator — Compact

## Trigger

Use as central legal-work dispatcher for 苹果中枢: intake, department routing, case workflow, audit handoff, and final delivery gating.

## Core rule

When the user says start/launch case handling, run the formal department workflow. Do not let the central agent alone read materials and claim the whole case system started.

## Workflow

### Phase 1 — CMS Intake

1. **FIRST: load `agent-cms` skill** and read the current numbering rule. Do not assume you remember it.
2. Identify case type and materials.
3. CMS creates/locates case number and directories with correct structure:
   - `0001-PGGMS-YYYYMMDD-当事人/`
   - `PGG-MS-YYYYMMDD-0001（一审/二审/再审等）/`
   - Standard folders only: 案件材料、案件过程报告、总结报告、正式文书
4. Copy original materials into `案件材料/`.

### Phase 2 — Department Dispatch

Dispatch to relevant departments in parallel via `delegate_task`:

| Department | Responsibility | Skill |
|------------|---------------|-------|
| 刑事辩护部/民事案件部 | Charge analysis, defense strategy | `dept-criminal-defense` |
| 证据管理部 | Evidence catalogue, chain of custody | `dept-evidence-management` |
| 律法支持部 | Legal research, citation verification | `dept-legal-support` |
| 案件推演部 (optional) | Risk prediction, simulation | `dept-case-simulation` |

Each department receives the full case materials and outputs its own work product to `案件过程报告/`.

### Phase 3 — Multi-LLM Collaborative Dispatch

(If user says "你们三个LLM一起协作办案" — see §Multi-LLM section below.)

### Phase 4 — Inspection & Audit Chain

After all departments complete:

1. **巡视组** (`dept-inspection-team`): independent verification of facts, law, procedure, and department flow. Marks PASS/WATCH/BLOCKED.
2. **自检** (central agent): check all files exist, all departments completed, all BLOCKED items resolved.
3. **审计组** (`dept-audit-team`): final audit of deliverables vs claims, legal citation accuracy, model call authenticity.
4. **归档**: update ledger, file structure confirmed.
5. **交付**: external deliverable if safe (PASS + no BLOCKED); otherwise internal report only.

### Multi-LLM collaborative dispatch

PGG Archon supports **two distinct patterns** for multi-LLM case collaboration. Pick by the trigger:

**Pattern A — `delegate_task` 3-LLM (heavy, isolated sub-contexts)** — use when:
- User says "你们三个LLM一起协作办案"
- Each LLM needs a long, isolated context to specialize (e.g. one writes complaint, another drafts settlement)
- Subagents need tool-calling (web research, file I/O) — direct-HTTP does not support this
- See `references/multi-llm-collaborative-dispatch.md` for the full playbook

**Pattern B — Direct-HTTP 4-channel (lightweight, parallel comparison)** — use when:
- User says "调用所有LLM / 4通道协作 / 调用一切资源" — they want comparison, not isolation
- Task is analytical/comparative (multi-LLM voting on a legal issue, parallel research, parallel drafting)
- Output is structured STRICT JSON and can be aggregated
- Audit trail is required (raw outputs must be persisted for review)
- See `references/4-channel-case-llm-orchestration.md` for the full pattern + verdict classification schema
- The reusable thin wrapper is at `scripts/case_llm.py` — `PYTHONPATH=$HOME/.hermes/hermes-agent python3 scripts/case_llm.py --ping` to health-check, `--prompt "..."` to run a 4-channel call

**Verdict classification (Pattern B — mandatory)**:
- **PASS**: http_status==200, content not empty, JSON parse succeeds
- **WATCH**: http_status==200, content present but not strict JSON (or `<think>` reasoning-only)
- **ERROR**: http_status != 200, content empty (0 chars), or JSON parse fails
- A single channel's ERROR is recorded but **never silently upgraded** to PASS/WATCH; numeric consensus uses PASS-only mean

## Pitfalls

1. **CMS is step zero.** Never create directories, files, or analyses before loading `agent-cms` and reading the current numbering rule.
2. **Do not bypass departments.** The central agent orchestrates; departments produce work products. If you do the analysis yourself without dispatching, the case has not actually been processed.
3. **Do not invent case-type codes.** Use `MS` as defined in CMS. Any other code (e.g. `XS`) will be flagged BLOCKED by inspection.
4. **Stage subdirectory is mandatory.** Structure is: root/ → stage-dir/ → standard folders. Without it, files don't belong to any trial stage.
5. **Only four standard stage folders.** 案件材料、案件过程报告、总结报告、正式文书. No extra folders.
6. **Complete the full chain before claiming done.** CMS → departments → inspection → self-check → audit → archive. Partial completion is not completion.
7. **Pick the right multi-LLM pattern (A vs B).** Pattern A (`delegate_task` 3-LLM) for isolated specialist work; Pattern B (direct-HTTP 4-channel via `case_llm.py`) for comparison/voting/structured aggregation. Mixing them or using the wrong one wastes tokens and breaks audit trails.
8. **MiniMax channel may be currently-degraded.** As of 2026-06-05, `minimax` (MiniMax-M3) has timed out 4/4 times in case PGG-MS-20260605-0006 at 90s with `max_tokens ∈ {2200, 3000, 3500, 4000}`. Treat as ERROR; do not retry. Verify channel health with `case_llm.py --ping` before relying on it. Investigation: plist `MINIMAX_API_KEY` is set, endpoint `api.minimax.chat/v1/chat/completions` returns HTTP 200 but the response is empty / takes >90s. Cause unknown as of 2026-06-05.
9. **mimo 0-char transient.** A `mimo` channel returning 0 chars is transient (recovers on retry); not a permanent failure. If a 4-channel round gets 0-char from mimo, retry the whole round once. Two consecutive 0-char failures → mark channel as degraded for the session.
10. **gpt5.5 endpoint and mode gotcha.** Only `chuangagent.eu.cc/v1/chat/completions` works for gpt-5.5; other 5yuantoken/minimax domains return SSL EOF or 401. The `/responses` mode returns 0 chars; use chat mode only.
11. **gpt5.5 long-task timeout (added 2026-06-05 case 0006).** For `max_tokens ≥ 4500` AND 4-channel consensus tasks, gpt-5.5 (chuangagent) frequently returns 90s timeout ERROR. Stable for `max_tokens ≤ 3000`. For P7 民事起诉状 FINAL (4891+ chars facts_and_reasons) or P3 法律意见书 (3000+ chars), consider **excluding gpt5.5 from the channel set** and using the remaining 3 channels (deepseek/agnes/mimo). If gpt5.5 must stay, expect 1 ERROR per round and aggregate over the surviving channels only.
12. **P7 fact-hallucination when long channels timeout (added 2026-06-05 case 0006).** When gpt5.5+minimax both 90s timeout on a long P7 民事起诉状 task, the surviving 3 channels (deepseek/agnes/mimo) lose half their context and may "freely invent" missing facts: case 0006 v1 起诉状 contained "高血压既往病史 / 工地事故 / 2025年3月15日 / 重型自卸货车" — all **non-existent in the source 材料**. **Mitigation (mandatory at P7 finalization)**:
   - In the prompt, **paste the source 客户《情况说明》真实事实 verbatim as a FACT_BLOCK** at the top, then require the model to use it without inventing. Explicitly forbid: free-form scene completion, alternative dates, alternative parties, alternative causes.
   - After generation, run a **programmatic regex self-check** (NOT another LLM inspection — the LLM 巡视 in the same session also failed to catch this) on the produced `facts_and_reasons` section:
     - `required_facts`: 10–15 facts that MUST appear (事故时间, 保单号, 工亡文号, 限额, 责任比例, 当事人全称, etc.)
     - `forbidden_facts`: 7+ invented markers from prior hallucination rounds (高血压, 工地, 3月15日, etc.) — extend this list from the actual error in your session
   - If self-check fails ≥1 项 → mark the draft `.OBSOLETE_事实错误` and regenerate (use the same fix)
   - The P5 巡视 / P6 审计 LLM panels are **NOT a substitute** for this regex self-check; they have been observed to pass hallucinated drafts
13. **Use the skill's `scripts/case_llm.py` directly — do NOT reimplement at `/tmp/`.** The reusable 4-channel thin wrapper at `apple-hub-orchestrator/scripts/case_llm.py` already supports `--ping`, `--prompt`, `--max-tokens`, `--timeout` and writes per-provider records with verdict classification. If you copy it to `/tmp/`, you lose the audit link between skill updates and your ad-hoc copy. Always invoke as `PYTHONPATH=$HOME/.hermes/hermes-agent python3 $HOME/.hermes/skills/apple-hub-orchestrator/scripts/case_llm.py --prompt "..."`.
14. **`cms_case_guard` symlink at `~/.hermes/bin/cms_case_guard`.** The Rust-native gate is symlinked to `~/.hermes/workspace/pgg-archon-governance/rust/cms_case_guard/target/release/cms_case_guard`; the symlink is at `~/.hermes/bin/cms_case_guard`. Both invocations work. Always run `cms_case_guard --next` before case creation and `cms_case_guard --validate <case_root> --case-type <XS|MS>` after directory structure is set. The `--validate` step is BLOCKED-tolerant for known legacy case-shape deviations (existing 0003/0006 both show BLOCKED with `EXTRA_TOP_LEVEL_DIRS` but the case is still considered valid by inspection team); the JSON output is archived into `审计记录/cms_case_guard_validate.json` as the audit evidence.

## Multi-LLM provider access notes

When dispatching to external LLMs for collaborative analysis:

- **MiMo** (mimo-v2.5-pro): API accessible via standard curl; key from MIMO_V25_PRO_API_KEY env var. Works reliably via delegate_task with terminal toolsets.
- **MiniMax** (MiniMax-M3): API key (MINIMAX_API_KEY) is **NOT reliably available** via `source ~/.hermes/.env` in terminal. Reliable access method: extract from launchd plist `~/Library/LaunchAgents/ai.hermes.*.plist` → `EnvironmentVariables.MINIMAX_API_KEY` using Python's `plistlib.load()`. Base URL: `https://api.minimax.chat/v1/chat/completions`. May time out on long responses (read timeout >120s on 4000+ token outputs); use max_tokens ≤ 3000 for reliability.
- **Claude**: Currently unavailable per user direction (June 2026). Do not attempt. Mark as ERROR in flow record.
- **gpt5.5**: Routes through chuangagent.eu.cc, chat completions mode only (responses API returns empty text).

## Boundary

No claim of replacing lawyer review, zero litigation risk, or official legal guarantee.

## Reference

- **Multi-LLM Pattern A** (`delegate_task` 3-LLM): `references/multi-llm-collaborative-dispatch.md`
- **Multi-LLM Pattern B** (direct-HTTP 4-channel, current default for analytical work): `references/4-channel-case-llm-orchestration.md`
- **Reusable thin wrapper** (Pattern B): `scripts/case_llm.py`
- **P7 民事起诉状 FINAL 事实幻觉 + 正则自检模式** (added 2026-06-05 case 0006): `references/p7-fact-hallucination-regex-selfcheck.md`
- Full routing matrix: `references/full-skill-archive-20260601.md`
