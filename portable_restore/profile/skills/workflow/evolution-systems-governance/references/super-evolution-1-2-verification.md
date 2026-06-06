# 超级进化1-2验收与配置记录

> 会话：2026-05-25
> 任务：验证超级进化1（河图洛书LLM路由）和超级进化2（GitHub仓库远程进化闭环）的学习完整性和落地状态，并完成深度配置

## 验收方法论

### 六维度验证标准

| 维度 | 验证方法 | 证据类型 |
|------|---------|---------|
| **学习吸收** | 搜索技能文档、SOUL.md、AGENTS.md 中是否含相关规则 | 技能文件路径、规则条目 |
| **落地实现** | 检查可执行产物：CLI工具、脚本、配置文件、仓库 | 文件路径、命令输出 |
| **健康检查** | 运行健康检查命令，验证所有组件可用 | 命令输出、状态码 |
| **路由验证** | 用真实任务描述测试路由决策 | 路由结果JSON、选中模型 |
| **配置同步** | 对比 Hermes config.yaml 与工具配置源码 | 配置差异、base_url对比 |
| **规则固化** | 检查强制入口规则、降级策略、五段链是否写入技能 | 技能章节引用 |

### 超级进化1验收流程

1. 读取原始需求文件：`~/Desktop/进化文件/超级进化/超级进化1-河图洛书llm路由.md`
2. 搜索技能库：`search_files pattern="河图洛书|quantum.*router" path=~/.hermes/skills`
3. 检查 Rust CLI 部署：`qr health` / `qr route "<任务描述>"`
4. 检查配置同步：对比 `~/.hermes/config.yaml` 与 `~/.hermes/quantum-router/src/config.rs`
5. 验证技能固化：`skill_view(name='quantum-channel-router')`
6. 检查 SOUL.md / memory 中是否含河图洛书规则

### 超级进化2验收流程

1. 读取原始需求文件：`~/Desktop/进化文件/超级进化/超级进化2-github仓库.md`
2. 检查 GitHub 认证：`gh auth status`
3. 检查远程仓库：`gh repo view appleoppa/hermes-github-evolution`
4. 检查本地工作区：`ls -la ~/.hermes/workspace/github-evolution/`
5. 检查 evolver 脚本：`ls ~/.hermes/workspace/github-evolution/scripts/evolver.py`
6. 检查 GitHub Actions：`gh api repos/appleoppa/hermes-github-evolution/actions/runs`
7. 检查基因回流：`ls ~/.hermes/workspace/github-evolution/genes/evolver_*.json`
8. 验证真实采样：读取基因文件，检查 `sampled_paths`、`text_hashes`、`workflow_files_seen`
9. 检查技能固化：`skill_view(name='hermes-agent', file_path='references/github-evolution-loop.md')`

## 超级进化1验收结果（2026-05-25）

| 维度 | 状态 | 证据 |
|------|------|------|
| 学习吸收 | ✅ 完整 | `quantum-channel-router` 技能 v1.2.0 |
| 落地实现 | ✅ 完整 | `~/.cargo/bin/qr`，源码 `~/.hermes/quantum-router/` |
| 健康检查 | ✅ 通过 | 5个模型全部 `ok`：GPT-5.5、DeepSeek-v4、Claude-opus-4-7、MiniMax-M2.7、GLM-4.5 |
| 路由验证 | ✅ 通过 | `qr route "复杂法律案件分析与文书撰写"` → B级（deepseek-v4-flash） |
| 配置同步 | ✅ 完整 | Hermes `config.yaml` 中 5 个 provider 已配置并与 qr 同步 |
| 规则固化 | ✅ 完整 | 河图洛书五段链、强制入口规则、降级策略已写入技能和 SOUL.md |

**核心落地产物**：
- Rust 路由引擎：`~/.hermes/quantum-router/`（Cargo 项目）
- CLI 工具：`qr health` / `qr route` / `qr cache` / `qr config`
- 技能文档：`quantum-channel-router/SKILL.md`（含超级进化1-14吸收规则）
- 分级标准：A=GPT-5.5（主脑）、B=DeepSeek（推理）、C=Claude（代码）、D=MiniMax（低成本）、E=GLM（兜底）
- 五段链：主脑统筹 → 反证审错 → 修复落地 → 旁证压缩 → 主脑收束

## 超级进化2验收结果（2026-05-25）

| 维度 | 状态 | 证据 |
|------|------|------|
| 学习吸收 | ✅ 完整 | `hermes-agent` 技能的 `references/github-evolution-loop.md` 和 `evolution-systems-governance` 技能 |
| GitHub 认证 | ✅ 通过 | `gh auth status` 显示已登录 appleoppa 账号，token 权限完整 |
| 远程仓库 | ✅ 存在 | `appleoppa/hermes-github-evolution` 私有仓库（2026-05-21创建） |
| 本地工作区 | ✅ 完整 | `~/.hermes/workspace/github-evolution/` 含完整目录结构 |
| Evolver 脚本 | ✅ 落地 | `evolver.py` 和 `awakening_cycle.py` 已部署 |
| GitHub Actions | ✅ 运行 | 最近3次 workflow 全部 success（2026-05-21） |
| 基因回流 | ✅ 验证 | genes/ 目录含 29 个 evolver 基因文件，inbox/ 含 22 个回流结果 |
| 真实采样 | ✅ 通过 | 基因文件含真实 GitHub 公开项目，含 sampled_paths、text_hashes、workflow_files_seen |

