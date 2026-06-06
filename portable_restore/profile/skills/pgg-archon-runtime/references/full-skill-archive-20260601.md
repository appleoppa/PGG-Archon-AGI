---
name: pgg-archon-runtime
description: PGG Archon 本地运行入口：真实使用 Multi-Agent Debate、ECC三层治理、模块三态检查、SQLite持久化与DSPy/AgentVerse吸收模式。
version: 1.0.0
---

# PGG Archon Runtime 本地运行入口

## 触发条件

当任务涉及：
- PGG Archon / APEX / AGI / 进化 / 开智吸收；
- 架构决策、模块状态核验、系统治理；
- 需要把学到的开源模式落地使用；
- 用户说“继续”“落地使用”“跑闭环”；
- 将 PGG Archon 与本地 sidecar（旁路组件）链接、同步 LLM provider、或配置 Feishu/Lark webhook。

## 必须执行的本地闭环

0. **先确认运行前提**
   - 如果用户问“联网了吗/连不上网吗/能看到模型URL吗”，必须实际检查：`curl -I https://github.com`、目标开源仓库 API、或读取 `~/.hermes/config.yaml`，不能凭记忆回答。
   - 默认本地应用优先：除非用户明确要求提交/推送，否则不要创建 Git commit；若误提交，立即 `git reset --soft HEAD~1` 回到未提交状态。
   - 本地 sidecar 已弃用项目不得按旧引用恢复；优先使用 `rust-sidecar-gateway-patterns` 中的通用模式。

1. **三态状态检查**
   - 调用 `~/.hermes/agent/pgg_archon_module_status.py`
   - 只接受外部证据：文件、数据库、skill存在性；禁止随机或自报。

2. **关键决策走 Debate Pipeline**
   - 调用 `~/.hermes/agent/pgg_archon_debate.py`
   - 使用三步：Propose → Critique → Synthesize。
   - 输出必须包含：共识点、分歧点、最终判定。

3. **执行链路走 ECC**
   - 调用 `~/.hermes/agent/pgg_archon_ecc.py`
   - Core 负责执行；Governance 负责审计/拦截；Learning 只能通过 Governance 更新经验。

4. **结果入 SQLite**
   - 调用 `~/.hermes/agent/pgg_archon_sqlite_persistence.py`
   - 数据库：`~/.hermes/data/pgg_archon.db`
   - 写入 experiments / genes / skills，不能只写Markdown报告。

5. **开源吸收依据**
   - DSPy: Teleprompter/Optimizer `compile(student, trainset, valset)` 思想。
   - AgentVerse: propose→critic→manager→iterate 的Critic循环。

## 禁止事项

- 禁止把“文件已生成”说成“能力已运行”。
- 禁止使用随机状态检查或模块自报作为激活证据。
- 禁止用 ZeroLang、负势湮灭、ΔE能量等不可测术语当作工程指标。
- 禁止不入库、不验证、不运行就宣称吸收完成。

## 参考记录

