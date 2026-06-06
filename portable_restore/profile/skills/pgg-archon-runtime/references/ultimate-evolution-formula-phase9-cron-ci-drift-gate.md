# 终极进化公式 Phase9 Cron/CI 漂移门禁

## 触发

当 Phase8 integrity manifest（完整性清单）已经通过后，用户继续要求融合/下一步，进入 Phase9：把 Phase8 从“报告完整性”推进为 cron/CI 可执行漂移门禁。

## 核心能力

Phase9 使用 sidecar（旁路）方式完成：

1. 读取 `workspace/ultimate_evolution_formula/phase8_chain_integrity_gate_report.json`。
2. 重新计算当前 Phase8 manifest。
3. 比较 stored/current manifest hash。
4. 调用 `pgg_ultimate_evolution` 原生工具 action：`chain_integrity_status`。
5. 核验 PGG DB 中 Phase8 gene readback。
6. 核验 cron wrapper 同时包含 `--phase8 --phase9`。
7. 核验 `workspace/ultimate_evolution_formula/model_review_phase9/phase9_gpt_review.json` 中 GPT review `ok=true`。
8. 输出 Phase9 gate：`PGGArchonUltimateEvolutionPhase9CronCIDriftGate/v1`。

## 文件与入口

- 主实现：`agent/pgg_archon_ultimate_evolution_ars_cycle.py`
  - `build_phase9_cron_ci_drift_gate`
  - `write_phase9_report`
  - `persist_phase9_to_pgg_db`
  - `run_phase9_cycle`
- CLI：`scripts/run_pgg_ultimate_evolution_ars_cycle.py --persist --phase9`
- cron wrapper：`~/.hermes/scripts/pgg_ultimate_evolution_phase3_ars_cycle.sh`
  - 使用项目 venv：`/Users/appleoppa/.hermes/hermes-agent/venv/bin/python`
  - 当前参数链：`--persist --phase4 --phase5 --phase6 --phase7 --phase8 --phase9`
- 原生工具：`tools/pgg_archon_tools.py`
  - action：`ci_drift_gate_status`

## 验证口径

必须验证：

```bash
venv/bin/python -m pytest tests/agent/test_pgg_archon_ultimate_evolution_ars_cycle.py tests/agent/test_pgg_archon_ultimate_evolution_formula.py -q
venv/bin/python -m py_compile agent/pgg_archon_ultimate_evolution_ars_cycle.py scripts/run_pgg_ultimate_evolution_ars_cycle.py tools/pgg_archon_tools.py
bash ~/.hermes/scripts/pgg_ultimate_evolution_phase3_ars_cycle.sh
```

完成态字段：

- `phase9_status=ci_drift_gate_passed`
- `phase9_gene_id=<id>`
- `blockers=[]`
- GPT review：`ok=true`, `status_code=200`

## 稳定性修复

Phase8/Phase9 manifest hash 必须忽略 JSON 中的运行时字段：

- `ts`
- `called_at`
- `latency_ms`

否则 cron 每次重写报告会因时间戳导致 hash 抖动，形成假漂移。实现上使用 `_strip_volatile_fields`、`_stable_artifact_sha256`、`_stable_artifact_size`。

## 边界

- 不修改 `run_agent.py`。
- 不读取或输出 secret。
- 不部署。
- 不 git push。
- Phase9 是 cron/CI 漂移门禁，不代表 AGI 完成，也不自动核心接管。
