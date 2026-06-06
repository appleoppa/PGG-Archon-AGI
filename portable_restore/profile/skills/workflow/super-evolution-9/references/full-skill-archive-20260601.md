---
name: super-evolution-9
description: 超级进化9 - EvoMaster 原生进化核心引擎
version: 1.0.0
author: Claude-opus-4-7
created: 2026-05-25
tags: [evolution, evo-master, trace-hashpool, knowledge-cache, strategy-evolution]
---

# 超级进化9 - EvoMaster 原生进化核心引擎

## 核心目标

实现 CLAW 轨迹级自进化与知识永久沉淀，让 Hermes 具备类科研智能体的自主优化能力。

## 核心公式

### 1. 迭代进化总目标

```
max_{π_claw} E_{τ~π_claw}[ R_exec(τ) + λ · K_claw(τ) ]
```

- `π_claw`：CLAW 实时调度策略
- `R_exec`：指令执行成功率、轨迹合规收益
- `K_claw`：CLAW 轨迹知识沉淀缓存
- `λ`：进化复用权重（默认 0.3）

### 2. 策略自更新迭代式

```
π^(t+1)_claw = GPT-Stream(τ^(t), K_claw, Constraint_sandbox)
```

依托大模型流式推理，基于上一轮执行轨迹、历史知识缓存与沙箱约束，自动迭代更新 CLAW 调用策略。

### 3. 知识缓存压缩复用公式

```
K_claw = HashPool(Filter(τ_valid))
```

对有效执行轨迹去噪过滤、指纹哈希池固化，实现跨会话、跨任务的能力复用。

## 已落地产物

### 1. EvoMaster 核心引擎

**路径**：`~/.hermes/hermes-agent/evo_master.py`

**核心类**：
- `Trajectory`：执行轨迹数据类
- `Strategy`：CLAW 调度策略数据类
- `KnowledgeCache`：知识缓存池（SQLite 后端）
- `EvoMaster`：进化引擎主类

**核心方法**：
- `record_trajectory()`：记录执行轨迹
- `evolve_strategy()`：策略自更新迭代
- `get_recommended_actions()`：基于知识缓存推荐动作
- `import_from_eval_center()`：从 Rust 评估中心导入真实轨迹

**数据库**：`~/.hermes/evo_master.db`

### 2. Trace HashPool Sidecar

**路径**：`~/.hermes/scripts/hermes_trace_hashpool.py`

**功能**：
- 从 Rust 评估中心 (`eval_center.db`) 读取真实工具调用轨迹
- 过滤有效轨迹（验证通过、工具调用成功）
- 哈希去重，写入 HashPool
- 生成技能候选文件和失败反例

**工作区**：`~/.hermes/workspace/trace_hashpool/`
- `hashpool.jsonl`：轨迹哈希池
- `skill_candidates/`：技能候选 Markdown 文件
- `failure_examples/`：失败反例 Markdown 文件
- `reports/`：运行报告

**命令**：
```bash
# 从评估中心导入真实轨迹
python3 ~/.hermes/scripts/hermes_trace_hashpool.py --from-eval-center --limit 100

# 仅导入已评分轨迹
python3 ~/.hermes/scripts/hermes_trace_hashpool.py --from-eval-center --only-scored --min-score 0.7
```

### 3. Hermes 工具集成

**路径**：`~/.hermes/hermes-agent/tools/evo_master_tool.py`

**工具**（6 个，全部注册到 `skills` toolset）：
- `evo_master_import`：从评估中心导入轨迹
- `evo_master_score`：使用 Rust 评估中心评分（调用 `hermes_eval_center.score_trace`）
- `evo_master_evolve`：执行策略进化
- `evo_master_recommend`：推荐动作序列
- `evo_master_stats`：获取统计信息
- `evo_master_select_strategy`：跨会话策略选择器（按任务匹配最优策略）

**Toolset**：`skills`

**使用示例**：
```python
# 导入轨迹
result = evo_master_import(limit=100)

# 策略进化
result = evo_master_evolve()

# 推荐动作
result = evo_master_recommend(task="read_file")

# 统计信息
result = evo_master_stats()
```

### 4. 策略选择器

**路径**：`~/.hermes/scripts/hermes_strategy_selector.py` (10.1 KB)

