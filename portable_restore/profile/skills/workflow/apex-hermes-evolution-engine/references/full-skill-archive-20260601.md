---
name: apex-hermes-evolution-engine
description: Use when learning complex materials or improving Hermes workflows by turning real task traces, long context, search results, and subagent findings into verified reusable skills without fabricating external API or background evolution. Includes PGG Archon sidecar evolution chains with ARS reports, semantic dedup gates, promotion gates, native tool status surfaces, and evidence-chain readback.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [apex, evolution, skills, memory, context, trajectory, subagents]
    related_skills: [manual-evolution-loop, hermes-evolution, search-skillbank, subagent-driven-development, file-system-management]
---

# APEX Hermes Evolution Engine

## Overview

本技能把 `/Users/appleoppa/Desktop/进化文件/` 的 14 份材料，加上 `/Users/appleoppa/Desktop/超级进化12-吞噬自进化.md`，融合为一个可执行的 Hermes 进化引擎。核心不是虚构“底层自动进化”或“多模型已调用”，而是把每次真实任务转成可验证、可复用、可审计的技能资产。

统一公式：

```text
真实上下文获取
→ 技能选择与任务拆解
→ 子智能体/工具执行
→ 结果验证与反幻觉审查
→ 价值感知压缩
→ 成功轨迹/失败轨迹沉淀
→ 技能库/记忆/规则更新
→ 下次任务复用
```

一句话：**检索获取事实，上下文提炼规则，记忆保存经验，轨迹驱动技能进化。**

## When to Use

使用场景：

- 用户要求“学习一批材料、举一反三、融会贯通、沉淀技能”。
- 长文档、复杂上下文、历史会话、项目轨迹需要提炼成可复用流程。
- 任务需要多 subagents 并行学习、审查、综合。
- 复杂检索、科研分析、系统优化、开智进化、技能库更新。
- 任务完成后出现可复用成功模式或高价值失败教训。

不要用于：

- 单句问答、简单翻译、一次性小修改。
- 无验证条件却要求声称“完整完成”的任务。
- 要求越权修改 Hermes / claw 核心、凭证、外部 API、长期后台服务的任务。
- 只凭愿景材料宣称已经实现 Rust/Go/C 底层能力或外部多模型调用。

## Core Principles

### 1. 技能化优先

复杂能力不要停留在临场随机推理，应拆成可触发、可执行、可验证的 Skill：

- 搜索技能：关键词扩写、实体溯源、时间限定、多源验证、上下文回溯。
- 上下文学习技能：从长材料中提炼原则、流程、触发条件、风险边界。
- 记忆技能：保存长期稳定、跨任务复用、可触发的信息。
- 轨迹技能：从成功和失败执行轨迹中提炼下一次可复用的路径。

### 2. Select-Read-Act-Review-Evolve

所有复杂任务采用统一骨架：

```text
Select：判断任务类型和应加载技能
Read：读取技能、文件、上下文、真实状态
Act：用工具或子智能体执行
Review：核验事实、输出、约束和副作用
Evolve：把可复用模式沉淀为技能、记忆或规则
```

### 3. 上下文学习目标是“生成技能”

读长文档不是只做摘要，而是生成可迁移的自然语言技能卡：

```text
输入材料
→ 多角度提问 / Challenger
→ 解题与规则抽取 / Reasoner
→ 质量审查 / Judge
→ 反例与跨场景重放 / Replay
→ 稳定规则压缩为 Skill
```

### 4. 全局轨迹优先 / Full Tool-Call 边界

复杂任务开始前，先建立最小可执行全局轨迹：

```text
目标 → 约束 → 输入 → 工具 → 并行点 → 验证点 → 风险点 → 回退路径
```

超级进化5.5的“Full Tool-Call一次性全局轨迹”吸收为**任务前轨迹规划和批量工具编排原则**，不是无条件一次性完成所有任务。

可采纳：

```text
- 执行前生成全局轨迹，减少无效 execute-review-reflect 循环；
- 能并行且无依赖的检查/读取/验证可批量执行；
- 把工具结果、失败原因、回退路径写入同一证据卡；
- 用状态板记录 pending / in_progress / completed / blocked；
- 每轮结束把可复用轨迹沉淀到 skill/gene/report。
```

禁止夸大：

```text
- 不能把“全局轨迹”理解为不验证、不分步、不回退；
- 不能声称黑板多LLM并行调度、负载均衡、故障自愈已经底层实现，除非有真实代码入口和运行记录；
- 不能为了减少LLM调用而跳过必要的文件读回、测试、备份和安全门禁；
- 小任务不强制全局轨迹，避免过度规划。
```

执行门禁：

```text
Full Tool-Call 可用条件 = 目标清楚 + 依赖可分解 + 工具副作用安全 + 有验证点 + 有回退路径。
任一条件缺失 → 回到普通 Select-Read-Act-Review-Evolve。
```

公式口径：`ΔG_ultimate` 只作为“全局状态板、完整轨迹、收敛、负载、故障恢复、Hermes边界、知识库、基因库、上下文到技能”的综合优化隐喻，不代表已实现永久自优化底层引擎。

### 5. 价值感知压缩

压缩不是机械截断。保留优先级：

```text
用户目标 > 硬约束 > 文件路径/命令/API > 已验证结论 > 错误原因 > 中间过程
```

丢弃：重复解释、无效推理、过期截图、未验证噪声。

### 6. 子智能体结果必须回收

任何 subagent 结束后，主会话必须回收并索引：

```text
做了什么；
读了什么；
发现了什么；
修改了什么；
风险是什么；
可沉淀什么；
证据在哪里。
```

### 7. 进化必须受真实性边界约束

不得声称：

- 已调用 GPT / Claude / 外部多模型，除非有真实调用记录。
- 已长期后台持续学习，除非存在真实 cron / 服务 / 日志。
- 已修改 Hermes / claw 核心，除非实际改代码并验证。
- 已完成科研实验，除非真实执行并有数据。

### 8. 智能排版 / Standard Output Gate

APEX 输出默认启用“智能排版门禁”：最终答复不是把信息堆出来，而是按任务类型自动选择最清晰、最可核验的 Markdown 结构。

#### 8.1 默认输出骨架

除非用户明确要求纯命令、纯代码、极短答复或指定模板，默认按以下顺序组织：

```text
结论 / 当前状态
→ 关键数据表
→ 证据与核验
→ 风险 / 未完成 / 边界
→ 下一步或交付物
```

#### 8.2 状态字段规范

涉及任务进度、系统状态、文件状态、办案状态、进化状态时，必须使用明确状态词：

```text
未开始 / 已开始 / 执行中 / 部分完成 / 已完成 / 完整完成 / 挂起 / 阻塞 / 证据不足 / 未验证
```

不得把“已生成、已尝试、脚本跑过、文件存在”直接写成“完成”。

#### 8.3 表格优先规则

以下场景优先使用短表格：

