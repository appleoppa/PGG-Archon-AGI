---
name: agent-operational-governance
description: 智能体运营治理总纲：任务前边界识别、执行中证据核验、文件系统纪律、安全归档、用户汇报格式与完成态门禁
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [agent-governance, due-diligence, filesystem, reporting, verification, archive]
    related_skills: [agent-due-diligence, file-system-management, user-reporting-preferences]
---

# Agent Operational Governance — Compact

## Trigger

Use for task boundary recognition, evidence-gated execution, filesystem hygiene, safe archiving, independent-agent deployments, and truthful status reporting.

PilotDeck hidden-feature activation/reference workflow: see `references/pilotdeck-hidden-feature-activation-governance-20260605.md` and `references/pilotdeck-hidden-feature-activation-20260606.md` for source/config/runtime/evidence separation, WebSocket gateway smoke, 15-feature PASS/WATCH/BLOCKED classification, and safe Custom Router/Permission/MCP activation patterns.

## Core gates

### /goal formula visibility gate

For this user, the long-term `/goal` rule is not satisfied by silently “internalizing” the formula. For AGI / evolution / PGG Archon / system repair / architecture / legal casework / multi-LLM audit tasks, begin with a compact visible gate before execution:

```text
【公式门禁】
总纲1：which AGI L0-L5 dimensions this task touches, current boundary/shortfall.
总纲2：which Agent_Evolve segment this run will execute: LDR(K) → GapDetect → CodeSelfFix → HotReload → TaskSolve → KnowledgeSettle.
T目标：the bounded T/engineering target for this run; do not imply full AGI.
真实性边界：what evidence would be insufficient and must not be overclaimed.
```

At the end of important tasks, include a short closure map: LDR / GapDetect / fix / verify / deliver / settle / `-ΣΔ_all`. If this is omitted, the user may correctly perceive that the `/goal` rule was not executed, even if the reasoning was internal.

### Tool-call time preview

For this user, before each tool call or parallel tool batch, briefly announce in Chinese what will be called and the expected completion window, e.g. “我现在读取/验证 X，预计 3–5 秒完成。” Keep it concise and do not turn the preview into a plan-only stop; immediately execute the tool call after the preview.

### Visible formula gate for important work

When the task is AGI/evolution, PGG Archon, system repair, architecture, legal casework, multi-LLM audit, or pre-commit governance, do **not** keep `/goal` formulas only implicit. Start with a compact visible gate:

```text
【公式门禁】
总纲1：本任务对应的 AGI 六维能力与当前边界。
总纲2：本轮 Agent_Evolve 走哪一段。
T目标：本轮最多推进到什么可验证工程目标。
真实性边界：哪些证据不足，不能宣称完成。
```

Finish with a compact closure mapping: `LDR(K) / GapDetect / CodeSelfFix or process fix / HotReload or verification / TaskSolve / KnowledgeSettle / -ΣΔ_all`. The user corrected that “后台内化” feels like non-execution; for important tasks the formula must be visible, evidence-backed, and tied to the actual tool outputs.

### Visible `/goal` formula gate for important work

When the task is AGI/evolution/PGG Archon, system repair, architecture, model routing, legal casework, multi-LLM collaboration, scoring, audit, or self-evolution, do **not** merely “internalize” the user’s `/goal` rule. Show a compact visible gate before execution and a compact closure after execution:

- **Before execution**: map the task to 总纲1 AGI L0-L5 six dimensions, state the current boundary/shortfall, identify the 总纲2 `Agent_Evolve = LDR(K) → GapDetect → CodeSelfFix → HotReload → TaskSolve → KnowledgeSettle` segment being used, and state the non-overclaim boundary.
- **After execution**: report which steps actually ran, what evidence was read back, what remains WATCH/BLOCKED, what `-ΣΔ_all` defects were reduced, and where knowledge was settled (memory / skill / manifest / reference).

User-facing reason: if this gate is only implicit, the user experiences it as “not executed.” Keep it concise; do not let the formula block real tool execution.

### Uninstalled-system boundary