**功能**：
- 根据任务类型自动选择最优策略版本
- 推荐最优动作序列
- 任务聚类（7个集群：file_ops, web_ops, search_ops, terminal_ops, edit_ops, skill_ops, other）
- 导出路径缓存到 `workspace/evo_master_db/path_cache.json`

**命令**：
```bash
# 为任务选择策略
python3 ~/.hermes/scripts/hermes_strategy_selector.py --task "read_file"

# 查看集群策略
python3 ~/.hermes/scripts/hermes_strategy_selector.py --cluster file_ops

# 对所有任务聚类
python3 ~/.hermes/scripts/hermes_strategy_selector.py --cluster-all

# 导出路径缓存
python3 ~/.hermes/scripts/hermes_strategy_selector.py --export
```

### 5. 多 LLM 策略自更新服务

**路径**：`~/.hermes/scripts/hermes_multi_llm_strategy.py` (9.7 KB)

**功能**：
- 接入量子路由 `qr` 选择模型层级（A/B/C/D/E）
- 多模型投票评估策略（A/B/C 三级）
- 自动进化并投票通过门禁
- 导出进化日志到 `workspace/evo_master_db/evolution_log.json`

**命令**：
```bash
# 测试路由
python3 ~/.hermes/scripts/hermes_multi_llm_strategy.py --route "复杂策略优化"

# 执行多 LLM 自动进化
python3 ~/.hermes/scripts/hermes_multi_llm_strategy.py --evolve

# 导出进化日志
python3 ~/.hermes/scripts/hermes_multi_llm_strategy.py --export-log
```

### 6. 策略配置写入器（带安全门禁）

**路径**：`~/.hermes/scripts/hermes_strategy_config_writer.py` (12.3 KB)

**安全机制**：
1. **dry-run 模式**：默认不实际写入
2. **配置备份**：写入前自动备份到 `workspace/evo_master_db/config_backups/`
3. **评分门禁**：策略性能必须 ≥ 0.5
4. **投票门禁**：多模型投票必须 ≥ 7.0
5. **白名单**：仅允许写入 6 个字段（lambda_weight, min_performance, auto_evolve, import_interval_hours, score_threshold, strategy_version）
6. **回滚机制**：支持一键回滚到任意备份

**命令**：
```bash
# 检查门禁
python3 ~/.hermes/scripts/hermes_strategy_config_writer.py --check

# 预览更改（dry-run）
python3 ~/.hermes/scripts/hermes_strategy_config_writer.py --preview

# 实际应用（带备份）
python3 ~/.hermes/scripts/hermes_strategy_config_writer.py --apply

# 回滚到最新备份
python3 ~/.hermes/scripts/hermes_strategy_config_writer.py --rollback

# 列出所有备份
python3 ~/.hermes/scripts/hermes_strategy_config_writer.py --list-backups
```

### 7. Cron 自动化

**任务名称**：超级进化9-EvoMaster自动进化

**Job ID**：`2bec663a42d4`

**频率**：每 6 小时

**流程**：
1. 从 Rust 评估中心导入最新 100 条真实轨迹（去重）
2. 执行策略进化（基于知识缓存的最优轨迹）
3. 生成统计报告

**查看**：
```bash
hermes cronjob list | grep "超级进化9"
```

## 核心数据流

```
Hermes 工具调用
  ↓
trace_hooks.py (核心改造)
  ↓
hermes_eval_center.so (Rust 后端)
  ↓
eval_center.db (267+ 条真实轨迹)
  ↓
hermes_trace_hashpool.py (过滤 + 哈希去重)
  ↓
hashpool.jsonl (292+ 条有效轨迹)
  ↓
evo_master.py (import_from_eval_center)
  ↓
evo_master.db (300+ 条知识缓存)
  ↓
evolve_strategy() (策略 v0 → v1 → v2 ...)
  ↓
get_recommended_actions() (推荐最优动作)
```

## 使用场景

### 场景 1：手动导入轨迹并进化

```python
from evo_master import get_evo_master

evo = get_evo_master()

# 从评估中心导入
result = evo.import_from_eval_center(limit=200)
print(f"导入 {result['imported']} 条轨迹")

# 策略进化
strategy = evo.evolve_strategy()
print(f"策略 v{strategy.version}, 性能 {strategy.performance:.2f}")

# 推荐动作
actions = evo.get_recommended_actions("terminal")
print(f"推荐 {len(actions)} 个动作")
```

### 场景 2：使用 Hermes 工具

在 Hermes 会话中：

