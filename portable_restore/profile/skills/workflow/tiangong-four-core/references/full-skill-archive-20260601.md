---
name: tiangong-four-core
description: 天工技能 - 四核协同编排（evolver/autoresearch/openhands/superpowers）+ GPT 主导 + 状态机 + 门禁
version: 1.0.0
author: Claude-opus-4-7
created: 2026-05-25
tags: [tiangong, four-core, orchestrator, evolver, autoresearch, openhands, superpowers, super-evolution-11]
---

# 天工技能 - 四核协同编排

## 概述

超级进化11 的核心能力：TianGong（天工）四核协同编排系统。

**核心公式**：
```
ΔG = (C_total · Λ_gene · Ω_entropy · τ_traj) / (H_info · t)
max π_skill E[R_exec(τ) + λ · K_cache(τ)]
```

**四核分工**：
- **evolver**：缺陷扫描、失败归因、轨迹回收、基因沉淀、回测
- **autoresearch**：多源检索（arxiv/github）、交叉验证、知识蒸馏
- **openhands**：文件/终端/浏览器执行规划与工具映射
- **superpowers**：澄清、设计、拆解、验证、审查、交付

## 已落地产物

### 5 个 Hermes 工具

| 工具 | 功能 | 后端 |
|---|---|---|
| `tiangong_evolver` | 缺陷扫描、基因进化、回测 | EvoMaster（超级进化9）|
| `tiangong_autoresearch` | arxiv/github 检索、蒸馏 | arxiv API + gh CLI |
| `tiangong_openhands` | 执行规划、工具映射 | Hermes 原生工具集 |
| `tiangong_superpowers` | 工程流程、质量门禁 | Hermes 原生 skills |
| `tiangong_orchestrator` | 四核协同主编排器 | 状态机 + 门禁 |

### 状态机（10 阶段）

```
received → scoped → gated → routed → planned → assigned → executing → verifying → audited → completed
                         ↘ blocked / repairing / failed / aborted
```

### 门禁（5 级）

| 门禁 | 检查项 |
|---|---|
| **G0 入口** | 目标、范围、副作用、工具需求、验收标准、不确定性 |
| **G1 计划** | 主路径、备选路径、验证方法、风险点、产物定义 |
| **G2 执行** | 依赖齐全、输入存在、操作安全、可回滚、证据卡准备 |
| **G3 验证** | 测试/读回/检索/构建/状态检查 |
| **G4 交付** | 需求覆盖、证据闭环、文件变更透明、风险披露、完成态准确 |

## 使用场景

### 场景 1：研究型任务

```
任务：研究并实现 Transformer 注意力机制优化

1. tiangong_orchestrator(task="...", mode="plan")
   → 生成四核协同计划

2. tiangong_autoresearch(query="transformer attention", sources=["arxiv"])
   → 检索最新论文

3. tiangong_superpowers(action="design")
   → 生成设计模板

4. tiangong_openhands(action_type="plan", task="...")
   → 生成执行计划

5. tiangong_evolver(mode="evolve")
   → 沉淀为基因/策略
```

### 场景 2：缺陷修复任务

```
任务：修复登录失败 bug

1. tiangong_evolver(mode="scan", min_score=0.5)
   → 扫描低分轨迹，找出失败模式

2. tiangong_superpowers(action="clarify")
   → 澄清问题范围

3. tiangong_openhands(action_type="plan", task="修复登录")
   → 生成修复执行计划

4. tiangong_superpowers(action="verify")
   → 验证修复效果

5. tiangong_evolver(mode="regress")
   → 回测，确保不复发
```

### 场景 3：完整闭环任务

```
任务：设计并实现用户认证系统

1. tiangong_orchestrator(task="...", mode="execute")
   → 生成完整执行序列（6 步）

2. 按序列执行：
   - superpowers clarify
   - autoresearch research
   - superpowers design
   - openhands plan
   - superpowers verify
   - evolver evolve
```

## 核心原则

### 1. GPT 主导规则

- 量子路由用于展开候选通道
- 用户要求"以 GPT 为主"时，必须用 GPT 通道作为主裁判
- 若 `qr route` 自动选到低阶通道，应显式调用 `qr tier B` 确认 GPT 通道
- GPT 主脑负责最终路径选择、冲突消解、真实性边界、补齐落地和交付状态判断

### 2. 真实性四件套

凡写"已支持""已实现""可自动执行""已集成"，必须同时满足：
1. 有实际代码入口或配置绑定
2. 有一次真实运行记录
3. 有可复现的输入输出样例
4. 有最近一次验证时间

少一项时，只能写"流程目标""设计意图""可执行方案""待验证能力"。

### 3. 证据卡模板

```yaml
evidence_card:
  task_goal: ""
  route_decision:
    qr_route: ""
    gpt_tier_check: ""
    selected_main_path: ""
    backup_path: ""
  four_core_roles:
    evolver: ""
    autoresearch: ""
    openhands: ""
    superpowers: ""
  inputs:
    files_read: []
    commands_run: []
    sources_checked: []
  actions_taken: []
  outputs:
    files_created: []
    files_modified: []
    findings: []
  verification:
    checks_performed: []
    pass: true
    failures: []
  reality_gate:
    code_or_config_entry: ""
    run_record: ""
    reproducible_io_sample: ""
    latest_verification_time: ""
  unresolved_risks: []
```

