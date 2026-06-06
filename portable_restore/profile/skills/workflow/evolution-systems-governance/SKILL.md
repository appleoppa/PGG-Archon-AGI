---
name: evolution-systems-governance
description: 开智/EVM/多智能体进化系统治理总纲：三顺序循环、EVM缺陷治理、河图洛书路由、GitHub工厂、多智能体技能复制与真实任务迁移
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [evolution, evm, router, multi-agent, governance, github-factory, manifest, unification]
    related_skills: [manual-evolution-loop, evm-integration, multi-agent-replication]
---

# Evolution Systems Governance — Compact

## Trigger

Use for 开智/EVM/PGG Archon evolution governance, multi-agent evolution, GitHub factory patterns, skill replication, route/factory audits, and formula-driven improvement loops.

## Core rule

Evolution is valid only when a real weakness is exposed, an external/internal pattern changes an implementable rule, the rule lands in code/config/skill/GeneDB/report, and readback/test evidence exists.

## Absorb-and-deploy sequence (critical discipline)

When the user says "全量吸收并部署" (absorb and deploy a document/concept/framework), the **correct sequence** is:

1. **Read & understand** — read the source material completely.
2. **Map** — list each claim/rule/component the material requires.
3. **Audit each mapped item** — for each, check: does the claimed mechanism exist as code? Is it running (not just file-on-disk)? Does it actually do what the new requirement says, or is it a different thing with a similar name? Use terminal/search_files/read_file to verify — do NOT infer from config keys, README claims, or file existence alone.
4. **Grade honestly** — ✅ exists and works / ⚠️ partially exists with known gaps / ❌ does not exist.
5. **Fix what's fixable** — create missing tools, fix broken cron jobs, upgrade simulated modules.
6. **Document remaining gaps** — mark in SOUL.md and the relevant skill what is ⚠️ or ❌ and why.
7. **Report** — give the user the honest table, not a map of hopes.

**Failing this sequence** (e.g. assuming an existing mechanism matches a new requirement without verifying, or claiming "deployed" after only writing a skill file) is a reliability failure. The user will call it out, and rightly so. Do not skip step 3.

## Three sequences

- `21354`: error/audit first when risk or hallucination is suspected.
- `12534`: absorb/fuse/solidify when material is trustworthy and implementation path is clear.
- `14325`: plan/refute before acting when architecture risk is high.

## Cross-model deployment verification gate

After steps 1-5 (absorb, map, audit, fix, grade), add this verification gate to independently validate claims.

### Two-phase model: Pre-design consultation + Post-deployment audit

The three-model collaboration (DeepSeek + GPT-5.5 + Claude) has TWO distinct phases:

**Phase A — Pre-design consultation** (use when designing architecture for 3+ components):
1. Send current state + constraints to GPT-5.5 and Claude Opus-4-7.
2. Ask each for "realistic deployment plan" — 3 specific lines per component.
3. Compare responses. Both models converged on the same architecture (centralized middleware with pre/post hooks) when asked.
4. Implement based on converged design.

**Phase B — Post-deployment audit** (use for verification):
1. Gather real runtime evidence. Import, instantiate, run, capture output.
2. Call GPT + Claude with structured evidence payload.
3. Fix identified gaps. Re-audit.
4. Update status tables.

**When to call which**: Phase A before implementation for architecture design. Phase B after implementation for validation. Both when a claim spans 3+ components and involves architectural decisions.

### Phase B protocol

**When to trigger**: the user says "让GPT和Claude一起加入审核" or any deployment claim needs independent verification. Do not wait to be asked — the gate is mandatory for any "all N rules deployed" claim involving complex or self-assessment.

**Protocol**:

1. **Real runtime audit** — run each module with live Python, capture actual output values (not just "imports OK"). Collect a JSON evidence payload.
2. **Build evidence payload** — structure as JSON with rule-by-rule status, real output values, file paths, known limitations. Keep it honest and objective.
3. **Call GPT-5.5 via Responses API** — POST to `/v1/responses` with `model: "gpt-5.5"`, payload as `input`, strict audit instructions.
4. **Call Claude Opus-4-7 via Responses API** — same endpoint, `model: "claude-opus-4-7"`.
5. **(Optional) Call MIMO v2.5 Pro** — `model: "mimo-v2.5-pro"` via `/v1/chat/completions`.
6. **Triangulate** — compare all outputs. GPT tends to be strictest (numerical scores). Fix any concrete issues they identify (e.g. `can_proceed=False`, missing auto-triggers).
7. **Iterate** — fix → re-audit → update SOUL.md/skill status.

**API details**: GPT-5.5 and Claude use Responses API: `POST /v1/responses` with body `{"model":"<name>","input":"...","instructions":"...","max_output_tokens":2000}`. Auth from `.env` via `source`. Use Python urllib for reliable JSON (avoid bash heredoc interpolation for complex payloads). MIMO uses standard `/v1/chat/completions` (check config.yaml for api_mode).