During health checks or ecosystem audits, a missing agent, sidecar, daemon, runtime, binary, repo, or mirror is not automatically a fault. First classify it as `EXPECTED_ABSENT` or `UNEXPECTED_MISSING`. If the user intentionally uninstalled or removed it, report only and do not clone/build/install/launch it unless the user explicitly asks to restore. See `references/uninstalled-agent-boundary.md`.

1. Define goal and risk.
2. Check prerequisites and current state with tools.
3. Execute low-risk reversible steps directly when benefit > risk.
4. Verify with readback/tests/hashes/DB rows.
5. Put artifacts in correct workspace; do not pollute root/Desktop unless authorized.
6. Report complete/partial/blocked truthfully.
7. When the user says "立即执行" after an audit or governance finding, continue with low-risk, reversible evidence-building actions immediately: generate manifests/reports, run targeted tests/import checks, and read back files. Do not stop at another plan, but also do not delete, commit, push, or alter core schedulers without explicit scope.

## Independent agent deployment/repair gate

When deploying, repairing, or configuring an independent agent that must remain physically isolated from Hermes (for example PilotDeck), apply `references/independent-agent-deployment-verification.md`: verify hidden-directory isolation first, then perform provider capability probes, config backup/editing, restart, config validation, API readback, UI smoke test, and latest router decision verification. Before making any provider the main agent/router/memory LLM, direct API test its required capability, especially `tools` / `tool_calls`; do not infer support from provider reputation. Treat stale router/events entries as historical noise unless the latest session decision still shows the issue.

PilotDeck-specific drift pitfall: PilotDeck.app/default startup may read `~/.pilotdeck/pilotdeck.yaml` even when the isolated deployment lives under `~/.pilotdeck-agi/home/.pilotdeck`; verify `/Users/appleoppa/.pilotdeck` is a symlink to the hidden configured home and that onboarding is marked complete, otherwise UI shows placeholder LLM setup despite a valid hidden config. For mixed tool/no-tool providers, keep chat-only models (e.g. Agnes) in the model pool only with `supportsToolUse: false`, pin agent/router/fallback to a tool-capable main model, and add a runtime router assertion that reroutes any tools-bearing request away from chat-only models while logging the mutation. For the full MIMO-main / GPT-collaboration / Agnes-chat-only pattern, startup-path repair, capability probes, drift baseline, and verification gates, see `references/pilotdeck-independent-agent-llm-governance-20260603.md`.

## Formula visibility gate for AGI/evolution/system work

When the task is AGI/evolution/PGG Archon/system repair/legal workflow/multi-LLM audit, do **not** only “internalize” the user's `/goal` formulas. Make them visible in a compact gate before execution and in a compact review after execution:

- Pre-task gate: map the task to 总纲1 L0-L5 six dimensions, identify the current boundary/shortfall, state the relevant 总纲2 `Agent_Evolve = LDR(K) → GapDetect → CodeSelfFix → HotReload → TaskSolve → KnowledgeSettle` segment, and state what will **not** be claimed.
- Post-task review: report LDR / GapDetect / fix or process change / verification output / delivered artifact / KnowledgeSettle, plus `-ΣΔ_all` defects reduced.
- If the user says the formula was not felt/executed, treat that as a workflow defect: stop positive summary, acknowledge the visibility failure, and patch the governing skill or reference immediately.

## Completion states

- `DONE`: verified deliverable exists/works.
- `PARTIAL`: useful work done but requirements remain.
- `BLOCKED`: specific dependency/failure prevents completion.
- `DRAFT`: unverified or intentionally preliminary.

## Evolution unification (进化统一)

**Principle**: All evolution achievements across sessions must have a single unified truth source, accessible from any channel/terminal. When you complete an evolution step (implement, absorb, fix, audit), write the state to the unified manifest.

**Implementation pattern**: Each system that accumulates evolution artifacts should have:
1. A `--update` command that regenerates the manifest from live code
2. A human-readable report format
3. A JSON file stored at `~/.hermes/data/` that any session can read
4. The manifest path recorded in SOUL.md + memory for cross-session discovery

**Example**: `EVOLUTION_MANIFEST.json` at `~/.hermes/data/` with `python -m se20.evolution_manifest --update`.