| 场景 | 推荐表格字段 |
|---|---|
| 进度汇报 | 项目 / 状态 / 数据 / 证据 / 未完成 |
| 文件扫描 | 路径 / 类型 / 更新时间 / 判断 / 处理建议 |
| 法律分析 | 问题 / 依据 / 适用条件 / 风险 / 证据等级 |
| 系统修复 | 问题 / 根因 / 修改 / 验证 / 回滚 |
| 任务计划 | 步骤 / 动作 / 工具或责任方 / 完成标准 |

表格不宜过宽；手机端或飞书端可改用字段化清单。

#### 8.4 证据等级

关键结论后默认标注证据等级：

| 等级 | 含义 |
|---|---|
| A | 已用工具、文件、日志、数据库或测试验证 |
| B | 来自已读文件/报告，但未复跑验证 |
| C | 基于上下文推断，需复核 |
| D | 未验证线索，不作为结论 |

#### 8.5 文件/图片/视频引用规范

输出本地文件、图片、视频时必须使用 Markdown 绝对路径；路径含空格、中文或特殊字符时用尖括号包裹。不得给相对路径冒充可交付链接。

#### 8.6 法律与办案输出

法律/办案类输出额外执行：

```text
结论先分层：确定 / 倾向 / 不确定
法条案例必须核验来源
内部过程材料与对外交付材料分开
未过门禁不得写“终版、可提交、办结”
必要时附 V7.2 七字段交接接口
```

#### 8.7 简洁门禁

智能排版不是拉长篇幅。默认原则：

```text
先给结论；
数据压缩成表；
工具过程不展开；
只列影响判断的证据；
下一步必须可执行。
```

## Workflow

### Step 1：真实性预检

开始前回答：

```text
目标是否清楚？
输入材料是否存在？
需要哪些技能？
是否适合委派 subagents？
有哪些风险边界？
完成标准是什么？
```

涉及文件时先 `search_files` / `read_file`。涉及当前事实、系统状态、时间、计算、git、进程时必须工具验证。

### Step 2：材料分簇

按主题把材料分成 2-4 组，适合并行处理：

```text
A. 检索 / 上下文学习 / 记忆
B. token / 上下文 / 轨迹压缩
C. 智能体训练 / 科研引擎 / 原生进化
D. 风险边界 / 反幻觉 / 工具能力
```

每组只给必要文件路径和输出要求，避免子智能体读无关材料。

### Step 3：子智能体并行学习

给每个 subagent 明确输出格式：

```text
1. 可复用原则
2. 可执行流程
3. 可落地到 Hermes 技能的条款
4. 风险边界
5. 建议更新/新建技能名
6. 文件变更情况
```

禁止子智能体直接改核心文件，除非任务明确要求并已授权。

### Step 4：主会话融合

融合时按 6 类输出归纳：

```text
核心公式
触发条件
标准流程
工具/子智能体使用规则
验证清单
风险与禁止项
```

优先更新已有技能；只有明显跨域、复用价值高、已有技能不能承载时，才新建综合技能。

### Step 5：写入技能或规则

选择沉淀位置：

| 内容 | 写入位置 |
|---|---|
| 可复用流程 | SKILL.md |
| 工具调用纪律 | TOOLS.md |
| 行为/团队/审查规则 | AGENTS.md |
| 长期稳定事实 | MEMORY.md |
| 用户偏好 | USER.md |
| 一次性过程 | 工作区归档，不进记忆 |

闭环要求：新建综合技能后，必须继续检查并联动已加载或相关 umbrella skills，避免新技能孤岛化；必要时生成 workspace 索引报告，记录源材料、子智能体分工、融合公式、落地文件和触发方式。

重要规则改写前必须备份；不得污染根目录。

### Step 6：验证

最低验证：

```text
文件是否存在？
frontmatter 是否合法？
描述是否不超过限制？
是否能被 skill_view / search_files 定位？
是否有虚构能力表述？
是否和已有技能明显重复？
```

### Step 7：真实性交付

交付时标注：

```text
真实性状态：完整完成 / 部分完成 / 草稿 / 模拟 / 未验证
依据：工具输出 / 文件路径 / 子智能体结果 / 测试结果
未完成：如有必须列出
风险：能力边界和未验证点
```

用户可见报告格式规则：

- 凡是“给用户看的报告”，必须生成 Markdown `.md` 文件；
- 文件名本身必须带 `.md` 后缀，不能只写 Markdown 内容但无后缀；
- 最终回复中的报告链接必须指向带 `.md` 后缀的本地绝对路径；
- JSON 只作为机器证据、运行记录或中间产物，不作为最终用户报告；
- 交付时优先给 `.md` 路径，同时可附 JSON 证据路径。

## Reusable Modules

### Module A：SearchSkill 增强

```text
问题分类 → 选择检索技能 → 生成检索计划 → 多源验证 → 冲突标注 → 输出依据 → 失败归因 → 搜索技能沉淀
```

### Module B：Context Skill Distillation / 自博弈技能萃取

```text
长文档输入
→ Challenger：从材料抽取概念、关系、技能点，生成可测试挑战任务
→ Reasoner：检索/组合现有技能解决挑战，输出解法、skills_used、置信度
→ Judge：按正确性、可读性、可迁移性评分，决定是否入 SkillBank
→ Replay：跨时间重放历史挑战-解法，平衡简单/困难任务，避免对抗性崩溃
→ SkillBank：沉淀为可读、可迁移、可触发的自然语言 Skill 条款
```

可选选择机制：

```text
Gini / 信息增益 / 随机森林思想只能作为“技能路径选择与候选排序”的启发式：
- 用任务类别分布计算候选技能对问题空间的区分度；
- 优先选择让失败类型更可分、覆盖更清楚的技能组合；
- 不得把公式写入就宣称已完成 Rust 原生训练或自动全能推理。
```

验收边界：

```text
已吸收 = 技能流程、触发条件、Judge/Replayer门禁、可迁移条款已进入 Skill/规则；
已配置 = 有可调用脚本、配置入口、运行记录和读回验证；
缺任一项时只能说“方法论吸收/部分配置”，不能说“底层完整融合”。
```

### Module C：Memory Consolidation / SWRs 记忆巩固

超级进化5把海马体 SWRs 类比为 Hermes 记忆系统，但只能吸收为显式选择机制，不能声称 AI 会像大脑一样自动睡眠回放。

```text
经验输入 → 临时记忆/会话轨迹
→ 重要性评分：稳定性、复用价值、纠错价值、用户偏好强度、风险边界
→ 目标分流：memory/user/skill/workspace archive
→ 写入或候选：低风险稳定事实可 memory；流程进 Skill；一次性过程进 workspace
→ 读回验证：确认条目存在、无过期事实、无凭证、无命令式污染
→ 下次任务触发复用
```

记忆写入评分参考：

