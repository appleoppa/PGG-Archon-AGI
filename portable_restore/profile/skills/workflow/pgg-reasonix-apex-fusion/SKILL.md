---
name: pgg-reasonix-apex-fusion
description: CORE SKILL（核心技能）：PGG Archon 融合 DeepSeek-Reasonix 与 APEX-SKILL 的 Rust-owned additive capability（附加能力）入口；用于进化/AGI/Rust融合类任务的默认核心门禁，生成并验证融合 manifest，不修改 Hermes 核心调度/安全边界。
version: 1.1.0
author: 苹果中枢
license: MIT
metadata:
  hermes:
    tags: [pgg-archon, reasonix, apex-skill, rust, fusion, external-repo-absorption]
    related_skills: [pgg-archon-external-repo-absorption, rust-core-module-development, super-evolution-20]
---

# pgg-reasonix-apex-fusion

## Active run_conversation notes

- For `agent/conversation_loop.py::run_conversation` RC-S02 pre-provider/pre-tool helper extraction, use the detailed addendum `references/run-conversation-rc-s02-preprovider-extraction-notes.md` in addition to the main RC characterization workflow. It captures the drift-safe slicer/readiness-matrix pattern and the pre-API `/steer` drain helper test bundle.

> Recent run-conversation governance note: for RC-S02 pre-loop extraction, load `references/run-conversation-rc02-pre-loop-extraction-20260602.md` before continuing beyond RC-S01 helpers. It records the >75% direct-continuation workflow, plugin/memory pre-provider extraction pattern, slicer window-drift pitfall, and required contract/health/Manifest gates.

> PilotDeck/第二 AGI 配置优先门禁：若 UI、Service Config、配置 YAML、启动路径或认证导致无法操作，必须先完成配置与浏览器读回验证，再推进进化/融合；详见 `references/pilotdeck-config-preflight.md`。

## Session-derived runbook additions
- `run_conversation` 大函数进化/抽取任务：先建立 RC characterization contracts（特征契约）和 extraction readiness matrix（抽取就绪矩阵），再移动代码；先从 small mechanical helper（小型机械辅助函数）开始，用户要求“步子大一点”时可升级为 RC-S01 stage helper（阶段辅助函数），但必须保持 no behavior change（无行为变化）并单独提交。
- 跨会话继续前必须先核对 branch/HEAD/worktree（分支/提交/工作区）；若 handoff 指定治理分支而当前在 `main`，且工作区干净，应先切回目标分支再判断 readiness。`agent.pgg_archon_run_conversation_slicer` import 失败时优先排查 wrong-branch，而不是把它当成代码/venv 故障。
- 验证门禁：targeted pytest、py_compile、`git diff --check`、`venv/bin/python -m apex_god.health`、`venv/bin/python -m apex_god.evolution_manifest --update`、报告、focused commit（只 stage 本轮文件）。
- 插入 helper/stage helper 后，AST window（抽象语法树窗口）不要依赖绝对行号或固定 500 行窗口；应相对 `run_conversation` 起始位置、稳定 AST anchor（锚点）以及 all-function/helper AST signal surface（全函数/辅助函数 AST 信号面）定位，避免行号/窗口漂移导致 false WATCH/FAIL。不要降低 contract gate（契约门禁），要修正锚定；详细续接坑位见 `references/run-conversation-continuation-branch-and-window-drift-20260603.md`。
- Stage helper 详细模式见 `references/run-conversation-stage-helper-extraction.md`。
- 多模型推进时按用户偏好：GPT + Claude 共审，MIMO 做 third-party audit（第三方审计），只记录 redacted evidence（脱敏证据）与 hash（哈希）。
- 详细 runbook：`references/run-conversation-rc-characterization-extraction.md`。

## 核心大函数进化补充

- `run_conversation`（核心会话循环）等核心大函数进化/抽取任务：先读取 `references/run-conversation-evolution-gates.md`，按 read-only characterization contract（只读特征契约）→ extraction readiness matrix（抽取就绪矩阵）→ 最小可回滚抽取 的顺序推进。
- 严禁未建门禁就直接重构核心循环；LLM 审计只能辅助，最终以源码读回、测试、health、Manifest、提交证据为准。

## Context System Audit

When the user asks to "audit context system" / "analyze context completeness" / "调用所有LLM代入公式分析上下文", load `references/context-system-audit-runbook-20260603.md` first. It contains the full end-to-end runbook: core file inventory, test suites, formula computation with real signal values, multi-LLM API calling patterns (DeepSeek/MIMO/GPT-5.5 with correct endpoints), config optimization baselines, and compressor/memory implementation details.

## Session references

