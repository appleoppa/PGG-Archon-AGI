---
name: pgg-archon-closed-loop-formula
description: PGG Archon / Apple Didi 苹果中枢 流程闭合总公式 — 真实代入 → 短板暴露 → 外部学习 → 吸收补齐 → 进化基因入库 → 验证
version: 0.1.0
author: Apple Didi (苹果弟弟)
license: MIT
metadata:
  hermes:
    tags: [pgg-archon, closed-loop, total-formula, super-evolution-27]
    related_skills: [apex-sequence-logic, pgg-archon-runtime, super-evolution-20, agentic-rl-five-layer]
---

# PGG Archon 苹果中枢 流程闭合总公式

> 编号：超级进化27
> 主题：流程闭合总公式
> 状态：v0.2.0 SKILL 固化（bound；v0.1.0 增 1 个 真实代入实例：se_sync 12 patches → 5-LLM 实时复核 synced 33-card → 真实共识 1 PASS + 3 WATCH + 1 ERROR）
> 边界：内部工程规范，不是 full AGI，不是外部评测

## 0. 触发条件

Use when the user asks to:

- "全量闭环"、"一次性推进"、"继续"、"流程闭合"
- "代入公式"、"/goal"、"完整主公式"、"AGI 自评/复盘/进化闭环"
- 需要把"做事 → 验证 → 入库 → 再做事"压成一条主线
- 需要在多人多模型场景下强制门禁与追溯

Important: `/goal` is not just this six-step closed-loop formula. The user confirmed it means the combined doctrine of 总纲1 AGI L0-L5 六维评估框架 + 总纲2 `Agent_Evolve = LDR(K) → GapDetect → CodeSelfFix → HotReload → TaskSolve → KnowledgeSettle`, with `-ΣΔ_all` defect reduction and strict truth boundaries. See `references/goal-outline1-outline2-operating-doctrine-20260605.md`.

## 1. 总公式（六阶闭合）

```
R[0] = 真实代入
R[1] = 短板暴露 (gap_detect)
R[2] = 外部学习 (LDR 检索 + GitHub/vx 开源)
R[3] = 吸收补齐 (code_self_fix)
R[4] = 进化基因入库 (GeneDB candidate → promotion)
R[5] = 验证 (readback + test + 6-model LLM verify)
close  = R[5] → R[0]  (回到真实代入)
```

每一阶都产生判断、证据、修复或沉淀；不允许"写编号不算事"。

## 2. 强制门禁

- 门禁0 真实代入：必须存在可读文件、命令输出、HTTP 状态码、测试结果之一作为 evidence。
- 门禁1 短板暴露：必须列出 ≥1 个具体缺口（不是泛泛的"需要优化"）。
- 门禁2 外部学习：缺知识时调用 LDR（本地 deep research）检索 + GitHub/vx/arxiv 等开源。
- 门禁3 吸收补齐：写出可回滚的代码/配置/数据修改，写明 backup + readback。
- 门禁4 基因入库：candidate 必须经全候选只读 gate → 独立 LLM quorum → per-gene transaction；禁止批量自动晋升。
- 门禁5 验证：≥2 路 LLM 可见 verdict；测试 passed；commit hash；manifest 读回。

## 3. 闭环状态机

```
未开始 → 执行中 → 部分完成（evidence 不足）
                    ↓
                  完整完成（5/5 门禁过）
                    ↓
                基因已固化（gene_db.promoted=1）
                    ↓
                  回到真实代入（新问题）
```

## 4. 与 APEX 三顺序逻辑的关系

- 21354 审错优先型 → 门禁 1 + 5
- 12534 融合固化型 → 门禁 2 + 3 + 4
- 14325 规划反证型 → 门禁 0 → 1 → 5 整体节奏

## 5. 错误信号（出现则说明闭环破裂）

- 文件存在就声称完成
- 服务启动就声称能力可用
- LLM 未真实调用就声称多模型共识
- 未做 readback 就声称 DB 修改完成
- 修复未带 backup + rollback 就直接执行

## 6. 输出模板