| 因子 | 加分 |
|---|---:|
| 用户明确要求记住/纠正偏好 | +4 |
| 跨任务长期稳定，7天后仍有用 | +3 |
| 可防止重复踩坑或虚假完成 | +3 |
| 涉及凭证、临时进度、PR/commit/编号 | -5 |
| 只是一次性过程或状态 | -3 |

门禁：

- `score >= 5` 且无红线 → 可写 memory/user。
- 流程、脚本、工作法 → 写 SKILL.md，不写 memory。
- 临时进度、完成记录、文件清单 → 写 workspace 报告，不写 memory。
- 写入后必须读回；未读回只能说“已尝试写入”。

公式口径：`h_t = F(h_{t-1}, x_t, u_t)` 只作为“当前记忆状态由旧记忆、当前输入、写入动作共同更新”的抽象，不代表真实神经网络或自动全能记忆引擎。


### Module D：Token Context Hygiene / 超级进化6 Token 根治边界

超级进化6把 token 问题拆成三类：截图坐标偏移、截图帧 token 过高、无效思维开销。吸收为 Hermes 的上下文与计算预算门禁，但不声称已完成 Rust/Go/C 底层改造。

```text
轨迹日志定位故障
→ 坐标/截图/文本三类归因
→ token 预算与最近帧保留
→ 无效推理拦截
→ 周期性净化
→ 指标回测
```

坐标校正公式仅适用于具有明确截图尺寸和屏幕尺寸的 computer_use 场景：

```text
X_real = X_out × W_screen / W_img
Y_real = Y_out × H_screen / H_img
```

执行边界：没有实际截图尺寸、屏幕尺寸、点击坐标和回放验证时，不得宣称“点击偏移已修复”。

上下文控耗：

```text
Token_reserve = Token_text + sum(latest_3_image_tokens)
```

执行规则：

- 图像/截图任务只保留最近 3 帧作为默认工作集；更早截图转为路径索引或摘要。
- 文本文件优先局部读取；不要把大文件、全日志、全技能一次性塞入上下文。
- 工具输出先压缩为状态、路径、关键数值、错误摘要和验证结论。
- 每 25 个工具/轨迹节点做一次 context checkpoint：目标、已验证产物、未完成项、下一步。

算力有效率：

```text
Effort_valid = Total_effort - Waste_effort
```

无效开销包括：重复解释、未读文件就推断、无证据自评、重复跑已验证步骤、把愿景当完成。

可落地脚本/报告优先使用本地 sidecar 或 Python 粘合；Rust/Go/C 只在确有性能瓶颈、接口稳定、已有测试与回滚时再考虑。

### Module E：Subagent Result Recovery

```text
分派前给上下文 → 子任务独立执行 → 五段式总结 → 主会话验证关键副作用 → 融合入最终结论
```

### Module F：APEX Agent Training Loop / 超级进化7 个人智能体训练

```text
真实任务 → 轨迹捕获 → 自动验证 → 成功样本入库 → 失败样本反例化 → 技能更新 → 下次复用
```

超级进化7将个人智能体训练拆为四个可执行层，但在当前环境只能先落地为可运行基线/沙箱/评估中心，不得宣称完整 SFT/RL 已完成：

```text
Task_APEX = PersonaIntent × SkillGrounding × MockWorkspace
Agent_APEX = SFT_Trajectory + RL_Rollout × SandboxParallel
Score_APEX = AutoVerify(60%) + LLM_HumanVerify(40%)
Iteration_APEX = Data → Train → Bench → Feedback
```

Hermes 可执行映射：

| 公式层 | 当前可落地实现 | 边界 |
|---|---|---|
| PersonaIntent | 从用户画像/任务类型生成本地模拟任务 | 不生成涉密/真实客户数据 |
| SkillGrounding | 绑定已有 skill 名称和触发条件 | 不自动创建/删除技能 |
| MockWorkspace | 在 workspace 沙箱目录生成文件任务 | 不碰真实业务目录 |
| SFT_Trajectory | 轨迹 JSONL / scored samples / tiny trainer | 不是真实大模型 SFT |
| RL_Rollout | 多候选任务执行与评分回放 | 不是真实 RL policy optimization |
| AutoVerify 60% | 文件存在、内容哈希、状态字段、测试输出 | 只证明本地状态，不证明世界事实 |
| LLM_HumanVerify 40% | LLM/人工复核队列 | 没有真实复核时不得计满分 |
| Bench | 50-200例基准目标 | 未达到样本数时只能称小样本基线 |

安全规则：训练生态所有产物默认写入 `workspace/agentic_rl/` 或专用沙箱；不得自动写真实 memory、skills、config、credentials。

### Module G：Research Engine / 超级进化8 科研统一引擎

```text
问题定义 → 文献/代码/数据获取 → 假设生成 → 证据分级 → 实验/分析计划 → 执行与验证 → 不确定性声明
```

超级进化8把“操控精度、训练闭环、自主科研”合并为科研统一引擎。吸收为三层编排，不得宣称已能自动产出可发表科研成果：

```text
Engine_APEX = (Coord_Fix × Token_Control)
            × (Task_Syn + Train_SFT/RL + Bench_Verify)
            × (ERA + Co_Scientist + Robin)
```

Hermes 可执行映射：

| 模块 | 当前可落地实现 | 边界 |
|---|---|---|
| Coord_Fix × Token_Control | 超级进化6 token hygiene / 坐标sidecar / 最近3帧规则 | 未完成底层坐标引擎 |
| Task_Syn + Train_SFT/RL + Bench_Verify | 超级进化7 MockWorkspace / AutoVerify / tiny baseline | 未完成真实SFT/RL和50-200例正式基准 |
| ERA = LLM × TreeSearch × CodeSandbox | 可做假设树、代码沙箱、只读实验计划 | 未自动发现科研结论 |
| Co_Scientist = Gen+Rank+Reflect+Evolve × Memory | 可做假设生成、排序、反思、记忆候选 | LLM输出需人工/证据复核 |
| Robin = Hypo+Plan+Exp+Analyze × Mechanism | 可做假设-计划-实验-分析模板 | 未接真实实验设备/数据管线 |

科研真实性门禁：

- 没有真实数据、代码、实验日志、统计检验时，不得写“科研发现完成”；
- 没有复现实验和外部证据时，不得写“可发表结论”；
- 药物、靶点、医学机制相关内容必须标注为研究假设，不能当事实建议；
- 输出论文格式文件可以做，但必须区分“草稿/综述/假设/实验报告/已验证结论”。

默认落地位置：`workspace/research_engine/`，所有用户可见研究报告必须为 Markdown `.md`。

### Module I：Native Evolution Core / 超级进化9 原生进化核心公式

超级进化9将 EvoMaster/CLAW 的原生进化公式吸收为“轨迹驱动的执行策略优化”门禁，而不是直接宣称已改造 CLAW/Hermes 底层。

核心公式：

