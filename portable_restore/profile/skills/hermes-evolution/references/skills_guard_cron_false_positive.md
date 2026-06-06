# skills_guard false-positive: cron job prompt 自拦截

## 问题现象

cron job `91064196c7eb`（"20轮开智进化循环-日志短板专项-20260524夜间"）在每次触发时被 `skills_guard` 的 `destructive_root_rm` 规则拦截，13 次连续失败，job 最终被暂停。

## 根因

`skills_guard.py` 中的 `destructive_root_rm` 规则：

```python
(r'rm\s+(-[^\s]*)?r.*\$HOME', "destructive_home_rm", "critical", "destructive",
 "recursive delete targeting home directory"),
```

这条规则设计目标是：**检测外部注入攻击**（攻击者试图通过 prompt injection 让 agent 执行 `rm -rf $HOME`）。

但 cron job 的 prompt 本身是系统生成的，包含合法的工作指令，其中可能含有 `rm` 等危险词。当 cron scheduler 在触发前将 prompt 送入 `skills_guard` 扫描时，合法词汇被误判为攻击载荷。

## 关键区分

| 场景 | 来源 | 应拦截？ |
|------|------|----------|
| 外部注入攻击 | 用户输入 / 外部 API 响应 | ✅ 是 |
| cron job prompt（系统自生成） | `jobs.json` 的 `prompt` 字段 | ❌ 否（白名单） |

## 正确修复方向

1. **区分 prompt 来源**：cron scheduler 组装的 prompt 应标记为"系统可信来源"，跳过后台审查
2. **白名单机制**：`skills_guard` 应对 cron scheduler 的内部调用路径放行
3. **上下文感知**：检查是否处于 cron scheduler → prompt scanning 的调用链，而不是用户输入 → scanning

## 错误修复方向（不要做）

- 从 job prompt 中删除所有危险词（如 `rm`）：导致工作指令不完整
- 禁用 `destructive_root_rm` 规则：降低整体安全性

## 相关文件

- 扫描器源码：`~/.hermes/hermes-agent/tools/skills_guard.py`
- 受影响 job：`~/.hermes/cron/jobs.json`（id: `91064196c7eb`）
- 错误日志：`~/.hermes/logs/errors.log`（08:05:40 ~ 08:47 连续 13 次）

## 教训

`skills_guard` 的设计假设"所有 prompt 都来自不可信外部"，但 cron job 的系统生成 prompt 属于"可信内部来源"。安全扫描器需要对内部调用路径做上下文感知，避免将系统自身生成的内容误判为攻击。

**风险级别**：高（导致全部 cron job 无人值守任务失效）
**修复优先级**：P0（系统级设计缺陷）