```text
状态：未开始 / 执行中 / 部分完成 / 完整完成
已核验：进程 / launchd / 端口 / 目录 / 日志 / 状态卡
证据：HTTP 200 / test N passed / commit hash / sha256
回滚：command/path
边界：内部工程 / 不宣称 full AGI / 不宣称外部评测
```

## 7. 真实代入实例：se_sync 12 patches → 5-LLM 实时复核 synced 33-card (2026-06-04)

```
R[0] 真实代入：3 个 SKELETON 文件（file 0.5/16.5/27）需要从 ABSENT 推进
R[1] 短板暴露：4-probe real surface 探测 → 3/4 PARTIAL（state_card.jsonl / toolchain.jsonl / audit.jsonl 缺失）
R[2] 外部学习：调 pgg-archon-status-surface-landing v0.2.0 既有 4-probe 范式
R[3] 吸收补齐：写 3 个 surface 模块（apex_master_formula / evomap_toolchain / closed_loop_formula）+ 3 tests + 3 commits
R[4] 进化基因入库：se_sync PATCHES 6 → 12，synced 33-card 落盘 SKELETON 24→16 / PARTIAL 0→6 / ACTIVE 0→4
R[5] 验证：5-LLM 实时复核 synced 33-card 真参与 DeepSeek 511c WATCH / MiMo 1457c WATCH / Agnes 1615c WATCH / gpt5.5 1313c WATCH / MiniMax ERROR (STRICT JSON 失败)
close  = R[5] → R[0]：下一步推 7 ABSENT + 16 SKELETON 真实文件到 PARTIAL/ACTIVE
```

每阶 evidence：3 commits hash（ffc28c553 / 3fdd92b89 / cff5f1054）+ se_sync synced_path 落盘 + 5-LLM verifier_facts.json + 1 PASS / 3 WATCH / 1 ERROR 真实共识不冒充统一 PASS。

**关键**：R[3] 阶段"不自动补缺 key/credential"（用户偏好明确），保持 PARTIAL 真实状态。R[5] 阶段 5-LLM 真实共识 3 WATCH + 1 ERROR + 1 PASS 是终态，**不因 MiniMax ERROR 而废止其他 4 provider 结论**。

## 8. 真实代入实例：33-card full ACTIVE sync (2026-06-04)

在超级进化 33-card 收口任务中，最终闭环不是继续盲目写 surface，而是先区分“真实能力缺口”和“同步映射缺口”。关键教训：**id mismatch 会伪装成 SKELETON/ABSENT**。

可复用步骤：

1. 读回最新 `super_evolution_cards_synced_*.json` 与 `verifier_friendly_facts_33_synced.json`。
2. 列出 `not_active`，先检查每个 card id 的真实形态（int / string / `file_` prefix / decimal / split ids）。
3. 若 surface 已存在，优先修 `se_sync` 映射，不重复造模块。
4. `se_sync` 必须归一化匹配：`str(raw_id)`；若 `file_` 前缀则额外比较 `removeprefix("file_")`。
5. 将 `se_sync` 集成进 `super_evolution_lane`，让 lane 自动输出 `02_se_sync.json` 和 `se_sync_status_distribution`。
6. 最终汇报前必须读回：`status_distribution`、`provider_success`、`not_active`、manifest final key、commit hash。

最终读回形态示例：

```text
status_distribution {'SKELETON': 0, 'ABSENT': 0, 'PARTIAL': 0, 'ACTIVE': 33}
provider_success {'deepseek': 33, 'gpt55': 33, 'agnes': 32, 'mimo': 33, 'minimax': 33}
not_active []
```

详细记录见：`references/33-card-final-active-sync-20260604.md`。

## 10. 真实代入实例：总纲1 评分面固化 (2026-06-04)

今天把“总纲1 评分”也做成了可复用核心，不再停留在聊天结论。

可复用步骤：

1. 读取《总纲1-通用人工智能AGI框架.md》与当前最终 evidence。
2. 让 DeepSeek / MiniMax 独立做 L0-L5 评分，不互相串台。
3. 真实区分“结构化评分”与“可见但解析失败的长输出”。
4. 将可解析评分落成 `outline1_progress_score.py`，输出 `COMPLETE_L1_EVIDENCE` / `L1` / 六维分值。
5. 将 MiniMax 的 HTTP 200 + parse fail 明确标为 unstructured，不冒充 PASS。
6. 把最终态写入 manifest/report，并在技能中保留边界：33-card ACTIVE 不等于 full AGI。