- `references/2026-05-29-runtime-loop.md`：本轮“学到就要落地使用”的完整本地闭环、验证口径和踩坑记录。
- `references/local-runtime-truthfulness.md`：AGI/APEX/PGG 仓库本地部署时，如何从外部材料收敛为真实可运行 runtime，并避免把 Web UI 壳或保留源码夸大成完整 AGI。
- `references/agi-runtime-deployment-truth-gate.md`：用户要求继续完成 AGI 部署未完成项时，用 UI-only / runtime online / root crate deployable / provider-backed / full generated core integrated 五态门禁防止过度宣称。
- `references/mainline-sidecar-service-deployment.md`：本地 agent/runtime 项目接入 PGG Archon 主链路时的服务化部署、健康桥接、runtime loop、gene DB 读回和安全边界门禁。
- `references/ultimate-evolution-formula-sidecar.md`：将“终极进化公式” `APEX_AK = Ω_A · EVM_full - ΣΔ_all` 以 read-only sidecar 融入 Hermes Agent 原生面，并用 GPT-5.5 主导 Claude/DeepSeek/MiniMax ARS 闭环的安全模式、schema 和验证门禁。
- `references/ultimate-evolution-formula-phase3-ars.md`：Phase 3 周期性 ARS sidecar 闭环：恢复上下文、核验 Phase1/2、本地证据采集、调用 `pgg_ultimate_evolution`、workspace 报告、PGG DB 入库读回、cron/no_agent wrapper 与边界。
- `references/ultimate-evolution-formula-phase4-dedup-gate.md`：Phase 4 ARS trend replay + semantic fingerprint 去重门禁；用于防止周期性 cron 重复写入同一 PGG gene 污染基因库。
- `references/ultimate-evolution-formula-phase5-6-promotion-status.md`：Phase 5/6 把 Phase3/4 报告、GPT/Claude Responses API 审查、promotion gate 和 `pgg_ultimate_evolution` 原生工具 `promotion_status` 状态面融合为可测试、可入库、幂等的 sidecar 晋升门禁。
- `references/ultimate-evolution-formula-phase8-integrity-gate.md`：Phase 8 将 Phase3-7 报告、GPT review、cron wrapper 与 PGG DB readback 哈希成 deterministic integrity manifest（确定性完整性清单），用于 cron/CI 漂移门禁。
- `references/ultimate-evolution-formula-phase9-cron-ci-drift-gate.md`：Phase 9 将 Phase8 manifest 落成 cron/CI drift gate（漂移门禁），接入 `pgg_ultimate_evolution` 原生工具 `ci_drift_gate_status`，并修复 JSON 时间戳导致的 manifest hash 抖动。
- `references/ultimate-evolution-formula-phase11-lifecycle-chain.md`：Phase 11 建立 gene_lifecycle + promotion_chain 表，为终极进化公式基因建立 5 态状态机（candidate/active/promoted/archived/retired）和晋升链审计轨迹；含增量迁移（ALTER TABLE）踩坑记录。
- `references/ultimate-evolution-formula-phase12-mcp-native-surface.md`：Phase 12 将终极进化公式作为 Hermes MCP 原生 read-only tool 暴露，复用 `tools.pgg_archon_tools`，GPT-5.5 主审，覆盖 tool 注册、只读 ARS plan、非法 JSON 拒绝测试，并明确不得改主循环/自动注册任意 MCP。
- `references/phase-report-filing-gate.md`：Phase 报告落盘门禁（workspace 路径规范、SHA256 写入规范、审计响应流程）。解决 `/tmp` 路径导致 subagent 审计找不到报告的幻觉误判问题。
- `references/ultimate-evolution-formula-phase13-mimo-mcp.md`：Phase 13 将 `Agent_APEX+MIMO+MCP = Model • Harness ∘ M_IMO ∘ F_auto ∘ Φ_MCP` 吸收为 `APEX_AK` 上层 read-only orchestration surface；含 MIMO/TopK/MCP 工程映射、默认安全 policy、测试门禁和禁止口径。
- `references/ultimate-evolution-formula-phase14-l5-self-fix.md`：Phase 14 L5 Self-Fix 最小真实运行态：把 tool_failure/test_error/user_correction 等信号转为 optskill_draft、Gate、测试、GeneDB 入库读回；强调草稿隔离、人审晋升和用户催促时继续闭环。
- `references/ultimate-evolution-formula-phase16-17-progressive-super-agi-gate.md`：Phase16/17 将 SUPER-AGI 公式吸收为 read-only formula driver 与 progressive gate；默认最多自动开放 T3（候选评分/隔离原型），T4/T5 必须 human review，保留 no secret/no core-loop forced modify/no production skill override/no untrusted MCP/GitHub execution 底线。
- `references/phase11-lifecycle-and-safe-push.md`：Phase11 继续执行时的 durable pattern：生命周期表入库、Phase11 gene 读回、persist 后再 gate、测试门禁、上游落后时推私有 feature branch，以及根目录副产物归档纪律。
- `references/upstream-absorption-branch-pattern.md`：当本地 PGG Archon 分支领先私有提交但落后官方 `origin/main` 时，使用隔离吸收分支审查、合并、测试、入库并只推 private 远程的完整模式。

## 连续进化执行纪律

**核心原则**：综合评分 >75 且低风险可回滚时，必须直接执行到测试、提交、推送。**不许停在方案建议或"下一步可以"。**

- 用户明确表达过不满："继续，不要让我催你？大于75你为什么不继续进行呢""那你还不继续"
- 当评分 >75 且在 hard boundary 内时：直接进入下一轮，不要只给"可进入下一步"式汇报
- 若新一轮发现 blocked 状态：完成审计、测试、入库、读回，明确 blocker 与下一步路径，不停在计划
- 每次推进后立即识别下一步，评分；>75 且低风险直接执行，不等用户再次提醒


