# Hermes 根目录全面评审与分阶段整改工作流

适用场景：用户要求对 `~/.hermes` 进行全面评审、删除迁移遗留、清理 OpenClaw/AutoClaw 残留、根目录清洁、权限止血、归档治理。

## 总原则

- 默认先做只读评审，除非用户明确确认整改。
- 破坏性动作前先备份或迁入安全归档；不确定就归档，不直接删除。
- 工作产物写入 `~/.hermes/workspace/`，不污染 Hermes 根目录。
- 不打印密钥；不修改 `.env`、`auth.json` 等运行凭据，除非用户明确授权。
- 完成态必须区分：只读已评审、已归档、已改权限、已删除、运行态已生效。

## 阶段 1：只读全面评审

必查范围：

1. 根目录文件和权限。
2. `config.yaml` / `.env` / `auth.json` / config 备份。
3. `profiles/`、`sessions/`、`logs/`、`cron/`、`skills/`、`memory/`、`memories/`、`workspace/`、`hermes-agent/`。
4. OpenClaw/AutoClaw/ClawDBot 残留路径。
5. 大文件、大目录、DB、缓存、归档、业务资产。
6. `0644` 且可能含密钥、token、credential、config、session backup 的文件。

输出应包含：

- 文件数、目录数、主要分区体量。
- P0/P1/P2 风险清单。
- 强保护资产清单。
- 可清理候选清单。
- OpenClaw/AutoClaw 残留分类。
- 明确说明“本轮是否修改文件”。

## 阶段 2：止血 + 根目录清洁

只有用户确认后执行。

推荐动作：

1. 创建安全归档目录：`workspace/存档/hermes-root-cleanup-<timestamp>/`。
2. 权限：归档目录 `0700`，归档文件 `0600`。
3. 迁移根目录明确残留：
   - `openclaw.json`
   - `openclaw.json.known-good`
   - `config.yaml.bak*`
   - 一次性修补脚本
   - `.DS_Store`
   - 调试日志
4. 为归档生成 `MANIFEST.json`，记录源路径、目标路径、大小、旧权限、新权限、hash。
5. 对高敏历史区域做权限收紧，而不是直接删除：
   - `workspace/session_repair_backup`
   - `workspace/session_repair_archive`
   - `workspace/安全扫描/remediation_*`
   - `workspace/存档/迁移备份/migration/logs`
   - `memory/openclaw`
6. 验证源路径已迁出、归档存在、核心运行文件仍存在、权限已收紧。

## 阶段 3：配置一致性修复

与 provider/model 相关的细节见 `llm-provider-diagnosis` 的 `references/provider-config-consistency-after-audit.md`。

根目录清理后常见后续项：

- 统一 `model.provider` 与 `providers:` key。
- 清除 legacy `custom_providers` 影子重复。
- 修复 `key_env` 变量名被红acted占位污染。
- 补齐 `default_model`。
- 验证 runtime provider 解析。
- 提醒新会话或 gateway 重启才代表运行态生效。

## 阶段 4：运行态与网关收口

- 检查 gateway 进程、lock、state 是否一致。
- 确认是否存在 profile gateway 空跑。
- 观察 `errors.log` 是否复现旧错误。
- 不手删 gateway lock/pid，除非按 Hermes 正规停启流程并有备份/验证。

## 完成态汇报模板

| 项目 | 状态 |
|---|---|
| 执行阶段 | 只读评审 / 止血清洁 / 配置修复 / 运行态验证 |
| 改动文件 | 数量 + 类型 |
| 删除文件 | 是/否 |
| 归档位置 | 绝对路径 |
| 权限变更 | 区域 + 数量 |
| 核心资产验证 | config/env/auth/db/sessions/skills/cron 是否仍存在 |
| 仍未处理 | 明确列出 |
| 下一阶段 | 一句话 |
