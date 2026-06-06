# 超级进化文件验证清单

## 适用场景

用户要求核查超级进化1-14的学习完整性和落地状态时，按本清单执行系统化验证。

## 验证维度

每个超级进化文件的验证必须覆盖以下维度：

| 维度 | 检查内容 | 证据类型 |
|------|---------|---------|
| **学习吸收** | 原始需求是否已吸收进技能/配置/规则 | 技能文档、SOUL.md、AGENTS.md、config.yaml |
| **落地实现** | 是否有可执行产物（脚本/CLI/配置/仓库） | 文件路径、命令输出、仓库存在性 |
| **功能验证** | 核心功能是否可用 | 健康检查、路由测试、API调用、workflow运行 |
| **配置同步** | 相关配置是否一致 | config.yaml、qr config、环境变量、Secrets |
| **规则固化** | 执行规则是否写入持久化文档 | 技能SKILL.md、治理文档、入口规范 |
| **真实数据** | 是否有真实外部数据/采样/hash | 基因文件、回流结果、API响应、commit记录 |

## 超级进化1验证模板（河图洛书LLM路由）

```bash
# 1. 读取原始需求
read_file ~/Desktop/进化文件/超级进化/超级进化1-河图洛书llm路由.md

# 2. 查找落地产物
find ~/.hermes -name "*quantum*" -o -name "*河图*" -o -name "*hetu*"
ls -la ~/.hermes/quantum-router/

# 3. 验证CLI工具
qr health
qr route "复杂法律案件分析与文书撰写"

# 4. 检查配置同步
qr config
read_file ~/.hermes/config.yaml | grep -A 10 "providers:"

# 5. 确认规则固化
skill_view quantum-channel-router
search_files pattern="河图洛书|quantum.*router" path=~/.hermes/skills

# 6. 汇总状态
# 输出表格：维度 | 状态 | 证据
```

## 超级进化2验证模板（GitHub仓库远程进化闭环）

```bash
# 1. 读取原始需求
read_file ~/Desktop/进化文件/超级进化/超级进化2-github仓库.md

# 2. 验证GitHub认证
source ~/.hermes/.env && export GH_TOKEN && gh auth status

# 3. 检查远程仓库
gh repo view appleoppa/hermes-github-evolution
gh api repos/appleoppa/hermes-github-evolution/contents

# 4. 查找本地工作区
ls -la ~/.hermes/workspace/github-evolution/

# 5. 验证evolver脚本
ls -la ~/.hermes/workspace/github-evolution/scripts/

# 6. 检查GitHub Actions
gh api repos/appleoppa/hermes-github-evolution/actions/runs --jq '.workflow_runs[0:3]'

# 7. 验证基因回流
ls -1 ~/.hermes/workspace/github-evolution/genes/ | head -10
cat ~/.hermes/workspace/github-evolution/genes/evolver_*.json | python3 -m json.tool | head -80

# 8. 检查真实采样
# 验证基因文件中是否含：repo、url、sampled_paths、text_hashes、verification

# 9. 确认规则固化
skill_view hermes-agent file_path=references/github-evolution-loop.md
search_files pattern="github.*evolution|evolver" path=~/.hermes/skills

# 10. 汇总状态
# 输出表格：维度 | 状态 | 证据
```

## 通用验证流程

1. **读取原始需求**：确认用户期望的核心能力
2. **查找落地产物**：搜索相关文件/目录/命令/仓库
3. **验证核心功能**：执行健康检查/测试命令/API调用
4. **检查配置一致性**：对比多处配置是否同步
5. **确认规则固化**：检查技能/治理文档是否已更新
6. **验证真实数据**：确认有外部数据/采样/hash/commit
7. **汇总状态表格**：维度 | 状态（✅/⚠️/❌）| 证据

## 状态判断标准

| 状态 | 含义 | 判断依据 |
|------|------|---------|
| ✅ 完整 | 该维度已完整落地并可验证 | 有明确证据：文件存在、命令成功、数据真实、规则固化 |
| ⚠️ 部分完成 | 基础设施就绪但未完全启用 | 脚本/配置存在但未定时触发，或只做只读采样未深度吞噬 |
| ❌ 未完成 | 该维度缺失或不可用 | 文件不存在、命令失败、配置缺失、规则未固化 |

## 真实能力边界

验证报告必须明确区分：

- **已完成**：有证据链支撑的完整闭环
- **部分完成**：基础设施就绪但未完全启用/集成
- **未完成**：原始需求中提到但当前未实现的能力

不得把"配置存在"、"通路可用"、"脚本存在"直接等同于"真实参与"或"完整落地"。

## 汇报格式

对用户汇报时使用表格 + 分段说明：

```markdown
## 核心证据

| 维度 | 状态 | 证据 |
|------|------|------|
| 学习吸收 | ✅ 完整 | ... |
| 落地实现 | ✅ 完整 | ... |
| 功能验证 | ✅ 通过 | ... |
| 配置同步 | ✅ 完整 | ... |
| 规则固化 | ✅ 完整 | ... |
| 真实数据 | ✅ 验证 | ... |

## 落地产物

1. ...
2. ...

## 当前执行规则（已固化）

- ...
- ...

## 真实能力边界

- ✅ 已完成：...
- ⚠️ 部分完成：...
- ❌ 未完成：...
```

## 陷阱与注意事项

1. **不能只读原始文件就判断**：必须查找实际落地产物
2. **不能只看配置存在**：必须验证功能真实可用
3. **不能只看脚本存在**：必须检查是否有真实运行记录/输出
4. **不能只看技能提到**：必须确认规则已写入SKILL.md正文
5. **不能只看仓库存在**：必须验证有真实commit/workflow/回流数据
6. **不能把"部分完成"说成"完整"**：明确区分基础设施就绪 vs 完全启用

## 后续扩展

本清单可用于验证超级进化3-14的落地状态，每个超级进化文件根据其核心能力调整具体验证步骤。