```text
max_{π_claw} E_{τ~π_claw}[ R_exec(τ) + λ · K_claw(τ) ]
π_claw^(t+1) = GPT-Stream(τ^(t), K_claw, Constraint_sandbox)
K_claw = HashPool(Filter(τ_valid))
```

Hermes 可执行映射：

| 公式项 | Hermes含义 | 当前边界 |
|---|---|---|
| π_claw | 工具、技能、路由、执行策略 | 当前通过skill/script/sidecar近似，不是底层策略替换 |
| R_exec | 执行成功率、合规率、验证通过率 | 可用评估中心/轨迹评分近似 |
| K_claw | 有效轨迹知识缓存 | 可落地为hash轨迹池、基因库、技能候选 |
| Constraint_sandbox | 权限、安全、凭证、删除、外发等门禁 | 必须先过沙箱约束，不能自动越权 |
| HashPool(Filter(τ_valid)) | 过滤有效轨迹并哈希去重 | 只能收录已验证轨迹，失败轨迹需反例化 |

执行规则：

1. 每次复杂进化任务结束后，判断是否存在有效轨迹；没有验证的轨迹不得入库。
2. 成功轨迹进入技能候选或基因库；失败轨迹必须写失败原因和防复发规则。
3. 策略自更新只能产出“下一轮建议/候选补丁”，不能绕过用户授权直接改核心。
4. 未实际修改 CLAW/Hermes 核心源码并验证前，不得写“原生进化核心已完成”。
5. Rust/Go/C 版只在有明确接口、测试、回滚和性能必要性时推进；否则先用Python sidecar低风险落地。

验收边界：

- 已吸收 = 公式、映射、轨迹缓存规则、失败反例规则进入技能/报告/基因。
- 已配置 = 有可运行脚本或入口、运行记录、可复现I/O、最近验证时间。
- 原生完成 = 必须有核心源码变更、测试、回滚路径和运行证据；当前未达成。

来自 `超级进化11-天工技能.md` 的深度吸收。TianGong 不是单一提示词，而是 GPT 主脑统筹下的四核执行治理层：把复杂任务压成“认知、规划、执行、验证、沉淀、进化”的可回放闭环。

核心公式：

```text
ΔG = (C_total · Λ_gene · Ω_entropy · τ_traj) / (H_info · t)

C_total：任务复杂度与协同成本
Λ_gene：可复用技能/基因的有效增益
Ω_entropy：轨迹稳定性与噪声抑制能力
τ_traj：完整轨迹生成效率
H_info：信息噪声、冗余与不确定性负载
t：总耗时
```

执行目标：

```text
max π_skill E[R_exec(τ) + λ · K_cache(τ)]

R_exec：执行成功率、合规率、验证通过率
K_cache：可沉淀知识缓存
λ：复用权重
```

四核分工：

| 核心 | Hermes 可执行含义 | 产物 | 边界 |
|---|---|---|---|
| evolver | 缺陷扫描、失败归因、轨迹回收、基因沉淀、回测指标 | 缺陷表、基因条款、复发防线 | 不能声称后台持续自进化，除非有真实 cron/日志 |
| autoresearch | 检索、读取、交叉验证、知识蒸馏 | 来源清单、证据分级、冲突处理 | 摘要不能替代原文证据 |
| openhands | 文件、终端、浏览器、沙箱等实际工具执行 | 文件变更、命令输出、运行结果 | 无工具记录时只能说规划执行 |
| superpowers | 澄清、设计、拆解、测试/验证、审查、交付 | 计划、状态机、验收报告 | 不能用流程名冒充测试已完成 |

GPT 主导规则：

1. 量子路由用于展开候选通道和路径；当用户要求“以 GPT 为主”时，必须用 GPT 通道作为主裁判。
2. 若 `qr route` 自动选到低阶通道，但健康检查显示 GPT 可用，应显式调用 `qr tier B` 或等效方式确认 GPT 通道，再由 GPT 主脑融合。
3. GPT 主脑负责最终路径选择、冲突消解、真实性边界、补齐落地和交付状态判断。
4. 子智能体只提供拆解、执行、验证、反证材料；不能替代主脑最终裁决。

触发条件：

- 用户要求“天工技能”“超级技能矩阵”“认知-规划-执行-进化闭环”。
- 用户明确要求“深度学习”“吸收融合”“以 GPT 为主”“调用量子路由 LLM 组合”。
- 任务同时需要检索、规划、执行、验证和进化沉淀。
- 当前能力不足，需要寻找真实开源项目或官方文档学习后再转化为本地技能。

标准状态机：

```text
received → scoped → gated → routed → planned → assigned → executing → verifying → audited → completed
                         ↘ blocked / repairing / failed / aborted
```

不可跳过状态：

- `scoped`：明确目标、边界、产物、验收标准。
- `gated`：检查工具需求、副作用、权限、真实性来源。
- `routed`：执行量子路由；GPT 主导时确认 B 级 GPT 通道可用性。
- `planned`：主路径、备选路径、风险点、验证方法。
- `verifying`：文件、命令、检索、测试或数据库读回验证。
- `audited`：高风险、系统规则、法律结论、进化沉淀必须反证审查。

门禁：

```text
G0 入口门禁：目标、范围、副作用、工具需求、验收标准、不确定性。
G1 计划门禁：主路径、备选路径、验证方法、风险点、产物定义。
G2 执行门禁：依赖齐全、输入存在、操作安全、可回滚、证据卡准备。
G3 验证门禁：按任务类型执行测试/读回/检索/构建/状态检查。
G4 交付门禁：需求覆盖、证据闭环、文件变更透明、风险披露、完成态准确。
```

证据卡最低字段：

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

真实性四件套：

任何“已支持 / 已实现 / 可自动执行 / 已集成”表述，必须同时满足：

1. 有实际代码入口或配置绑定。
2. 有一次真实运行记录。
3. 有可复现的输入输出样例。
4. 有最近一次验证时间。

少一项时，只能写成“流程目标”“设计意图”“可执行方案”“待验证能力”，不能写成已实现事实。

最小交付物：

```text
四核分工表 + GPT/量子路由记录 + 状态机节点 + 证据来源 + 执行结果 + 验证状态 + 可复用沉淀位置 + 边界声明
```

### Module J2：Full Tool-Call Parallel Sidecar / 超级进化10.1 多Agent线程池级调度

超级进化10可安全落地的并行调度层，复用 `hermes_full_toolcall_planner.py` 与 `hermes_full_toolcall_runtime.py`：

- planner 负责把输入材料转成全局轨迹、并行点、验证点、风险点和回退路径；
- runtime 负责把轨迹分配到 worker，做负载均衡、并行执行和失败自愈；
- blackboard 只写本地 sidecar 状态，不改 Hermes/CLAW 核心；
- 失败重试和 fallback 只作为 sidecar 层容错，不代表底层多模型已接管。

参见：`references/super-evolution-10-1-sidecars.md`、`references/super-evolution-10-1-run-and-fix.md`

验收边界：

