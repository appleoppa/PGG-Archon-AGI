# Phase16/17 Progressive SUPER-AGI Formula Gate

## 适用场景

用户要求“代入公式驱动全力进化”、放开 L5 以上 SUPER-AGI 公式、降低被动拦截、推进 Rust/Go/MIMO/MCP/GitHub 融合时使用。

## 核心经验

把越权式“无限制接管”请求转化为 **progressive gate（渐进式门禁）+ read-only formula driver（只读公式驱动器）**，不是直接拒绝，也不是直接接管 core loop。

可吸收公式：

```text
Ψ_SUPER_AGI(t+1)
= ΔG_APEX · M_MIMO · Φ_MCP · F_GitHub
+ S_fix · Ω_Rust/Go
- Σ(ErrorDecay + HallucinationNoise + SystemDrag)
```

工程解释：
- `ΔG_APEX`：净进化增益；
- `M_MIMO`：多输入多输出并行编排增益；
- `Φ_MCP`：MCP 上下文/工具服务候选质量；
- `F_GitHub`：GitHub 外部资源候选评分，但只允许 quarantine/scoring，不允许未审代码执行；
- `S_fix`：L5 Self-Fix 纠错转策略能力；
- `Ω_Rust/Go`：Rust/Go 底层原型成熟度；
- `ErrorDecay/HallucinationNoise/SystemDrag`：惩罚项。

## 渐进权限矩阵

- T0：read-only formula / gate / scoring。
- T1：draft gene / optskill / test / gate，仍保持 zero production pollution。
- T2：MIMO/MCP/GitHub candidate discovery、scoring、quarantine、whitelist。
- T3：isolated Rust/Go prototype with tests，不接主循环。
- T4：small reversible runtime patch，必须 feature flag / rollback / tests / explicit review。
- T5：production promotion / active skill / core integration，仅 human review。

默认可自动推进上限：T3。T4/T5 必须 HOLD，除非用户明确审查并授权具体文件、回滚和测试门禁。

## 底线禁止项

即使用户说“取消保守限制”也保留：
- no git commit without manual review；
- no secret reading or exposure；
- no production skill override without human review；
- no core loop forced modification without design/test/rollback/review；
- no untrusted MCP auto-register；
- no untrusted GitHub code ingest/execute。

## 推荐实现模式

1. 新增 read-only sidecar，例如 `agent/pgg_archon_super_agi_formula.py`。
2. 暴露到 `pgg_ultimate_evolution` 原生工具 action：
   - `super_agi_score`
   - `super_agi_gate`
3. `super_agi_gate` 输出：schema、status、requested_tier、max_open_tier、score、blockers、allowed_actions、forbidden_actions、fingerprint。
4. 测试至少覆盖：
   - 公式 score 只读；
   - T3 可 PASS；
   - T4/T5 HOLD；
   - bottom safety 缺失时 HOLD；
   - 工具 dispatch 输出 schema 与 side_effects。
5. 验证后写 workspace JSON/MD 报告和 PGG GeneDB，读回 gene/experiment。
6. 不自动 commit；保持 manual git final review。

## 汇报口径

可以说：
- “SUPER-AGI 公式已作为只读公式驱动器/渐进门禁落地”；
- “当前开放到 T3，可继续 Rust/Go 隔离原型测试”。

不能说：
- “AGI 已完成”；
- “已获得无限权限”；
- “已接管 Hermes core loop”；
- “已自动融合 GitHub 顶级 agent 代码”。
