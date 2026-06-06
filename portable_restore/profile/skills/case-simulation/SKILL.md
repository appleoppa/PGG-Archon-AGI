---
name: dept-case-simulation
version: "1.0.0"
description: 案件推演部：风险预测、模拟法庭、策略推演
metadata:
  {
    "openclaw": {
      "original_id": "tui-yan",
      "original_name": "案件推演部",
      "timeout": 240,
      "mode": "异步",
      "capabilities": ["风险预测", "模拟法庭", "策略推演"]
    },
    "category": "openclaw-dept",
    "tags": ["推演", "风险预测", "模拟法庭", "策略"]
  }
---

# Case Simulation Department — Compact

## Trigger

Use for mock court, litigation risk prediction, opponent strategy simulation, judge perspective, settlement range, and procedural scenario planning.

## Workflow

1. Confirm procedural stage and available evidence.
2. Build claims/defenses and legal elements.
3. Simulate at least three perspectives: claimant, respondent/defendant, neutral adjudicator.
4. Rate risks by evidence sufficiency, legal uncertainty, procedure, enforcement and cost.
5. Propose strategy: supplement evidence, amend claims, settlement, preservation, or trial focus.

## Boundary

Simulation is not outcome guarantee. Mark assumptions and evidence gaps clearly.

## Output

`scenario`, `win/loss drivers`, `opponent arguments`, `judge concerns`, `risk_level`, `recommended_moves`.

## Reference

Full simulation templates archived at `references/full-skill-archive-20260601.md`.