**Cross-channel discovery**: Every new dialog, Feishu channel, or CLI session should be able to `cat ~/.hermes/data/<MANIFEST>.json` to see the full state. Memory should hold the path, not the data. SOUL.md should reference it under execution discipline.

## Forbidden

Do not call a start a completion; do not hide failed commands; do not mix unrelated files into commits; do not claim unavailable agents/models/tools participated.

## Hard rule: no fabrication (不许造假)

**Trigger**: When the user says "不许造假", "让GPT和Claude一起加入审核", or questions a deployment claim — STOP all positive-summary output immediately. Switch to audit mode:

1. **Real runtime evidence only** — file existence is not evidence of functionality. Import, instantiate, run, capture output.
2. **Cross-model audit for claims** — after initial self-assessment of a deployment claim spanning 3+ components, call GPT-5.5 and Claude Opus-4-7 via Responses API for independent verification.
3. **Known limits must be stated** — if a module uses a downgraded implementation (e.g. TF-IDF instead of transformer embeddings), say so explicitly.
4. **Fix, don't explain away** — when GPT/Claude identify a concrete problem (can_proceed=False, missing auto-hooks, 0-score engines), fix it. Then re-audit.
6. **Report honest scores** — if GPT gives 58/100, report 58/100. Don't adjust. Report what was fixed after audit.
7. **Downgrade overclaims** — when audit finds ✅ should be ⚠️, update ALL status tables immediately. Do not add justifications.

### Measurement honesty pitfall

**Problem**: System self-measurement scripts check file existence, importability, and config completeness — NOT actual production runtime usage. Scores of "0.93 overall" based on file checks feel inflated and misrepresent real capability.

### Runtime repair audit pattern: untracked overlays and LLM evidence

When auditing or repairing local AGI/runtime overlays that are intentionally untracked, do not send `git diff` alone to GPT/Claude for verification — it may be empty even after real file edits. For cross-model audit, provide extracted code snippets around the modified symbols plus real test output. If GPT/Claude report "no diff provided", rerun the audit with snippets before accepting or reporting a score.

For provider monkeypatch / SDK interception repairs, require a reversible patch contract: preserve original callable references, make patch operations idempotent, provide `unpatch`/restore checks, align public state probes such as `is_patched()`, and test both replacement and restoration. See `references/agi-runtime-repair-cross-model-audit.md`.

**Rule**: When presenting system capability scores, distinguish between:
- **Structural score** (files exist, imports work, config is correct)
- **Runtime score** (component has been exercised in production, logged actual interactions)

If only structural evidence exists, say so explicitly. Prefer runtime evidence. When the user shows reference scores from another system, do NOT just replicate the numbers — measure YOUR system's actual delta honestly and explain the gap.

For the full cross-model audit protocol and post-audit iteration cycle, see `evolution-systems-governance` skill → `references/cross-model-deployment-verification.md`.

## Stop-point pitfall

If a task includes external research, subagent review, extraction, drafting, and file delivery, do not stop after an intermediate review summary. Completion requires the final artifact to exist and be verified. If the user challenges a premature stop (e.g. "why stopped?"), immediately resume execution and finish the artifact before explaining.

## User-intent recovery pitfall

When a health check finds a missing repo, daemon, mirror, binary, runtime DB, or LaunchAgent, do **not** automatically treat absence as accidental corruption. First classify whether the component is:

- actively required by the current task;
- a known active production dependency;
- a historical residue;
- user-uninstalled / intentionally removed;
- unknown.

If the component may have been intentionally removed, stop recovery and ask or report the boundary. Automatic low-risk remediation may remove broken residues and verify absence, but must not restore uninstalled agents, mirrors, sidecars, services, or launchd jobs without explicit user authorization. This is especially important during “other local agents” inventory and cleanup tasks.

## Git/GitHub portable restore / mirror-to-private pitfall

For Hermes/PGG state migration to a private GitHub repo, use the portable restore pattern in `references/hermes-portable-restore-github-migration.md`: migration branch, sanitized restore bundle, staged secret scan, local isolated restore, push, then decisive fresh remote clone + restore/verify against clean `TARGET_HOME`. Watch for broad `.gitignore` rules such as `data/*` silently omitting required portable manifests; local rsync proof is insufficient unless a remote clone also passes.

