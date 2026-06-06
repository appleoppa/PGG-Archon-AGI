# Cron 脚本断裂与 macOS SSL 链路故障查证记录

## 触发场景

- cron 任务报 `error` 且 stderr 出现 `ModuleNotFoundError: No module named 'hermes_cli.apex_runtimeos'`
- GitHub `git fetch/push` 报 `LibreSSL SSL_connect: SSL_ERROR_SYSCALL in connection to github.com:443`
- watchdog / 进化 cron 持续失败但配置和密钥看起来都对

---

## 问题1：Cron 脚本引用了不存在的模块路径

### 症状

```
ModuleNotFoundError: No module named 'hermes_cli.apex_runtimeos'
```

### 根因

Cron 任务配置的 `script` 字段引用了 `hermes_cli.apex_runtimeos`，但真实模块路径是：

- 实际位置：`agent/apex_runtimeos_*.py`
- 错误引用：`hermes_cli.apex_runtimeos`

### 修复原则

Cron `no_agent` 脚本使用 Python subprocess 执行，必须引用正确的 import 路径：

| 模块 | 正确路径 |
|---|---|
| `apex_runtimeos_autonomy` | `agent.apex_runtimeos_autonomy` |
| `apex_runtimeos_evm_gate` | `agent.apex_runtimeos_evm_gate` |
| `apex_runtimeos_sequence` | `agent.apex_runtimeos_sequence` |

**禁止**引用 `hermes_cli.apex_runtimeos`（不存在）。

### 验证命令

```bash
# 验证模块是否存在
cd ~/.hermes/hermes-agent && venv/bin/python -c "from agent import apex_runtimeos_autonomy; print('OK')"

# 验证 cron 脚本引用的模块
grep -r "hermes_cli.apex_runtimeos" ~/.hermes/cron/  # 应无结果
```

---

## 问题2：macOS GitHub SSL_ERROR_SYSCALL

### 症状

```
fatal: unable to access 'https://github.com/...': LibreSSL SSL_connect: SSL_ERROR_SYSCALL in connection to github.com:443
```

### 根因

macOS 系统代理配置（`~/.zshrc` / `launchd` / 网络设置）指向 `127.0.0.1:7890`，但本地没有真实监听进程。HTTPS 请求被系统代理拦截后直接失败，而不是走直连。

### 已知修复

在 `launchd` gateway 环境变量中配置 `NO_PROXY` / `no_proxy`，豁免飞书域名：

```
NO_PROXY=open.feishu.cn,msg-frontier.feishu.cn,.feishu.cn,open.larksuite.com,.larksuite.com
no_proxy=open.feishu.cn,msg-frontier.feishu.cn,.feishu.cn,open.larksuite.com,.larksuite.com
```

对于 GitHub SSL 故障，需要额外豁免 `github.com`：

```bash
# 临时测试：禁用代理后直接访问
git -c http.proxy= -c https.proxy= fetch origin

# 或在 gitconfig 中为 github.com 禁用代理
# ~/.gitconfig 中添加：
[http "https://github.com"]
    proxy =
```

### 关键区分

| 故障类型 | 表现 | 解决方案 |
|---|---|---|
| macOS 系统代理无监听 | `SSL_ERROR_SYSCALL` | 豁免域名或禁用代理 |
| GitHub token 过期 | `403 Forbidden` | 刷新 token |
| 网络完全断开 | `Could not resolve host` | 检查网络 |
| 远程有本地没有的提交 | `rejected: fetch first` | `git pull --rebase` 后再 push |

---

## 验证清单

- [ ] cron stderr 无 `ModuleNotFoundError: hermes_cli.apex_runtimeos`
- [ ] `venv/bin/python -c "from agent import apex_runtimeos_..."` 成功
- [ ] GitHub fetch/push 无 `SSL_ERROR_SYSCALL`
- [ ] cron 任务 `last_status` 为 `ok` 而非 `error`

---

## 相关文件

- cron jobs 配置：`~/.hermes/cron/jobs.json`
- cron 输出日志：`~/.hermes/cron/output/<job_id>/`
- 实际模块路径：`~/.hermes/hermes-agent/agent/apex_runtimeos_*.py`
- macOS 代理豁免：gateway launchd plist / `~/.zshrc`
