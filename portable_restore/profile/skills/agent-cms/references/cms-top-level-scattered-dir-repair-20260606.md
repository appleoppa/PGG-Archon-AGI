# 0006 CMS 顶层散目录修复模式 — 2026-06-06

## 触发

`cms_case_guard --validate` 对案件目录报：

```text
STAGE_DIR_COUNT expected 1 got 0
EXTRA_TOP_LEVEL_DIRS [...]
```

典型原因：案件根目录下直接放了 `任务记录/正式文书/案件过程报告/审计记录/总结报告/案件材料/证据材料/`，缺少阶段目录层。

## 正确修复流程

1. 先备份整个案件目录，不得无备份移动：

```bash
BACKUP_DIR="$HOME/.hermes/workspace/苹果中枢办案库/_backups/<case>_cms_structure_fix_$(date +%Y%m%d_%H%M%S)"
ditto "$CASE" "$BACKUP_DIR/<case>-before-fix"
```

2. 创建阶段目录：

```text
<case_root>/PGG-MS-YYYYMMDD-NNNN（一审）/
```

3. 标准顶层目录迁入阶段目录：

```text
案件材料/
案件过程报告/
总结报告/
正式文书/
```

4. 非标准目录降入标准目录子层，避免 `EXTRA_STAGE_DIRS`：

```text
任务记录/ -> 案件过程报告/任务记录/
审计记录/ -> 案件过程报告/审计记录/
证据材料/ -> 案件材料/证据材料/
```

5. 写结构修复记录到：

```text
PGG-MS-YYYYMMDD-NNNN（一审）/案件过程报告/审计记录/<case>-CMS结构修复记录.md
```

6. 复跑：

```bash
~/.hermes/bin/cms_case_guard --validate "$CASE" --case-type '民商事案件'
```

目标：

```json
{"status":"PASS","errors":[],"warnings":[]}
```

## 已验证实例

`PGG-MS-20260605-0006` 修复后：

```text
status: PASS
case_seq: 6
case_code: MS
```

## 边界

此修复只调整归档结构，不改动案件实体事实、法律意见、文书内容或审计结论。修复后仍需根据案件性质另跑 `legal_doc_gate` / 巡视 / 审计。