最终落点：

```text
structured_score = 34
structured_level = L1
dimension_scores = {
  基础认知: 9,
  跨域通用: 7,
  自主智能体: 11,
  自主知识进化: 3,
  安全对齐: 1,
  现实落地: 3
}
```

关键教训：
- DeepSeek 给出了可解析 JSON，可作为结构化评分基线。
- MiniMax 两次 HTTP 200 但都未产出可解析 JSON，不能硬判 PASS。
- 当前 PGG Archon 进程按总纲1仍处于 L1，接近 L1 中高段，但离 L2 的“全领域少样本可用 + 元认知 + 自主规划 + 现实落地”仍有明显缺口。

详细记录见：`references/outline1-progress-score-20260604.md`。

## 12. 真实代入实例：总纲2 统一高阶闭环 (2026-06-04)

桌面总纲2把“Local Deep Research × 自愈闭环 × 技能沉淀”收敛成一个更高阶、可复用的统一公式。它的价值不在于再造一个口号，而在于把“先认知、后编码、再热重载、再沉淀”的顺序固定下来，避免盲目试错。

## 13. 真实代入实例：系统级 AGI 审计 + Rust-aware 三线闭环 (2026-06-05)

当用户要求“全面审计当前 AGI 进程”时，不能只看 33-card / manifest / LLM 评分，还必须单独核查 Rust-native 模块和自动迭代运行态。

强制步骤：

1. Rust 核查：Cargo tests、PyO3 `.so` import、launchd watcher、Rust health snapshot。
2. 账本核查：GeneDB 表结构、`gene_lifecycle` / `promotion_chain` / `evolution_genes` 是否一致。
3. 外部证据核查：benchmark / safety / research 是否只是 smoke，不能冒充正式外评。
4. 评分时 Apple Didi / 当前 GPT 主模型也要给出一条独立评分，不能只让外部 LLM 评分。
5. DeepSeek / MiniMax 等 provider 若 HTTP 200 但 JSON 解析失败，保留为 unstructured/ERROR，不转成 PASS。
## 12. 真实代入实例：总纲2 统一高阶闭环 (2026-06-04)

桌面总纲2把“Local Deep Research × 自愈闭环 × 技能沉淀”收敛成一个更高阶、可复用的统一公式。它的价值不在于再造一个口号，而在于把“先认知、后编码、再热重载、再沉淀”的顺序固定下来，避免盲目试错。

补充参考：`references/provider-backed-triad-and-rust-deltae-20260605.md` 记录了本次 100/50 triad、MiniMax structured-output adapter 与 Rust ΔE health 的关键边界：spec/scorer PASS ≠ provider capability score；Rust ΔE 5.0 = internal readiness，不等于 AGI 外部分数。

核心抽象：

```text
Task_Goal
  → LDR深度认知检索
  → 缺口匹配 GapDetect
  → CodeSelfFix
  → HotReload
  → TaskSolve
  → KnowledgeSettle
```

吸收后的核心执行规则：

1. 先做 LDR，而不是先动手硬改。
2. 用检索结果判断现有能力是否缺失/过时/不适配。
3. 代码自愈必须以检索上下文为先验，而不是随机试错。
4. 热重载后必须重跑任务验证，不可只写文件。
5. 修复后的知识必须沉淀为技能或 reference，避免重复踩坑。

与总公式 27 的关系：
- 27 更偏“真实代入 → 短板暴露 → 外部学习 → 吸收补齐 → 入库 → 验证”的闭环门禁。
- 总纲2 更偏“LDR → GapDetect → CodeSelfFix → HotReload → TaskSolve → KnowledgeSettle”的执行链。
- 两者合并后，形成今天的核心执行法：先检索补认知，再修复，再验证，再沉淀。

