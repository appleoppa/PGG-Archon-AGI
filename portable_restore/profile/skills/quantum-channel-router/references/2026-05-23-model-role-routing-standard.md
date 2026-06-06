# 2026-05-23 超级路由模型角色新标准

## 触发背景

用户明确纠正旧超级路由标准：不能再把 MiniMax 当默认基础通道。新的排序以“综合能力 + 中文能力 + 编程能力 + token 成本/额度”为综合依据。

## 模型角色排序

| 分级 | 模型 | 用户定义 | 主要用途 |
|---|---|---|---|
| A | gpt-5.5 | 最强大脑，综合能力第1，token 单价第2 | 默认复杂任务、综合判断、策略设计、冲突裁决、最终结论 |
| B | deepseek-v4-flash | 最强中文，综合能力第2，token 单价第1 | 中文法律、中文长文本、批量推理、中文事实整理、低成本推理 |
| C | claude-opus-4-7 | 编程大师，综合能力第3，token 单价第3 | 代码编写、重构、调试、架构实现、复杂工程审查 |
| D | MiniMax-M2.7-highspeed | 执行力强，综合能力第4，用户有 token plan，消耗便宜 | 草稿、摘要、格式化、批量执行、低风险重复任务 |
| E | glm-4.5-air | 能力偏落后，与 MiniMax 接近；当前仅剩约 3000 万 token 额度 | 仅显式要求 GLM/消耗额度/极低风险任务时使用；额度用完后抛弃 |

## 路由规则

默认开放任务不再走 MiniMax，而是走 GPT：

```text
默认 / 综合 / 开放判断 → A GPT
中文 / 法律 / 长文本 / 低成本推理 → B DeepSeek
代码 / debug / 重构 / 测试 / 工程实现 → C Claude
简单 / 摘要 / 格式化 / 批量 / 执行 → D MiniMax
glm / 剩余token / 3000万 / 额度消耗 → E GLM
```

## 降级链

```text
A GPT 不可用 → B DeepSeek
B DeepSeek 不可用 → A GPT
C Claude 不可用 → A GPT
D MiniMax 不可用 → B DeepSeek
E GLM 不可用 → D MiniMax
再不行 → 扫全部可用
```

## 实现位置

- Rust 路由源码：`~/.hermes/quantum-router/src/config.rs`
- 健康检查/降级：`~/.hermes/quantum-router/src/health.rs`
- 已安装 CLI：`~/.cargo/bin/qr`
- 技能说明：`quantum-channel-router/SKILL.md`

## 验证样例

未来修改后应至少验证：

```bash
qr tier A   # gpt55_5yuantoken / gpt-5.5
qr tier B   # deepseek_v4_flash / deepseek-v4-flash
qr tier C   # claude_opus47_5yuantoken / claude-opus-4-7
qr tier D   # minimax_m27_highspeed / MiniMax-M2.7-highspeed
qr tier E   # glm45_air / glm-4.5-air

qr route "综合判断一个复杂开放任务"
qr route "中文法律长文本案例分析"
qr route "Rust代码重构debug测试"
qr route "批量整理摘要格式化执行"
qr route "glm 3000万 剩余token 额度消耗"
```

预期分别命中 A/B/C/D/E。

## 防回退坑点

- 不要把 A 恢复成 MiniMax；A 必须是 GPT 最强大脑。
- 不要把 DeepSeek 和 GPT 混在同一个 B 级；DeepSeek 是 B，GPT 是 A。
- GLM 不是稳定长期低成本通道，只是剩余额度消耗通道。
- MiniMax 的价值是执行力和 token plan 便宜，不是默认主脑。
