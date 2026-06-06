---
name: apple-lawyer-suite
version: "1.1.0"
description: 苹果律师工作套件：办案全流程AI助手
metadata:
  {
    "openclaw": {
      "requires": { "env": [] },
      "capabilities": ["reasoning", "file_read"],
      "evolution": {
        "enabled": true,
        "version": "1.0.0"
      }
    },
    "author": "苹果哥",
    "category": "legal",
    "tags": ["法律", "诉讼", "非诉", "文书", "咨询"]
  }
---

# Apple Lawyer Suite — Compact

## Trigger

Use as an umbrella for legal intake, research, drafting, review, strategy, evidence and final delivery coordination.

## Workflow

1. Clarify legal task and jurisdiction.
2. Route to specialist skill/department.
3. Require legal basis and evidence verification.
4. Draft or analyze.
5. Inspection/audit before external use.
6. If unsafe, produce internal report with blockers and preliminary findings.

## Contract review deliverable discipline

For顾问单位合同审阅/签署前审查, do **not** stop at extraction, preliminary issue spotting, or subagent复核. A complete contract-review job should produce a verified user-usable artifact, normally with: Contract Safety Score（合同安全评分）, risk heatmap, risk register, clause-by-clause review, lawyer-ready redlines（可直接替换文本）, missing provisions, signing checklist, legal-basis notes, and evidence trail. Generate the report file, then read it back or otherwise verify file existence/size/hash before reporting completion.

Detailed pattern: `references/contract-review-executive-deliverable-pattern.md`.

## Boundary

AI output is legal work support, not a substitute for lawyer review or court/authority decision.

## Reference

Full suite workflow archived at `references/full-skill-archive-20260601.md`.
