# 2026-05-23 评估中心与开源吞噬采集器落地记录

## 触发背景

用户确认：实际模型训练闭环已做，但继续追问两个未完成点：

1. Hermes 原生核心改造是否已做；
2. 自动吞噬全球开源前三项目是否已做。

审计结论：二者均不能夸大为完成。已完成的是安全接口层和只读采集层。

## 关键别名

用户将“评估中心”定义为固定别名，指 Hermes 的轨迹评分、训练、预测和评估流水线。以后用户说“打开评估中心”“评估中心怎么样了”，默认理解为这套系统。

## 本轮可复用落地模式

### 1. 原生核心改造先走安全桥接层

不要一上来修改 Hermes 主链路源码、凭证或配置。优先使用现有正式挂载点：

```bash
hermes cron create --script <script> --no-agent ...
```

本轮确认的低风险路径：

- 脚本放在 `/Users/appleoppa/.hermes/scripts/`
- 产物放在 `/Users/appleoppa/.hermes/workspace/`
- cron 用 `no-agent` 模式执行脚本
- 默认只生成报告、评分、候选和 dry-run apply plan
- 不写 `config.yaml`、`.env`、`auth.json`
- 不改 `run_agent.py`、`cron/scheduler.py`、`cron/jobs.py`

新增安全桥接器：

```bash
/Users/appleoppa/.hermes/scripts/hermes_eval_center.py status
/Users/appleoppa/.hermes/scripts/hermes_eval_center.py audit
/Users/appleoppa/.hermes/scripts/hermes_eval_center.py run
```

用途：统一读取评估中心状态、模型评估、预测记录、开源吞噬报告和 cron 接入状态。

### 2. 自动吞噬外部项目先做只读采集器

不能把“搜索到项目”说成“已吞噬”。正确阶段划分：

```text
只读采集 → 许可证/README 审计 → 架构拆解 → 沙箱复现 → 能力抽取 → 技能/基因候选 → 核心接口化
```

新增只读采集器：

```bash
/Users/appleoppa/.hermes/scripts/hermes_open_source_devour_scout.py --query "agent framework" --top 3
```

边界：

- 只读 GitHub 元数据、README、license
- 不 clone 仓库
- 不复制源码
- 不自动改 Hermes 核心
- 不看许可证不得复用代码

本轮示例候选：

| 项目 | 许可证 | 能力信号 |
|---|---|---|
| `obra/superpowers` | MIT | agent, workflow |
| `langchain-ai/langchain` | MIT | agent, evaluation, planning, tool, workflow |
| `TauricResearch/TradingAgents` | Apache-2.0 | agent, benchmark, multi-agent |

## 汇报纪律

当用户问“这个做了吗”时，必须区分：

| 表述 | 允许条件 |
|---|---|
| 已完成训练闭环 | 有模型、评估、预测文件，且能读回运行 |
| 已完成安全接口层 | 有桥接脚本、运行记录、cron/状态读回 |
| 已完成只读采集器 | 有真实外部元数据/README/license 报告 |
| 已完成核心改造 | 必须实际改 Hermes 核心源码并验证，不满足则禁止说 |
| 已完成自动吞噬 | 必须完成采集、审计、复现、能力抽取和验证，不满足则禁止说 |

## 常见陷阱

1. 把 sidecar / cron / script adapter 夸大成“核心源码改造”。
2. 把 GitHub 搜索和 README 摘要夸大成“吞噬完成”。
3. 把路线图写完夸大成“工程落地”。
4. 为追求“原生核心”而直接改高风险主链路。
5. 忘记用户已定义“评估中心”别名，重复询问其含义。
