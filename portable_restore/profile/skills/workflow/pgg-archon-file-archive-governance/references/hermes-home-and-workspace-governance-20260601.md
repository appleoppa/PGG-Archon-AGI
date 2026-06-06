# Hermes Home / Workspace 文件治理会话沉淀（2026-06-01）

## 适用场景

用户要求对 `~/`、`~/.hermes` 或 `~/.hermes/workspace` 做全量审计、整理、净化、分类存放、规则固化时使用。

## 本次固化的治理模式

### 1. 先审计，后移动

必须先生成可读审计包：

- 原路径清单；
- 文件/目录大小；
- mtime；
- sha256（重要文件）；
- 活跃引用命中；
- 迁移目标；
- 可回滚 manifest。

不能直接凭文件名删除或移动。

### 2. 根目录只保留入口，不保留业务产物

`/Users/appleoppa` Home 根目录：

- 保留：系统目录、shell session、Hermes/WebUI/运行状态目录。
- 迁出：外部 repo、测试残留、案件档案、临时 JSON、debate result 等。

`~/.hermes/workspace` 根目录：

- 保留：`AGENTS.md`、`SOUL.md`、`IDENTITY.md`、`USER.md`、`MEMORY.md`、`TOOLS.md`、`INDEX.md` 和一级资产目录。
- 不保留：独立规范原件、报告、JSON、过程产物。

`~/.hermes` 根目录：

- 保留：`config.yaml`、`.env`、`auth.json`、`state.db`、活跃 WAL/SHM、gateway 状态、核心目录。
- 迁出：`config.yaml.bak*`、`state.db*b ak/corrupt*`、`tmp/`、散落备份。

### 3. 当前权威文件也不能散放

用户明确纠正：

> 当前权威不是散放在根目录的理由。

因此三类文件必须收口：

- 开智/进化规范 → `workspace/开智/规范/`
- 部门/办案配置 → `workspace/治理/部门配置/`
- 文件治理规则 → `workspace/治理/`

根目录入口文件只做索引和跳转。

### 4. 引用修复策略

- 活跃入口、config、workflow、template、skill reference 必须修复到新路径。
- 历史审计文件原则上不强改，避免篡改历史证据；只在报告中说明。
- 修复后生成 `*_REFERENCE_FIXES.json`。

### 5. 噪音净化规则

可清理：

- `.DS_Store`
- 非 `venv` / 非 `node_modules` 内的 `*.pyc`
- 非 `venv` / 非 `node_modules` 内的 `__pycache__/`
- 空目录，但排除保留容器，如 `plugins/`、`secrets/`、`state/`、`sandboxes/`、`hooks/`

注意：运行 smoke test 后 `hermes-agent` 可能重新生成 `__pycache__`，最终报告前要再清一次并复查。

### 6. 不可自动处理的红线

不得直接删除或移动：

- `config.yaml`、`.env`、`auth.json`
- `state.db`、活跃 `state.db-wal`、`state.db-shm`
- `hermes-agent/`、`workspace/`、`profiles/`、`skills/`、`cron/`、`sessions/`、`logs/`
- 其他 profile 的 skills/plugins/cron/memories，除非用户明确授权

### 7. 验证门禁

治理后至少验证：

- gateway loaded；
- cron running；
- SQLite `integrity_check`；
- 关键业务 smoke test，例如 legal KB native smoke；
- 分类索引 `unclassified = 0`；
- 根目录旧路径不存在；
- 新路径存在；
- `.DS_Store` / 非 venv pyc / 非 venv pycache 为 0。

## 本次产物位置

- Home 治理报告：`workspace/审计队列/home_directory_audit_20260601/`
- Workspace 根目录规范收口报告：`workspace/审计队列/workspace_governance_20260601/root_authority_specs_fix/`
- Hermes Home 治理报告：`workspace/审计队列/hermes_home_governance_20260601/`
- Hermes Home 底层规则：`workspace/治理/HERMES_HOME_FILE_MANAGEMENT_RULES.md`
- Hermes Home 分类索引：`~/.hermes/INDEX.md`

## 未来执行提示

这类任务不要只“说明为什么存在”。用户说“继续/全量修复”时，应直接进入：

1. 审计；
2. manifest；
3. 迁移/净化；
4. 引用修复；
5. 验证；
6. 报告；
7. skill/reference 固化。