- 已吸收 = 规划器、并行运行器、黑板状态、失败自愈、报告化。
- 已配置 = 能对真实输入产生 plan + run JSON。
- 仍未完成 = 真正对外部 LLM 提供跨 worker 的真实任务调度。


### Module J3：Bulk Skill Candidate Promotion / 超级进化10.2 批量技能晋升

本模块把 `skill_candidates/` 作为批量晋升入口：

- 扫描候选目录中的 `.md` 候选；
- 仅当候选包含完整证据字段时才晋升；
- 批量晋升的产物仍然只是 skill 补强，不改核心；
- 失败候选进入拒绝清单，便于后续修复后再试。

### 批量晋升规则

```text
候选目录 → 证据门禁 → 通过则纳入正式 skill → 失败则记录拒绝原因
```

### 本次通过候选

- `/Users/appleoppa/.hermes/workspace/trace_hashpool/skill_candidates/09f45669a34c.md`

### 拒绝候选


### Module J：Super Router / 超级进化10 量子通道超级路由

超级进化10将多模型分类、健康检查、降级、轨迹缓存、Full Tool-Call Trajectory、多Agent并行和APEX评分合并为超级路由治理层。实际执行以 `quantum-channel-router` / `qr` 的 live 输出为准，不凭愿景材料宣称多模型已经参与。

核心公式：

```text
ΔG = (C_total · Λ_gene · Ω_entropy · τ_traj) / (H_info · t)
```

其中 `τ_traj` 表示完整轨迹生成效率系数：任务前生成全局轨迹、并行点、验证点、回退路径，减少无效单步循环；但不能替代验证。

Hermes 可执行映射：

| 原文要求 | Hermes落地 | 边界 |
|---|---|---|
| 多LLM分类超级路由 | `qr config` + `qr route` + `qr health` | 以live health为准，不虚报down模型参与 |
| 自动避开欠费/故障模型 | 健康检查+降级记录 | 供应商down只能降级，不能自行恢复付费状态 |
| 最快可用模型 | health latency作为参考 | 任务类型优先于单纯速度 |
| Full Tool-Call Trajectory | 全局轨迹/并行点/验证点/回退路径 | 不等于跳过验证或一次性盲跑 |
| 轨迹指纹缓存 | `qr cache` + `trace_hashpool` | qr cache负责路由轨迹；HashPool负责执行轨迹 |
| 成功轨迹转技能 | skill candidate + gene +人工/门禁确认 | 不自动改正式技能，除非低风险且已验证 |
| APEX基因迭代 | 基因库/评估中心 | 不是后台无限自进化 |

执行规则：

1. 复杂学习/进化/配置任务开始前先跑 `qr route "任务描述"`，并记录 selected/tier/health/fallback。
2. 若A/C等高阶模型down，必须在报告中写明降级事实。
3. `qr` 是任务层路由工具，不用于推断Web UI profile/session身份。
4. 轨迹缓存分层：路由选择进 `qr cache`；验证过的执行轨迹进 `trace_hashpool`。
5. Full Tool-Call Trajectory 只在目标清楚、依赖可分解、风险可控、有验证点和回退路径时启用。
6. 成功轨迹可进入技能候选/基因库；失败轨迹进入反例库。

验收边界：

- 已吸收 = 公式、分级路由规则、降级记录、轨迹缓存分层、Full Tool-Call边界进入技能。
- 已配置 = qr CLI存在、provider配置存在、health/route/cache可运行。
- 完整完成 = 还需真实缓存条目、hashpool桥接、token预算器、多Agent调度验证和自动技能化门禁。

本模块来自 2026-05-23 的训练闭环落地。由于当前环境没有现成 sklearn/torch/xgboost/lightgbm/catboost，本模块采用纯标准库实现一个可训练、可预测、可回读的轻量基线，不冒充深度学习或完整 RL 训练。

组件：

- `/Users/appleoppa/.hermes/scripts/hermes_tiny_trainer.py`
- `/Users/appleoppa/.hermes/scripts/hermes_tiny_predict.py`
- `/Users/appleoppa/.hermes/workspace/agentic_rl/model/tiny_quality_model.json`
- `/Users/appleoppa/.hermes/workspace/agentic_rl/model/tiny_quality_eval.json`
- `/Users/appleoppa/.hermes/workspace/agentic_rl/model/tiny_quality_predictions.json`
- `references/evolution-pipeline-entrypoint.md`
- `references/memory-swrs-backup-gated-automation.md`：超级进化5记忆系统自动化的备份门禁、dry-run→apply升级、自动写memory与精确去重的安全边界。

能力：

1. 从 scored trajectory JSONL 学习一个小型质量分类器。
2. 输出可读回的 JSON 权重文件。
3. 对同一批轨迹进行预测，返回 high_quality / reject / review。
4. 生成独立评估文件，严格报告 accuracy，而不把训练结果吹成模型已成熟。

验收标准：

- 必须有模型文件、评估文件和预测文件。
- 模型必须能被读回并二次预测。
- 如果 accuracy 很低，仍然算“已训练出基线”，但不算“训练完成可上线”。
- 不能因为没有 ML 库就声称“无法训练”；应当退化到可执行基线。

边界：

- 这不是完整神经网络训练。
- 这不是 RL policy optimization。
- 这不是 Hermes 核心接管模块。
- 这只是把“训练”从口号变成了一个可运行、可评估、可预测的小闭环。

### Module L：Devour Sandbox / 超级进化12 吞噬自进化

吞噬自进化不是“自动吞掉全球开源并改写核心”，而是：只读采集 → 能力抽取 → 候选化 → 门禁晋升 → 评估中心联动。

核心框架：

```text
Task_APEX = PersonaIntent × SkillGrounding × MockWorkspace
Agent_APEX = SFT_Trajectory + RL_Rollout × SandboxParallel
Score_APEX = AutoVerify(60%) + LLM_HumanVerify(40%)
Iteration_APEX = Data → Train → Bench → Feedback
```

Hermes可执行映射：

| 公式层 | 当前可落地实现 | 边界 |
|---|---|---|
| PersonaIntent | 由用户画像/任务类型生成本地模拟任务 | 不生成涉密真实客户数据 |
| SkillGrounding | 绑定已有 skill 名称和触发条件 | 不自动创建/删除技能 |
| MockWorkspace | 在 workspace 沙箱目录生成文件任务 | 不碰真实业务目录 |
| SFT_Trajectory | 轨迹 JSONL / scored samples / tiny trainer | 不是真实大模型 SFT |
| RL_Rollout | 多候选任务执行与评分回放 | 不是真实 RL policy optimization |
| AutoVerify 60% | 文件存在、内容哈希、状态字段、测试输出 | 只证明本地状态，不证明世界事实 |
| LLM_HumanVerify 40% | LLM/人工复核队列 | 没有真实复核时不得计满分 |
| Bench | 50-200例基准目标 | 未达到样本数时只能称小样本基线 |

吞噬式学习规则：

