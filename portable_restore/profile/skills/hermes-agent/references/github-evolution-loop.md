# GitHub 远程进化闭环配置记录

## 适用场景

用户要求把 Hermes 的进化、研究、代码验证、资源吸收放到 GitHub 上执行，并使用仓库、Gist、Actions、Secrets、API、容器能力形成远程闭环时，按本记录执行。

## 超级进化2吸收规则：GitHub 仓库远程进化闭环

来源：`/Users/appleoppa/Desktop/进化文件/超级进化2-github仓库.md`。

该文件已吸收为以下规则：

1. GitHub 仓库/Gist/Actions/API/容器只能作为远程进化工厂，不能替代本地主脑验收。
2. 令牌即使由用户授权，也只允许存在于环境变量、GitHub Secrets 或安全凭据存储；不得写入报告、记忆、技能、仓库文件、Gist 或日志。
3. “完全配置”必须同时通过：当前 GitHub CLI 或 token 可用、repo 可访问、Gist 可访问、Actions 可访问、Secrets 列表可见、evolver/evomap 脚本存在、回流文件有真实 repo/path/hash、结果可被本地主机读回验证。
4. 每 15 分钟自动循环必须先以只读/低风险 watchdog 方式运行；没有当前认证和远程写入验证时，只能标记为“本地部分吸收，远程认证阻断”。
5. `PHI_RATIO +5%` 只能作为实验指标或节奏参数，不能在没有效果评估和回滚机制时宣称真实能力提升。
6. 远程 workflow 成功只证明容器执行和数据回流；只有含真实采样路径/hash并经本地门禁验证的 gene 才能写入本地进化基因库。

只读核验脚本：`/Users/appleoppa/.hermes/scripts/verify_super_evolution2_github_hardening.py`。

## Evolver + Evomap 升级记录（2026-05-22）

已落地脚本：`~/.hermes/workspace/github-evolution/scripts/evolver.py`

远程闭环：
1. `evolve.yml` 在 GitHub Actions 容器内运行 evolver。
2. evolver 使用 GitHub API 搜索真实公开项目。
3. 对每个项目读取元数据、语言、根目录信号文件、工作流文件、小段文本内容。
4. 每条 gene 必须包含来源仓库、采样路径、内容 hash、traits、机制、边界。
5. 同时写入 `inbox/evolver_*.json`、`genes/evolver_*_genes.json`、`research/evolver_*_evomap.json`。
6. 本地主机必须 `git pull` 后读取 JSON 并验证 `minimum_gene_gate=true`，才可写入本地 EVM 基因库。

已验证远程 run：`26246491019`。本轮真实回流 4 个公开项目、4 条 genes，dominant traits 包括 agent_tooling_pattern、automated_test_gate、evaluation_gate、container_reproducibility。

新增边界：远程 workflow 成功只证明容器执行和数据回流；只有含真实采样路径/hash的 gene 才能入库；深度代码迁移必须另做逐仓库审计和测试。

## 本次沉淀的可复用流程

1. 先核验主辅脑配置，不输出密钥明文，只确认环境变量存在与最小请求可用。
2. 核验 GitHub 授权：优先检测 `GITHUB_TOKEN` 与 `GH_TOKEN`，再用 GitHub 命令工具确认账号、权限和 API 可访问性。
3. 若命令工具缺失，安装 GitHub CLI；这属于配置步骤，不要固化为“GitHub 不可用”。
4. 在 workspace 下建立本地项目骨架，不在根目录乱放文件。
5. 创建专用私有仓库，写入最小闭环代码：任务模板、流水线、远程执行脚本、回流目录。
6. 创建 Gist 作为轻量任务队列或中转站。
7. 将模型密钥写入仓库 Secrets，不写入仓库文件、不展示给用户。
8. 配置 GitHub Actions：远程容器执行检索/验证脚本，把结果提交回仓库收件箱。
9. 手动触发一次流水线，等待完成后拉回本地验证。
10. 若第一次主题过窄导致空结果，不要冒充成功吸收；换更合适主题重跑，直到有可验证回流结果。
11. 回写本地状态文件：远程仓库、Gist、Actions、Secrets、最近验证结果、下一步边界。

## 验收标准

- GitHub 账号身份已确认。
- 仓库存在且可推送。
- Gist 存在且可访问。
- Secrets 列表能看到已配置项，但不输出值。
- Actions 至少一次成功运行。
- 本地能拉回远程生成的结果文件。
- 结果文件中有真实 GitHub API 数据或其他可验证外部来源。
- 报告必须区分“最小闭环已通”和“深度吸收尚未完成”。

## 安全规则

- 用户即使说“全部权限”，也不在聊天中展示令牌。
- 令牌只放环境变量、Hermes 环境文件或 GitHub Secrets。
- 不把 GitHub 令牌写进记忆、技能、报告、仓库文件或 Gist。
- 只展示账号、权限范围和配置状态。

## 用户汇报方式

对苹果哥汇报时保持中文、简洁、无表格：

- 已完成什么
- 验证结果是什么
- 真实能力边界是什么
- 下一阶段该升级什么

不要展示命令细节、路径细节或英文日志。
