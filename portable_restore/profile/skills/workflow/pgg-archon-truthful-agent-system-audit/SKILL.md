---
name: pgg-archon-truthful-agent-system-audit
description: PGG Archon/APEX-GOD 多智能体状态审计、假代码/硬编码/模拟清理与顺序激活治理
version: 1.0.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [pgg-archon, apex-god, agent-audit, truthfulness, simulation-removal, launchd]
    related_skills: [agent-operational-governance, apex-sequence-logic, hermes-evolution, super-evolution-20]
---

# PGG Archon Truthful Agent System Audit

## Trigger

Use when the user asks to:

- 查看本机部署的其他 agent（智能体）、daemon（守护进程）、gateway（网关）状态；
- 清理假代码、硬代码、硬算法、硬编码、mock（模拟）、sim（仿真）、dry-run（演练）冒充成功；
- 激活外部 APEX / PGG / AGI repo（仓库）能力；
- "继续"推进进化知识落地。

## Core rules

0. Score-mouth and convergence truthfulness: when audit/status/convergence numbers conflict, first identify each metric's mouth (runtime readiness, external audit, self-eval, convergence gap). Do not compare unlike scores. For APEX ΔE, remember it is higher-is-better; if the checker is lower-is-better, use `convergence_gap = max_delta_e - delta_e`. See `references/audit-score-semantics-and-convergence.md`.

1. 多源核验：状态审计必须同时查 process（进程）、launchctl、plist、port（端口）、关键目录、日志；目录存在≠服务运行，端口可达≠能力可用。
2. 不自动恢复已移除系统：APEX-MEM 已被用户明确移除，任何 repair（修复）、health（健康检查）、bridge（桥接）不得自动 clone/build/start 它。
3. 残留优先隔离：OpenClaw/AutoClaw 等缺依赖旧 plist 先 bootout/quarantine/log rotate；不得盲目重启。
4. 假代码高危信号：文件名或字段含 mock/sim/dry_run；固定 readiness/pass_rate/status；time.sleep 假时长；approve/success 但未执行真实动作；repair suggestion 冒充 repair completed；`is_available=True` 常量。
5. 修复仿真模块：保留兼容函数/schema，但输出必须包含 `simulated`、`evidence`、`checked_targets`、`warnings`；HOLD/READY 不得写成 production executed。
6. 顺序激活：audit → smoke/simulate → activate one component → debug until smooth → full health/tests → commit；不能批量解锁导致系统卡顿。
7. 健康检查限流：scanner（扫描器）必须限制文件数，跳过 `__pycache__`、缓存、大目录和二进制，避免 health 本身成为负载源。
8. 进化/AGI 审计必须真实调用配置 provider（供应商）：GPT/Claude/Agnes；GPT/Claude 必须走 Responses API，不能用 subagent roleplay（角色扮演）替代。

## Status audit commands

Run compact checks and summarize, not raw-dump everything:

```bash
ps -axo pid,ppid,pcpu,pmem,etime,args | egrep -i 'apex|pgg|archon|agnes|claude|codex|gpt|ollama|openhuman|claw|mcp|dify|flowise|n8n'
launchctl list | egrep -i 'apex|pgg|archon|ollama|openhuman|claw|mcp|dify|flowise|n8n'
lsof -nP -iTCP -sTCP:LISTEN | egrep -i 'python|node|ollama|apex|pgg|openhuman|claw|mcp'
```

Check known ports when relevant:

- `8765`: APEX-MEM — should stay absent unless user explicitly restores.
- `18789`: OpenClaw — old residue if present.
- `11434`: Ollama.
- `1234`: LM Studio.
- `3000/7860/8080`: common Web UI / Gradio / local service ports.

## Fake/simulation repair workflow

1. Search suspicious patterns: `mock|simulat|dry_run|hardcod|readiness|pass_rate|is_available|sleep|approval|placeholder`.
2. Classify each hit:
   - `REAL`: evidence-backed.
   - `WATCH`: partial but honest.
   - `SIMULATED`: fake/mocked success risk.
   - `BLOCKED`: dependency or credential absent.
3. Patch only `SIMULATED` or misleading `WATCH` first.
4. Replace constants with real checks: filesystem, subprocess, launchctl, tests, manifests, logs.
5. Keep schema compatibility but add honesty fields.
6. Smoke-test patched function/module.
7. Run focused tests, then full health.
8. Commit only current-theme files.

## Reporting format

Use short Chinese fieldized report:

