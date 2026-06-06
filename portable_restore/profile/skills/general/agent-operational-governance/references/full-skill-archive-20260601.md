---
name: agent-operational-governance
description: 智能体运营治理总纲：任务前边界识别、执行中证据核验、文件系统纪律、安全归档、用户汇报格式与完成态门禁
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [agent-governance, due-diligence, filesystem, reporting, verification, archive]
    related_skills: [agent-due-diligence, file-system-management, user-reporting-preferences]
---

# Agent Operational Governance

## Overview

这是面向 Hermes 智能体日常执行的运营治理伞形技能。它把三类原本分散的经验统一到一个入口：

1. **任务边界与尽职调查**：不要把简单指令过度系统化；不要凭配置、文件名或上一轮声明下结论。
2. **文件系统与资产纪律**：根目录只放系统/运行时/配置；工作产物进入 workspace；破坏性动作前先识别资产、备份、验证。
3. **用户汇报与完成态门禁**：中文、简洁、证据分级；不能从 artifact/status/exit_code 推断完成。

## When to Use

- 汇报进度、状态、清理结果、迁移结果、审计结果、扫描结果。
- 需要移动、删除、归档、整理 Hermes/workspace 文件或技能支持文件。
- 用户要求“交付给我”“检查是否完成”“整理一下”“清理一下”。
- 输出用户可读报告、Feishu/移动端消息、结论摘要。
- 任何涉及“已修复/已治理/已迁移/已完成”的声明。

## 1. Task Boundary Gate

### 不要过度推导

用户说“交付给我”通常就是在当前对话或指定渠道交付结果，不等于建立自动化交付体系。除非用户明确要求“建立体系 / 自动化 / 标准化 / 长期运行”，否则按字面完成。

### 区分交付渠道

- 电脑端当前会话：直接在对话内给出结果。
- Feishu/手机端：使用 Feishu 安全格式，少表格、少密集 Markdown。
- 未指定渠道：默认当前会话，不主动扩展到其他平台。

## 2. Evidence & Due Diligence Gate

### 全量扫描，不只读配置

- 配置文件声明的路径不存在，不代表资源不存在。
- 某路径存在，不代表数据可用。
- 重要结论要通过 `search_files` / `read_file` / `terminal` 工具验证实际状态。

### 内容溯源，不靠名字猜

判断资源来源、依赖关系、数据质量时，需要检查：

1. frontmatter / metadata / 正文标记；
2. 代码或脚本中的真实引用链；
3. 内容样本是否符合业务目标；
4. 必要时抽样 DB schema、行数、关键字段。

### 声明修复 ≠ 实质修复

遇到“已修复 / 已治理 / 已升级 / 已完成”时，必须验证实际改动点：

- patch 后读回文件内容；
- DB 更新后 `SELECT` 读回字段值；
- 目录迁移后检查来源已移除、目标完整；
- runner/cron 结束后检查业务产物，而非只看 exit code。

### 代码/本地服务状态评分门禁

当用户要求“评估某项目/服务现在状态和评分”时，不要只读 README 或状态命令。至少核验以下证据面，再给分：

1. **仓库态**：`git status --short --branch`、最近提交、未跟踪/不应入库产物（如 target、DB、日志）。
2. **构建态**：运行最小编译检查和测试；区分 `cargo check`、单元测试、集成测试、doctest/全量测试，不把局部通过说成全量通过。
3. **运行态**：真实检查进程、端口、PID/LaunchAgent/服务管理器、健康检查 endpoint（如 `/healthz`），不要只相信 status 文案。
4. **真实业务链路**：抽样跑一个最短用户路径；若 CLI/HTTP 返回的是 mock/格式化字符串，要明确标为“模拟链路”，不能按真实 LLM/agent 能力计分。
5. **配置一致性**：对比代码默认配置、环境变量注册、实际可用 provider/model 列表，指出“配置声明存在但运行时不可用”的差异。
6. **评分透明**：给出总分和分项权重；分数来自已核验证据，未实测项按风险扣分而不是按设计文档加分。

### 审计顺序

数据修改类任务的顺序必须是：

```text
INSERT/UPDATE/移动/写入 → 读回验证 → 质量/边际/完整性检查 → 汇报
```

不要用提交前快照作为提交后质量结论。

## 3. File System Governance

### 根目录边界

Hermes 根目录只放系统、运行时、配置、会话、cron、日志、skills、memory、cache、profiles、gateway 等系统资产。工作产物、临时分析、报告、脚本草稿进入 `~/.hermes/workspace/`。

### Workspace 标准