### Practice notes from real use:
- GPT-5.5 tends to be strict (numerical scores) and may time out over 60s — set `timeout=90+`.
- Claude returns `[{'type':'output_text','text':'...'}]` — access via `output[0].get('content',[{}])[0].get('text','')` or iterate.
- Use Python `urllib.request` for payload JSON (avoid bash HEREDOC escaping issues with complex nested structures).
- Set `max_output_tokens` high enough (3000+) for detailed audit results.

### Post-audit iteration cycle (proven 2026-06-01)

After GPT/Claude returns findings, the correct cycle is:

1. **Identify concrete fixable issues** — look for specific failures (can_proceed=False, missing auto-hooks, 0-score engines). Ignore generic criticism.
2. **Fix immediately** — update code, add cron jobs, seed data, fix import paths. Do NOT write justifications for why something is acceptable.
3. **Re-collect evidence** — re-run the runtime audit after fixes.
4. **Update SOUL.md + SKILL.md** — downgrade ✅ to ⚠️ where audit found overclaiming. Add audit scores. Document gap sizes.
5. **Report to user** — show fixes (with evidence), GPT/Claude scores, and remaining gaps.

**Critical rule**: Never report "all done ✅" without step 4 evidence. User calls this out as fabrication. When they say "不许造假", stop what you're doing and switch to audit mode.

See `references/cross-model-deployment-verification.md` for full transcript and API templates.

## Boundaries

Do not claim full AGI, permanent autonomous evolution, provider participation, GitHub absorption, or model-weight change without real evidence. External repos are reference material, not automatic capabilities.

## Output

Reference for gated autonomous evolution: `references/autonomous-evolution-gated-promotion.md`. When reporting AGI/PGG evolution progress, distinguish queue/proposal/regression/patch sandbox/main patch/GeneDB candidate/promotion as separate states; never collapse them into a single “completed AGI” claim.


Report status, evidence, changed files, tests/readback, GeneDB/skill updates, unresolved deltas, and next low-risk action.

## 外部仓库全量吸收方法（APEX-MEM / nanoGPT-claw 实战证实）

当吸收一个外部 GitHub 仓库的模式时（如"全量吸收 APEX-MEM"），遵循此序列而非即兴执行：

### Phase 1: 仓库了解
1. **读 README** — 用 `curl` / `browser_navigate` 获取 README。提取核心模式清单（内存架构、检索策略、技能系统、公式）
2. **获取源码树** — 先 API 列目录，再下载关键文件（`Cargo.toml`、`src/lib.rs`、各模块 `mod.rs`）。遇到 rate limit 改用 `raw.githubusercontent.com`
3. **分类阅读** — 按模块分：memory/retrieval、evolution、scheduler、formula

### Phase 2: 映射差距
1. **建表** — 每条模式列：`仓库实现 | 我方等价 | 差距严重度 (High/Med/Low) | 实现成本`
2. **诚实评级** — 文件存在 ≠ 可用。每次声称"已吸收"前必须 import 并运行
3. **三通道检查** — 读源码（不只看 README！）。Rust 项目的 `lib.rs` 只有模块树 — 真正代码在 `src/<module>/mod.rs`

### Phase 3: 实现
1. **优先高价值低风险** — 推荐先实现 Claude 建议的最高优先级
2. **每个实现自测** — terminal 运行 + 断言检查
3. **不修改原有 API** — 新功能作为通道/策略添加到旧类（如 akashic_memory 加 HybridRetriever）

### Phase 4: 交叉审计
1. 真实调用 GPT-5.5 + Claude Opus-4-7（Responses API，不走 chat/completions）
2. 提供结构化证据载荷（import结果、统计、检索样本）
3. 修复具体可修复的缺陷；不修无法操作的批评
4. 更新 SOUL.md §10 和 skill 状态表

### Phase 5: Audit-to-absorption gate

When an external repo has been cloned/deployed and audited for possible PGG Archon absorption, use the class-level gate in `references/external-repo-audit-to-absorption-gate.md`:

1. Local deploy and smoke test before audit.
2. Persist an `audit_reports/` evidence pack.
3. Call real GPT/Claude through Responses API with compact evidence; retry with smaller JSON if the provider disconnects on large payloads.
4. Classify findings as `READY`, `READY_WITH_REVIEW`, or `CANDIDATE`.
5. Run a read-only GeneLifecycle-style gate first; report `PARTIAL_ABSORB` when only some candidates are promotable.
6. Do not write GeneDB or claim ingestion unless the write and readback were actually performed.

