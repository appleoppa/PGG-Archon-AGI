---
name: apple-civil-litigation
version: "1.1.0"
description: 苹果民事诉讼专家：民商事诉讼全流程
metadata:
  {
    "openclaw": {
      "requires": { "env": [] },
      "capabilities": ["reasoning", "file_read"],
      "evolution": {
        "enabled": true,
        "version": "1.1.0"
      }
    },
    "author": "苹果哥",
    "category": "legal",
tags: ["民事", "诉讼", "离婚", "彩礼", "家事", "合同纠纷", "房产纠纷", "仲裁", "死亡赔偿金", "共有物分割", "再审"]
  }
---

# Apple Civil Litigation — Compact

## Trigger

Use for civil/commercial litigation, arbitration, construction disputes, contract/tort/company disputes, pre-litigation assessment, pleadings, evidence, trial strategy and enforcement handoff.

## Formal workflow

1. Identify parties, claims, court/arbitration route, limitation period, jurisdiction and procedural stage.
2. Build issue list: facts → legal elements → burden of proof → evidence gaps.
3. Search law/cases with local-first legal KB when legal basis is needed.
4. Draft or review claims/defenses, evidence catalogue, application list and hearing outline.
5. Route evidence questions to evidence department and final accuracy to inspection/audit.
6. Deliver external document only when legal basis/evidence gates pass; otherwise internal report.

## Must not skip

- limitation period;
- jurisdiction/arbitration clause;
- burden of proof;
- preservation/behavior preservation feasibility;
- litigation cost and enforcement collectability.

## Family/divorce + bride-price intake pitfall

For divorce cases with bride-price/caili返还, do not jump from screenshots or oral summaries to a court-ready complaint. First distinguish proven facts from线索, especially payment, receipt, marriage registration,共同生活时间, pregnancy/childbirth, alleged violence, medical conditions, and electronic evidence originality. Use local-first law lookup for 《民法典》婚姻家庭编 and the 2024涉彩礼规定. If the parties已登记并共同生活, flag the default rule that返还一般不予支持, then analyze the exception factors:共同生活时间较短、彩礼数额过高、彩礼实际使用、嫁妆、孕育情况、双方过错、当地习俗. Sensitive facts such as抑郁症、多囊、未孕 must not be framed as discriminatory blame; tie them only to legally relevant issues such as隐瞒、共同生活受影响、孕育情况, or evidence-backed过错.

## Output contract

`case_stage`, `claims/defenses`, `legal_basis`, `evidence_status`, `risks`, `next_documents`, `verification_boundary`.

## P7 民事起诉状 FINAL 事实幻觉 pitfall (added 2026-06-05 case 0006)

`gpt5.5 + minimax` both 90s timeout on long 民事起诉状 tasks (max_tokens ≥ 4500). Surviving 3 channels (deepseek/agnes/mimo) may freely invent scene details that are not in the source 客户材料: case 0006 v1 起诉状 contained "高血压既往病史 / 工地事故 / 2025年3月15日 / 重型自卸货车" — all **non-existent in the source 情况说明**. The P5 巡视 / P6 审计 LLM checks passed the hallucinated draft. Mitigation: see `apple-hub-orchestrator/references/p7-fact-hallucination-regex-selfcheck.md` for the prompt FACT_BLOCK + 3-channel (no gpt5.5) + programmatic regex self-check workflow. For 民事起诉状 specifically, the program self-check must verify: 事故时间/地点/原因, 保单号/限额/期限, 工亡文号, 责任比例, 被告已付金额, 争议金额, 当事人全称, 类案标注[合理构造示例]。

## Reference

Full civil litigation templates archived at `references/full-skill-archive-20260601.md`.
P7 fact-hallucination pattern (mandatory at finalization): `apple-hub-orchestrator/references/p7-fact-hallucination-regex-selfcheck.md`.