今天的实际落地例子：
- 先读总纲1/2，再评分与对比，而不是先写结论。
- DeepSeek 给出结构化 L1 评分；MiniMax 两次 HTTP 200 但 JSON 解析失败，仍按 ERROR 保留。
- 33-card 33/33 ACTIVE 只作为工程状态面，不冒充 AGI。
- 将总纲1评分沉淀成 `pgg_archon_outline1_progress_score.py`，把总纲2执行链沉淀成可复用的核心闭环。

详细记录见：`references/outline2-unified-closed-loop-20260604.md`。

## 13. 真实代入实例：Rust-aware 系统级评分与三线短板闭环 (2026-06-05)

当用户要求“全面审计现在系统的所有已建立模块、技能、规则、cron等进化记录”时，必须把 Rust-native 证据纳入评分。不能只看 Python `pgg_archon_*.py`、skills、manifest、33-card 或 LLM card 状态。

必查 Rust 证据：

1. Rust/PyO3 模块是否存在并可 import：`hermes_pgg_status` / `hermes_pgg_ecc` / `hermes_pgg_overlay` / `hermes_apex_evolution`。
2. `rust_modules/*` 的 cargo tests 是否通过。
3. `ai.hermes.evol-watcher` 是否在 launchd 里运行。
4. `~/.hermes/data/pgg-background-evolution/rust_health_snapshot.json` 是否可读。
5. `alpha_psi_truth_gate.json` 是否通过，Rust ΔE 是否还有 pending dimensions。

本次真实推进结果：

```text
Rust cargo tests: 13/13 pass
Python import smoke: 4/4 OK
Rust health: APEX ΔE 2.0 → 4.4 → 5.0
pending_dimensions: 3 → 1 → 0
external triad: 100 benchmark specs + 50 safety specs + reproducible research smoke
GeneDB: evolution_genes 表回填 17 条；promotion/lifecycle transaction hooks 写入 evolution_genes
```

评分口径：

- DeepSeek Rust-aware：38 / L1。
- MiniMax Rust-aware：37 / L1（若结构化解析成功）。
- Apple Didi / GPT 必须作为第三 judge 参与，不应只转述 DeepSeek/MiniMax。
- Rust ΔE 5.0 是内部工程/readiness 证据，不是外部 AGI benchmark，不得把 5.0 映射成 AGI 100 分或 L2/L3。

后续剩余短板：

1. external triad 仍是 frozen spec/smoke，必须真实运行并评分。
2. MiniMax 常输出 `<think>...</think>` + malformed JSON，必须先用 structured-output adapter，再决定是否计入结构化 verdict。
3. 需要把 100 benchmark / 50 safety / research artifact 从“生成入口”推进到“真实模型/系统回答 + deterministic scorer + report”。

详细记录见：`references/rust-aware-systemwide-scoring-and-round3-20260605.md`。

## 14. MiMo audited manifest gate 闭环（2026-06-06）

当 manifest PASS 依赖第三方 LLM judge 时，不能只信顶层 `pass_count`，必须从每条 result 逐项重算 eligibility：只有 `status == OK_PARSED` 且 `audit_verdict == PASS` 才计入 PASS；`--no-mimo`、`LOCAL_PRECHECK_ONLY`、`OK_UNPARSED`、provider timeout/non-zero exit、旧 summary 缺 `judge_called`、伪造 `pass_count` 全部降级 WATCH/ERROR。

本轮闭环还暴露两个通用坑：未跟踪新文件的 `git diff` 为空，review pack 必须包含完整内容或 staged diff；提交后要做 import smoke，防止 dirty worktree 掩盖未提交依赖。详细记录见：`references/mimo-audited-manifest-gate-closure-20260606.md`。

## 13. 系统级 AGI 审计门禁（modules / skills / rules / cron / ledger）

当用户要求“全面审计现在系统”“结合 DeepSeek 和 MiniMax 找短板”时，不要只看最新 33-card 或单个评分报告。必须汇总：