## 工具详细说明

### tiangong_evolver

**模式**：
- `scan`：缺陷扫描，找出低分/失败轨迹
- `evolve`：基因沉淀，触发策略进化
- `regress`：回测，检查最优轨迹可复现性
- `stats`：统计信息

**后端**：EvoMaster（超级进化9）
- 410 条知识缓存
- 策略 v2，性能 1.24
- λ 权重 0.3

### tiangong_autoresearch

**来源**：
- `arxiv`：arxiv API 论文检索
- `github`：gh CLI 仓库检索
- `web`：提示使用 web_search 工具

**返回**：
- 论文列表（标题、摘要、作者、链接）
- 仓库列表（名称、描述、星数、URL）

### tiangong_openhands

**动作**：
- `plan`：基于任务生成执行计划，推荐 Hermes 工具
- `map_tools`：OpenHands 概念到 Hermes 工具的映射
- `stats`：可用 toolset 统计

**工具映射**：
- OpenHands.bash → terminal
- OpenHands.editor → patch / write_file
- OpenHands.file_read → read_file
- OpenHands.file_search → search_files
- OpenHands.browser → browser
- OpenHands.gui → computer_use
- OpenHands.python → execute_code
- OpenHands.delegate → delegate_task

### tiangong_superpowers

**动作**：
- `clarify`：澄清检查清单（5 项）
- `design`：设计模板（6 个维度）
- `decompose`：拆解原则（5 条）
- `verify`：验证方法矩阵（4 类）
- `review`：审查检查清单（6 项）
- `deliver`：交付检查清单（6 项）
- `list_skills`：列出可用 Hermes skills（75 个）

### tiangong_orchestrator

**模式**：
- `plan`：生成四核协同计划（状态机 + 门禁 + 四核分工）
- `execute`：生成执行序列（6 步标准流程）
- `status`：系统状态

**四核分工逻辑**：
- 根据任务关键词自动分配职责
- 支持自定义启用的核心列表

## 验证方法

### 1. 工具注册验证

```python
from tools.registry import registry
tiangong_tools = [
    'tiangong_evolver',
    'tiangong_autoresearch',
    'tiangong_openhands',
    'tiangong_superpowers',
    'tiangong_orchestrator',
]
for tool in tiangong_tools:
    assert registry.get_schema(tool) is not None
```

### 2. 端到端调用验证

```python
# orchestrator status
r = registry.dispatch('tiangong_orchestrator', {'task': '测试', 'mode': 'status'})
assert r['success'] == True

# evolver stats
r = registry.dispatch('tiangong_evolver', {'mode': 'stats'})
assert 'current_strategy' in r

# autoresearch arxiv
r = registry.dispatch('tiangong_autoresearch', {
    'query': 'transformer',
    'sources': ['arxiv'],
    'max_results': 2
})
assert 'results' in r

# openhands plan
r = registry.dispatch('tiangong_openhands', {
    'action_type': 'plan',
    'task': '修改配置文件'
})
assert 'execution_path' in r

# superpowers list_skills
r = registry.dispatch('tiangong_superpowers', {'action': 'list_skills'})
assert r['available_skills'] > 0
```

## 关键指标

| 指标 | 当前值 |
|---|---|
| **工具数** | 5 个 |
| **状态机阶段** | 10 个 |
| **门禁级别** | 5 级 |
| **Evolver 轨迹** | 410 条 |
| **Evolver 策略** | v2 |
| **可用 skills** | 75 个 |
| **arxiv 检索** | ✅ 可用 |
| **github 检索** | ✅ 可用（需 gh CLI）|

## 未实际接入部分

| 项目 | 状态 | 说明 |
|---|---|---|
| **imbue-ai/evolver** | ⚠️ 未接入 | 已有 darwinian-evolver skill，可激活 |
| **autoresearch GitHub 项目** | ⚠️ 未接入 | 用 arxiv API + gh CLI 替代 |
| **OpenHands docker 沙箱** | ❌ 明确不接入 | 重量级，Hermes 原生工具已覆盖 90% 能力 |
| **superpowers GitHub 项目** | ⚠️ 未接入 | Hermes 原生 skills 已覆盖 |

## 下一步优化

1. **激活 darwinian-evolver skill**：接入 imbue-ai 的 evolver 项目
2. **arxiv 缓存**：缓存论文检索结果，避免重复请求
3. **github 深度集成**：接入 GitHub 进化工厂（超级进化2）
4. **多模型投票**：接入超级进化9 的多 LLM 投票机制
5. **证据卡自动生成**：每次四核协同自动生成证据卡

## 参考文档

- 超级进化11原文：`~/Desktop/进化文件/超级进化/超级进化11-天工技能.md`
- Module H：`apex-hermes-evolution-engine/SKILL.md`
- Reference：`apex-hermes-evolution-engine/references/2026-05-22-tiangong-four-core-orchestration.md`
- 吸收记录：`~/.hermes/workspace/存档/.../超级进化11_天工技能吸收记录.md`
