# Cron 审计、合并与低风险清理模式

## 适用场景

用户要求“查看所有 cron / 逐项梳理 / 审计 / 合并 / 清理”时使用。目标不是只列 `hermes cron list`，而是形成可回滚、可验证的 cron 资产治理闭环。

## 执行顺序

1. **加载 Hermes cron 规则**
   - 先使用 `hermes-agent` 的 cron 入口规则。
   - 再用运营治理规则确认：清理前必须备份，清理后必须读回。

2. **只读盘点事实源**
   - `hermes cron list`
   - `hermes cron status`
   - `~/.hermes/cron/jobs.json`
   - `~/.hermes/cron/output/<job_id>/` 最近输出
   - `~/.hermes/scripts/<script>` 脚本存在性与关键内容
   - gateway / launch 状态只作为调度在线证据，不代表业务成功。

3. **脚本路径解析坑位**
   - cron `script` 相对路径不是按 job `workdir` 解析，而是按 `HERMES_HOME/scripts/` 解析。
   - 审计 `script_exists` 时必须检查 `~/.hermes/scripts/<script>`，不要误判为 `workdir/<script>` 缺失。

4. **逐项分类**
   每个 job 至少记录：
   - id / name / enabled
   - schedule / next_run_at / last_run_at / last_status
   - deliver / no_agent / provider / model / skills / toolsets
   - script / script_exists
   - output_count / latest_output hash / latest_output sample
   - 风险等级：low / medium / high
   - 建议动作：keep / keep-watch / pause-archive / consolidate

5. **合并清理原则**
   - 默认不删除 cron，先 `enabled=false` 暂停归档。
   - 对“最近失败 + 明确可替代”的任务，暂停归档。
   - 对“高频 + 外部副作用（commit/push/发布/写外部系统）+ 有低频替代”的任务，暂停并合并到低频替代链路。
   - 对 watch dog（正常 silent、异常才通知）可保留，但标记 medium risk。
   - 对 distinct pair（如预测与结果核查）不要机械合并。

6. **备份与报告**
   - 修改前备份 `~/.hermes/cron/jobs.json` 到 `workspace/审计/cron-audit-<timestamp>/jobs.json.before-cleanup`。
   - 写入 JSON 报告和 Markdown 报告，记录：备份 hash、变更清单、逐项审计、合并口径、验证结果。

7. **读回验证**
   - 修改后重新运行 `hermes cron list` 和 `hermes cron status`。
   - 验证 active 数量、暂停任务不再出现在 active 列表、gateway 仍 running、next run 正常。
   - 报告中明确：删除数量、暂停数量、回滚路径。

## 完成态口径

可以说：
- “已审计 N 个 cron，暂停归档 M 个，active 从 X 降到 Y，未删除，已备份，读回验证通过。”

不能说：
- “cron 业务都成功完成”，除非检查了对应业务产物。
- “脚本不存在”，除非按 `~/.hermes/scripts/` 路径查过。
- “已清理干净”，除非说明清理范围只是 cron job 配置，不包括历史 output/log 全量瘦身。
