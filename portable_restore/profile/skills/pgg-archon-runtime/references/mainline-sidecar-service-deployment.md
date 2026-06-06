# PGG Archon mainline sidecar 服务化部署记录

## 适用场景

当用户要求把一个本地 agent / runtime / claw 类项目“接入 Hermes / PGG Archon 主链路”“开启 AGI 之路”“吞噬吸收并落地”时，不应只生成报告或把源码存在说成能力完成。优先采用受控 mainline sidecar（主链路旁路组件）模式：先服务化运行，再接入 PGG Archon 健康证据与 runtime loop，最后入 gene DB 读回。

## 推荐闭环

1. 先做真实构建与测试
   - Rust 项目：`cargo metadata`、`cargo check --all-targets`、`cargo test --all-targets`、CLI help/status。
   - 修复阻断后重新跑完整检查。

2. 服务化部署
   - release build 后安装到稳定 PATH，例如 `~/.local/bin/<binary>`。
   - 建立配置、数据、日志目录。
   - macOS 使用 LaunchAgent 管理长期 daemon，日志放入 `~/Library/Logs/<service>/`。

3. 运行态验证
   - 验证 launchd label 为 running。
   - 验证进程存在。
   - 验证 CLI status 或健康探针 responding。
   - 不得把“二进制存在”当作“服务可用”。

4. PGG Archon 接入
   - 新增 `~/.hermes/agent/pgg_archon_<name>_mainline.py` 作为健康证据桥接。
   - 修改 `pgg_archon_module_status.py` 纳入模块状态检查。
   - 修改 `pgg_archon_runtime_loop.py` 读取 sidecar 健康态并写入实验结果。
   - 健康且边界清晰后写入 gene DB，并读回验证。

5. 安全边界
   - 默认不替换 Hermes Agent 核心。
   - 默认不共享 Hermes 凭据。
   - 默认不启用外部 gateway（Feishu/GitHub 等），除非用户明确授权并完成安全审查。
   - 只称为受控协同节点 / mainline sidecar，不夸大为完整 AGI 或核心替换。

6. 清理历史吸收源
   - 对已吸收且不再活跃的旧 runtime / workspace / skill 口径，先备份隔离再从活跃路径移除。
   - gene DB 中旧命名残留要计数、删除、再读回计数为 0。
   - profile 中外部 gateway 凭据引用要避免多 profile 抢同一 app。

## 完成态门禁

完成交付前至少具备：

- release/构建通过；
- 测试通过；
- daemon running；
- CLI/status responding；
- PGG 模块状态检查纳入；
- runtime loop 纳入 sidecar 证据；
- gene DB 写入并读回；
- 报告和机器证据 JSON 生成；
- 若涉及历史系统清理，备份路径与活跃残留计数明确。

## 汇报口径

字段化汇报，不要大段叙事：

- 当前状态：已部署 / 已接入 / 已清理 / 已验证；
- 证据：daemon、PID、health、gene DB、报告路径；
- 边界：未替换核心、未共享凭据、未启用外部 gateway；
- 备份：列出备份路径；
- 下一步：只有在用户要求继续强化时再列。