```
  → PGG score gate (threshold=75)
  → /api/learn (idempotent)
  → bridge schema drift CI gate (local dry-run)
```




权限网关进化链（已落地 dry-run，每轮需 10 样本 + /api/learn + PGG gene DB 读回）：

1. permission gateway：Intent→Plan→Confirm→Execute→Receipt→Evaluate
2. receipt replay evaluator：读取历史 10 条 dry-run，重新评估阻断率与失败分类
3. confirmation contract：confirmation_id / scope / expiration / replay_nonce / receipt binding
4. bridge v0 state→plan→metrics：state.json / plan.json / metrics.json / hash binding
5. negative replay gate：overreach_action / missing_rollback / hash_mismatch / no_confirmation / credential_request / device_api_request → 全部阻断
6. schema registry：state@v0 / plan@v0 / metrics@v0 / negative_replay@v0 版本化 + drift check
7. bridge schema drift CI gate：上面全部串成单命令门禁

每次落地需验证：py_compile + 样本测试 + /api/learn 写入 + gene DB 入库读回 + 报告。

## TaskOrchestration 三态证据口径（当前现行）

TaskOrchestration（任务编排）完成态只接受当前仍有效的外部证据：

- `~/.hermes/agent/pgg_archon_debate.py`：Propose → Critique → Synthesize 的多智能体辩论入口；
- `~/.hermes/agent/pgg_archon_ecc.py`：Core / Governance / Learning 三层执行治理入口；
- `~/.hermes/skills/pgg-archon-runtime/SKILL.md`：运行时流程规则。

`pgg_archon_nano_mainline.py` / nanoGPT-claw 相关证据已退役，不得再作为 TaskOrchestration 激活前提；否则会把已退役 sidecar（旁路组件）的缺失误判为 PGG Archon 编排链路 partial。

### Feishu gateway 与多 provider 配置门禁

需要配置 nanoGPT-claw 自带 Feishu gateway 和模型 provider 时：

1. 先加载 `hermes-agent` 技能，但不要修改受保护技能；用它确认 Hermes 配置/凭据注入习惯。
2. 编程修改前按用户偏好真实调用 GPT/Claude 审查；GPT/Claude 必须走 Responses API (`/v1/responses`)，不能退回 `/v1/chat/completions`。
3. provider registry 至少读回：`gpt55_5yuantoken`、`claude_opus47_5yuantoken`、`minimax_m27_highspeed`、`deepseek_v4_flash`。
4. MiniMax Anthropic endpoint 使用 `https://api.minimaxi.com/anthropic/v1/messages`，认证头是 `X-Api-Key`；不要同时加 `Authorization: Bearer ...`，否则可能 401。
5. **优先 Hermes 式 WebSocket 长连接**：当用户配置 Feishu/Lark 入口时，默认走 `lark_oapi.ws.Client` 连接 `msg-frontier.feishu.cn`，不要先让用户折腾 webhook Request URL / challenge / localtunnel。现行一键入口：`/Users/appleoppa/.local/bin/nanogpt-oneclick-deploy`。
6. 若必须使用 webhook，才启用 `NANOGPT_CLAW_FEISHU_ENABLED=true`；服务 wrapper 从 `~/.hermes/.env` 和 `~/.hermes/secrets/nanogpt_*.env` 注入环境变量，不把 secrets 写进 plist、报告或技能。
7. 飞书 WebSocket 完成态必须看到：`connected to wss://msg-frontier.feishu.cn/ws/v2`、`received message_id=...`、`replied message_id=...`。若回复 400 且错误码 `99991672`，不是链路坏，而是应用未开通/发布 `im:message:send_as_bot` 等消息发送权限。
8. 验证必须包括：`nano-gpt-claw-service providers`、launchd 重启、Feishu WebSocket receive/reply 日志、外部 GPT/Claude/MiniMax/DeepSeek provider 探测、PGG gene DB 入库读回。
9. 提交纪律：只 add 本轮源码文件；清理 `target/.rustc_info.json`、`nanoGPT-claw.memory.db` 等运行副产物；提交后 push 并确认 `master...origin/master` clean。