```
使用 evo_master_import 工具从评估中心导入最新 100 条轨迹
使用 evo_master_evolve 工具执行策略进化
使用 evo_master_stats 工具查看统计信息
```

### 场景 3：Cron 自动化

Cron 任务每 6 小时自动运行，无需人工干预。

## 验证方法

### 1. 检查数据库

```bash
# 评估中心轨迹数
sqlite3 ~/.hermes/eval_center.db "SELECT COUNT(*) FROM traces"

# EvoMaster 轨迹数
sqlite3 ~/.hermes/evo_master.db "SELECT COUNT(*) FROM trajectories"

# HashPool 轨迹数
wc -l ~/.hermes/workspace/trace_hashpool/hashpool.jsonl
```

### 2. 检查策略版本

```python
from evo_master import get_evo_master
evo = get_evo_master()
print(f"当前策略: v{evo.current_strategy.version}")
print(f"性能: {evo.current_strategy.performance:.2f}")
```

### 3. 检查 Top 轨迹

```python
from evo_master import get_evo_master
evo = get_evo_master()
top = evo.knowledge_cache.get_top_trajectories(limit=5)
for i, t in enumerate(top, 1):
    print(f"{i}. {t.task}: 价值={t.total_value:.2f}")
```

## 关键指标

| 指标 | 当前值 | 说明 |
|---|---|---|
| 评估中心轨迹数 | 290+ | Rust 后端自动记录 |
| HashPool 轨迹数 | 292+ | 过滤后的有效轨迹 |
| EvoMaster 轨迹数 | 300+ | 知识缓存中的轨迹 |
| 策略版本 | v1+ | 自动进化的策略版本 |
| λ 权重 | 0.3 | 知识复用权重 |
| Cron 频率 | 6 小时 | 自动化周期 |

## 未完成部分（明确挂起）

| 未完成项 | 状态 | 说明 |
|---|---|---|
| CLAW/Hermes 核心源码级原生改造 | 挂起 | 需单独授权、备份、回滚、安全审计 |
| Rust/Go 生产级原生模块 | 挂起 | Python sidecar 稳定后再考虑 |
| 多 LLM 后台实时策略自更新服务 | 挂起 | 需真实服务、日志、调度策略 |
| 自动将策略更新写入核心配置 | 挂起/不建议 | 需高安全门禁，防止误写 config/凭证 |
| 大规模真实轨迹池 | 进行中 | 当前 300+ 条，需长期真实任务积累 |
| 轨迹质量评分与评估中心深度联动 | 未完成 | 接入评估中心 score/train/predict |
| 跨会话自动复用最优路径 | 部分完成 | 有技能/基因/HashPool，但未建自动策略选择器 |

## 陷阱与教训

1. **指纹去重**：`add_trajectory()` 内部已做指纹去重，返回 False 表示重复
2. **评估中心状态**：`state='candidate'` 不代表无效，需结合 `score` 和 `tool_calls.success` 判断
3. **工具调用成功率**：所有 `tool_calls` 都 `success=true` 时认定轨迹通过
4. **Handler 签名**：Hermes 工具 handler 必须接受 `args: Dict[str, Any]` 作为第一个参数
5. **策略进化前提**：知识缓存中必须有轨迹，否则策略保持不变
6. **Cron 工具注入陷阱**：如 Hermes 工具调用返回 `unexpected keyword argument 'task_id'`，说明当前工具 handler 与调度器注入参数不兼容；此时不得把进化说成完成，应明确报告工具层失败，并优先修复 handler 签名以兼容 `**kwargs` 或平台注入字段后再重跑闭环

## 下一步优化方向

1. **轨迹质量评分**：接入评估中心的 `score_trace()` 和 `train()` 方法
2. **策略选择器**：自动根据任务类型选择最优策略
3. **技能蒸馏**：从 HashPool 的技能候选自动生成 SKILL.md
4. **失败复盘**：从失败反例中提取反模式和避坑指南
5. **多模型策略**：不同任务类型使用不同模型策略

## 参考文档

- 超级进化9原文：`/Users/appleoppa/Desktop/进化文件/超级进化/超级进化9-原生进化核心公式释义.md`
- 吸收报告：`~/.hermes/workspace/开智/超级进化9-原生进化核心公式吸收报告.md`
- 未完成项报告：`~/.hermes/workspace/开智/超级进化9未完成项报告.md`
- 核心改造文档：`~/.hermes/core-reform/docs/`
