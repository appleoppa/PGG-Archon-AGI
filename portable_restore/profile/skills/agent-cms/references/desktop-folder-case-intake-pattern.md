# Desktop Folder Case Intake Pattern

## Trigger

Use when the user says to read a local folder (often Desktop) and “启动办案程序/开始办案”. This is authorization to start formal intake from the folder materials, not just summarize them.

## Pattern

1. **Load governing skills first**
   - `agent-cms` for numbering/archive/ledger.
   - Matter-specific legal department skill, e.g. civil/family litigation.
   - Evidence management and inspection/audit skills.
   - Local-first legal KB skill when legal basis is needed.

2. **Read the folder without polluting it**
   - Enumerate files under the provided folder.
   - Read text files directly.
   - OCR/image-analyze screenshots or scans; mark OCR as a transcript/excerpt, not original evidence.
   - Preserve original materials; copy them into the case archive with the case number prefix.

3. **Allocate the global case number**
   - Search existing case archive numbers and choose the next global four-digit sequence.
   - Use the established format:
     - Case number: `PGG-MS-YYYYMMDD-000N`
     - Directory: `000N-PGGMS-YYYYMMDD-当事人+案由`
     - Stage: `PGG-MS-YYYYMMDD-000N（阶段）`

4. **Create formal stage structure**
   - `案件材料/`
   - `案件过程报告/`
   - `总结报告/`
   - `正式文书/`
   - `部门流转/`
   - Optional `证据底稿/` for OCR, hashes, extraction notes.

5. **Produce real department流转 evidence**
   - 案件管理中心立案台账 JSON.
   - 部门派发单.
   - 证据管理部回执: evidence list, proof purpose, 三性评价, gaps, supplement plan.
   - Matter department回执: claims/defenses, issues, legal basis, risks.
   - 法律支持部回执: local KB statute/case hits and applicability boundary.
   - 巡视组门禁回执: `PASS` / `WATCH` / `BLOCKED`.

6. **External-delivery gate**
   - If key identity, payment, original electronic evidence, medical, police, or court-ready materials are missing, mark `BLOCKED_FOR_EXTERNAL_DELIVERY`.
   - In that case, generate an **internal preliminary report** and補证清单, not a court-ready pleading.
   - If the user has authorized Desktop output for this case, sync only the final/internal report to a Desktop output folder; do not scatter process files on Desktop.

7. **Verification before reporting**
   - Read back the ledger/report or list archive files.
   - Report case number, archive path, Desktop report path if synced, gate status, and immediate补证 priorities.

## Pitfalls

- Do not say “已启动办案程序” merely after reading the folder. There must be a case number, archive directory, copied materials, department receipts, and gate conclusion.
- Do not turn OCR or咨询人转述 into proven facts. Mark them as线索 unless original electronic data and objective evidence are available.
- Do not create a court-ready诉状 when the inspection gate is `BLOCKED`; produce an internal report instead.
- Do not modify or rename the user’s original Desktop materials unless explicitly instructed; work from copied archive materials.