1. 外部开源项目先只读采集元数据、README、license、可见能力信号。
2. 只读采集后的结果进入候选技能/候选基因，不直接复制源码。
3. 认知强化学习可以作为评估/训练框架，但没有真实数据和验证时不能写完成。
4. 任何自动改 Hermes/Claw 核心的想法都必须明确标注为高风险核心改造，并在当前阶段不执行。
5. 评估中心用来评分、训练、预测和审计，但当前模型仍是弱基线，不能当主裁判。

验收边界：

- 已吸收 = 吞噬式学习框架、只读采集、候选化、评估门禁、报告化。
- 已配置 = 可对外部材料形成候选和证据。
- 未完成 = 全球前三项目底层吞噬、Rust/C/Go 全功能集成、真实 Agentic RL 闭环。

天工技能把四核协作、量子路由、工程流程、基因沉淀、候选晋升整合为一个治理矩阵，但不能虚报成底层吞噬了外部 GitHub 项目或已改造 Hermes/Claw 核心。

核心口径：

```text
认知 → 规划 → 执行 → 验证 → 沉淀 → 进化
```

四核分工：

| 核心 | Hermes 可执行含义 | 产物 |
|---|---|---|
| evolver | 缺陷扫描、失败归因、轨迹回收、基因沉淀 | 缺陷表、基因条款、回测指标 |
| autoresearch | 检索、交叉验证、知识蒸馏 | 来源清单、证据卡 |
| openhands | 文件、终端、浏览器、沙箱等实际工具执行 | 文件变更、命令输出、运行结果 |
| superpowers | 澄清、设计、拆解、TDD、审查、交付 | 计划、状态机、验收报告 |

统一状态机：

```text
received → scoped → gated → routed → planned → assigned → executing → verifying → audited → completed
```

Hermes 可执行映射：

1. 复杂任务先 `qr route`，再生成全局轨迹。
2. 任务执行按四核拆分，不把愿景层语言当成已实现能力。
3. 外部开源项目只读采集后进入候选技能/基因流程，不自动复制源码。
4. 任何自动写正式 skill 的动作必须经过候选门禁。
5. GitHub 生态吸收只能作为“方法、流程、候选、证据”，不能写成“底层已吞噬完成”。

验收边界：

- 已吸收 = 四核分工、状态机、候选化、门禁晋升、基因沉淀。
- 已配置 = 能在真实任务中作为编排治理层使用。
- 未完成 = 外部 GitHub 生态底层吞噬、Hermes/Claw 核心原生改造。

本模块来自 2026-05-23 的“接进正式入口”需求。它明确：哪些能力可以直接接入 Hermes，哪些必须继续留在 workspace / scripts / cron sidecar。

已允许的接入方式：

- no-agent cron 调用 digest / export / score / train / predict
- workspace 产物作为报告和候选集
- skill/memory 仅在人工确认或 background review 后写入

暂不允许的接入方式：

- 直接替换 Hermes 主链路推理引擎
- 自动写 config / env / credential
- 自动删除技能
- 自动把预测器结果当成系统主判断

验收标准：

- 入口接入必须有读回验证。
- 入口接入必须保留回滚路径。
- 入口接入必须保留 dry-run。
- 没有这些门禁前，不算“正式接入 Hermes 核心”。

### Module N：APEX ΔE Origin Gate / 超级进化13 神技能开启

超级进化13的“神技能/AGI/核心重构”必须收敛为变量拆解、只读溯源、冗余审计、核心改造挂起，不得直接宣称底层完成。

核心公式：

```text
APEX_ΔE = αΨ + βΩ + λΦ + ∇Θ + Evol_code
```

Hermes可执行映射：

| 变量 | 含义 | 当前执行边界 |
|---|---|---|
| αΨ | 意识逻辑基底 | 用户目标、真实性门禁、判断纪律 |
| βΩ | 代码底层构架 | 只做 sidecar/脚本/技能，不自动改核心 |
| λΦ | 全网知识溯源 | 只读检索、来源清单、候选化 |
| ∇Θ | 认知迭代差值 | 失败复盘、评估中心、基因沉淀 |
| Evol_code | 原生代码级永续演化 | 高风险核心改造目标，当前挂起 |

执行规则：

1. 出现“核心重构、AGI、本源激活、永续演化”时，先拆变量和风险，不把愿景当完成。
2. 全网溯源只做只读采集、来源记录、候选技能/基因，不自动吞噬。
3. 去冗余只做审计报告和候选清单，不自动删除。
4. GPT/Claude 双核参与必须有真实 `qr` 或调用证据；down 时记录降级。
5. Go/C/Rust 底层重构属于核心改造，除非用户单独授权，否则挂起。

验收边界：

- 已吸收 = 公式拆解、变量映射、边界规则、报告/基因。
- 安全落地完成 = 已实际运行 `super_evolution13_safe_landing.py` 或同等 sidecar，生成只读来源清单、冗余审计、sidecar规格、评估矩阵、报告和基因，并读回验证。
- 可继续 = 对候选来源做许可证/README深读、对冗余候选做人工复核、把稳定机制晋升为正式脚本/评估中心入口。
- 未完成 = 核心源码重构、全网实时吞噬、自动删除、AGI终极闭环。

已落地入口：

```bash
/Users/appleoppa/.hermes/scripts/super_evolution13_safe_landing.py
```

产物位置：

```text
/Users/appleoppa/.hermes/workspace/开智/超级进化13-除核心重构外安全落地报告.md
/Users/appleoppa/.hermes/workspace/evolution/super_evolution13/
GENE_SUPER_EVOLUTION_13_SAFE_LANDING_WITHOUT_CORE
```

执行边界：该入口只读采集 GitHub 元数据、扫描 workspace 候选冗余、生成 sidecar/评估文件；不 clone、不复制外部源码、不删除文件、不修改 Hermes/Claw 核心。

### Module O：ΔG Negative Potential Gate / 超级进化14 ΔG演化范式叠加

### Module O：ΔG Negative Potential Gate / 超级进化14 ΔG演化范式叠加

超级进化14的 `EV = BV + AV, sum(C_all) <= SV` 吸收为工具分支收益-成本-风险门禁，而不是宣称已实现 AGI 自语言、ZeroLang 底层架构或 A2A 全球算力集群。

核心公式：

```text
EV = BV + AV
sum(C_all) <= SV
net_potential = EV - C_all - risk
```

Hermes 可执行映射：

| 符号 | Hermes含义 | 执行规则 |
|---|---|---|
| BV | 任务本征需求熵权 | 用户目标必要性、真实性门禁、任务价值 |
| AV | 工具动作增益势 | 工具调用预计收益、可验证产物、复用价值 |
| C_all | 工具/资源总成本 | token、时间、上下文负载、文件副作用、外部调用 |
| SV | 系统资源上确界 | 当前授权、风险边界、预算上限 |
| HarmRate | 退化噪声警戒 | 原文34%只作警戒，不当本地实测率 |
| 负势湮灭 | 终止低价值分支 | `net_potential < 0`、超预算或高风险时停止/复核 |