- 核心文件：`AGENTS.md`, `MEMORY.md`, `TOOLS.md`, `SOUL.md`, `USER.md`, `IDENTITY.md`。
- 工作目录：智库、向量库、开智、办案库、config、scripts、tools、workflows、standards、templates、logs、任务队列、审计队列、存档、监控日志。
- 不在 workspace 根部长期保留随机脚本、重复备份、过程文件夹、空壳目录。

### Cron 注册表与输出保留

- cron 审计后维护 `~/.hermes/workspace/治理/CRON_REGISTRY.md`：记录 active/paused、分类、频率、脚本路径、输出数量、风险等级、side effects、复审窗口。
- cron output 清理默认保留每个 job 最新 20 份；旧输出移入 `workspace/审计/cron-*/archived-old-cron-output/`，写 manifest 记录源路径、目标路径、hash、大小和移动时间。
- 第一轮 cron 清理不删除 job，只暂停/归档重复、断裂或高副作用任务；删除必须另行确认。
- 脚本路径按 Hermes 实际规则解析为 `~/.hermes/scripts/`，不要误用 job workdir 拼接脚本路径。

### 破坏性操作前五步

1. 检查真实内容，不凭名称判断。
2. 对 DB/索引/知识库检查 schema、行数、样本。
3. 识别受保护资产：向量库、法规/案例库、基因库、业务库、输出目录。
4. 不确定就归档，不直接删除。
5. 操作后验证来源、目标、断链引用和残留。

### 密钥泄漏治理

- 默认扫描 `~/.hermes`，不要打印原始密钥。
- `.env` 且权限 `0600` 是正常密钥存放点；配置、日志、session、归档备份是泄露面。
- 修复前先建 remediation 备份；修复后重扫。
- 优先把配置里的明文 `api_key` 改成 `key_env`/环境变量引用。

## 4. Reporting Governance

### 默认风格

- 中文、简洁、直接。
- 默认用“状态 / 数据 / 证据 / 风险 / 下一步”的结构。
- 不用命令输出堆砌替代结论。
- 不要暗示未经验证的完成。

### 默认骨架

| 项目 | 内容 |
|---|---|
| 当前状态 | 未开始 / 执行中 / 部分完成 / 完成 / 证据不足 |
| 核心数据 | 数量、比例、前后变化 |
| 证据等级 | 已核验 / 部分核验 / 未核验 |
| 风险边界 | 不能夸大的部分 |
| 下一步 | 若未完成，下一动作 |

### Feishu/移动端

- 避免密集表格和深层嵌套 Markdown。
- 优先使用标题行 + 字段块 + 短 bullet。
- 本地路径不要宣称“可点击”，除非已验证平台支持。
- 链接不可点击时，改成纯路径/code block + 简短操作说明。

## 5. Verification Checklist

- [ ] 是否先确认任务边界，没有把简单指令扩展成系统工程？
- [ ] 是否实际扫描/读回/抽样，而非只看配置或文件名？
- [ ] 是否验证了上一轮或工具声称的“完成/修复”？
- [ ] 是否按“写入/移动 → 读回 → 质量检查 → 汇报”的顺序执行？
- [ ] 文件是否进入正确位置，根目录未污染？
- [ ] 破坏性操作是否有备份/归档和断链检查？
- [ ] 汇报是否有清晰状态、数据、证据等级、风险边界？
- [ ] 是否避免从 exit_code、状态文件或 artifact 单独推断完成？

## Supporting References