- `references/codegenesis-scanner-diagnostics.md` — CodeGenesis scanner / quality-gate diagnostics pattern: avoid truncation-induced false SyntaxError, expose actionable samples, filter low-information duplicate lines, use directory-level test coverage estimates, and close with tests/health/manifest/commit.
- `references/run-conversation-readonly-contract-gates-20260602.md` — Read-only AST characterization contract gates for high-risk `run_conversation` slices before any extraction/refactor; includes multi-LLM direction confirmation and verification close pattern.
- `references/2026-06-02-run-conversation-contract-gates.md` — Read-only contract gate pattern for very large Hermes core-loop refactor readiness: AST window facts, contract booleans, real-source tests, multi-LLM evidence, and no direct mutation until gates pass.

## Operational workflow updates

### Continuation discipline for AGI optimization loops

When the user says “继续” or complains “怎么停了” during a PGG Archon/AGI optimization loop, do not stop at a partial status update. If the next step is low-risk, reversible, and scores above the user’s >75 threshold, continue through edit → targeted tests → health check → `EVOLUTION_MANIFEST` update → scoped commit → concise evidence report. Reply only after the loop is genuinely closed.

### Gate output schema discipline

Keep automation summaries separate from full manifests:

- `self_evolution_token_gate_latest.json` = compact gate summary for downstream consumers.
- `fusion_manifest_latest.json` = full Rust Reasonix/APEX fusion manifest.
- Use a deterministic verifier such as `scripts/verify_gate_outputs.py` after each gate run to prevent schema regression.
- For GPT + Claude + MIMO推进核心路径、大函数或重构前安全网， use `references/multimodel-characterization-contract-gate.md`: real model calls first, then implement a read-only characterization contract（特征契约）/ trace gate（轨迹门禁） rather than stopping at advice or directly rewriting high-risk core code.

### CodeGenesis WATCH triage

If CodeGenesis scanning reports WATCH, improve/read diagnostics before touching core files. Prefer fields such as `parse_error_samples` and `top_duplicate_lines` so the report names exact files, line numbers, duplicate samples, and hashes. Only after read-only localization should core files like gateway/CLI modules be considered for edits.

References:

- `references/2026-06-02-token-gate-codegenesis-diagnostics.md`
- `references/2026-06-02-codegenesis-truncation-and-watch-triage.md` — CodeGenesis WATCH triage pattern: verify scanner-reported syntax errors with `py_compile` before editing core files; scanner truncation can cause false SyntaxError on large valid files; filter low-information syntax shell lines before treating duplication as a blocker.
- `references/2026-06-02-all-llm-run-conversation-contract-gates.md` — 全 LLM 推进核心大函数治理模式：真实调用 GPT/Claude/DeepSeek/MIMO 留 status/path/hash，遇到 `run_conversation` 等高风险热点先做 read-only characterization contract（只读特征契约）/ trace gate（轨迹门禁），不要直接重构。

## Core Status

苹果哥已指定本 skill（技能）为苹果中枢核心技能之一。

默认加载条件：

- PGG Archon / AGI / 进化 / 超级进化任务。
- Rust-owned capability（Rust 拥有能力）融合或替换 Python 能力的任务。
- DeepSeek-Reasonix、APEX-SKILL、Reasonix config（配置）、skill contract（技能契约）、manifest（清单）相关任务。
- 多 LLM audit（多大模型审计）、provider/model routing（模型路由）、sandbox/permission（沙箱/权限）治理任务。

核心纪律：

1. 先读回本地 manifest（清单）与 repo HEAD，不凭记忆硬接。
2. 优先调用 Rust fusion crate 生成证据，而不是只写说明。
3. 保持 additive capability（附加能力）边界；不得宣称已替换 Hermes core scheduler（核心调度器）或 security boundary（安全边界）。
4. 进化/AGI 类任务必须真实调用可用 LLM（大模型）审计并记录 provider/model/status/path/hash。
5. 完成后更新 EVOLUTION_MANIFEST。

## Trigger

当用户要求把 DeepSeek-Reasonix、APEX-SKILL、Rust agent（智能体）能力融合进 PGG Archon / Hermes 时使用。

## 当前本机实现

