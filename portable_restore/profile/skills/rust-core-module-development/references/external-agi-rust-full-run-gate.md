# 外部 AGI/Rust 仓库“全量运行”安全门禁

## 适用场景

用户要求对外部或复刻的 Rust/Python/AGI 仓库“立刻全量运行”“跑起来”“全量测试”。这类仓库常包含：

- 根 Rust crate + 嵌套模块；
- Python 工具包 / Web UI；
- install/launcher/deploy/docker-compose；
- daemon/watchdog/self-evolution/auto-commit/push；
- build artifacts、target/release、配置样例和 gateway 入口。

## 标准执行顺序

1. **入口盘点**
   - 识别 `Cargo.toml`、`requirements.txt`、`pyproject.toml`、`Dockerfile`、`docker-compose.yml`、`install.sh`、`launcher.sh`、`deploy*.sh`、daemon、自演化脚本。
   - 统计 Rust/Python/test 文件数量，先不运行高风险入口。

2. **低副作用全量检查优先**
   - Rust：`cargo metadata --no-deps` → `cargo check --all-targets` → `cargo test --all-targets`。
   - Python：`python3 -m compileall -q .`。
   - CLI：优先 `--help` / `help` / `status` 这类只读或状态命令。

3. **低风险修复可以直接做**
   - 明显语法错误：如 `import uuid::Uuid` → `use uuid::Uuid`、错误 raw string、字面量中多余 `\n`、重复模块声明。
   - 测试编译阻断：如未导出 module、测试 mock 类型不匹配、缺少直接依赖。
   - 修复后必须重跑 check/test。

4. **服务启动门禁**
   - `start`、daemon、launcher、install、deploy、docker-compose、自演化脚本、auto commit/push 均属于副作用入口。
   - 只有在源码已编译通过、配置/密钥/端口/外联边界清楚、并能限制到 localhost 时，才考虑健康检查式启动。
   - 编译未过时，不启动服务；只能报告阻断项和修复路径。

5. **结果表达**
   - 区分：`完整通过`、`部分通过`、`编译阻断`、`服务未启动`。
   - 不把 `cargo metadata` 或 Python compile 通过说成整体可运行。
   - 报告应列：执行项、通过项、阻断项、已修复项、未运行高风险项、下一步修复路径。

## 典型阻断分类

- 依赖缺失：`semver`、`url`、`flate2`、`tar`、`wasmtime`、`tokio_stream`、`bytes` 等。
- feature 缺失：如 `reqwest::multipart`、`nix::sched`。
- 模块错配：Rust `pub mod` 指向 Python 包目录、re-export 与实际类型不一致。
- sanitized 拼合痕迹：重复 import、placeholder/mock 模块、跨版本 workspace 结构不一致。

## 交付模板

```text
结论：完整通过 / 部分通过 / 阻断
已运行：metadata/check/test/compileall/status
已修复：低风险补丁列表
未运行：install/launcher/deploy/docker/daemon/self-evolution
阻断：错误类别 + 代表性路径
下一步：依赖/feature/module/re-export 分层修复
证据：报告路径 + 机器日志/JSON 路径
```
