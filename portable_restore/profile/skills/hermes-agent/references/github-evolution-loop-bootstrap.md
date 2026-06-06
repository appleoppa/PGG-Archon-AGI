# GitHub 进化闭环启动配方

适用场景：用户授权 Hermes 使用 GitHub、Gist、Actions、容器和多模型路由搭建自动化研究/验证/回流系统，用于自我进化、代码实验、论文/项目精华吸收等长期闭环。

## 核心架构

- 本地 Hermes：负责调度、验收、真实性核验、成果吸收和技能沉淀。
- GitHub 仓库：承载任务、研究材料、进化基因、实验代码、回流队列。
- Gist：轻量任务中转站；本地卡顿或仓库流程过重时优先用它承接小任务。
- GitHub Actions：远程容器执行检索、提炼、测试、验证和结果写回。
- GitHub Secrets：只存密钥，不在仓库、聊天、报告、记忆或技能正文中输出明文。

## 推荐最小目录

```text
workspace/github-evolution/
  README.md
  evolution-system.json
  tasks/
  research/
  genes/
  experiments/
  actions/
  inbox/
  archive/
```

## 主辅脑状态记录

在状态文件中记录模型名和环境变量引用，不记录密钥值。推荐字段：

```json
{
  "brain": {
    "primary": "gpt-5.5",
    "assistants": ["deepseek-v4-flash", "MiniMax-M2.7-highspeed"]
  },
  "status": {
    "models_verified": true,
    "github_cli_installed": true,
    "github_authenticated": false,
    "minimum_local_workspace_ready": true,
    "remote_loop_ready": false
  }
}
```

## 启动顺序

1. 先核验主辅脑配置是否只引用环境变量，避免明文密钥。
2. 对每个模型做极小请求验证，只报告“可用/不可用”，不输出密钥。
3. 核验 GitHub API 可达、GitHub CLI 是否可用、当前是否已登录。
4. 建立本地最小工作区和状态文件。
5. 本地验证通过后，再创建远程仓库、Gist、Actions 和 Secrets。
6. 跑通一次最小远程任务：任务包 → Actions 容器 → 结果写回 inbox → 本地复核。

## 安全边界

- 用户说“全部权限”时，理解为授权继续配置，但仍应采用最小可用权限和安全存储。
- 不要求用户把令牌发到聊天里；让用户在本机登录或写入本机环境变量/GitHub Secrets。
- 若无 GitHub 登录或令牌，只能完成本地骨架和 API 连通验证，不能声称远程闭环已完成。
- 远程创建仓库、Gist、Secrets、Actions 前要先核验授权状态。

## 最小验收标准

- 三类模型密钥存在且极小请求成功。
- 本地工作区必要文件存在。
- GitHub API 可访问。
- GitHub CLI 已安装或有等价 API 调用路径。
- 明确区分：本地最小闭环已完成、远程 GitHub 闭环是否已完成。
