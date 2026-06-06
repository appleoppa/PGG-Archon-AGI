---
name: pgg-archon-file-archive-governance
description: PGG Archon AGI workspace 文件/档案治理：GitHub 开源规范吸收、六类分区、档案 manifest、引用审计和清理验证。
version: 1.0.0
created: 2026-06-01
---

# PGG Archon 文件与档案治理

## 触发条件

当任务涉及：

- 整理 `/Users/appleoppa/.hermes/workspace`；
- 归档、合并、删除历史文件；
- 制定 PGG Archon AGI 文件/档案规则；
- 清理报告、审计队列、备份、外部仓库、开智/AGI 资产；
- 防止 workspace 根目录污染。

## 核心规范入口

- `/Users/appleoppa/.hermes/workspace/治理/PGG_ARCHON_AGI_FILE_ARCHIVE_STANDARD.md`
- `/Users/appleoppa/.hermes/workspace/治理/WORKSPACE_STORAGE_RULES.md`
- `/Users/appleoppa/.hermes/workspace/治理/PGG_ARCHON_ARCHIVE_MANIFEST.json`
- `/Users/appleoppa/.hermes/workspace/AGENTS.md`

## 开源学习来源

已吸收：

1. cookiecutter-data-science：按生命周期分层，raw/interim/processed/reports/references。
2. The Turing Way - filenaming：机器可读命名、日期/版本/语义一致。
3. The Turing Way - project repository：README/目录说明让协作者理解结构。
4. The Turing Way - data governance：权限、敏感级别、共享边界和生命周期。
5. Frictionless Data Package：数据/档案应有机器可读 metadata/descriptor。

证据：`/Users/appleoppa/.hermes/workspace/审计队列/workspace_governance_20260601/github_learning/`

## 六类分区

1. `current_authority`：根部入口文件，如 `AGENTS.md`、`SOUL.md`、`TOOLS.md`。
2. `case_assets`：`苹果中枢办案库/`、`办案/`。
3. `legal_knowledge_assets`：`智库/`、`法律知识向量库/`。
4. `agi_runtime_assets`：`开智/`、`agentic_rl/`、`agi-routing/`、`evolution/`、`evm/`、`evo_master_db/`、`trace_hashpool/`、`量子路由/`。
5. `governance_assets`：`治理/`、`standards/`、`templates/`、`workflows/`、`scripts/`、`tools/`、`config/`、`recovery/`、`skills/`。
6. `reports_audit_logs`：`reports/`、`审计队列/`、`logs/`、`监控日志/`、`任务队列/`。
7. `external_learning_repos`：`github/`、`github-evolution/`。

## 执行流程

1. 只读盘点：生成 top-level inventory、大小、文件数、候选垃圾。
2. 引用审计：移动任何目录前，搜索 workspace 和 hermes-agent 中的旧路径引用。
3. 分类索引：生成 `PGG_ARCHON_WORKSPACE_CLASSIFICATION_INDEX.json`，目标是 `unclassified=0`。
4. 建立/更新规范：同步 `PGG_ARCHON_AGI_FILE_ARCHIVE_STANDARD.md`、`WORKSPACE_STORAGE_RULES.md`、`PGG_ARCHON_ARCHIVE_MANIFEST.json`。
5. 低风险整理：
   - 根部过程报告 → `reports/<domain>/`；
   - 审计旧目录 → `审计队列/历史审计/`；
   - 配置/补丁备份 → `治理/历史归档/config_and_patch_backups/`；
   - 历史开智记录 → `开智/历史进化记录/`；
   - 研究/技能资产 → `开智/研究资产/` 或 `开智/技能资产/`。
6. 删除门禁：只直接删除 `.DS_Store`、`*.pyc`、`__pycache__`、确认空临时目录、已由现用 catalog 和回归替代的 legacy 缓存。
7. 验证：核心路径存在、SQLite integrity、法律 KB native smoke、classification unclassified=0、噪音清零。
8. 报告：写入 `审计队列/workspace_governance_<date>/`。

## 删除红线

不得直接删除：

- `智库/`；
- `法律知识向量库/catalog.sqlite3`；
- `苹果中枢办案库/`、`办案/`；
- 当前入口文件；
- 未完成引用审计的 AGI/开智运行资产；
- 未压缩留证的历史修复材料；
- `github/`、`github-evolution/`，除非引用审计和吸收报告都通过。

## 验证命令示例

```bash
find /Users/appleoppa/.hermes/workspace -name .DS_Store -type f -delete
cd /Users/appleoppa/.hermes/hermes-agent
venv/bin/python /Users/appleoppa/.hermes/workspace/审计队列/local_official_kb_repair_20260601/native_legal_kb_toolchain_smoke.py
```

## 常见坑

1. macOS Finder 会重新生成 `.DS_Store`，最后一步要再次清理。
2. `审计` 二字会误命中 `审计队列`，引用审计要区分 exact path 和泛词。
3. 外部 repo 内部自带大量引用，不能当作 workspace 活跃引用直接改。
4. 案件结构空目录是办案流程占位，不按垃圾删除。
5. 旧目录移动后要生成分类索引和动作 JSON，避免“移动了但不可追踪”。
