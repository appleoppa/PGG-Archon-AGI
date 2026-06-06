# Hermes 系统清理续轮模式：state/session、workspace、工具链、Web UI upload

## 适用场景

用户在完成第一轮 Hermes 根目录 / Web UI / 用户目录低风险清理后，要求“继续按建议顺序处理”或继续做系统整理、合并、清除。

## 核心原则

1. **继续执行，不再停在建议**：用户已确认“继续按建议顺序处理”时，直接推进低风险、可回滚、可验证步骤。
2. **数据库先备份再压缩**：`state.db` 用 `VACUUM INTO` 生成 compact copy，做 `PRAGMA integrity_check` 后才替换原库；原库保留备份。
3. **sessions 先索引/备份，不硬删**：旧 session 文件可以打包备份，但不要直接删除，除非已确认 Hermes UI/session 索引机制不会断链。
4. **workspace 只建资产索引，不按 hash 粗暴删案件资料**：重复候选如果包含 `办案`、`案件`、`苹果中枢办案库`、迁移备份等，默认只是证据，不是删除授权。
5. **工具链用官方命令审计**：Rust/npm 目录大不等于垃圾。先跑 `rustup toolchain list`、`rustup show`、`npm list -g --depth=0 --json`、`npm cache verify`；只有多余 toolchain/明确不用全局包/可再生噪声才清理。
6. **Web UI upload 只列清单**：`~/.hermes-web-ui/upload/` 可能是用户上传材料或聊天附件，默认不删除，只统计大小、类型、重复候选。
7. **不向桌面输出，除非用户明确授权**：报告默认进入 `~/.hermes/workspace/审计队列/` 或 `workspace/存档/`。

## 推荐执行顺序

1. `state.db / sessions`
   - 建归档目录：`~/.hermes/workspace/存档/second_cleanup_state_sessions_<timestamp>/`
   - 复制 `state.db` 为 `state.db.before_vacuum`
   - `PRAGMA integrity_check`
   - `VACUUM INTO '<archive>/state.db.vacuumed'`
   - compact DB 再做 `integrity_check`
   - 仅当 compact 有效且大小不大于原库时替换原 `state.db`
   - sessions 生成 `sessions_inventory.json`
   - 超过阈值的旧 sessions 只打包备份，不删除

2. `workspace` 资产索引
   - 输出：`~/.hermes/workspace/审计队列/workspace_asset_index_<date>/workspace_asset_index.json`
   - 统计顶层分区大小、文件数、目录数、最近修改时间
   - 列大文件
   - 对中小文件按 size + sha256 找重复候选
   - 对含案件关键字的重复组标注 `contains_case_asset=true`

3. Rust/npm 工具链审计
   - 输出：`~/.hermes/workspace/审计队列/toolchain_audit_<date>/toolchain_audit.json`
   - 记录 `.cargo`、`.rustup`、`.npm-global` 前后大小
   - 运行官方命令列出 active/default toolchain 和全局 npm 包
   - 只删除 `.DS_Store` 等可再生噪声；不要因为目录大就删除工具链/cache

4. Web UI upload 审计
   - 输出：`~/.hermes/workspace/审计队列/webui_upload_audit_<date>/webui_upload_audit.json`
   - 统计总大小、文件数、扩展名分布、最大文件、重复候选
   - 默认不删除 upload 文件

5. 生成第二轮报告
   - 输出：`~/.hermes/workspace/审计队列/第二轮清理与资产索引报告_<date>.md`
   - 必须包含：已处理/未处理、前后大小、备份路径、完整性检查、Gateway 状态、证据文件路径

## 验证门禁

- `state.db` 替换后读回文件大小，并保留原始备份。
- SQLite `integrity_check` 必须为 `ok`。
- sessions 原文件未删除时，报告明确“只备份，不删除”。
- workspace 重复候选只作为后续治理依据，不声明已去重。
- 工具链前后大小无变化时，要解释原因：当前没有明确可删的多余 toolchain/全局包。
- Web UI upload 如不删除，要说明原因：可能关联用户上传资料或聊天附件。
- `hermes gateway status` 应在报告中体现服务仍 loaded / 未受影响。

## 常见坑

- `du -sh` 与 Python byte 统计显示会有单位/取整差异，报告中可并列“bytes”和人类可读大小。
- `state.db` VACUUM 节省可能很小；这不是失败，只要 integrity ok 且备份存在即可。
- 旧 sessions 数量很多也不能默认删除；历史会话可能仍被 session browser / session_search 使用。
- workspace 最大项可能变成上一轮归档本身；报告应区分“新增归档导致体量上升”和“实际垃圾残留”。
- 生成 Markdown 报告时，避免在外层 Python 字符串未正确三引号的情况下直接写中文全角标点；必要时用工具 `write_file` 或明确 `content = f"""..."""`。