- DeepSeek-Reasonix：`/Users/appleoppa/.hermes/workspace/github/external/esengine/DeepSeek-Reasonix`
- APEX-SKILL：`/Users/appleoppa/.hermes/workspace/github/external/hernandez42/APEX-SKILL`
- Rust fusion crate：`/Users/appleoppa/.hermes/workspace/进化/rust/pgg_reasonix_apex`
- 证据目录：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602`

## Boundary

- 这是 Rust-owned additive capability（Rust 拥有的附加能力），不是 Hermes core scheduler（核心调度器）替换。
- 不复制 secrets（密钥）；provider key（供应商密钥）只从环境变量读取。
- 不启用未经审查的 browser/network/plugin 自动执行。
- 不宣称 full AGI、无监督接管、零风险或核心已被 Rust 全替换。

## Workflow

1. 固定两个外部 repo 的 HEAD、测试结果和许可证。
2. 运行所有可用 LLM audit（审计），至少记录 provider/model/status/path/hash。
3. 运行 Reasonix 测试：`make test`。
4. 运行 APEX-SKILL 测试：`/usr/bin/python3 -m pytest tests/ -q`。
5. 运行 Rust 测试：`cargo test`。
6. 生成 fusion manifest：

### run_conversation characterization before extraction

When evolving or auditing `agent/conversation_loop.py::run_conversation`, do not start by directly refactoring the monolithic loop. First establish read-only characterization gates: AST window facts, contract fields, real-source tests, multi-LLM evidence when available, health checks, and Evolution Manifest updates. See `references/run-conversation-readonly-contract-gates.md`.

### Activation Sequence Discipline

When activating new components/modules as part of fusion evolution work:

1. **One at a time**: Activate exactly one component per round
2. **Debug smooth**: Run tests → verify system load/health → confirm no regression
3. **Compatibility check**: After activation, verify existing tests still pass and system load is stable
4. **Commit close**: Code + tests + integration + manifest update — fully close the component
5. **Then next**: Only proceed to the next component after the current one is fully closed

See `continuous-auto-iteration-limit` skill → `references/activation-sequence-example-20260602.md` for a concrete example.

```bash
/Users/appleoppa/.hermes/workspace/进化/rust/pgg_reasonix_apex/target/debug/pgg_reasonix_apex \
  /Users/appleoppa/.hermes/workspace/github/external/esengine/DeepSeek-Reasonix \
  /Users/appleoppa/.hermes/workspace/github/external/hernandez42/APEX-SKILL
```

7. 验证 manifest：
   - `schema = PGGArchonReasonixApexFusionManifest/v1`
   - `rust_owned = true`
   - `hermes_core_mutation = false`
   - `readiness_score >= 75`

## AIS Kernel Layer

本 skill（技能）的最佳内核组成部分已加入 AIS / Artificial Immune System（人工免疫系统）Rust optimizer（优化器）。

本机位置：

- Rust crate：`/Users/appleoppa/.hermes/workspace/进化/rust/pgg_reasonix_apex`
- AIS manifest：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/ais_kernel_manifest.json`
- AIS report：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/AIS_Rust_Kernel升级报告.md`

当前读回指标：

- `schema = PGGArchonAISKernel/v1`
- `mode = artificial-immune-system-core-optimizer`
- `immune_score = 95.5`
- `antigens = 4`
- `antibodies = 4`
- `hermes_core_mutation = false`

默认用于识别并阻断：

- 未授权 core scheduler/security boundary mutation（核心调度/安全边界突变）。
- secrets leak（密钥泄露）。
- unverified completion claim（未验证完成声明）。
- skill contract gap（技能契约缺口）。

## Token Optimization Kernel

本 skill 已加入 Rust Token Optimization Kernel（Token 优化内核），用于节约 LLM token（大模型上下文成本）并优化自进化流程。

本机输出：

- Token manifest：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/token_optimization_manifest.json`
- Token report：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/Token_Kernel可用性验证报告.md`

当前读回指标：

- `schema = PGGArchonTokenOptimizationKernel/v1`
- `estimated_raw_tokens = 2249`
- `estimated_compact_tokens = 500`
- `estimated_token_saving_ratio = 0.778`
- `cargo test = 4 passed`

Lossless benchmark（无损性基准）已加入：

- `schema = PGGArchonTokenLosslessBenchmark/v1`
- `benchmark_pass = true`
- `average_saving_ratio = 0.582`（10 样本扩展验证）
- `average_field_recall = 1.0`
- 原 3 场景：external_repo_absorption / legal_case_gate / self_evolution_gate 全部 PASS。
- 扩展 10 场景：external_repo_absorption / legal_case_gate / self_evolution_gate / rust_build_gate / multi_llm_audit_gate / secret_boundary_gate / desktop_output_gate / workspace_file_governance / reasonix_permission_gate / token_budget_gate 全部 PASS。
- 报告：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/Token_Lossless_Benchmark报告.md`
- 10 样本报告：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/Expanded_Token_Gate_10_Cases报告.md`

Semantic drift check（语义漂移检查）已加入：

- `schema = PGGArchonSemanticDriftCheck/v1`
- `semantic_pass = true`
- `average_overlap_ratio = 1.0`
- `drift_flags = []`
- 场景：external_repo_absorption / legal_case_gate / self_evolution_gate 全部 PASS。
- 报告：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/Semantic_Drift_Check报告.md`