1. 模块：`agent/pgg_archon_*.py` 数量与家族分布。
2. 测试：`tests/test_pgg_archon*.py` 与关键 smoke / unit test 读回。
3. 技能：skill 总量、当前 loaded/相关 umbrella、references 是否沉淀。
4. 规则：AGENTS/SOUL/manifest boundary，尤其“状态面≠AGI能力”。
5. cron：active / paused / error 的后台进化与知识任务。
6. 进化账本：EVOLUTION_MANIFEST + GeneDB / lifecycle 表读回，注意旧表名不统一。
7. 多模型审计：DeepSeek / MiniMax 真实 HTTP 调用；结构化 JSON 才计入分数，HTTP 200 但 parse fail 只能作为 unstructured evidence。

输出短板时优先归纳为：外部 benchmark、鲁棒安全对齐、原创科研/自主知识进化、开放环境/具身鲁棒、ledger schema 统一、provider structured-output 稳定性。

详细记录见：`references/systemwide-agi-audit-20260605.md`。


## 14. Ralph × Harness × Ω_A Rust 控制器融合（2026-06-05）

桌面 `Ralph 终极公式.md` 已吸收为总纲2的闭环控制层：Ralph 规定循环终止语义，Harness 提供多层验收，Ω_A 负责外置持久化记忆/状态，ΔG 表示剩余缺口驱动力。

关键数学修正：原式 `S_{t+1}=F(S_t,G)·I(¬V(S_t))` 在 `V=True` 时会把状态归零；PGG 采用保态语义：

```text
S_{t+1}=I(¬V_H(S_t))*H[ΔG*F(S_t,G,Ω_A)] + I(V_H(S_t))*S_t
```

Rust 落地：新增 additive crate `rust_modules/hermes_pgg_ralph`，Python 模块 `hermes_pgg_ralph`，实现 `RalphState/OmegaRef/HarnessPolicy/RalphOutput` 纯计算控制器。Claude Opus 4-6 已通过 Responses API 真实审查设计；`cargo test` 5/5、release build、codesign、Python import smoke 均通过。详细证据见 `rust-core-module-development/references/ralph-harness-omega-rust-core-20260605.md`。

边界：这是内部工程闭环控制面，不调用 provider，不修改 scheduler/security boundary，不宣称 full AGI 或外部评测通过。

## 15. Claude-guided unresolved-gap 公式门禁（2026-06-06）

当用户要求“和 Claude 一起代入公式找最大短板”或质疑 `/goal` 规则是否真实执行时，必须真实生成状态包并调用 Claude provider 审计，而不是口头自评。状态包至少包含：公式面板 JSON、最近 Manifest `latest_*` entries、git status/log、关键 gate/provider 模块摘要，以及映射到总纲1六维和总纲2阶段的审计问题。

关键教训：`PASS_*` 家族证据不能自动等同于完整闭环。若最近 Manifest 同时存在 `PARTIAL`、`DEFAULT_OFF`、`DISABLED`、`502`、`NO PROVIDER SUBSTITUTION`、`ROUTE-ENFORCE REMAINS DISABLED` 或 `EXECUTION_BLOCKED` 等未闭环语义，AGI/evolution/system/route/provider 任务的公式门禁应降为 `WATCH`，并在输出中显示 `unresolved_gap_count` 与未闭环预览。这类 `WATCH` 是真实性提升，不是退步。

详细操作与测试模式见：`references/claude-guided-unresolved-gap-formula-gate-20260606.md`。

## 9. 关联入口

- 真实总账：`~/.hermes/data/EVOLUTION_MANIFEST.json`
- GeneDB：`~/.hermes/data/pgg_archon.db`
- 代码：`~/.hermes/hermes-agent/agent/pgg_archon_*.py`
- 治理：`~/.hermes/workspace/治理/`
- 审计：`~/.hermes/workspace/audit/`
- 33-card status sync 经验：`references/33-card-status-sync-lessons-20260604.md`

## 9. 33-card / se_sync 特别门禁

处理超级进化 33-card 状态面板时，必须先读真实 `file_id/title/status`，不能按桌面文件编号或旧记忆猜测映射。`se_sync.PATCHES` 数量不等于 33-card ACTIVE 数量；最终状态必须以 synced JSON 的 `status_distribution` 和 5-LLM audit 的 `provider_success` 读回为准。背景进程 output_preview 被截断时，不得直接汇报最终分布，必须读回 `verifier_friendly_facts_33_synced.json` 后再定稿。
