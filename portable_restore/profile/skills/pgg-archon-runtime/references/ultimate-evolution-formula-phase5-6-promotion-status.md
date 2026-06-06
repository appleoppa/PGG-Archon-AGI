# 终极进化公式 Phase5/6：晋升门禁与原生工具状态面融合

## 适用场景

用户在 PGG Archon / APEX / AGI 进化链路中说“继续融合”“继续”，且前序已经存在：

- Phase3：周期性 ARS sidecar 报告与 PGG DB 入库读回；
- Phase4：ARS trend replay + semantic fingerprint 去重门禁；
- Phase5/6 目标：把前序报告链路收束为可读、可测、可入库的 promotion gate（晋升门禁）和 native tool status surface（原生工具状态面）。

## 可靠执行模式

1. **先恢复证据，不凭记忆继续**
   - 读回 workspace 中的 Phase3/4/5 JSON；
   - 查询 PGG DB 中 phase3/4/5/6 gene 记录；
   - 确认 cron wrapper 当前参数，避免重复入库污染。

2. **Phase5 必须融合三类证据**
   - Phase3 ARS 报告：`phase3_ars_cycle_report.json`；
   - Phase4 去重报告：`phase4_ars_trend_replay_dedup_report.json`；
   - GPT + Claude 真实 Responses API 审查证据：`model_review_phase5/phase5_dual_model_review.json`。

3. **Phase5 promotion gate 的最小门禁**
   - `phase3_verified`；
   - `phase4_verified`；
   - `score_threshold >= 75`；
   - `trend_stable`；
   - `dedup_gate_active`；
   - `dual_model_review_ok`；
   - `p0_blocker_absent`。

4. **Phase6 融合方式**
   - 不改 `run_agent.py`；
   - 给 `pgg_ultimate_evolution` 增加只读 action：`promotion_status`；
   - action 读取 Phase5 gate 并返回：
     - `PGGArchonUltimateEvolutionPromotionStatus/v1`；
     - Phase5 gate 原始 payload；
     - `side_effects=read_only_status`；
   - 再由 Phase6 报告包装成：
     - `PGGArchonUltimateEvolutionPhase6ToolStatusSurface/v1`。

5. **cron/no_agent wrapper 更新**
   - 使用项目 venv，避免系统 Python 缺 pytest/依赖；
   - 推荐参数：`--persist --phase4 --phase5 --phase6`；
   - Phase3/4/5/6 persistence 均应 idempotent（幂等），重复运行返回已存在 gene，不再污染 DB。

## 验证口径

最低验证：

```bash
venv/bin/python -m py_compile agent/pgg_archon_ultimate_evolution_ars_cycle.py tools/pgg_archon_tools.py scripts/run_pgg_ultimate_evolution_ars_cycle.py
venv/bin/python -m pytest tests/agent/test_pgg_archon_ultimate_evolution_ars_cycle.py tests/tools/test_pgg_archon_tools.py -q
venv/bin/python scripts/run_pgg_ultimate_evolution_ars_cycle.py --persist --phase4 --phase5 --phase6
```

完成态证据：

- tests 全过；
- Phase5 report 和 Phase6 report 已生成；
- PGG DB 有 phase5/phase6 gene 读回；
- 第二次运行显示 Phase3/4/5/6 不重复污染；
- 最终汇报明确：这是 sidecar/status surface，不是自动核心接管。

## 踩坑

- 不要把 `decision=allow_candidate_promotion` 说成“已自动晋升核心能力”；它只是 promotion candidate gate 通过。
- 不要为了继续推进去改 `run_agent.py`，除非用户明确授权核心接管/核心循环修改。
- 不要只写 Markdown 报告；必须 JSON + 测试 + PGG DB 入库读回。
- GPT/Claude 审查必须走 Responses API `/v1/responses`，不能用 `/v1/chat/completions` 或角色扮演冒充。