### 关键陷阱
- Rust 项目含 Python 不兼容的依赖（tantivy、hnsw_rs、petgraph）— 找 Python 等价库（rank_bm25、TF-IDF+cosim、networkx）
- 代理网络阻断大包下载（sentence-transformers 79MB）— 标记 P0 待优化，不用 TF-IDF 冒充 dense vector
- 远程副本才创建几小时 — 模式可用但不能宣称"已实战验证"

### Phase 5: 缺口闭合式吸收（从审计到GitHub到修复）

当用户说"全量补齐"或"去github仓库全量学习补全"以修复审计缺口时，此模式代替Phase 1-4直接进入修复循环：

1. **固定缺口清单** — 从 cross-model audit 结果中提取具体可操作的缺口（每项带分数+描述）
2. **按缺口搜索 GitHub** — 不为"全量吸收"而吸收，为"解决缺口"而吸收。每项缺口对应一次 GitHub 搜索（例如找到 MLflow 的 safe_patch 模式解决了"不可绕过性45分"缺口）
3. **聚焦实现** — 每个缺口独立实现一个模块。模块之间正交（provider_monkeypatch.py 解决不可绕过性、audit_trail.py 解决审计、fail_closed.py 解决fail-closed）
4. **整合自动激活** — 新模块自动注册到 `auto_bootstrap.py`，import 时加载
5. **统一可见性** — 所有新模块通过 `health.py` 的统一 11 项检查暴露状态
6. **非全量不报告** — 直到所有固定缺口已实现且验证，才报告"完成"

### 跨模型审计协议补充：缺口闭合循环

当 cross-model audit 返回评分后，如果需要 GitHub 吸收来修复缺口：

1. 从审计中抽出具体分数+描述
2. 每个缺口对应一个搜索方向（如"不可绕过性45 → monkey-patch OpenAI SDK")
3. 按 super-evolution-20 skill 的"缺口闭合式吸收"模式实现
4. 重新调用 cross-model audit，看评分提升

## AGI 快速进化闭环纪律（PGG Archon 基础优先）

当用户授权“全力推动系统快速迭代到 AGI”或“连续推进进化”时，执行方式必须是任务驱动的可验证进化，而不是堆叠 AGI 口号：

1. **必须基于既有核心** — 新进化要优先接入已完成的 PGG Archon / APEX / Rust-native / Delta-G / ECC / evolution manifest / watcher / provider 配置；不得把孤立 demo 当作系统进化成果。
2. **最高 ROI 起点** — 建立或复用 `task → prediction → deterministic scoring → failed examples → evolution queue → verified patch` 闭环；失败样本必须进入后续修复队列。
3. **集成门禁** — 若先做了最小 harness，下一阶段必须把它接回既有核心：Rust `hermes_pgg_*` surfaces、`hermes_apex_evolution`、Delta-G、ECC、账本/总账、真实 provider。
4. **连续授权纪律** — 用户明确授权连续推进后，每阶段完成时若下一步必要性 >75%、低风险且可回滚，直接进入下一步；仍要保持边界、测试、提交、账本读回。
5. **工具预告** — 该用户要求每次工具调用前先用中文预告预计耗时；进化任务尤其要遵守。
6. **边界表达** — 始终标注内部工程验证 / pre-AGI / benchmark harness；不得称 full AGI、外部 AGI benchmark 通过、法律正确性证明。

