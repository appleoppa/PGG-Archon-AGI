---
name: evolution-systems-governance
description: 开智/EVM/多智能体进化系统治理总纲：三顺序循环、EVM缺陷治理、河图洛书路由、GitHub工厂、多智能体技能复制与真实任务迁移
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [evolution, evm, router, multi-agent, governance, github-factory]
    related_skills: [manual-evolution-loop, evm-integration, multi-agent-replication]
---

# Evolution Systems Governance

## Overview

这是面向“开智进化循环 + EVM治理 + 河图洛书路由 + GitHub工厂 + 多智能体迁移/复制”的伞形技能。它把原本分散在多个窄技能中的流程合并为一个 class-level 入口：

- 用现行开智规范驱动真实进化闭环；
- 用 EVM 暴露和治理缺陷；
- 用多模型路由/反证仲裁提升可靠性；
- 用 GitHub/外部学习作为反幻觉外脑；
- 用 SKILL.md + delegate_task 复制多智能体体系，而不是复制旧框架本身。

## When to Use

- 用户要求执行、重跑、审计、修复“开智进化循环”。
- 用户提到 EVM、河图洛书路由、超级路由、GitHub factory、进化基因库。
- 用户要求把外部/旧多智能体系统迁移为 Hermes skills。
- 任务涉及自我进化、技能沉淀、短板暴露、真实任务迁移。
- 需要判断是否调用多模型链、外部学习、反证仲裁。

## 1. Current Evolution Loop Standard

唯一现行标准以工作空间当前规范为准；旧 cron、旧状态机、旧 R1-R5、旧五回合材料只能作为复盘资料，不能覆盖现行规范。

核心闭环：

```text
公式审错与修复 → 21354/12534/14325 各5遍 → 短板自然暴露 → EVM缺陷治理 → 超级路由决策 → GitHub/开源/官方文档学习 → 河图洛书/多模型反证仲裁 → 吸收补齐 → EVM回测 → 进化基因入库 → 验证 → 自驱报告与真实任务迁移
```

### Entry Prerequisite Gate

真实任务开始前先识别任务类型和强制触发技能；若多个入口并列，先执行任务前必须动作并记录证据字段。开智任务最低顺序：

1. 加载进化治理技能；
2. 读取现行规范；
3. 判断是否命中 quantum-channel-router；
4. 命中则先 route；
5. 再进入任务本体。

## 2. APEX Three-Sequence Logic

- **21354**：审错优先，用于事实核验、历史冲突、幻觉风险。
- **12534**：融合固化，用于吸收新知、沉淀技能、形成规则。
- **14325**：规划反证，用于复杂项目、cron/无人值守、执行路径压力测试。

三种顺序必须真实代入，每一步产生判断、证据、修复或沉淀；不能只写编号。

## 3. EVM Defect Governance

### Formula

```text
EVM = E × V × M × A × Base × 7古法 × (1 - defect_rate(含短板惩罚))
```

关键规则：

- 古法因子只乘 7 项，不额外乘八卦。
- 缺陷率使用平均缺陷 + 最大短板惩罚，而不是简单平均。
- 古法增强使用软上限；boost 系数可配置。

### Defect Mapping

| Defect | Ancient governance lens |
|---|---|
| ΔMem / ΔSoul | 黄帝内经 |
| ΔErr / ΔTok | 道德经 |
| ΔAgt / ΔRun | 易经 |
| ΔPan / ΔClw | 河图洛书 |
| ΔPrm / ΔNet | 天干地支 |
| ΔRes / ΔLog | 五行 |

### Route Necessity Gate

不要把所有任务默认送入多模型链。先判断复杂度、风险和不确定性：

- 低风险简单任务：主模型直接处理。
- 高风险、事实密集、法律、配置、进化、系统修复任务：进入路由/反证链。

## 4. 河图洛书 / Super Router Integration

### 超级进化1吸收：LLM 路由作为进化器官

来源：`/Users/appleoppa/Desktop/进化文件/超级进化1-河图洛书llm路由.md`。该指令已吸收为进化系统规则：用户交付多个模型 key 后，Hermes 必须主动决定如何组合使用 LLM，而不是等待用户逐次指定。路由不是装饰性健康检查，而是进化闭环中的“判断/反证/修复/压缩/收束”器官。

执行口径：

- 默认以 GPT-5.5 / A 级作为主脑和总裁判；A 级不可用时按 live `qr route` 降级，并明确记录降级。
- DeepSeek/B 级负责中文推理、法律/长文本、反证审错。
- Claude/C 级负责代码、结构、工程实现；不可用时不得冒充代码模型参与。
- MiniMax/D 级负责批量执行、草稿、整理、低成本吞吐。
- GLM/E 级负责压缩、摘要、格式化和轻量旁证。
- 开智进化任务必须证明路由实际改变了至少一项：短板识别、外部学习路径、修复动作、仲裁结论或完成态判断。

