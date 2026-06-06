# 评估中心 / 超级进化12流水线记录

本参考记录 2026-05-23 会话中形成的可复用工程模式，供未来处理“评估中心”“超级进化12”“吞噬式自进化”“模型训练闭环”时使用。

## 固定别名

用户已指定：**“评估中心”** 指 Hermes 的轨迹评分、训练、预测和评估流水线。

当用户说：

- 打开评估中心
- 评估中心怎么样了
- 评估中心跑一轮
- 评估中心为什么分低

应默认理解为检查或运行以下链路，而不是泛泛解释概念。

## 当前安全入口

不要直接硬改 Hermes 主链路。优先使用已有正式挂载点：

```bash
hermes cron create --script <script-under-.hermes/scripts> --no-agent ...
```

评估中心主入口：

```text
/Users/appleoppa/.hermes/scripts/hermes_eval_center.py
```

支持命令：

```bash
/Users/appleoppa/.hermes/scripts/hermes_eval_center.py status
/Users/appleoppa/.hermes/scripts/hermes_eval_center.py audit
/Users/appleoppa/.hermes/scripts/hermes_eval_center.py run
```

每日流水线脚本：

```text
/Users/appleoppa/.hermes/scripts/hermes_evolution_pipeline.py
```

流水线步骤：

```text
digest → proposal → apply_dry_run → export → score → pack → train → predict → crossval → devour_sandbox
```

## 关键产物

```text
/Users/appleoppa/.hermes/workspace/evolution/pipeline/latest_pipeline_report.json
/Users/appleoppa/.hermes/workspace/agentic_rl/model/tiny_quality_eval.json
/Users/appleoppa/.hermes/workspace/agentic_rl/model/tiny_quality_crossval.json
/Users/appleoppa/.hermes/workspace/evolution/sandbox/devour_mechanisms/summary.json
/Users/appleoppa/.hermes/workspace/evolution/open_source_devour/latest_top3_agent_framework.json
```

## 质量门禁

流水线报告应区分：

- `overall=ok`：流水线和沙箱机制运行成功；
- `model_effect_status=weak_baseline`：训练模型效果仍弱；
- `model_crossval_binary_accuracy`：比单次随机 split 更可信；
- `devour_sandbox_passes/total`：机制沙箱是否通过。

不要把 `overall=ok` 解释为“模型已经好用”。

## 模型训练经验

当前训练器是纯标准库最小基线，不是深度学习或完整 RL。

重要教训：

1. 样本少且标签不平衡时，单次随机 split 的 accuracy 会严重误导。
2. 必须报告留一交叉验证和多数类基线。
3. 如果交叉验证低于多数类基线，应标记 `weak_baseline`，不能夸大模型效果。
4. 标签最好拆成 safety / success / verification / usefulness，不宜长期只用 high/reject。

## 开源吞噬安全边界

当前“自动吞噬全球开源前三项目”只能说完成到：

```text
只读采集 → README/license/元数据审计 → 机制级抽取 → 自写沙箱复现
```

不能说：

- 已复制或移植源码；
- 已完整复刻外部项目；
- 已完成 Hermes 主链路核心改造；
- 已自动吃透全球开源项目。

## 已抽取的三类机制

| 来源 | 机制 | Hermes 沙箱场景 |
|---|---|---|
| obra/superpowers | 技能门禁开发闭环 | `skill_gated_development_loop` |
| langchain-ai/langchain | Agent Graph + Trace + Evaluation | `mini_agent_graph_trace_eval` |
| TauricResearch/TradingAgents | 多角色正反审议 + 风险仲裁 | `multi_role_debate_risk_decision` |

## 未完成项目记忆

未来继续时优先围绕这些收敛，不要无限扩张：

1. 提升训练模型效果；
2. 把机制级沙箱接入真实任务；
3. Hermes 主链路原生核心改造仍未硬改；
4. 自动吞噬外部开源项目仍未完成源码级/能力级完整吸收。

## 操作纪律

- 做前先 `qr route`。
- 状态类结论必须读 `hermes_eval_center.py status` 或最新 JSON 报告。
- 不碰 `config.yaml`、`.env`、`auth.json`、Hermes 主链路源码，除非用户明确要求并有备份/回滚。
- 外部项目只读采集时，不 clone、不复制源码、不自动写核心。