参考：
- `references/pgg-nanogpt-local-agent-link.md`：PGG Archon ↔ NanoGPT-Claw 本地 agent 链接；sidecar health、provider registry、localhost 边界、SQLite evidence/gene 入库读回与真实性边界。
- `references/nanogpt-feishu-multiprovider-gateway.md`：专用飞书 App、GPT/Claude/MiniMax provider、service wrapper 与外部 API 探测。
- `references/nanogpt-feishu-webhook-server.md`：飞书 inbound webhook server、快速 ACK、event_id 去重、challenge 验证、公网 HTTPS 隧道与提交清理纪律。
- `references/nanogpt-feishu-webhook-ingress.md`：nanoGPT-claw 飞书 webhook 入口、临时公网隧道失效诊断、用户极简配置话术与完成态证据门禁。
- `references/nanogpt-feishu-websocket-bridge.md`：Hermes 式 Feishu WebSocket 长连接桥；绕开 Request URL/challenge/localtunnel，含一键部署、权限 99991672 修复、receive/reply 验证口径。
- `references/evolution-pipeline-execution-surface.md`：PGG Archon evolution pipeline 闭环执行面；目标→证据→诊断→Debate→ECC→验证→评分→入库→读回，含下一轮 rollback/quarantine gate。
- `references/recursive-materialization-and-rust-migration-rule.md`：递归 phase 物化硬规则、禁止 planned-only 虚进化、sidecar 无限续进边界、cycle index append-only 治理，以及 Rust 优先/Go 延后底层渐进迁移策略。
- `references/authorized-core-canary-integration.md`：用户明确授权 Hermes / PGG Archon core 集成后，如何用最小 `run_agent.py` observe-only canary hook、默认关闭 feature flag、hash-only receipt、备份回滚、测试、GeneDB 和 GPT/Claude review 完成真实核心集成，同时不误称 production takeover / unrestricted AGI。
- `references/agi-global-governance-baseline.md`：当用户要求把 AGI_Global / 终极公式“写入底层内核、全 LLM 强制继承、后台永久生效”时的安全物化模式：降级为 bounded read-only governance baseline + kernel governance rules + tool/report/GeneDB/tests，保留 P0 熔断和不可覆盖边界。

## Retired local sidecar note

NanoGPT-claw / NanoGPT-AGI has been retired locally as a half-finished sidecar. Do not restore its old launchd services, Feishu app binding, localtunnel/websocket bridge, runtime DBs, or secrets. Reusable engineering patterns were absorbed into `rust-sidecar-gateway-patterns`: real provider dispatch, chat context store, error incident triage, SQLite evolution ledger, macOS Rust CLI deployment gates, webhook quick ACK, and sidecar escalation boundaries.

## 第三方审计 LLM

- `references/third-party-auditor-llm.md`：

- `mimo_v25_pro_auditor` / `mimo-v2.5-pro` 是专用第三方审计 LLM，可用于审查真实性、夸大风险、可交付边界和下一步瓶颈。
- 必须真实调用并记录 `response_id`、`http_status`、hash；不得把主模型自评冒充第三方审计。
- MIMO 审计通道可用不等于官方 benchmark 通过，报告中必须保留此边界。
- **MIMO key 核验坑位**：不得只因当前工具子进程 `os.environ` 没有 `MIMO_V25_PRO_API_KEY` 就断言未配置；还必须检查 `~/.hermes/.env` 和 provider `key_env`，必要时手动加载 `.env` 后真实调用。若先前误报，追加 correction gene 并修正报告。详见 `references/mimo-env-loading-and-audit-correction.md`。

## 当前法律 AGI 状态快照

- Phase217：`PASS_ACTIONABLE_GAPS_CLOSED_BOUNDARIES_ENFORCED`，score `99.9`，GeneDB `gene 339` 已读回。
- 可行动缺失项：`[]`；已落地 normalized corpus index、本地前置 benchmark、`legal_gap_closure_gate`。
- 审计证据：GPT-5.5、Claude Opus 4-7、MIMO 三路真实 HTTP 200。
- 允许口径：L6 有边界法律办案流程门禁强化版。
- 禁止口径：full AGI completed、零程序错误、零退件风险、替代律师人工复核、无监督生产接管、官方外部评测通过。

## 快速验证命令

```bash
python3 ~/.hermes/agent/pgg_archon_module_status.py
python3 ~/.hermes/agent/pgg_archon_debate.py "是否应将新开源模式接入PGG Archon默认治理链路？"
python3 ~/.hermes/agent/pgg_archon_ecc.py
python3 ~/.hermes/agent/pgg_archon_sqlite_persistence.py
```
