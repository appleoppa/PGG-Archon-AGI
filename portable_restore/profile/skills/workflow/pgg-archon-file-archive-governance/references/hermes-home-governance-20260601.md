# Hermes Home Governance 2026-06-01

## 触发

当用户要求全量审计/清理 `~/.hermes` 或根目录文件管理规则时使用。

## 当前规则文件

- `/Users/appleoppa/.hermes/workspace/治理/HERMES_HOME_FILE_MANAGEMENT_RULES.md`
- `/Users/appleoppa/.hermes/INDEX.md`
- `/Users/appleoppa/.hermes/workspace/审计队列/hermes_home_governance_20260601/HERMES_HOME_CLASSIFICATION_INDEX.json`

## 分类模型

1. `core_runtime_files`：`config.yaml`、`.env`、`auth.json`、`state.db`、活跃 WAL/SHM、gateway 状态等。
2. `core_source_runtime_dirs`：`hermes-agent/`、`bin/`、`scripts/`、`run/`。
3. `profiles_skills_plugins`：`profiles/`、`skills/`、`plugins/`、`memory/`、`memories/`。
4. `automation_state`：`cron/`、`sessions/`、`logs/`、`kanban/`、`agents/`、`agent/`。
5. `workspace_and_archives`：`workspace/`、`archives/`、`backups/`。
6. `engines_and_modules`：APEX/PGG/quantum/native/lsp/work 等运行或学习模块。
7. `caches_and_optional_state`：cache、audio/image cache、eval/evo DB、optional caches。

## 安全红线

不得自动删除或移动：

- `config.yaml`、`.env`、`auth.json`；
- `state.db`、活跃 `state.db-wal`、`state.db-shm`；
- `hermes-agent/`、`profiles/`、`skills/`、`cron/`、`sessions/`、`workspace/`；
- 其他 profile 的 skills/plugins/cron/memories，除非用户明确授权。

## 已验证清理模式

可直接净化：

- `.DS_Store`；
- 非 venv / 非 node_modules 内的 `*.pyc`、`__pycache__/`；
- 空目录，排除 `plugins/`、`secrets/`、`state/`、`sandboxes/`、`hooks/` 等保留容器；
- 根目录 `config.yaml.bak*` 迁入 `archives/hermes_home_governance_YYYYMMDD/config_backups/`；
- 根目录 `state.db*.bak*` / `*corrupt*` 迁入 `archives/hermes_home_governance_YYYYMMDD/state_db_backups/`；
- `tmp/` 迁入 `workspace/审计队列/hermes_home_governance_YYYYMMDD/tmp_legacy/`。

## 验证门禁

治理后必须验证：

```bash
hermes gateway status
hermes cron status
python - <<'PY'
import sqlite3
con=sqlite3.connect('/Users/appleoppa/.hermes/state.db')
print(con.execute('pragma integrity_check').fetchone()[0])
PY
cd /Users/appleoppa/.hermes/hermes-agent
venv/bin/python /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/native_legal_kb_toolchain_smoke.py
```

## 常见坑

1. `state.db` 大但活跃，不能因体量删除。
2. `state.db` 备份可迁移归档，但不要压缩/删除到不可回滚。
3. `work/github-mirror` 可能是 GitHub mirror 任务中间态，不能直接删；先做 git refs 验证。
4. `lsp/node_modules` 是工具依赖，不能按普通缓存直接删。
5. `hermes-agent` 本地改造不能 GitHub 提交，除非用户明确授权。
