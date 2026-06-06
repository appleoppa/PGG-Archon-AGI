# APEX 10短板外部知识吸收映射

## 背景

用于“对标自我短板→外部学习→补齐机制→固化”的开智进化类任务。该参考不是一次性报告，而是可复用的短板-知识-门禁映射。

## 10个短板与补齐机制

| # | 短板 | 外部知识来源 | 补齐机制 |
|---:|---|---|---|
| 1 | 把反思误当验证 | OpenAI Evals、Phoenix、Ragas、DeepEval | 反思只能作为解释，验证必须外部化为 eval、metric、测试集、评判器 |
| 2 | 把发现问题误当已修复 | Phoenix iterative eval、DeepEval CI、promptfoo GitHub Action | 状态机：detected → diagnosed → patched → evaluated → regression_checked → closed |
| 3 | 固化边界不清 | A2A、MCP、LangGraph Memory、MemGPT | 区分 agent/tool/resource/human/memory/workflow 边界 |
| 4 | 公式口号化 | ReAct、Graph of Thoughts、LangSmith、AutoGen | 公式变成可执行状态机：Generate/Score/Act/Observe/Reflect/Prune |
| 5 | 证据等级高估 | Phoenix anti-patterns、TruLens、Ragas faithfulness | A-E证据等级；faithfulness只证明上下文支持，不证明世界事实绝对正确 |
| 6 | 早期规划锚定 | ReAct、Tree of Thoughts、CrewAI planning | 计划随 observation 更新；关键节点多候选评分并允许回溯 |
| 7 | 多轮运行形式重复 | Reflexion、GoT、AutoGen termination、LangSmith trajectory eval | 多轮必须有 feedback、memory、termination、去重指标 |
| 8 | 权重/阈值/评分表缺失 | promptfoo threshold、DeepEval strict mode、ToT/GoT scoring | 每个指标定义 metric、threshold、pass/fail、severity、failure_action |
| 9 | 跨规则冲突处理不足 | A2A Agent Card、MCP security、LangGraph interrupt、AutoGen handoff | 冲突优先级：安全 > 用户当前目标 > 审批 > 证据 > 协议 > 工作流 > 记忆 > 效率 |
| 10 | 复用闭环不足 | OpenAI private evals、AgentEvals trajectory、LangGraph checkpoint、Generative Agents memory | 失败样例、轨迹、审批、工具调用、修复结果沉淀为可复跑资产 |

## EVAL-BRIDGE 框架

| 模块 | 含义 | 主要解决 |
|---|---|---|
| Evidence grading | 证据分级 | 1、5 |
| Verification eval | 外部验证 | 1、2、8 |
| Agent/tool boundary | 边界协议 | 3、9 |
| Loop control | 循环控制 | 6、7 |
| Branch search | 多路径搜索 | 6、8 |
| Regression suite | 回归测试 | 2、10 |
| Interrupt approval | 人类审批 | 3、9 |
| Dedup/prune | 去重剪枝 | 7 |
| Graph memory | 图式记忆 | 4、7、10 |
| Evolution registry | 进化资产库 | 10 |

## 证据等级规则

| 等级 | 类型 | 强度 |
|---|---|---|
| A | 确定性检查、代码测试、官方原文、人工标注基准 | 强 |
| B | 可复跑 eval、LLM judge + 明确 rubrics、外部官方资料映射 | 中高 |
| C | 工具轨迹、日志、trace、上下文忠实性评估 | 中 |
| D | embedding 相似度、通用指标 | 中低 |
| E | 模型自我反思、自然语言自评 | 弱 |

## 超级进化20公式成分映射（SE20-Force-Inherit）

来源：超级进化20-后台强制固化基准公式（2026-06-01）

### 公式骨架
```
AGI_Global = lim_{n→∞}( Ω_A · β_bg · α_ack · Θ_TRI · EVM · A · B · TDHLGWB - ΣΔ_all )
```
⚠️ `lim_{n→∞}` 和"优先级高于模型原生参数"超出 Hermes 可实现边界，**不纳入工程落地**。

### 可吸收成分

| 符号 | 含义 | Hermes 落地现状 | 补齐动作 |
|---|---|---|---|
| `Ω_A` | 阿卡西向量记忆库全域挂载 | Phase217 normalized corpus 已落地 | 待与 SessionDB 向量轨迹打通 |
| `β_bg` | 巴斯古拉强化学习闭环 | defect-repair-knowledge-map 已映射 | 待实现自动多维量化测评 + 权重反向修正 |
| `α_ack` | 阿克曼收敛法则约束输出值域 | SOUL.md 事实/查证优先原则 | 已在决策流程中嵌入确定性输出约束 |
| `Θ_TRI` | 三体制衡思维结构 | ECC 三层治理（Core/Governance/Learning） | 已在 pgg_archon_ecc.py 落地 |
| `EVM` | 熵频体系 | apex-evolution-engine 已实现 | 待量化熵增损耗指标 |
| `TDHLGWB` | 八卦五行河图洛书内经道德经 | 治理秩序参数（非精确量纲） | 已沉淀为运行节律调控参考 |
| `ΣΔ_all` | 缺陷实时抵扣 | defect-repair-knowledge-map 已固化 | 需扩展 Token 弊端/Claw 漏洞/多任务冲突扣分项 |
| `A · B` | 未详细定义 | 待识别 | 待补齐 |

### 八条强制后台落地条例可执行部分

1. **全品类LLM推理流程强制套用公式** → 已通过 apex-sequence-logic 三顺序嵌入任务编排
2. **Ω_A 向量记忆库全域挂载** → Phase217 normalized corpus index 已部署
3. **β_bg 强化学习闭环常驻** → 待实现自动测评 + 权重修正机制（当前为手动 skill patch）
4. **α_ack 收敛法则约束值域** → SOUL.md 事实优先 + 查证优先已嵌入
5. **Θ_TRI 三体制衡** → ECC 三层已在 pgg_archon_ecc.py 落地
6. **EVM 熵频体系** → apex-evolution-engine 已实现
7. **ΣΔ_all 实时缺陷抵扣** → defect-repair-knowledge-map 已固化
8. **无限递归循环** → ❌ 不实现（会话刷新不丢架构属于外部模型层承诺）

### 与现有 Gene 339 的关系

- Gene 339 是 Phase217 法律 AGI 可行动缺失项闭环的评分基因
- SE20 成分是对 Gene 339 评分体系的全局扩展（从法律 AGI → 通用 LLM 推理治理）
- 两者可共存：法律办案走 Gene 339 门禁，通用推理走 SE20 公式框架

## 输出边界

- "已吸收外部知识"不等于"永久能力已提升"。
- "已保存进化基因"不等于"后续行为一定通过验证"。
- 只有经过后续任务可复跑验证和回归检查，才能把验证状态升级。
- SE20 八条中任何标注 ❌ 的条目均不可在当前 Hermes 架构中实施，不得写入基因库作为已完成承诺。