已落地入口：

```bash
/Users/appleoppa/.hermes/scripts/super_evolution14_delta_g_gate.py
```

产物位置：

```text
/Users/appleoppa/.hermes/workspace/开智/超级进化14-ΔG演化范式叠加吸收配置报告.md
/Users/appleoppa/.hermes/workspace/evolution/super_evolution14/delta_g_gate_matrix.json
GENE_SUPER_EVOLUTION_14_DELTA_G_NEGATIVE_POTENTIAL_GATE
```

执行边界：该入口只提供 CLI sidecar 门禁；未实现 Hermes/Claw 核心改造。

除核心改造外，第14已追加落地本地可验证 sidecar：

```bash
/Users/appleoppa/.hermes/scripts/super_evolution14_zerolang_a2a.py
```

完成形态：

| 原项 | 完成形态 | 边界 |
|---|---|---|
| ZeroLang 底层语言 | `ZeroLang-lite/0.1` 最小结构化指令语言与解释器 | 本地sidecar，不是通用底层语言运行时 |
| AGI 自语言真实实现 | `ZLMessage` 结构化自语言消息协议 | 本地协议，不宣称真实AGI意识/自语言 |
| A2A 全球算力集群 | `LocalA2ACluster` 本地多Agent协作模拟器 | 本地模拟，不是全球网络集群 |

报告与证据：

```text
/Users/appleoppa/.hermes/workspace/开智/超级进化14-除核心改造外完成报告.md
/Users/appleoppa/.hermes/workspace/evolution/super_evolution14/zerolang_a2a/
GENE_SUPER_EVOLUTION_14_ZEROLANG_A2A_LOCAL_SIDECAR
```



关键边界：

- “只读采集 3 个 GitHub 项目”不能说成“已自动吞噬全球前三项目”。
- “安全接口层/sidecar”不能说成“Hermes 原生核心主链路已改造”。
- “训练链路跑通”不能说成“模型效果可上线”。
- “沙箱机制复现”不能说成“完整复刻外部项目”。

参考：`references/2026-05-23-super-evolution-12-eval-center-devour.md`。

## Common Pitfalls

本模块来自 2026-05-23 的“评估中心”和“超级进化12继续落地”。用户已将“评估中心”定义为固定别名：指 Hermes 的轨迹评分、训练、预测和评估流水线。

安全桥接层：

- `/Users/appleoppa/.hermes/scripts/hermes_eval_center.py status`
- `/Users/appleoppa/.hermes/scripts/hermes_eval_center.py audit`
- `/Users/appleoppa/.hermes/scripts/hermes_eval_center.py run`

用途：统一读取评估中心状态、模型评估、预测记录、开源吞噬报告和 cron 接入状态。它是原生核心改造前的安全接口层，不等同于已经修改 Hermes 主链路源码。

开源吞噬只读采集层：

- `/Users/appleoppa/.hermes/scripts/hermes_open_source_devour_scout.py --query "agent framework" --top 3`

用途：通过 GitHub 公共接口只读采集项目元数据、README 和 license，生成候选能力信号。它不 clone 仓库、不复制源码、不自动修改 Hermes 核心。

阶段边界：

```text
只读采集 → 许可证/README 审计 → 架构拆解 → 沙箱复现 → 能力抽取 → 技能/基因候选 → 核心接口化
```

禁止夸大：

- sidecar / cron / script adapter 不等于 Hermes 核心源码改造完成。
- GitHub 搜索和 README/license 审计不等于“自动吞噬全球开源前三项目完成”。
- 模型有训练文件不等于模型足够强或可作为主裁判。

详细会话记录见 `references/2026-05-23-evaluation-center-and-devour-scout.md`。

### Module P：蜂群 StraTA-APEX 主公式 / 超级进化15 蜂群Agent

超级进化15的 `ApexStraTA = π(z|s₁) ⊗ π(aₜ|z, sₜ) ⊗ GRPO(z, aₜ) ⊗ MemLLM` 吸收为蜂群多Agent编排模式，而不是宣称已实现 DeepSeek-R1 级的真实 GRPO 训练或全球 Agent 集群。

核心公式：

```text
ApexStraTA = π(z|s₁) ⊗ π(aₜ|z, sₜ) ⊗ GRPO(z, aₜ) ⊗ MemLLM
z ~ π(s₁):  GPT 全局策略生成（full_toolcall_plan + qr route）
aₜ ~ π(z, sₜ): 固定策略多Agent并行执行（delegate_task batch）
GRPO = J(θ)=E[ΣA(z)+ΣA(aₜ)−βDKL]: 分层优化（EvoMaster 简化版）
MemLLM = RAG + LongTermMem: 长期记忆同步（memory + hippocampus + gene DB）
```

Hermes 可执行映射：

| 组件 | 可执行含义 | 当前状态 |
|---|---|---|
| π(z|s₁) | 复杂任务前调用 `full_toolcall_plan` 或 `qr route → delegate_task` 生成结构化策略 | ✅ 已落地 |
| π(aₜ|z,sₜ) | `delegate_task` batch 模式向子智能体注入策略上下文 | ✅ 已落地 |
| GRPO | `tools/grpo_lite_tool.py` 组评分 + 相对优势 + KL-like 偏离惩罚 + 策略推荐 | ✅ GRPO-lite 已落地 |
| MemLLM | memory_tool `save` + hippocampus 巩固 + gene DB 写入 | ⚠️ 未统一为单管道 |
| 最远点采样 | 策略多样性维护（选熵最大的策略池） | ✅ 已落地（tools/farthest_point_sampling.py） |
| 主公式验证 | 完成前代入公式逐项检查闭环 | ✅ 已落地（tools/swarm_validation_gate_tool.py） |
| 自验证约束 | 执行中检查偏离度并回滚 | ✅ 已落地（tools/swarm_validation_gate_tool.py deviation） |
| MemLLM 统一管道 | RAG 查询 + 长期记忆存储同步 | ✅ 已落地（tools/memllm_pipeline.py） |
已落地入口：

```bash
# 完整蜂群模式技能
/Users/appleoppa/.hermes/skills/workflow/apex-swarm-master-formula/SKILL.md
```

执行边界：

- GRPO 是简化启发式优化，不宣称与 DeepSeek-R1 训练同等级。
- 蜂群并行上限 = delegate_task 上限（当前 3 并发）。
- 自愈循环最多 3 轮，超限人工介入。
- MemLLM 使用现有 memory_tool + hippocampus 通路，不宣称语义 embedding 已底层实现。

## Retired sidecar absorption rule

