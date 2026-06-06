# Legal Task Gate Core Fusion Runtime Note — 2026-06-06

PGG Archon Runtime 已新增可复用法律任务门禁核心：

```text
agent/pgg_archon_legal_task_gate.py
```

## 使用语义

在半外部法律评测、办案流程预检、法律文书 anti-fabrication gate、管辖/金额专项弱项评测中，优先复用此核心模块，而不是在 runner 内重复写 prompt/scorer。

核心函数：

```python
from agent.pgg_archon_legal_task_gate import build_legal_task_prompt, score_legal_task
```

- `build_legal_task_prompt(item)`：按 domain 注入法律任务门禁。
- `score_legal_task(expected, text, domain=...)`：按 domain 做过程合规评分。

## 已固化的开源学习成果

- LegalBench/LexGLUE 模式：任务域拆分，不用单一通用 scorer。
- LegalBench-RAG 模式：法律输出必须 source/evidence grounding。
- 管辖任务：case_type、被告住所地、合同履行地、标的额、协议/专属管辖、刑事犯罪地/侦查地 checklist。
- 金额任务：ledger 化，金额/日期/利率/责任比例/保险限额/扣减项/证据引文；缺数字时必须 abstain，不得编造总额。

## 验证证据

- pytest：17 passed。
- 弱项真实 provider 复跑：DeepSeek 20/20；MiMo 20/20。
- Manifest：`latest_20260606_legal_task_gate_core_fusion`。

## 边界

该模块是 deterministic core gate：不调用 provider、不联网、不写文件、不改 Hermes scheduler/security boundary。它证明流程门禁生效，不证明法律结论正确，也不是官方 LegalBench/LexGLUE 成绩。