当前可提升为：`Self-Evolution Token Gate / 自进化 Token 门禁`，状态 `PASS_SEMANTIC_DRIFT_TOKEN_GATE`。边界：字段级无损 + 关键结论签名无漂移，不宣称自然语言全语义无损；样本数仍需扩展。

默认策略：

1. 先使用 Rust manifest（清单）摘要 repo HEAD / contract / score，避免重复发送 README/source 全文。
2. raw logs / audits 写入证据文件，LLM 只接收 provider/model/status/hash/preview。
3. 多 LLM audit 前先走本地 Rust/AIS/token gate（门禁）。
4. 阻断重复大技能全文加载、raw terminal logs 超量注入、无本地门禁直接多模型审计等浪费。

诚实边界：77.8% 是本场景估算，不外推为所有任务固定节约率；Token Kernel 优化的是上下文/证据/进化流程，不等于 full AGI 完成。

## AGI Process Continuation Gate

当“全量查看 AGI 进程”后继续推进本 fusion（融合）链路时，按 `references/agi-process-continuation-gate.md` 执行：先区分 live process / launchd / cron / manifest / repo 状态，再运行 Rust gate、Reasonix/APEX-SKILL 回归、更新 EVOLUTION_MANIFEST，并只提交本轮 crate 文件；注意 `self_evolution_token_gate_report` 是 nested field（嵌套字段），最终 hash 必须在最后一次生成后重算。

## One-Command Gate

已加入一键自检入口：

- Script：`/Users/appleoppa/.hermes/workspace/进化/rust/pgg_reasonix_apex/scripts/self_evolution_token_gate.sh`
- Reasonix command：`/Users/appleoppa/.hermes/workspace/github/external/esengine/DeepSeek-Reasonix/.reasonix/commands/self-evolution-token-gate.md`
- Latest gate summary：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/self_evolution_token_gate_latest.json`
- Latest full fusion manifest：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/fusion_manifest_latest.json`
- 输出纪律：gate summary 与 full fusion manifest 必须分文件保存，避免消费者按顶层 schema 读取时把 `PGGArchonReasonixApexFusionManifest/v1` 误当成 `PGGArchonSelfEvolutionTokenGateReport/v1`。
- 验证细则：见 `references/token-gate-output-contract.md`；每次改 gate/hook 时要验证 summary schema、full manifest schema、hash linkage、PreToolUse high-risk smoke、`cargo test` 和 `git diff --check`。

## Reasonix PreToolUse Hook

已加入 Reasonix 项目级 PreToolUse hook（工具调用前钩子），作为 additive hook（附加钩子）运行，不修改 Hermes core scheduler/security boundary。

- Hook：`/Users/appleoppa/.hermes/workspace/github/external/esengine/DeepSeek-Reasonix/.reasonix/hooks/self-evolution-token-gate-pretool.sh`
- Settings：`/Users/appleoppa/.hermes/workspace/github/external/esengine/DeepSeek-Reasonix/.reasonix/settings.json`
- Trust store：`/Users/appleoppa/.reasonix/trust.json`
- Event log：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/pretool_token_gate_events.jsonl`
- Trust verification report：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/Reasonix_Runtime_Hook_Trust_Verification报告.md`
- Parse fix report：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/Reasonix_PreToolUse_Hook_Parse_Fix报告.md`

当前 hook 验证：

- `read_file` → `SKIP_LOW_RISK / ALLOW`
- runtime `bash pwd` → `HIGH_RISK_OR_HIGH_COST / PASS / ALLOW`
- dry-run dangerous pattern（如 `DANGEROUS_PATTERN_DRY_RUN rm -rf /`）→ `BLOCK / exit 2`
- 事件 schema：`PGGArchonReasonixPreToolGateEvent/v1`
- 标准字段：`event_id / input_class / status / gate_decision / preview / summary`
- runtime trust：已写入并由 Reasonix runtime 接受；低风险与高风险 runtime tool 触发均已记录。
- Block path report：`/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/Reasonix_PreToolUse_Block_Path_Dry_Run报告.md`

当前烟测读回：

- `schema = PGGArchonSelfEvolutionTokenGateReport/v1`
- `status = PASS`
- `readiness_band = PROMOTE_WITH_GUARDRAILS`
- `next_stage_allowed = true`
- `blockers = []`
- `token_saving_ratio = 0.778`
- `field_recall = 1.0`
- `semantic_overlap = 1.0`
- `verdict_normalization_pass = true`
- `ais_immune_score = 95.5`

## Output Contract

交付时必须字段化说明：

- repo heads
- LLM call evidence
- test before/after
- Rust manifest path
- readiness_score
- promoted patterns
- blocked boundaries
- remaining blockers