## 4. 河图洛书 / Super Router Integration

典型五阶段链：

| Step | Role | Model class |
|---|---|---|
| 1 | 主脑统筹 | GPT 系主模型 |
| 2 | 反证审错 | DeepSeek/强审错模型 |
| 3 | 修复落地 | MiniMax/执行模型 |
| 4 | 旁证压缩 | GLM/压缩模型 |
| 5 | 主脑收束 | GPT 系主模型 |

### Provider Pitfalls

- 5yuantoken 中文乱码时用 `json.loads(resp.content)`，不要用 `resp.json()`。
- MiniMax anthropic mode base URL 是 `https://api.minimaxi.com/anthropic`，最终 endpoint 为 `/anthropic/v1/messages`。
- DeepSeek base URL 不带 `/v1` 时才匹配其 chat/completions 路径。
- HTTP 200 不等于有效输出；必须检查非空用户可见文本、结论、证据、缺陷或修复内容。
- provider 密钥通常在 `.env`，Python 子进程要显式加载或使用项目 loader。

## 5. GitHub Factory / External Brain

### 超级进化2吸收：GitHub 仓库远程进化闭环

来源：`/Users/appleoppa/Desktop/进化文件/超级进化2-github仓库.md`。该指令已吸收为 GitHub 工厂规则：GitHub 的仓库、Gist、Actions、API 与容器用于远程检索、验证、演化和成果回流，但完成态必须由本地主脑验收，不能由远程 workflow 成功或文件存在直接推断。

执行口径：

- GitHub token 不进入记忆、技能、报告、仓库文件、Gist 或日志，只能使用环境变量、GitHub Secrets 或安全凭据存储。
- “完全配置”必须通过当前认证、repo、Gist、Actions、Secrets、evolver/evomap、回流数据、本地读回验证八类检查。
- 每15分钟自动循环只能在认证、权限、回流、门禁都通过后启用；否则只保留只读核验或本地候选任务。
- `PHI_RATIO +5%` 只能作为实验指标，必须有评估和回滚，不能直接宣称能力提升。
- 外部仓库吸收必须包含真实 repo、路径、hash、traits、机制和边界；未读真实内容不得声称吸收代码能力。

## 5. GitHub Factory / External Brain

GitHub factory 和外部学习用于给进化循环提供外部反馈，不是写报告装饰：

- 外部来源必须在短板暴露之后读取；
- 来源必须改变补齐动作；
- 反证仲裁必须产生修正增量；
- 结果需要落入规则、技能、数据库、配置或真实任务迁移。

### GitHub Mirror / Save-to-User-Repo Pitfall

当用户要求"拉取/复刻/保存到我的 GitHub"时，不要只检查远程链接存在就宣称已保存：

- 先把源分支拉到独立 worktree/目录，避免覆盖本地已有分支或未推送 commit；
- 推送前确认当前 GitHub 登录账号、目标 owner/repo 是否有写权限；第三方源仓库 403 要如实报告并改推用户账号仓库；
- GitHub Push Protection 拦截 secret 时，禁止绕过或把 secret 原文写入报告；应创建 sanitized mirror（脱敏镜像）再推送；
- 区分"原始拉取目录"和"脱敏发布目录"，并用本地/远程 commit 一致性作为完成证据。

### cron 脚本导入路径修复模式

cron 脚本（如 watchdog、autopromote、super_evolution）中的导入路径随模块重构可能断裂。典型断裂模式：

```bash
# 错误：hermes_cli.apex_runtimeos 不存在
from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli

# 正确：真实路径是 agent.apex_runtimeos_autonomy
from agent.apex_runtimeos_autonomy import (
    summarize_autonomy_status,
    build_runtimeos_health_watchdog_notice,
    score_autowrite_candidates,
    promote_autowrite_candidates
)
```

修复步骤：
1. 用 `inspect.signature` 或直接 import 测试真实函数名
2. 确认目标函数在 `agent/` 模块而非 `hermes_cli/` 下
3. 脚本改完后立即 `bash script.sh` 验证 exit 0
4. 确认函数返回值结构（空 dict / 空 list 在健康状态下是正常的）

**验证命令：**
```bash
cd ~/.hermes/hermes-agent
hermes-agent/venv/bin/python -c "from agent.apex_runtimeos_autonomy import summarize_autonomy_status; print(summarize_autonomy_status())"
```

### macOS GitHub SSL_ERROR_SYSCALL

macOS 系统代理（`127.0.0.1:7890` 等）若无真实监听，HTTPS 请求会被拦截并报 `LibreSSL SSL_connect: SSL_ERROR_SYSCALL` / `SSL_UNEXPECTED_EOF_WHILE_READING`。三层解法：

**1. git 层绕过（已知）：**
```bash
git -c http.proxy= -c https.proxy= fetch origin
```

**2. Python urllib 层：**
urllib 使用 LibreSSL，无法复现 `curl --noproxy '*'` 的直连成功路径。必须在代码层包装异常：

