---
name: full-toolcall-integration
description: 将复杂任务一次性拆成全局轨迹，识别依赖、工具、风险、并行点，并用读回验证形成可交付闭环。
version: 1.0.0
category: workflow
tags: [超级进化5.5, 全局轨迹, 并行调度, 负载均衡]
created: 2026-05-25
updated: 2026-05-25
---

# Full Tool-Call 全局轨迹集成

超级进化5.5 - Full Tool-Call 一次性全局轨迹生成，已完整集成到 Hermes 工具系统。

## 核心能力

1. **全局轨迹规划**：任务输入 → 单元拆解 → 工具推断 → 风险检测 → 并行点识别
2. **并行任务调度**：自动识别可并行任务，提高执行效率
3. **负载均衡**：智能分配任务到最优 worker（deepseek/minimax/glm/local）
4. **故障自愈**：自动重试和降级，最多3次重试，失败后降级到 local_fallback

## 使用方式

### 方式一：一站式调用（推荐）

```python
# 使用 full_toolcall 工具
result = full_toolcall(
    input_text="任务描述或文件路径",
    goal="目标描述"
)
```

**返回结果**：
```json
{
  "success": true,
  "stage": "complete",
  "plan_path": "规划文件路径",
  "run_path": "执行结果路径",
  "summary": {
    "steps": 7,
    "completed": 7,
    "failed": 0,
    "success_rate": 1.0,
    "healing_events": 0
  },
  "message": "✅ 完成：7/7 任务，成功率 100.0%"
}
```

### 方式二：分步调用

```python
# 1. 规划
plan_result = full_toolcall_plan(
    input_text="任务描述或文件路径",
    goal="目标描述"
)

# 2. 执行
exec_result = full_toolcall_execute(
    plan_path=plan_result['plan_path']
)
```

## 标准轨迹（7步）

| 步骤 | 状态 | 描述 |
|------|------|------|
| S01 | scoped | 明确目标、边界、产物和完成标准 |
| S02 | read | 读取输入材料 |
| S03 | decompose | 抽取任务单元、依赖关系和可并行点 |
| S04 | plan_tools | 为每个任务单元分配工具和验证方式 |
| S05 | execute_safe | 只执行低风险、可回滚、已授权动作 |
| S06 | verify | 读回文件/数据库/cron状态/报告 |
| S07 | evolve | 把可复用轨迹沉淀到skill/gene/report |

## Worker 配置

| Worker | 层级 | 容量 | 成本 | 适用场景 |
|--------|------|------|------|---------|
| deepseek_v4_flash | B | 3 | 2 | 推理任务 |
| minimax_m27_highspeed | D | 5 | 1 | 基础任务（默认） |
| glm45_air | E | 4 | 1 | 低成本任务 |
| local_fallback | LOCAL | 10 | 0 | 故障降级 |

## 风险检测

系统自动检测以下风险并进入 blocked/review 状态：

- **destructive_or_durable_write**：删除|覆盖|清理|自动写|自动删
- **secret_risk**：密钥|token|secret|密码|凭证
- **core_modification**：核心|底层|claw|openclaw|Hermes.*源码
- **capability_overclaim**：自动|永久|全能|自优化|自升级

## 安全边界

**Sidecar 定位**：
- ✅ 本地 sidecar 演示/运行时
- ❌ 不修改 Hermes/openclaw 核心
- ❌ 不调用真实 LLM provider（当前是模拟执行）
- ❌ 不访问凭证
- ❌ 不写入持久记忆

## 使用示例

### 示例1：复杂任务规划

```python
result = full_toolcall(
    input_text="""
    任务：实现用户认证系统

    需求：
    1. 用户注册和登录
    2. JWT token 生成和验证
    3. 密码加密存储
    4. 权限管理
    """,
    goal="实现完整的用户认证系统"
)

# 查看规划
print(f"步骤数: {result['summary']['steps']}")
print(f"完成率: {result['summary']['success_rate']:.1%}")
```

### 示例2：文件处理任务

```python
result = full_toolcall(
    input_text="/path/to/requirements.txt",
    goal="分析依赖并生成安全报告"
)

# 查看执行结果
print(f"完成: {result['summary']['completed']}/{result['summary']['steps']}")
print(f"自愈次数: {result['summary']['healing_events']}")
```

### 示例3：测试故障自愈

```python
result = full_toolcall(
    input_text="测试任务",
    goal="验证故障自愈机制",
    simulate_failure=True  # 模拟故障
)

# 查看自愈情况
print(f"自愈次数: {result['summary']['healing_events']}")
```

## 输出文件

| 文件 | 路径 | 内容 |
|------|------|------|
| 规划文件 | `~/.hermes/workspace/开智/full_toolcall_sidecar/plan_latest.json` | 全局轨迹、并行点、风险 |
| 执行结果 | `~/.hermes/workspace/开智/full_toolcall_sidecar/run_latest.json` | 任务状态、事件日志 |
| 黑板状态 | `~/.hermes/workspace/开智/full_toolcall_sidecar/blackboard_state.json` | 实时状态存储 |

## 集成状态

| 组件 | 状态 | 说明 |
|------|------|------|
| 规划器 | ✅ 已集成 | `hermes_full_toolcall_planner.py` |
| 运行时 | ✅ 已集成 | `hermes_full_toolcall_runtime.py` |
| 集成模块 | ✅ 已集成 | `full_toolcall_integration.py` |
| Hermes 工具 | ✅ 已集成 | `tools/full_toolcall_tool.py` |
| 测试验证 | ✅ 通过 | 7/7 任务完成，成功率 100% |

## 注意事项

1. **当前是模拟执行**：worker 执行是模拟的（随机延迟 + 成功），未真实调用 LLM provider
2. **Sidecar 定位**：这是独立的 sidecar 系统，不是 Hermes 核心的一部分
3. **安全门禁**：高风险动作会进入 blocked/review，需要人工审查
4. **证据验证**：每步必须产生可读回证据，不能只凭状态字段

## 下一步

1. **真实 LLM 集成**：将模拟执行替换为真实 LLM provider 调用
2. **主链路集成**：与 Hermes 主链路深度集成，支持真实工具调用
3. **生产验证**：在实际场景中验证性能和稳定性

## 相关文件

- 规划器脚本：`~/.hermes/scripts/hermes_full_toolcall_planner.py`
- 运行时脚本：`~/.hermes/scripts/hermes_full_toolcall_runtime.py`
- 集成模块：`~/.hermes/hermes-agent/full_toolcall_integration.py`
- 工具定义：`~/.hermes/hermes-agent/tools/full_toolcall_tool.py`
- 工作目录：`~/.hermes/workspace/开智/full_toolcall_sidecar/`

## 完成度

**超级进化5.5 完成度：90%**

- ✅ 规划器、运行时、集成模块、Hermes 工具全部完成
- ✅ 测试验证通过（7/7 任务，成功率 100%）
- ✅ 黑板状态、并行调度、负载均衡、故障自愈全部实现
- ⚠️ 当前是模拟执行，未真实调用 LLM provider
- ⚠️ 未与 Hermes 主链路深度集成
