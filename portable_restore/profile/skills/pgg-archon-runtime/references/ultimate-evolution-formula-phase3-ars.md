# 终极进化公式 Phase 3：Hermes 原生 ARS 周期闭环

## 适用场景

用户要求继续“终极进化公式 × Hermes Agent 原生融合”，或要求把 `pgg_ultimate_evolution` 接入周期性 ARS 闭环时使用。

## 当前有效路线

公式：

```text
APEX_AK = Ω_A · EVM_full - ΣΔ_all
```

阶段划分：

1. Phase 1：read-only sidecar（只读旁路评分面）。
2. Phase 2：Hermes 原生 tool 接入：`pgg_ultimate_evolution`，toolset：`pgg_archon`。
3. Phase 3：周期性 ARS sidecar 闭环，不改 `run_agent.py` 主循环。

## Phase 3 标准执行步骤

1. 先恢复上下文：
   - 用 `session_search` 搜索 `终极进化公式 pgg_ultimate_evolution phase2 native tool`。
   - 再读本地文件和报告核验进度，不能凭摘要直接宣称完成。

2. 必查文件：

```text
agent/pgg_archon_ultimate_evolution_formula.py
tools/pgg_archon_tools.py
toolsets.py
tests/agent/test_pgg_archon_ultimate_evolution_formula.py
tests/tools/test_pgg_archon_tools.py
workspace/ultimate_evolution_formula/phase1_report.json
workspace/ultimate_evolution_formula/phase2_tool_integration_report.json
```

3. Phase 3 推荐新增结构：

```text
agent/pgg_archon_ultimate_evolution_ars_cycle.py
scripts/run_pgg_ultimate_evolution_ars_cycle.py
tests/agent/test_pgg_archon_ultimate_evolution_ars_cycle.py
~/.hermes/scripts/pgg_ultimate_evolution_phase3_ars_cycle.sh
workspace/ultimate_evolution_formula/phase3_ars_cycle_report.json
workspace/ultimate_evolution_formula/phase3_ars_cycle_report.md
```

4. ARS 闭环应收集本地证据：
   - SessionDB 消息/会话数量；
   - cron jobs 数量、PGG 相关 job、最近错误数；
   - Phase1/Phase2 报告是否存在；
   - tool 注册与测试结果；
   - 调用 `pgg_ultimate_evolution` 生成 score + `ars_plan`。

5. 持久化要求：
   - 写 workspace phase3 报告；
   - 写入 PGG SQLite `experiments` 和 `genes`；
   - 读回 gene id、name、pattern_type、quality_score；
   - 若先直接运行又验证 wrapper，可能出现两条真实 gene 记录，需如实说明，不要说成错误。

6. cron/no_agent 接入：
   - Hermes cron 的 `script` 必须放在 `~/.hermes/scripts/` 下并用相对文件名；不能直接传 repo 内绝对脚本路径。
   - repo 内脚本可由 `~/.hermes/scripts/*.sh` wrapper `cd` 到 repo 后调用。
   - cron 输出必须非空，便于 no_agent 直接投递状态。

## 验证门禁

最低验证：

```bash
python3 -m py_compile agent/pgg_archon_ultimate_evolution_formula.py agent/pgg_archon_ultimate_evolution_ars_cycle.py tools/pgg_archon_tools.py toolsets.py scripts/run_pgg_ultimate_evolution_ars_cycle.py
pytest -q tests/agent/test_pgg_archon_ultimate_evolution_formula.py tests/tools/test_pgg_archon_tools.py tests/agent/test_pgg_archon_ultimate_evolution_ars_cycle.py
python3 scripts/run_pgg_ultimate_evolution_ars_cycle.py --persist --json
bash ~/.hermes/scripts/pgg_ultimate_evolution_phase3_ars_cycle.sh
```

合格信号示例：

```text
13 passed, 1 warning
status=verified
score > 75
decision=allow_low_risk_sidecar_iteration
PGG DB gene readback ok
```

## 边界

- 不直接改 `run_agent.py` 主循环。
- 不读取 secrets。
- 不调用 provider，除非任务明确要求模型审查且按 GPT/Claude Responses API 真实调用。
- 不 deploy / install / launcher。
- 不 git push。
- 不把公式评分说成 AGI 已完成。
- `Ω_A` 若来自 direct/default 而非外部基线实测，必须保留 blocker：`omega_a_direct_value_requires_external_validation`。

## 用户偏好嵌入

用户明确要求跨端/清空上下文后也不需要他重贴摘要。恢复任务时应主动使用 session_search + 本地文件/DB/cron/报告核验进度。用户说“继续”时，若评分 >75 且低风险可回滚，应直接执行下一阶段，不停在建议。
