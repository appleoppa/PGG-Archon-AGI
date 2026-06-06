# Contract Review Executive Deliverable Pattern

## When to use

Use for顾问单位合同审阅、合同修改建议、格式合同风险审查、签署前法律意见类任务。

## Key lesson from session

Do not stop after extraction, preliminary risk spotting, or subagent复核. The deliverable is not complete until a verified report file exists and is read back.

## GitHub-derived presentation pattern

Public contract-review agent projects commonly present results with:

1. Contract Safety Score（合同安全评分）
2. Severity Ratings（风险等级：重大/中高/中/低）
3. Red Flags Quick Scan（核心风险速览）
4. Clause-by-Clause Analysis（逐条条款审查）
5. Key Terms / Risk Register（关键条款与风险登记册）
6. Lawyer-ready Redlines（可直接替换的红线语言）
7. Missing Provisions（缺失条款清单）
8. Action Checklist（签署前行动清单）
9. Evidence Trail（材料、检索、复核、文件读回证据）

## Required workflow

1. Intake: identify client party, counterparty, contract type, review stance, signing stage.
2. Case management: assign case number and archive uploaded source file.
3. Extraction: convert/extract text and read back enough to verify extraction quality.
4. Legal basis: use local official legal KB first; mark any missing/non-hit special statutes as needing official-source verification rather than inventing article text.
5. Risk review: produce score, risk heatmap, risk register, clause-by-clause comments, redline language, and signing checklist.
6. Verification: generate at least one user-usable report file (prefer DOCX + Markdown/HTML when possible), then read back the generated file and report path, size/hash or equivalent evidence.

## Pitfalls

- A subagent or reviewer summary is not a deliverable.
- A `.doc` extraction success is not contract review completion.
- Markdown tables converted to DOCX may become plain text; for polished Word output prefer real HTML tables before `textutil -convert docx` or another proper DOCX generator.
- If the user asks why work stopped, immediately continue execution and finish artifacts; do not justify at length.