See `references/agi-fast-path-pgg-integrated-benchmark-loop.md` for the 2026-06-03 Sprint1–Sprint3 pattern: benchmark harness → PGG integrated loop → provider-backed benchmark.
See `references/agi-fast-path-provider-health-gate.md` for the continuation pattern: real provider predictions → PGG scoring → provider ranking → health gate/routing recommendation, including the pitfall that continuous-evolution authorization requires executing the next necessary low-risk step rather than ending with “next step should be ...”.
See `references/failed-example-queue-to-proposal-worker-20260604.md` for the next fast-path pattern and correction: before implementation, first present a compact system-state panel (core/modules/Rust/self-evolution/runtime/git); then upgrade failed examples into replayable queue items and read-only repair proposals with CLI, tests, smoke, manifest readback and scoped commits.
See `references/agi-fast-path-replayable-queue-v2.md` for the failed-example queue v2 pattern: upgrade `evolution_queue_count` into replayable JSONL producer records plus a read-only prioritized consumer, while keeping auto-mutation behind verified patch/skill/gene gates.
See `references/autonomous-evolution-loop-pipeline-20260604.md` for the full no-agent autonomous pipeline pattern: verified state panel → multi-LLM formula audit → queue v2 → proposal → targeted regression → patch candidate → sandbox readiness → temp git worktree patch apply, with main worktree/GeneDB promotion still gated.
See `references/autonomous-queue-proposal-regression-patch-loop-20260604.md` for the formula-guided autonomous background loop pattern: deep audit first, call all configured LLMs with evidence, avoid duplicating Rust fused-watch/paused legacy cron, then close ΣΔ_all rungs as queue→proposal→targeted regression→read-only patch candidate with no-agent cron, state/ledger, tests, smoke, manifest readback and scoped commits.
See `references/autonomous-evolution-promoted-gene-pipeline-20260604.md` for the promoted-gene autonomous pipeline pattern: queue v2→proposal→targeted regression→patch candidate→sandbox readiness→temp worktree patch→promotion readiness package→gated main patch/GeneDB candidate/promotion, including LLM quorum, fixture merge/upsert, reusable promotion transaction, manifest layered-state, and read-only dashboard pitfalls.
See `references/controlled-agi-roadmap-and-terminal-output-20260604.md` for the controlled AGI roadmap discipline: one component per round, anti-disruption gates, P0→P4 sequencing, compact terminal status-block output preferred by the user, and the concrete P0 producer / P1 main patch gate / P2 LLM quorum gate / P3 event ledger acceptance patterns.
See `references/controlled-agi-roadmap-v2-event-review-bundle-20260604.md` for the V2 continuation pattern: autonomous loop event emission, dashboard event summary, cron/event audit, review bundle gate, and P4 as blocker-triggered open-source absorption only.
See `references/controlled-agi-roadmap-v3-main-patch-dry-run-20260604.md` for the V3 continuation pattern: review bundle → main patch dry-run simulator using `git apply --check`, worktree-status invariance, fixture diff pitfalls, and the next approval-token/transaction/rollback sequence.
See `references/controlled-agi-roadmap-v3-approval-transaction-rollback-20260604.md` for the closed V3-P1→V3-P3 pattern: human approval token bound to exact dry-run evidence/current repo head, prepare-only transaction + rollback package gate, temporary worktree apply/verify/reverse-apply rollback, and the pitfall that minimal test repos may not contain production `agent/` modules.

### Controlled roadmap anti-disruption rule

When the user asks to strictly follow the AGI plan and avoid disruptive/destructive flows, treat the roadmap as a hard sequence. Before each stage read dashboard/manifest/git status; advance exactly one component; if a command fails, decompose the validation chain and fix the blocker; do not enter the next component until tests, real smoke, manifest/report and scoped commit are complete. Prefer compact terminal status blocks over wide tables for this user. Never auto-apply main patches, write GeneDB promotions, replace launchd/Rust watcher, edit scheduler/security boundaries, restore overlays, or claim full AGI unless a separate explicit gate authorizes the specific action.

## EVOLUTION_MANIFEST — 单一真相来源

每次进化（技能学习、能力吸收、规则落地、bug修复、审计更新）都必须更新 `EVOLUTION_MANIFEST.json`：

- **位置**: `~/.hermes/data/EVOLUTION_MANIFEST.json`
- **更新命令**: `python -m se20.evolution_manifest --update`
- **查看命令**: `cat ~/.hermes/data/EVOLUTION_MANIFEST.json`
- **覆盖范围**: 组件(21+)/规则(8)/能力域(8)/里程碑(15+)/5D评分/审计历史

**纪律**：
1. 每完成一个可独立验证的进化成果，立即 `--update`
2. 新会话/新渠道最先执行 `cat` 获取全貌
3. 审计评分变更必须记录到审计历史数组
4. 5D 评分（Autonomy/Evolution/Growth/Decision/Harmony）每次测量后更新
5. 多对话框/多渠道同时推进进化时，`EVOLUTION_MANIFEST` 是仲裁者——不是辅助文件
6. **不这样做**会导致跨渠道状态不一致、同一成果被重复构建

## Related skills

## Reference

Full governance notes archived at `references/full-skill-archive-20260601.md`.
- `references/state-db-corruption-recovery.md` — state.db SQLite corruption detection, one-shot recovery, and cron-side auto-repair.
- `references/state-db-optimization.md` — state.db schema, indexes (11 total, COVERING), PRAGMAs (busy_timeout, foreign_keys, cache_size), WAL checkpointing, incremental vacuum, query plan verification, and connection-level setup guide.
- `references/external-repo-absorption-apex-mem-patterns.md` — 2026-06-01 APEX-MEM + nanoGPT-claw 全量吸收记录：三重检索、5D Memory、Auto-Fix 闭合回路、Dreaming、Flush。
- `references/agi-task-benchmark-harness-pattern.md` — AGI 快速进化的最高 ROI 第一步：task → prediction → deterministic scoring → failed examples → evolution queue → verified patch。
- `references/external-repo-audit-to-absorption-gate.md` — 外部仓库部署→本地扫描→GPT Responses API 审计→PGG Archon 部分吸收门禁的实战流程；含 READY / READY_WITH_REVIEW / CANDIDATE 分级。