**核心落地产物**：
- 远程仓库：`appleoppa/hermes-github-evolution`（私有）
- 本地工作区：`~/.hermes/workspace/github-evolution/`
- Evolver 引擎：`scripts/evolver.py`（GitHub API 搜索 + 元数据采样 + 基因提取）
- GitHub Actions：`.github/workflows/evolve.yml`（远程容器执行）
- 基因库：29 个 evolver 基因文件，含真实项目采样路径和内容 hash
- 回流验证：22 个 inbox 结果文件，本地可读回验证

## 超级进化2深度配置（2026-05-25）

### 配置目标

完成"每15分钟自动循环"的 cron 配置，实现：
- evolver 自动执行
- 基因自动提取
- 结果自动推送到远程仓库
- Silent watchdog 模式（只在有新基因或错误时通知）

### 配置步骤

1. **创建 watchdog 脚本**：`~/.hermes/workspace/github-evolution/scripts/github_evolver_cron.py`
   - 记录执行前后 inbox 文件数
   - 执行 evolver.py
   - git add + commit（只在有变更时）
   - git push 到远程仓库
   - Silent watchdog：只在有新基因或错误时输出

2. **修复 GitHub 认证**：
   - 问题：HTTPS 推送需要 token，SSH 推送需要 key
   - 方案：使用 `GH_TOKEN` 环境变量通过 HTTPS 推送
   - 实现：`git push https://${GH_TOKEN}@github.com/appleoppa/hermes-github-evolution.git main`

3. **创建 cron 任务**：
   ```python
   cronjob(
       action='create',
       name='GitHub进化工厂15分钟循环',
       no_agent=True,
       schedule='*/15 * * * *',
       script='workspace/github-evolution/scripts/github_evolver_cron.py',
       workdir='/Users/appleoppa/.hermes'
   )
   ```

4. **验证首次执行**：
   - 手动运行 watchdog 脚本
   - 检查新基因生成
   - 检查远程仓库最新 commit
   - 确认 silent watchdog 行为

### 配置结果

| 维度 | 状态 | 证据 |
|------|------|------|
| 15分钟自动循环 | ✅ 已配置 | cron job `a17f243152c1` 已创建，每15分钟触发 |
| Watchdog 脚本 | ✅ 已部署 | `github_evolver_cron.py` 已更新并修复认证问题 |
| 认证修复 | ✅ 完成 | 改用 GH_TOKEN 通过 HTTPS 推送，已验证可用 |
| 首次自动推送 | ✅ 成功 | 最新 commit: `chore: evolver auto cycle 20260525_073814` |
| 新基因生成 | ✅ 验证 | 新增 `evolver_20260524_233739.json`，共23个回流文件 |
| Silent Watchdog | ✅ 生效 | 只在有新基因或错误时输出，无新基因时静默 |

### 关键代码片段

```python
# Silent watchdog 逻辑
if result.returncode != 0:
    print(f"❌ Evolver 执行失败 (exit {result.returncode})")
    print(result.stderr)
    sys.exit(1)
elif new_genes > 0:
    print(f"✅ 新增 {new_genes} 条基因，已推送到远程仓库")
# 否则静默（无输出 = 无通知）
```

```bash
# HTTPS + GH_TOKEN 推送方案
git push https://${GH_TOKEN}@github.com/appleoppa/hermes-github-evolution.git main
```

## 真实能力边界

### 超级进化1

- ✅ 已完成：Rust CLI、5-provider配置、health/route/cache入口、分级标准、五段链、降级策略
- ⚠️ 未完成：真实cache条目积累、HashPool桥接、多Agent线程池级调度、全自动技能化

### 超级进化2

- ✅ 已完成：GitHub 认证、远程仓库、本地工作区、evolver 脚本、Actions 自动化、基因回流、真实采样验证、15分钟自动循环
- ⚠️ 待观察：长期稳定性、GitHub API 配额、token 过期处理
- ⚠️ 未完成：深度代码迁移、完整仓库理解、自动吞噬外部项目代码能力（当前只做只读元数据采样）

## 可复用模式

1. **验收六维度**：学习吸收、落地实现、健康检查、路由验证、配置同步、规则固化
2. **Silent Watchdog**：只在有新结果或错误时输出，无变化时静默（避免噪音通知）
3. **HTTPS + Token 推送**：避免 SSH key 配置，直接用环境变量中的 GH_TOKEN
4. **no_agent cron**：脚本自身产生最终消息，LLM 不参与（适合定时数据采集、健康检查、自动化流水线）
5. **基因真实性门禁**：必须含 sampled_paths、text_hashes、workflow_files_seen，不能只有 repo 名称
