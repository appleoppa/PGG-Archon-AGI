# APEX-MEM 私有远程仓库同步与可复现部署模式

适用场景：用户问“本地能力是否已同步到我的远程私有仓库”“其他电脑是否只需 clone 部署”或要求把 APEX-MEM / Rust memory sidecar（记忆侧车服务）做成可复现安装包。

## 核心判断纪律

- 不能把本地工作树能力冒充为远程仓库能力。必须核查：`git status --short`、`git rev-parse HEAD`、`git ls-remote origin refs/heads/main`、`gh repo view ... isPrivate`。
- `HEAD == origin/main` 只说明提交同步；若 `git status --short` 非空，仍不能说全部能力已同步。
- Hermes bridge（桥接）通常位于 Hermes-Agent 仓库，不属于 APEX-MEM 源码仓库；若要“其他电脑只 clone 即可部署”，必须把 bridge 模板和安装脚本纳入 APEX-MEM 或同步到对应 Hermes 私有仓库。
- LaunchAgent、runtime data、已编译 binary 不是源码仓库默认内容；需要部署脚本和 smoke test（冒烟测试）使目标机可重建。

## 推荐仓库化资产

在 APEX-MEM 仓库中加入：

- `scripts/deploy_macos.sh`：构建 release binary、写入 LaunchAgent、启动服务、等待 `/health`、调用 smoke test。
- `scripts/smoke_test.sh`：验证 `/health`、`/v1/stats`、1MiB body limit 返回 413、REST+MCP graph seed 检索。
- `scripts/install_hermes_bridge.sh`：复制 `hermes_bridge/agent/apex_mem_client.py` 和 `hermes_bridge/tools/apex_mem_tool.py` 到目标 Hermes Agent，并尝试把 `apex_mem` 加入 `pgg_archon` toolset。
- `hermes_bridge/agent/apex_mem_client.py`、`hermes_bridge/tools/apex_mem_tool.py`：bridge 模板。
- `ops/launchd/com.appleoppa.apex-mem.plist.template`：LaunchAgent 模板。
- `docs/REMOTE_DEPLOYMENT.md`：clone、deploy、bridge、verify、WATCH 边界。

## 执行顺序

1. 本地验证当前仓库：
   - `bash -n scripts/*.sh`
   - `cargo fmt --check`
   - `cargo clippy --all-targets --all-features -- -D warnings`
   - `cargo test`
   - `cargo check --benches --locked`
   - `./scripts/smoke_test.sh http://127.0.0.1:8765`
2. scoped add：只 add 本任务相关文件，如 `Cargo.* README.md benches src tests docs hermes_bridge ops scripts`。
3. commit：例如 `feat: absorb upstream fixes and add reproducible deployment`。
4. push 到私有远程。
5. 远程读回：确认 `origin/main` 等于本地 HEAD，`gh repo view` 显示 private=true。
6. fresh clone 到临时目录，执行：
   - `bash -n scripts/*.sh`
   - `cargo build --release`
   - 使用不同端口（如 `127.0.0.1:9877`）启动 fresh clone binary
   - `./scripts/smoke_test.sh http://127.0.0.1:9877`
   - 可选：`HERMES_AGENT_DIR=... ./scripts/install_hermes_bridge.sh`
7. 杀掉临时服务，避免端口/进程残留。

## 完成口径

可以说：

> APEX-MEM 当前本地已验证能力已 commit 并 push 到私有远程仓库；fresh clone build + smoke test 已通过。其他电脑可 clone 该仓库并运行部署脚本部署 sidecar；若需要 Hermes bridge，目标电脑需已有 Hermes Agent 并执行 bridge 安装脚本。

不能说：

- 完全零依赖一键部署（目标机仍需 Git、Rust/Cargo、macOS launchctl、私有仓库权限）。
- 已替换 Hermes core memory provider。
- 生产级外网开放安全。
- 零供应链风险。

## 常见坑

- `git push` 成功前不要回答“已同步远程”。
- fresh clone 验证不能复用当前工作树或当前已部署 binary。
- 用不同端口启动 fresh clone 服务，避免误打本机常驻服务。
- 在 foreground terminal 命令里不要使用 shell `&` 偷跑服务；应使用 Hermes background process 管理，或部署脚本正式交给 launchctl。
- bridge 安装脚本要幂等：如果 `toolsets.py` 已含 `apex_mem`，应通过而不是重复写入。
