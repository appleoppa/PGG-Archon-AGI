# Hermes 全量审计与第一轮低风险整理模式

适用：用户要求审计/整理 `~/.hermes`、Hermes Web UI、用户目录非系统文件夹，目标是发现文件体系架构、重复、过期、冗余、垃圾，并进行第一轮安全整理。

## 核心原则

1. **先全量只读，后低风险可回滚整理**：不要一上来删除。第一轮优先移动/压缩归档，保留 MANIFEST。
2. **系统资产保护**：不得直接处理 `.env`、`auth.json`、运行中 `config.yaml`、`state.db`、`sessions/`、`skills/`、`profiles/`、Hermes Agent 源码、Web UI 主库、上传目录、办案库、向量库。
3. **其他 profile 边界**：`~/.hermes/profiles/<name>/` 属于其他 profile，除非用户明确授权，不改其中 skills/plugins/cron/memories。
4. **桌面输出边界**：没有明确要求，不向 Desktop 同步报告；报告放 `~/.hermes/workspace/审计队列/`。

## 推荐执行轨迹

### 1. 并行只读审计

可把三块并行委派给 subagent（只读）：

- Hermes 根目录：统计一级/二级目录、大小、文件数、大文件、`.DS_Store`、空目录、backup/tmp/old/copy 候选、重复 hash 候选。
- Hermes Web UI：区分 npm 全局安装包、运行时目录、Web UI 主库/WAL/SHM、upload、logs、历史 `webui-*` 恢复备份目录。
- 用户目录非系统文件夹：跳过/浅扫 `Library`、`Applications`、`Desktop`、`Documents`、`Downloads`、`Movies`、`Music`、`Pictures`、`Public`、`.Trash` 等系统/标准目录；重点统计自建顶层目录和散落文件。

### 2. 生成机器可读审计 JSON

建议路径：

```text
~/.hermes/workspace/审计队列/hermes_full_audit_<date>/hermes_root_audit.json
```

字段至少包含：

- generated_at / root
- top directories: size, file count, dir count, mtime, protected flag
- root_files
- large_files
- backup_like
- ds_store
- empty_dirs
- duplicate_small_medium
- sensitive_perm_candidates

### 3. 第一轮可处理项

只处理低风险、可回滚项目：

- `.DS_Store`：Finder 可再生元数据，移入归档。
- 用户根目录散落临时结果文件：例如明显一次性 `debate_result.json`，移入归档。
- 空/近空实验目录：例如 0B 或仅空子目录的自建目录，移入归档，不硬删。
- Web UI 历史恢复/备份目录：如 `workspace/存档/webui-*`，先打包 `tar.gz`，验证 tar 可读，再移除原散落目录。

推荐归档路径：

```text
~/.hermes/workspace/存档/full_system_cleanup_<timestamp>/
```

必须写：

```text
MANIFEST.json
```

MANIFEST 记录每个动作的 src、dst、reason、size、sha256（可行时）、verified。

### 4. 验证门禁

整理后必须读回验证：

- MANIFEST 存在。
- 每个 move_file/move_dir：源路径不存在，目标路径存在。
- 每个 compress_then_remove_dirs：tar.gz 存在且可打开，源目录均不存在。
- `.DS_Store` 检查要排除本次归档目录，否则会把已归档的 `.DS_Store` 误判为复生。
- Hermes 核心资产仍存在：`config.yaml`、`hermes-agent/`、`state.db`。
- Web UI 核心资产仍存在：`.hermes-web-ui/hermes-web-ui.db`、npm 安装目录。
- Gateway 仍 loaded / 运行状态正常。

### 5. 报告格式

报告放：

```text
~/.hermes/workspace/审计队列/hermes_full_audit_<date>/全量审计与第一轮整理报告_<date>.md
```

报告必须包含：

- 当前状态：只读审计 + 第一轮整理是否完成。
- 审计范围。
- 核心发现：数量、体量、候选类别。
- 已执行动作：动作数、移动文件数、移动目录数、压缩批次数、归档体量、归档路径、MANIFEST 路径。
- 验证结果：失败数必须列明。
- 未处理/禁止直接处理项：state.db/sessions、向量库、办案库、Rust/npm 工具链、Web UI upload、其他 profiles。
- 下一轮建议：workspace 深度治理、state/session 瘦身、工具链正规清理、upload 审计。

## 常见坑

- `node_modules` 和 `dist` 在 npm 全局 Hermes Web UI 安装包中通常是运行必需，不要按普通缓存删。
- SQLite 主库、WAL、SHM 在服务运行时不能直接删除。
- 案件材料重复 hash 不等于可删；可能是迁移备份、作废案卷和正式案卷的证据链。
- `.DS_Store` 在验证期间可能被 Finder 重新生成；若复生，追加归档并重验。若只存在于本次归档目录内，不算残留。
- `state.db` 和 `sessions/` 体量大时，走专门 slimming 流程，不并入第一轮普通清理。
