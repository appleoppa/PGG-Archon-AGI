# 主动卸载与误恢复边界（2026-06-02）

## 适用场景

本规则适用于健康巡检、智能体生态盘点、外部仓库吸收、sidecar / daemon / launchd / mirror / runtime 修复等任务。

## 事件抽象

健康巡检发现某个系统缺失时，不能直接推定为异常损坏。缺失可能来自：

1. 用户主动卸载；
2. 安全清理；
3. 迁移后不再使用；
4. 临时停用；
5. 真正误删或故障。

## 必须执行的判定顺序

1. 查当前状态：binary / runtime / repo / launchd / port / mirror。
2. 查近期会话或记忆：是否有“主动卸载、删除、不要恢复”的用户指令。
3. 对已卸载系统，只报告 `EXPECTED_ABSENT`，不得自动 clone、build、install、launch。
4. 若用户明确要求恢复，才可进入恢复流程，并留下 rollback（回滚）证据。
5. 若误恢复，必须立即回退并删除误建部署项，再更新 skill / memory。

## 严禁口径

- 禁止把“缺失”直接称为“异常”。
- 禁止把“可从 mirror 恢复”当作“应该恢复”。
- 禁止在健康巡检中自动恢复用户已卸载的 agent（智能体）/ sidecar（边车）/ daemon（守护进程）。

## 汇报格式

```text
status = EXPECTED_ABSENT | UNEXPECTED_MISSING | RUNNING | BROKEN | QUARANTINED
reason = user_uninstalled | cleanup_policy | missing_binary | launch_failure | unknown
next_action = report_only | ask_before_restore | repair | quarantine | remove
```

## 本次沉淀的稳定规则

`APEX-MEM` 已被用户主动卸载清除并删除本地镜像；未来巡检发现其缺失时，应判定为 `EXPECTED_ABSENT`，不得自动恢复。该条属于当前用户环境事实；若用户将来明确要求恢复，以最新明确指令为准。