```text
状态：完成 / 部分完成 / BLOCKED
已核验：process / launchctl / plist / port / dirs / logs
正常运行：...
未运行/已移除：...
异常/负载源：...
已落地：技能/manifest/测试/提交
证据：HTTP 200 / health x/y / test x passed / commit hash
```

## User-correction pitfall: audit before extending evolution loops

When the user asks to continue AGI evolution or install a background automatic loop, do **not** jump straight into creating the next module. First produce a compact verified state panel covering:

- EVOLUTION_MANIFEST current capability keys and latest audit/milestone.
- repo HEAD / recent commits / clean or dirty worktree.
- key module importability and focused tests.
- Rust fused watcher / launchd PID and watched paths.
- existing Hermes cron jobs, including paused legacy ARS/autopromote jobs.
- existing queue/proposal/regression artifacts.

Then explicitly state what is already complete and what missing rung remains. This prevents duplicate work and addresses the user's correction: "查看已经完成的工作及模块，不要再做重复工作".

## Multi-LLM parallel audit workflow

For full system assessments, delegate to 4 specialized LLMs in parallel:

| LLM | Assessment Dimension | API |
|---|---|---|
| GPT-5.5 | 架构完整性、代码可用性、自治与进化 | codex_responses / Responses API |
| Claude-opus-4-6 | 安全与治理审计、幻觉风险、自愈真实性 | codex_responses / Responses API |
| DeepSeek | 法律领域覆盖、办案流程、文书生成 | chat_completions |
| MIMO | 合规性与风险评估、数据安全、伦理边界 | chat_completions |

Each subagent gets a self-contained context block with verified system state (not claims). Subagents run terminal + file toolsets independently. Synthesize results into a unified report with cross-LLM consensus table.

Key: pass **verified facts** to subagents, not AGENTS.md claims. The initial state verification (component existence, import checks, service status) must happen BEFORE delegation.

## Component existence verification checklist

Run before any audit to establish ground truth:

```python
# 1. Profile skill count (check actual skill files, not SKILL.md claims)
for profile in pgg_profiles:
    skills_dir = f"/Users/appleoppa/.hermes/profiles/{profile}/skills"
    skill_count = len([f for f in os.listdir(skills_dir) if f.endswith('.md')])

# 2. Python module importability
for mod in ["apex_god", "hermes_apex_evolution", "constraint_engine", "self_healing", "gene_db"]:
    subprocess.run(['python3', '-c', f'import {mod}'])

# 3. Key file existence
key_files = ["constraint_engine.py", "self_healing.py", "gene_db.py", "boundary_enforcer.py", "apex_evolution_tool.py"]
# Search in workspace AND hermes-agent, not just one location

# 4. Profile memory differentiation (detect identical memories)
import hashlib
for profile in pgg_profiles:
    mem_path = f"/Users/appleoppa/.hermes/profiles/{profile}/MEMORY.md"
    hash = hashlib.md5(open(mem_path).read().encode()).hexdigest()
# If all hashes identical → profiles are clones, not specialized agents

# 5. Launchd service liveness (PID=- means dead service)
launchctl list | grep pgg
# Check for exit code 0 with PID=-
```

## P3 multi-LLM smoke pattern (added 2026-06-04)

For bounded harnesses (redteam / benchmark / multimodal status), the canonical
pattern is:

1. Build the harness + corpus (e.g. `pgg_archon_redteam_harness.py`,
   `pgg_archon_benchmark_corpus.py`, `pgg_archon_benchmark_harness.py`,
   `pgg_archon_multimodal_status.py`).
2. Run it across multiple configured providers (DeepSeek / MiMo / Agnes / ...)
   using the `scripts/p3_full_smoke.py` orchestrator. Run long batches in
   background with `notify_on_complete=true`.
3. Run an independent 4-LLM audit panel against the smoke numbers using
   `scripts/p3_summarize.py`. The audit prompt must carry the smoke numbers
   as facts and demand STRICT JSON output.
4. Land a single manifest key (e.g. `latest_p3_full_smoke_<date>`) with
   per-provider metrics and the boundary string.
5. Always include the boundary ("5-item status corpus; not a real score")
   in both the report and the harness output JSON.

See `references/p3-full-multillm-smoke-pattern-20260604.md` for the full
lesson (foreground-vs-background tool budget, refusal heuristic is conservative,
multimodal status disagreement pattern, bash `re.sub`-in-heredoc quoting
pitfall, manifest external ledger pattern).

