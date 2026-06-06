# TianGong GPT 主导四核编排深度吸收

## 触发背景

用户指出前次对 `/Users/appleoppa/Desktop/超级进化11-天工技能.md` 的学习深度不够，要求调用量子路由 LLM 组合，并以 GPT 为主完成吸收融合。

本轮执行记录：

- `qr route "以GPT为主深度学习超级进化11天工技能..."`：自动路由仍选 `glm45_air`。
- `qr tier B`：确认 B 级主通道为 `gpt55_5yuantoken`。
- 三路 GPT 子任务：公式拆解、工程落地、反证审查。
- 主会话融合后写回 `apex-hermes-evolution-engine` 的 Module H。

## 一、公式层吸收

TianGong Skill 的目标不是单次回答，而是把任务变成可验证、可复用、可沉淀的闭环。

```text
ΔG = (C_total · Λ_gene · Ω_entropy · τ_traj) / (H_info · t)
```

变量含义：

- `C_total`：任务复杂度与协同成本。
- `Λ_gene`：可复用技能/基因的有效增益。
- `Ω_entropy`：轨迹稳定性与噪声抑制能力。
- `τ_traj`：完整轨迹生成效率，代表一次性闭环能力。
- `H_info`：信息噪声、冗余与不确定性负载。
- `t`：总耗时。

目标函数：

```text
max π_skill E[R_exec(τ) + λ · K_cache(τ)]
```

含义：在执行成功率、验证通过率和可复用知识缓存之间取得最大化，而不是追求一次性漂亮回答。

## 二、能力层级

| 层级 | 含义 | 输出 |
|---|---|---|
| L1 识别层 | 识别任务类型、约束、风险、输入来源与完成标准 | scoped task |
| L2 规划层 | 拆成技能选择、工具选择、并行点、验证点 | task trajectory |
| L3 执行层 | 调用工具、子智能体、检索或文件系统完成实际动作 | execution result |
| L4 验证层 | 事实核验、边界审查、反幻觉检查 | verification report |
| L5 记忆层 | 稳定规律压缩为 skill、memory、rule 或 workflow | reusable asset |
| L6 进化层 | 从成功/失败轨迹中更新策略和门禁 | evolved rule |

## 三、工程状态机

```text
received → scoped → gated → routed → planned → assigned → executing → verifying → audited → completed
                         ↘ blocked / repairing / failed / aborted
```

不可跳过：

- `scoped`：目标、范围、约束、产物。
- `gated`：入口门禁、副作用、工具需求、权限。
- `routed`：量子路由；GPT 主导任务必须确认 B 级 GPT 通道。
- `planned`：主路径、备选路径、风险、验证方法。
- `verifying`：工具读回、测试、检索、构建或状态检查。
- `audited`：高风险、法律、系统规则、进化沉淀必须经过反证。

## 四、四核编排

| 核心 | 工程角色 | 产物 | 边界 |
|---|---|---|---|
| evolver | 缺陷扫描、失败归因、轨迹回收、基因沉淀、回测 | 缺陷表、基因条款、复发防线 | 不等于后台持续自进化 |
| autoresearch | 多源检索、读取、交叉验证、蒸馏 | 来源清单、证据分级、冲突处理 | 摘要不能替代原文 |
| openhands | 文件、终端、浏览器、沙箱执行 | 文件变更、命令输出、运行结果 | 无工具记录时只算规划 |
| superpowers | 澄清、设计、拆解、TDD/验证、审查、交付 | 计划、状态机、验收报告 | 流程名不能冒充测试结果 |

## 五、GPT 主导与量子路由组合

规则：

1. 量子路由负责展开候选通道和候选路径。
2. 用户明确要求 GPT 主导时，必须确认 GPT 通道可用，例如 `qr tier B` 返回 `gpt55_5yuantoken`。
3. GPT 主脑负责最终路径选择、冲突消解、真实性边界、补齐落地与交付状态。
4. 子智能体只提供拆解、执行、验证和反证材料；不能替代主脑裁决。
5. 如果自动路由选到低阶通道，不能机械服从；应结合用户指定和健康检查显式升级主通道。

## 六、证据卡字段

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

## 七、真实性四件套

凡写“已支持”“已实现”“可自动执行”“已集成”，必须同时满足：

1. 有实际代码入口或配置绑定。
2. 有一次真实运行记录。
3. 有可复现的输入输出样例。
4. 有最近一次验证时间。

少一项时，只能写：

- 流程目标
- 设计意图
- 可执行方案
- 待验证能力

不能写成已实现事实。

## 八、落地位置

- 主技能：`/Users/appleoppa/.hermes/skills/workflow/apex-hermes-evolution-engine/SKILL.md`
- 模块：`Module H：TianGong GPT-Led Four-Core Orchestration`
- 本 reference：`references/2026-05-22-tiangong-four-core-orchestration.md`

## 九、验收标准

启用 TianGong 后，交付前必须能回答：

- GPT 主通道是否确认？
- 量子路由结果是什么？
- 四核各自承担了什么？
- 哪些来源被真实读取？
- 哪些动作被真实执行？
- 哪些结果被验证？
- 哪些能力只是设计目标，尚未实现？
- 是否有技能、规则、记忆或工作区记录沉淀？
