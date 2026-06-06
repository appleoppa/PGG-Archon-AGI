---
name: agent-cms
version: "2.1.0"
description: 案件管理中心：负责编号、派发、归档与台账（标准 4 目录 + 可选 10 目录多阶段扩展）
metadata:
  {
    "openclaw": {
      "original_id": "an-guan",
      "original_name": "案件管理中心",
      "timeout": 180,
      "mode": "同步",
      "subagents": "*"
    },
    "category": "apple-case-system",
    "tags": ["案件管理", "编号", "归档", "台账"]
  }
---

# Agent CMS — Compact

## Trigger

Use when starting or managing case intake, case numbering, dispatch, archive directories, case ledger, or department handoff.

## Current numbering rule

- Case number: `PGG-{案件类型代码}-YYYYMMDD-{四位全局序号}`.
  - `XS` = 刑事案件，例如交通肇事罪：`PGG-XS-20260605-0005`
  - `MS` = 民事/民商事案件，例如合同、婚姻、工伤争议：`PGG-MS-20260601-0004`
- The 4-digit sequence is **global across all case types and dates**; scan `~/.hermes/workspace/苹果中枢办案库/` including `外部案件档案_legacy_home/` and use max+1.
- Directory: `{序号}-PGG{类型代码}-YYYYMMDD-当事人+案由`, e.g. `0005-PGGXS-20260605-邮政第三方劳务司机交通肇事`.
- Stage subdir: `PGG-{类型代码}-YYYYMMDD-{序号}（一审/二审/再审/一审侦查阶段等）`.
- Stage folders: 案件材料、案件过程报告、总结报告、正式文书.
- Documents/evidence/tasks/audits prefix with main case number, e.g. `PGG-XS-20260605-0005-刑事辩护部工作报告.md`.
- Preflight guard: **Rust-native** `~/.hermes/workspace/pgg-archon-governance/rust/cms_case_guard/target/release/cms_case_guard`. Run before case creation/after archive changes:
  - `cms_case_guard --next`
  - `cms_case_guard --validate <case_root> --case-type <案件类型>`
- Legacy Python guard `~/.hermes/workspace/pgg-archon-governance/scripts/case_intake_guard.py` is deprecated; use only as fallback comparison, not as primary guard.

## Alternative: 10-subdir "full multi-stage" layout

For full multi-LLM, multi-department workflows (P0-P7 stages with parallel research, evidence catalog, multi-channel review, audit), the 4-folder default is too coarse. Use this **10-subdir** structure within the stage subdir:

```
NNNN-PGG{type}-YYYYMMDD-当事人+案由/
  PGG-{type}-YYYYMMDD-NNNN（一审/二审/再审等）/
    01-案件材料/        ← 客户原始材料 + 提取版
    02-法律意见/        ← 法律顾问部
    03-法律依据/        ← 律法支持部
    04-证据目录/        ← 证据管理部
    05-案件分析/        ← 民事/刑事案件部
    06-诉讼策略/        ← 诉讼策略部
    07-推演预测/        ← 案件推演部（模拟法庭）
    08-巡视复核/        ← 巡视组
    09-审计报告/        ← 审计组
    10-终版文书/        ← 民事起诉状/答辩状/代理意见等
    99-台账/            ← 案件台账 + 4通道LLM协作纪要 + 原始输出JSON
```

**When to use 10-subdir instead of 4-folder**:

| Use 4-folder (default) | Use 10-subdir |
|---|---|
| Simple case, single department | Multi-department / multi-LLM case |
| Single-stage work (e.g. just a contract review) | P0-P7 staged workflow |
| Small output, no need for per-stage archival | Each stage produces separate deliverable for review/audit |
| No multi-LLM collaboration | 4-channel LLM协作 (Pattern B from `apple-hub-orchestrator`) |

**Worked example**: PGG-MS-20260605-0006 (燕赵财险雇主责任险合同纠纷) used the 10-subdir layout. All 11 standard subdirs were populated (4 deliverables `v1.md`, 3 raw `4通道原始输出.json` files, 1 evidence catalog, 1 case ledger, 1 source `.docx`, 1 source `.md`).