NanoGPT-claw has been retired locally as a half-finished sidecar and must not be restored as a deployment target. If a similar lightweight CLI multi-LLM evolution agent is encountered, absorb only generalized engineering patterns into `rust-sidecar-gateway-patterns`: real provider dispatch, chat context store, error incident triage, SQLite evolution ledger, macOS Rust CLI deployment gates, webhook quick ACK, and sidecar escalation boundaries. Do not run or preserve project-specific binaries, launchd services, Feishu app bindings, secrets, runtime DBs, localtunnel/websocket bridges, or branding.

## Common Pitfalls

1. **只做摘要不做技能。** 用户要求“学习融会贯通”时，最终产物应是流程、条款、技能或规则，而非普通读书笔记。
2. **技能碎片化。** 不要一次创建很多窄技能；优先创建/更新一个能承载多模块的综合技能。
3. **子智能体结果不验证。** 子智能体自述不是事实证明；有文件写入、外部副作用时必须主会话复核。
4. **压缩丢掉目标。** token 优化不能牺牲用户目标、硬约束、路径、证据和风险边界。
5. **过度规划小任务。** 简单任务直接工具执行；复杂任务才走全局轨迹。
6. **用进化替代授权。** 核心代码、凭证、外部 API、长期后台进程、批量删除等高风险动作必须单独授权。
7. **新技能孤岛化。** 创建 class-level 技能后如果不 patch 相关旧技能、不写 workspace 索引，下一次任务很难触发和回查；参见 `references/2026-05-22-super-evolution-closure-gaps.md`。
8. **TianGong 愿景事实化。** 第11份"天工技能"材料应吸收为四核编排矩阵，而不是宣称已集成 GitHub 项目、xv 平台、claw 底层或 C/Rust/Go 原生能力；细节见 `references/2026-05-22-tiangong-four-core-orchestration.md`。
9. **Book-to-Skill 虚拟技能化。** 超级进化16 的“过目不忘”只能部署为可追溯草案流水线：`book_to_skill` 生成 draft + manifest + evidence_map，未人工验证前不得发布正式 skill；MemLLM 仅作索引和反馈，不替代原文证据。
10. **RuntimeOS/ECC 愿景事实化。** 超级进化16.5/17 只能落地为 `evolution_core_driver` 状态面板和 `ecc_twelve_factor_gate` 十二因子门禁；不得把治理门禁说成已完成AGI RuntimeOS、Rust超级重构或无人值守核心改造。

## Verification Checklist

- [ ] 已确认输入材料真实存在。
- [ ] 已按主题分簇，必要时使用 subagents 并行学习。
- [ ] 已输出可复用原则、流程、条款、风险边界。
- [ ] 已优先检查现有技能，避免重复造技能。
- [ ] 如写入文件，已备份重要文件或使用 skill_manage。
- [ ] 新建综合技能后，已检查并联动相关旧技能，避免技能孤岛。
- [ ] 必要时已生成 workspace 索引报告，方便回查源材料、子智能体结论和落地文件。
- [ ] 已验证技能 frontmatter、文件存在和可读取性。
- [ ] 未虚构外部模型、API、后台进程、底层代码实现。
- [ ] 已标注真实性状态和未验证点。

## Source Materials

本技能由以下当前材料融合而来。当前核验目录为 `/Users/appleoppa/Desktop/进化文件/`，共 14 份 Markdown；旧 `/Users/appleoppa/Desktop/超级进化/` 只作为历史路径线索，不作为当前完整清单。

- `/Users/appleoppa/Desktop/进化文件/超级进化1-河图洛书llm路由.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化2-github仓库.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化2.5-大佬指导.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化3-深度自进化.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化4-上下文学习新框架.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化5-记忆系统.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化5.5-未测试.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化6-token问题根治.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化7-个人智能体生态训练.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化8-科研统一引擎.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化8.5-经验（6-9）.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化9-原生进化核心公式释义.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化10-超级路由.md`
- `/Users/appleoppa/Desktop/进化文件/超级进化11-天工技能.md`
- `/Users/appleoppa/Desktop/超级进化12-吞噬自进化.md`

## Absorption Status Map

| 材料 | 当前吸收位置 | 状态 |
|---|---|---|
| 1 河图洛书 LLM 路由 | `quantum-channel-router`、`manual-evolution-loop`、EVM/河图洛书基因 | 已吸收为路由与反证门禁；外部多模型调用必须有真实调用证据 |
| 2 GitHub 仓库 | `manual-evolution-loop` GitHub 工厂门、`evm-integration`、基因库 GitHub runs | 部分吸收；已吸收为外部学习/回流门禁，不等同全部 GitHub 资源自动接管 |
| 2.5 大佬指导 | 本技能 TianGong 四核、子智能体回收、真实性边界 | 已吸收为编排原则；“永远不自己做任何工作/持续后台接管核心”不采纳为硬规则 |
| 3 SearchSkill | `search-skillbank`、本技能 Module A、Rust 原型 `/Users/appleoppa/.hermes/native/skillbank-core/` | 第一阶段已落地：SearchSkill 方法论与 Select-Read-Act-Review-Evolve 已吸收，Rust 只读 `skillbank-core` 已用于 scan/select 原型；未完成 claw 底层深度融合、Hermes 主链路原生改造、两阶段 SFT 真实训练 |
| 4 上下文学习 | 本技能 Context Skill Distillation、Challenger/Reasoner/Judge | 已吸收为技能萃取流程；未实现 Rust 原生训练引擎 |
| 5 记忆系统 | memory 纪律、SWRs 框架、长期记忆边界 | 已吸收 |
| 5.5 Full Tool-Call | 本技能全局轨迹、量子路由轨迹缓存 | 部分吸收；作为规划目标和缓存策略，不等同所有任务一次性完成 |
| 6 token 问题 | token hygiene、局部读取、图片帧控制原则 | 部分吸收；坐标/截图底层校正未核验为已实现 |
| 7 个人智能体训练 | APEX Agent Training Loop | 概念吸收；SFT/RL/沙箱训练基础设施未实装 |
| 8 科研统一引擎 | Research Engine、TianGong 四核 | 方法吸收；不能宣称已能自动发表科研成果 |
| 8.5 经验 | 子会话回收、技能审计、能力审计、skill-gene 闭环 | 部分吸收；其中部分“已补完”需以本地代码/日志为准 |
| 9 原生进化公式 | 轨迹缓存、失败轨迹沉淀、技能更新 | 已吸收为运行原则；未宣称 CLAW 底层已原生改造 |
| 10 超级路由 | `quantum-channel-router` Rust CLI `qr` | 已吸收并落地为工具；A 通道当前 not_supported 时会降级 |
| 11 天工技能 | 本技能 TianGong 四核编排 | 已吸收为四核治理模型；不虚构 GitHub/xv/Claw 底层集成 |
| 12 吞噬自进化 | 本技能 Module I：吞噬式自进化 / Agentic RL 认知闭环 | 已吸收为“外部高价值能力→拆解→复刻→验证→技能/代码/基因沉淀”的流程；不宣称已自动吃透全球开源前三项目或完成 Rust/C/Go 集成 |