- `references/agent-due-diligence.md`：声明修复、审计顺序、路径验证、系统健康审计的细节案例。
- `references/rust-workspace-deploy-verification.md`：Rust 多层工作区部署验证模式，含根/嵌套工作区区分、Cargo.toml 常见修复、源码语法错误隔离、Web UI Flask 测试客户端用法。
- `references/rust-generated-runtime-deploy-pattern.md`：当生成式 AGI/Rust 仓库全量源码难以一次性编译时，如何诚实收敛为可编译、可运行、可交互的 Rust runtime surface，并用 Web UI 代理验证。
- `references/hermes-full-audit-workflow.md`：Hermes 根目录全面只读评审、历史 Claw 系配置残留、密钥泄露面、配置一致性与清理优先级工作流。
- `references/file-system-management.md`：workspace 清理、资产保护、密钥泄漏治理、归档规则。
- `references/user-reporting-preferences.md`：中文简洁汇报和 Feishu/移动端格式偏好。
- `references/cron-background-review-dual-gate.md`：cron job 的 toolsets 配置层与后台执行审查层双层门控冲突，导致后台 cron 无法写文件；含根因分析、验证命令和解决方向。
- `references/session-extraction-report-pattern.md`：大体量会话导出/历史记录的关键信息提取、完成态归纳、证据链与恢复入口 Markdown 报告模式。
- `references/macos-hermes-cleanup-pattern.md`：macOS/Hermes 低风险文件清理追加模式，含 `.DS_Store` 可再生噪声、`tmp` 空目录保留、`MANIFEST.json` 证据链与汇报字段。
- `references/workspace-storage-governance-cleanup.md`：workspace 文件存储规则治理与清理模式，覆盖顶层归位、历史修复证据压缩、legacy store 删除门禁、Finder `.DS_Store` 复生处理和用户催促时继续执行的偏好。
- `references/local-skills-and-cron-task-audit.md`：本地技能库与 cron/task 审计模式，含 raw skill 与 runtime skill 对账、归档重复技能、cron 名称/频率漂移、任务事实源分层。
- `references/cron-audit-consolidation-cleanup.md`：Hermes cron 全量审计、相对脚本路径解析、备份、暂停归档、高频外部副作用任务合并、读回验证与报告模式。
- `references/hermes-context-token-governance.md`：Hermes 上下文/token 膨胀治理模式，覆盖混合压缩阈值、summarizer 输入硬上限、工具输出预算、reasoning/codex 落库降噪、AGENTS.md 主入口瘦身。
- `references/system-check-context-budget.md`：系统健康检查/办案条件检测的上下文预算模式；原始工具输出落盘，当前会话只回传 PASS/FAIL、数量、异常和证据路径，避免一次检测增长 40k token。
- `references/hermes-state-db-slimming-pattern.md`：Hermes `state.db` / `sessions/` 续清理模式，覆盖 request dump 删除、row-level gzip 回滚、历史 compression prompt/tool output/reasoning/system_prompt 定向瘦身、FTS/VACUUM/WAL checkpoint 与 gateway 停启验证。
- `references/hermes-full-system-first-pass-cleanup.md`：Hermes 根目录、Hermes Web UI、用户目录非系统文件夹的全量审计与第一轮低风险可回滚整理模式，含并行只读审计、MANIFEST、归档验证和禁止触碰项。
- `references/hermes-system-cleanup-continuation.md`：Hermes 系统清理续轮模式，覆盖 `state.db/sessions` 备份+VACUUM、workspace 资产索引、Rust/npm 工具链审计、Web UI upload 清单和第二轮报告门禁。
- `references/hermes-third-pass-cleanup-and-legal-vector-kb.md`：Hermes 第三轮破坏性清理与法律知识向量库重构模式，覆盖明确授权删除、sessions 保留窗口、旧 Chroma 只读迁移、法律 RAG 分层、开源方案对标和验证字段。

## Hermes Root Audit & Cleanup Pattern

When auditing or cleaning `~/.hermes`, use a staged, evidence-first workflow:

1. **只读全面评审**：先统计目录、文件数、权限、大文件、DB 表、历史 Claw 系配置残留、provider/cron/gateway 配置一致性；不要凭文件名或历史记忆判断。
2. **第一阶段只止血不删除**：对根目录明确残留和低风险垃圾先迁入 `workspace/存档/hermes-root-cleanup-<timestamp>/`，写 `MANIFEST.json`，记录 hash；不要直接删除。
3. **密钥治理边界**：不要打印或编辑运行态密钥；`.env`/`auth.json`/运行态 `config.yaml` 只做存在性、权限、key-env 映射检查。历史备份、日志、session repair、remediation originals 是泄露面，优先收紧权限或隔离。
4. **权限止血**：对 `workspace/session_repair_*`、`workspace/安全扫描/remediation_*`、`workspace/存档/迁移备份/migration/logs`、`memory/openclaw` 等敏感历史区统一目录 `0700`、文件 `0600`。
5. **验证门禁**：执行后必须确认源路径已消失、归档路径存在、核心运行资产仍存在、group/other 权限已清零，再汇报。
6. **Finder 噪声复生门禁**：macOS `.DS_Store` 可能在验证期间被 Finder 重新生成；发现复生时追加迁入同一归档（如 `moved-after-verify/`），更新 `MANIFEST.json` 和清理日志，再复查目标范围为 0。不要把一次复生误报为清理失败，也不要扩展到 `Library/` 等高噪声系统区。
7. **下一阶段才修配置**：根目录清洁后再处理 provider 命名分裂、`custom_providers`/`providers` 影子配置、辅助模型 401、profile 定位等一致性问题。

See `references/hermes-full-audit-workflow.md` for the detailed checklist, allowed actions, forbidden actions, and report template.

See `references/hermes-full-audit-workflow.md` for the detailed checklist, allowed actions, forbidden actions, and report template.