When asked to download/copy a GitHub account or repository into private remotes:

1. Treat repo creation, local clone, and remote push as separate completion gates.
2. Verify authentication and target owner before creating private repos; avoid destructive `--mirror` pushes into an existing repo unless the user clearly authorized overwriting refs.
3. Record the discovered source repo list and target private repo list before bulk work.
4. For each repo, require final evidence: local bare/non-bare clone exists with refs, push command completed successfully, target repo is private, and remote branches/tags/refs are visible after push.
5. Large repos may spend a long time in pack/upload with no stdout; use tracked background processes with `notify_on_complete`, per-repo logs, and periodic remote readback. Do not call the batch done until every large repo has final readback.
6. If tool/time limits interrupt a long transfer, report `PARTIAL` explicitly with per-repo statuses; do not imply private repo creation equals code transfer.
7. If the follow-up is "是否部署到本地？", do not answer from the earlier clone claim. Re-check the live filesystem, recreate the local clone if needed, inspect project files, install into an isolated environment, run tests, and perform a minimal runtime smoke test. Deployment means installed + executable + verified, not merely downloaded.
8. For Python package repos, if tests expose small low-risk source bugs, fix them, rerun tests, remove generated artifacts, add `.gitignore`, and push only the deployment-related fixes. See `references/github-private-mirror-local-python-deploy.md`.
9. For Rust/Tauri/Node monorepos, use layered deployment gates: verify repo/submodules, install pnpm + Rust prerequisites from project docs, build/check the Rust core, compile/build the JS app, verify the desktop shell separately, then run core + web smoke tests on localhost. See `references/github-rust-tauri-node-local-deploy.md`. Do not call a GUI window launch mandatory when core + web services are verified and desktop shell `cargo check` passes; report that boundary honestly.
10. For similarly named GitHub repos (e.g. an apparent fork/variant), do not infer relationship from the name. Clone/read both repos, compare tracked file lists and core entrypoints, verify whether original core files still exist, and run the minimal build/check path for the candidate. Report “same class / fork / unrelated project” only from evidence. Treat tracked runtime artifacts (`*.db`, `*.db-wal`, `*.pid`, `__pycache__`, `*.pyc`) as engineering hygiene risks, not proof of functionality. For Rust repos, if `cargo` is absent from PATH, also check `$HOME/.cargo/bin/cargo` before declaring Rust unavailable; if `cargo check` fails, quote the concrete compiler error and classify deployment as `PARTIAL`, not `DONE`.

## "全量吸收并部署" pitfall

When the user says "全量吸收并部署" (fully absorb and deploy) a document/concept:

1. **Read and truly understand** -- don't skim.
2. **Audit existing mechanisms first** -- check what actually exists vs what's needed. Don't trust "ready" labels from configs or your own previous claims.
3. **For each requirement**: list what exists (✅), what partially exists (⚠️), what doesn't exist (❌). Be honest.
4. **Build/optimize the gaps** -- for each ❌, create a real working implementation. Delegate parallel tasks when independent.
5. **Verify every component** -- import, instantiate, run a test call. Don't stop at file creation.
6. **Update system references** -- SOUL.md, governing skills, memory reflect the new state.
7. **Report honest status** -- not "all done ✅" until each component has been proven.

**Key distinction**: 声明部署 ≠ 实质部署. The user will call this out if you skip steps 2-5. The correction signal is "你确定你全部理解并全部部署了吗？如果已有的机制，需要对比优化" -- when you hear that, you skipped the audit step.

## "全量补齐" user preference (proven 2026-06-01)

The user's "全量" (full/complete) directive carries specific expectations:

1. **No partial stops** — "全量补齐" means the user expects every identified gap to be fixed, not just the easy ones. When you hit a blocker (proxy network, missing SDK), you must find a compliant alternative within environment limits. Saying "不能做" is acceptable only after exhausting all options.

