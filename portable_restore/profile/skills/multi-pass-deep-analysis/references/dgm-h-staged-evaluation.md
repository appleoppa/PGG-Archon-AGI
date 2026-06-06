# DGM-H 分阶段评估模式 (staged evaluation)

## 来源
- **lemoz/darwin-godel-machine** (★13): Python DGM实现
  - Archive系统: 所有验证过的agent存档, 用performance+novelty双指标
  - Benchmark驱动: 不是自评, 而是跑benchmark验证修改
  - 存档路径: 所有编译过的变体都保存(stepping stones matter)

- **tylergibbs1/evolve** (★2): TypeScript DGM-H实现
  - 核心洞察: "underlying LLM stays frozen. All gains come from evolving the code that wraps it."
  - Staged evaluation: cheap screen → full eval (先筛后精)
  - Parent selection: sigmoid + novelty bonus
  - Archive: 所有compiled variant都保留(stepping stones)

## 对multi-pass的映射

| DGM-H概念 | multi-pass中的对应 |
|-----------|------------------|
| Archive（存档） | multi-pass-archive.json |
| Staged evaluation | screening(轻量) → deep dive(深度) |
| Population（种群） | 存档的分解策略集合 |
| Benchmark（基准） | 自检清单: 正交性/覆盖率/效率 |
| Novelty bonus（新颖性） | missed_directions字段 |
| Parent selection（选祖策略） | 下次任务时加载最近最相似的分解策略 |

## 一句话原理
冻结底层LLM, 只改进包装层(代码+提示+工具+工作流)。所有能力提升来自"我们怎么做", 而不是"我们换成什么模型"。