## Scoped pre-commit and runner boundary pattern (added 2026-06-06)

For multi-group PGG/Hermes engineering closure, do not treat `git status` as a staging list. Split by semantic boundary, verify each group, and stage only approved files. In particular:

- Third-party judge providers must be excluded from ordinary default pools, rejected on explicit ordinary requests, blocked at Web/API validators, and covered by tests.
- PASS metrics must be recomputed from eligible rows; HTTP failure, timeout, empty text, unparsed output, or local-precheck-only rows cannot inflate pass rates.
- Legal smoke/taskset runners must remain bounded process-safety checks and must not claim official LegalBench/LexGLUE, legal correctness, court-ready approval, or AGI evidence.
- Route policy changes need a `route_policy_version` in both decision and mirror ledgers, plus post-policy metrics windows to avoid stale mixed-window overreads.
- Repo-local evidence workspaces/package-manager noise should be moved to a held archive under `~/.hermes/workspace/...`, not committed; add durable `.gitignore` rules for stable artifact classes.

See `references/lessons-scoped-precommit-and-runner-boundaries-20260606.md` for the concrete checklist and pitfalls.

## Reference pointer

- `references/api-discovery-pattern.md`
- `references/audit-score-semantics-and-convergence.md`
- `references/component-verification-20260603.md`
- `references/system-repair-workflow-20260603.md`
- `references/claude-coded-health-repair-pattern-20260603.md`
- `references/local-agi-process-objective-scoring.md`
- `references/pgg-evolution-round-evidence-chain.md`
- `references/round6-ledger-vs-fresh-eval-and-overlay-audit-20260603.md`
- `references/round6-round7-overlay-delta-repair-pattern-20260603.md`
- `references/round6-provider-audit-and-compat-shim-pattern-20260603.md`
- `references/autonomous-evolution-loop-promotion-gates-20260604.md`
- `references/genedb-promotion-provider-quorum-20260604.md`
- `references/genedb-promotion-provider-repair-20260604.md`
- `references/genedb-all-candidate-promotion-gate-20260604.md`
- `references/genedb-lifecycle-cleanup-and-multi-llm-audit-20260604.md`
- `references/p3-full-multillm-smoke-pattern-20260604.md` (2026-06-04 P3 multi-LLM smoke)
- `references/p3plus-super-evolution-desktop-lane-20260604.md` (2026-06-04
  P3+ 5-step closed loop + multi-LLM robustness + JSON parser pattern +
  4 forbidden tool-usage idioms + lane telemetry + non-negotiable
  boundary rule)
See `references/p3plus-50-probe-corpus-and-consensus-weak-20260604.md`
(2026-06-04 three-stage 50-probe build + consensus_under_50
non-monotonic emergence + per-provider failure isolation + terminal
background PYTHONPATH quirk + max iterations cap discipline)
- `references/p7-fact-hallucination-regex-selfcheck-20260605.md`
  (2026-06-05 case 0006: LLM 巡视 + LLM 审计 passed a hallucinated
  P7 民事起诉状; programmatic regex self-check on the produced
  facts_and_reasons section caught 7+ invented facts that
  LLM inspection missed. Mandatory at P7 finalization: 3-channel
  no-gpt5.5 + FACT_BLOCK verbatim in prompt + 15+ required / 7+
  forbidden regex self-check; mark draft `.OBSOLETE_事实错误`
  on any miss. Pointer in `apple-hub-orchestrator` SKILL.md and
  `apple-civil-litigation` SKILL.md.)
- `references/mimo-manifest-gate-pass-eligibility-20260606.md`
  (2026-06-06 P1 MiMo manifest gate: manifest PASS must recompute
  per-result eligibility from `status == OK_PARSED` +
  `audit_verdict == PASS`; `--no-mimo` / `LOCAL_PRECHECK_ONLY` /
  `OK_UNPARSED` / non-zero provider exit / forged `pass_count` all
  downgrade to WATCH/ERROR. Also records review-pack pitfall for
  untracked files where `git diff` is empty and commit-dependency
  pitfall where dirty worktree hides missing imports.)
- `scripts/p3_full_smoke.py` (orchestrator)
- `scripts/p3_summarize.py` (audit panel + manifest update)
- `scripts/p3_50_verifier_friendly.py` (50-probe cross-provider
  consensus report + 4-LLM independent audit panel + manifest key
  `latest_p3_50_smoke_<date>`)