2. **Audit → GitHub → Implement cycle** — When the user says "去github仓库全量学习补全", the correct response is: extract concrete gaps from the audit, search for each gap on GitHub/real repos, learn the pattern, implement, verify. Do not report "gap X can't be fixed" without first searching for how others fixed it.

3. **Report with closure** — "缺口X评分Y→修复后评分Z" format. The user wants to see before/after scores, not narrative.

4. **All LLMs participate** — When the user says "调用所有可以调用的LLM", they mean: use DeepSeek (当前会话) + GPT-5.5 + Claude Opus-4-7 for consultation AND verification. GPT/Claude calls must be real (Responses API), not role-played.

5. **Not "all gaps equal"** — Prioritize gaps with biggest score impact. Provider-level bypassability (45→95) matters more than cosmetic polish.

### Recognition signals
- "全量补齐" = full closure, not partial
- "全量解决" = exhaustive fix, not "we can fix this later"
- "所有llm共同出击" = three-model collaboration, real API calls
- "去github仓库全量学习补全" = search open-source patterns, not just implement from memory

## 2026-06-02 真实性治理补丁

- Agent（智能体）状态审计必须多源核验：process（进程）、launchctl、plist、port（端口）、关键目录、日志；目录存在不等于服务运行，端口可达不等于能力可用。
- 已被用户明确移除的系统不得被自动修复恢复。当前典型红线：APEX-MEM 不得自动 clone/build/start/bridge，除非用户显式要求恢复。
- 遗留残留优先隔离而非重启：OpenClaw/AutoClaw 等缺依赖旧 plist，先 bootout/quarantine/log rotate，再判断是否需要删除。
- 健康检查自身也要资源治理：扫描器必须限制文件数，跳过 `__pycache__`、缓存、大目录和二进制；不能让 health（健康检查）成为卡顿源。
- 对“假代码/硬编码/模拟成功”保持 WATCH/BLOCKED 口径：固定 readiness/pass_rate/status、mock/sim/dry-run、time.sleep 假时长、repair suggestion 冒充 repair completed，均不得作为真实完成。

## References

- `references/hermes-portable-restore-github-migration.md` — GitHub-safe portable restore migration pattern for Hermes/PGG state: never push `~/.hermes` wholesale, build a sanitized `portable_restore/` skeleton, force/include manifest despite broad `data/*` ignores, run secret scan + local restore + fresh remote clone restore before claiming recoverability.
- `references/router-web-runtime-gate-anti-stall-20260606.md` — Router/Web/runtime hook gate pattern: anti-stall after skill loading, MiMo judge isolation across router/API/test layers, bounded Web validators, mirror-only run_agent hooks, targeted LLM review packs, scoped commit + manifest closure.
- `references/pilotdeck-evolution-pipeline-evidence-chain.md` — PilotDeck self-evolution 8-step pipeline and structured evidence-chain completion gate. Use when guiding PilotDeck evolution or validating a PilotDeck `DONE` claim.
- `references/pilotdeck-provider-triad-minimax-mimo-agnes.md` — PilotDeck provider-triad configuration pattern: remove GPT from PilotDeck scope, add MiniMax-M3, keep MIMO default/tools/memory, Agnes chat-only audit, update stale invariants/evidence chain, and verify with direct MiniMax tools probe plus gateway smoke.

- `references/pilotdeck-mimo-gpt-bridge-governance.md` — PilotDeck independent-agent repair pattern: hidden home + default symlink, MIMO主控, GPT no-tools bridge collaboration, Agnes no-tools guard, and final verification checklist.
- `references/pilotdeck-8-step-evolution-pipeline.md` — PilotDeck self-evolution completion gate: file_scan → Karpathy check → import_parse/build → integrated_report → EVM monitor → Tao correction → β_bg evolution → pipeline_completion. Use before any PilotDeck evolution `DONE` claim.
- `references/pilotdeck-bridge-auth-hardening.md` — PilotDeck GPT bridge bearer-auth hardening pattern: optional local token, `set -a` env export pitfall, no-auth/with-auth probes, and invariant-checker regression guard.

Full governance examples archived at `references/full-skill-archive-20260601.md`.