```python
# evolver.py / github_evolver_cron.py 标准模式
def request_json(url, headers=None):
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        return json.loads(resp.read())
    except Exception:  # SSL_ERROR_SYSCALL / UNEXPECTED_EOF / timeout
        return {}       # 返回空结构，不抛异常

def request_text(url):
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        return resp.read().decode()
    except Exception:
        return ""
```

**3. evolver.py 推送失败处理：**
网络不可达时 `exit(0)` 而非 `exit(1)`，避免 cron 日志被 error 污染。GitHub 推送放在最后，成功则推，失败则本地保留。下次 cron 触发时若网络恢复则自动重试。

**诊断命令：**
```bash
# 验证 CLI 工具是否可达
curl -v --noproxy '*' https://api.github.com

# 验证代理是否在监听
nc -z 127.0.0.1 7890

# 查看系统 SSL 后端
python3 -c "import ssl; print(ssl.OPENSSL_VERSION)"
curl --version | grep SSL
```

详见 `references/cron-script-module-path-and-macos-ssl.md`（hermes-agent 技能）。

## 6. Multi-Agent Replication Pattern

复制多智能体系统时，价值在数据、规则、知识和配置，不在旧框架。

### Three Layers

1. Hub Orchestrator SKILL.md：统一入口，负责路由和质量门禁。
2. Sub-agent SKILL.md：每个角色的职责、规则、输入输出和知识路径。
3. Data/Knowledge/Config：放入 workspace 或 migration，SKILL.md 只引用，不嵌入密钥。

### Migration Flow

1. 全量盘点源系统文件和角色。
2. 提取每个 sub-agent 的 role / rules / identity / memory / workflows。
3. 为每个角色写 class-level skill 或归入已有部门伞形 skill。
4. 建 hub 的路由表和 delegate_task 模板。
5. 多轮 gap analysis：文件数、类别数、关键文件、路径映射、内容大小/哈希抽样。

## 7. Completion Gates

开智/进化类任务必须同时满足：

- 短板来自真实代入或真实失败；
- 外部学习发生在短板之后；
- 学习改变补齐动作；
- 补齐已落地到规则/技能/流程/配置/数据库；
- 进化基因或等效记录已入库并读回验证；
- EVM/路由/反证环节有有效输出；
- 自驱报告和真实任务迁移已生成；
- 不从 exit_code、日志存在或状态字段单独推断完成。

## 8. References

- `references/manual-evolution-loop.md`：现行开智循环门禁、三顺序、已知陷阱。
- `references/evm-integration.md`：EVM formula、provider quirks、router/GitHub factory 集成细节。
- `references/no-agent-evolution-truth-gates.md`：no_agent 进化流水线的真实性门禁，避免把 exit/status/dry-run/样本失衡误报为完整进化。
- `references/super-evolution-verification-checklist.md`：超级进化1-14验证清单，含六维度验证标准、验证模板、状态判断标准和汇报格式。
- `references/super-evolution-1-2-verification.md`：超级进化1（河图洛书LLM路由）和超级进化2（GitHub仓库远程进化闭环）的验收方法论、配置步骤、真实能力边界和可复用模式（2026-05-25）。
- `references/super-evolution-3-verification.md`：超级进化3（深度自进化 - SearchSkill + SkillBank + Select-Read-Act）的六维度验证标准、Rust核心层验证三步法、Python粘合层验证、完整流程验证和2026-05-25验证记录。
- `references/super-evolution-4-5-verification.md`：超级进化4（Emv 熵 Skill 框架）和超级进化5（海马体 SWRs 记忆系统）的六维度验证标准、验证命令模板、重要性评分机制、安全边界、通用验证模式和2026-05-25验证记录。
- `references/super-evolution-5.5-integration.md`：超级进化5.5（Full Tool-Call 全局轨迹生成）的 Sidecar 系统验证、Hermes 工具集成、三步验证法、工具注册模式、集成状态汇报格式和关键陷阱（2026-05-25）。
- `references/super-evolution-9-verification.md`：超级进化9（EvoMaster 原生进化核心公式）的六维度验证标准、Sidecar 验证三步法、主链路集成验证、真实数据积累验证、完成度计算公式、未完成项清单和关键陷阱（2026-05-25）。
- `references/github-mirror-push-protection.md`：GitHub 复刻/保存到用户仓库时的权限核验、Push Protection 脱敏镜像、读回验证流程。

## Verification Checklist

- [ ] 是否读取并服从现行规范，而不是旧状态机？
- [ ] 是否真实执行三顺序代入，而不是只写编号？
- [ ] 短板是否自然暴露，有证据来源？
- [ ] 是否进入 EVM/路由/外部学习/反证，且输出有效？
- [ ] 补齐是否实际落地，而非只写分析？
- [ ] 基因/记录是否写入后读回验证？
- [ ] 多智能体迁移是否优先保留数据、规则、知识、配置？
