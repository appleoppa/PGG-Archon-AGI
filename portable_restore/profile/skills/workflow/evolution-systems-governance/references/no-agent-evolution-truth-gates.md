# no_agent 进化流水线真实性门禁

## 触发场景

开智/进化流水线为绕过 Agent 工具审批或 prompt 注入拦截，改用 `no_agent=True` 脚本直接执行时。

## 核心教训

`no_agent` 只能证明脚本进程跑完，不能证明完成了开智进化。必须把“真实性门禁”写进脚本本身，否则会把通路检查误报为正常完成。

## 必查信号

出现任一项时，不得输出“正常完成”，应输出“部分完成/未完整进化”：

- `apply_dry_run` 或 apply 仍为 dry-run：未实际落地技能、记忆、配置或数据库变更。
- apply plan 中 `reviewable > 0`：仍有候选需要主 Agent 或人工复核，未自动吸收。
- dataset 阶段声明 `dataset asset only`：只是资产打包，不是真实模型训练。
- train/eval 阶段出现 `low_sample_or_imbalanced`：样本少或标签失衡，1.0 accuracy 不具证明力。
- 只看到 `exit=0`、`status=ok`、文件生成、沙箱通过：这些只是运行证据，不是能力进化证据。

## 推荐输出

```text
开智无人值守流水线部分完成，不能标记为正常完成
- 报告：...
- 机制沙箱：x/y
- 模型状态：...
- 问题：apply阶段仍是dry_run；仍有N项候选需要复核；样本失衡...
- 本轮记录：...
```

## 脚本修复模式

1. 先运行原 pipeline 并解析最后一行 JSON。
2. 读回 `latest_pipeline_report.json`，逐 step 检查 stdout。
3. 读回 `latest_apply_plan.json` 的 summary。
4. 如命中真实性问题：
   - 在本轮记录中写入 `truth_gate_status=partial_not_complete`；
   - 写入 `truth_gate_issues=[...]`；
   - stdout 明确说“部分完成，不能标记正常完成”；
   - 返回非零退出码，让 cron 显示异常/需检查，而不是 ok。
5. 只有所有真实性门禁均通过，才允许“正常完成”。