**Critical rule for `99-台账/`**: when using 4-channel LLM pattern, this is where every `*_4通道原始输出.json` lands — never scatter audit JSONs into the stage subdirs. The 台账 is the audit anchor.

## Workflow

1. Intake facts/materials.
2. Allocate number and directory.
3. Dispatch to appropriate legal departments/subagents.
4. Maintain ledger and evidence chain.
5. Archive reports and deliver only authorized final/internal report.

## Desktop-folder intake pattern

When the user asks to read a local case folder and start the办案程序, treat it as formal intake authorization: enumerate/read materials, OCR images if needed, allocate the next global case number, create the archive/stage structure, copy originals into `案件材料/`, generate department流转 receipts, run the inspection gate, and deliver either an external-ready document or an internal preliminary report if blocked. Keep process files in the case archive; if Desktop output is authorized for that case, sync only the final/internal report. See `references/desktop-folder-case-intake-pattern.md`.

## Pitfalls (discovered 2026-06-05)

Read these before creating any new case. Each one was a real mistake corrected by the user.

1. **Do NOT invent or flatten case-type codes.** Case-type code must match the matter/department: `MS` for民事/民商事, `XS` for刑事, and other approved department codes only when confirmed by CMS/department rules. A criminal case such as交通肇事罪 must use `PGG-XS-YYYYMMDD-NNNN` and directory `NNNN-PGGXS-YYYYMMDD-当事人+案由`; using `PGG-MS` for a criminal case is BLOCKED.
2. **The 4-digit number is GLOBALLY cumulative across all case types and dates, not per-date and not per-case-type.** Do NOT assume `0001` is safe just because this is your first case today. Scan ALL existing case directories across the entire `~/.hermes/workspace/苹果中枢办案库/` including `外部案件档案_legacy_home/` and any subdirectory with patterns like `XXXX-PGGMS-YYYYMMDD-` / `XXXX-PGGXS-YYYYMMDD-` / other PGG codes. The next number is `max + 1`. If existing cases are 0001, 0002, 0003, 0004, the new case is 0005. As of 2026-06-05: 0001-0005 exist (0005 is the刑事交通肇事案); next new case is 0006.
3. **Always create the stage subdirectory layer.** Structure: `0001-PGGMS-YYYYMMDD-当事人/` → `PGG-MS-YYYYMMDD-0001（一审/二审/再审等）/` → standard folders. Without it, files don't belong to a specific trial stage.
4. **Pick the right folder layout.** Default = 4-folder (案件材料、案件过程报告、总结报告、正式文书). For full multi-stage multi-LLM workflows, use the 10-subdir layout documented above. Don't mix them in the same case. Don't scatter `*_4通道原始输出.json` files outside `99-台账/`.
5. **Load this skill FIRST** before creating any directories or files. Do not assume you remember the numbering rule from a prior session — it can change.
6. **Do not do the analysis yourself.** CMS allocates → dispatches to departments → each produces its own work product. The central agent orchestrates, not replaces departments.
7. **When using 4-channel LLM collaboration (Pattern B from `apple-hub-orchestrator`), the audit JSON file is mandatory.** For every LLM task round, write `*_4通道原始输出.json` to `99-台账/` with full per_provider record (http_status, visible_chars, verdict, elapsed_s). Without it, the task did not happen for audit purposes — only the merged `v1.md` is not sufficient.
8. **苹果中枢办案库 is case-archive-only.** `~/.hermes/workspace/苹果中枢办案库/` stores only case directories, case ledger/metadata, and legacy case archives. Do **not** store governance tools, Rust projects, compiled binaries, evaluation reports, or general PGG evolution artifacts inside it. Put governance/tools under `~/.hermes/workspace/pgg-archon-governance/`; standard executable shims may live under `~/.hermes/bin/`.

## Reference

Full CMS procedure archived at `references/full-skill-archive-20260601.md`.
Global renumbering fix pattern at `references/global-renumbering-pattern-20260605.md` (中文目录重命名、批量编号替换、台账同步)。
Case WATCH boundary pattern at `references/case-watch-boundary-pattern-20260605.md`（P0-P7 与 FINAL 文件存在不等于可提交终版；CMS BLOCKED、类案构造、当事人/法院待补时必须标 WATCH）。
