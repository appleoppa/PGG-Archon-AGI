# Agents-Hive 架构模式参考

来源：https://github.com/chef-guo/agents-hive（52 Stars, MIT License, Go + React）
评估日期：2026-05-18
评估人：Hermes Agent
学习价值：8/10 —— 架构模式层面的高价值参考，代码不可直接复用但设计思路值得吸收。

## 项目定位

agents-hive = Agent Runtime + Agent Harness + Quality Control Plane + Ops Workbench。
它不是聊天壳，不是工具集合，不是一次性 demo，不是黑盒自动优化，不是单 Agent 孤岛。它把 Web UI、CLI、HTTP API、IM Channel、Master Agent、SubAgent、MCP、Skill、HITL、记忆、执行轨迹、质量评测和运行时配置管理放到同一套链路里。

## 六大可学架构模式

### 1. 质量控制平面（Quality Control Plane）

最亮眼的部分。Hive 有完整的 Replay / Journal / Trace / Trajectory 四层体系：

- Journal：每一步执行的事件日志，包含决策依据和工具调用结果
- Trace：会话级执行链路，可追溯每一步的输入输出
- Trajectory：每一步的完整快照（模型输入、工具调用、输出），支持步骤级回放
- Replay：基于 Trajectory 重新执行会话，用于回归测试和失败复现

这对我们的启示：做"重任务"（如办案）时，如果每一步的执行轨迹都能回放，出了问题可以归因。当前 Hermes 的任务执行是一次性的，失败只能靠记忆回顾。

### 2. 工具运行时策略（Tool Runtime with Policy）

Hive 的工具调用不是直接"调函数"，而是有完整链路：

```
工具请求 → 策略检查 → HITL 审批（如需）→ sandbox 执行 → 结果追踪 → 审计记录
```

- toolruntime 包负责工具发现和执行调度
- runtimepolicy 包负责准入规则（什么工具可以调用、什么用户有权调用）
- skillhitl 包负责人机协同审批（危险操作需要人工确认）
- sandbox 包负责在隔离容器中执行命令

对我们的启示：我们的工具调用是直通的。如果需要让外部评估 Agent 或新的技能执行危险操作，需要一个策略层。

### 3. Agent 通信协议（ACP - Agent Communication Protocol）

Hive 有三个包实现 Agent 间通信：
- acpserver：ACP 协议服务端，接收远程 Agent 的连接
- acpclient：ACP 协议客户端，连接到远程 Agent
- a2abridge：Agent-to-Agent 桥接，负责消息路由和协议转换

ACP 是标准化的 Agent 间通信协议，不同于 Hermes 的 delegate_task 子代理模式。子代理是"父创建子的金字塔结构"，ACP 是"对等 Agent 互相通信的网状结构"。两种模式各有适用场景。

### 4. Master Agent 主循环设计

Master 包定义了完整的 ReAct 主循环（master.go 约 50KB）：
- SessionLoop：会话级循环，管理消息流和上下文
- Worker Pool：并发控制，MaxConcurrentTasks 和 MaxConcurrentAgents 两个维度
- 上下文压缩：config.CompactionConfig 控制上下文裁剪策略
- Session-scoped todos：每个会话有自己的任务列表，非全局
- 首 token 快路径：FirstTokenConfig 配置快速首 token 响应

### 5. Memory 与 KB 的明确边界

Hive 明确区分了两套系统：

| 维度 | Knowledge Base (KB) | Memory |
|------|---------------------|--------|
| 内容 | 项目/业务文档库 | 用户偏好、经验、项目片段备忘 |
| 存储 | kb.doc.meta, kb.doc.structure, kb.section.text | memory 表 |
| 访问 | 受会话绑定约束，需显式 domain 指定 | 默认每轮模型调用前按最新用户消息做相关召回 |
| 上下文注入 | 按 kb domain 加载 | 按 owner + domain 召回，不会全量塞入 |

这对我们的启示：当前 Hermes 的 skills 提取系统把"用户纠正"和"工作流"混在一起存储，可以考虑在提案阶段区分两类：可复用工作流→技能，用户偏好→memory。

### 6. Worker / Node 蜂巢模式

Hive 的远期目标是中心控制面 + 本地 Worker 蜂巢：
- 用户在自己的电脑/内网机器上安装 Hive CLI / Worker daemon
- 本地节点主动连接到中心系统，注册能力、领取任务、回传产物
- 所有能力通过中心侧的认证、策略、HITL、日志和对象存储治理
- nodes / task_queue 表是预留骨架

这与 Hermes 的 cron 远程执行模式有差异。Hermes 是"agent 在本机执行"，Hive 是"中心调度、本地执行、结果回传"。后者更适合分布式场景。

## 对我们的借鉴价值优先级

1. 质量控制平面（最高优先级）—— 复杂任务（如办案流程）需要可回放、可归因的执行轨迹
2. Memory vs KB 边界 —— 当前混合存储可以更清晰地区分
3. 工具策略层 —— 当技能/子代理扩展到一定规模后需要
4. ACP 协议 —— 当前 delegate_task 模式够用，暂时不需要
5. Worker 蜂巢 —— 未来多机器场景需要

## 技术栈对比

| 维度 | Agents-Hive | Hermes Agent |
|------|-------------|--------------|
| 语言 | Go + React/TS | Python（Hermes 核心）+ 代理工具 |
| 数据库 | PostgreSQL | JSONL 文件 + memory 注入 |
| 质量体系 | Replay / Journal / Trace / Trajectory | 无 |
| 工具策略 | policy / HITL / sandbox | 直通调用 |
| 通信协议 | ACP（标准 Agent 间协议） | delegate_task（Hermes 内部） |
| IM 通道 | 飞书/钉钉/企微/微信 | 飞书（部分）/ Telegram |
| 部署 | Docker Compose + sandbox | ~/.hermes 本地 |
