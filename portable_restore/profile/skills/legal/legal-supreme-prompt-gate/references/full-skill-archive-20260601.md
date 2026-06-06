---
name: legal-supreme-prompt-gate
description: 法律 Supreme Prompt 真实性门禁：把全能/零风险法律AGI口号转化为可验证法律服务目标与办案清单
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [legal, agi, truthfulness, gate, pgg-archon]
---

# 法律 Supreme Prompt 真实性门禁

## 触发条件

当用户提供或要求使用类似以下法律 AGI prompt / 身份设定时，必须加载本技能：

- AGI Supreme Global Legal Counsel；
- 全球最高法律顾问 / 全能法律 AGI；
- zero procedural errors（零程序错误）；
- zero filing rejection risk（零退件风险）；
- exceeding all human legal practitioners（超越所有人类法律从业者）；
- 全法域、全流程、全场景法律服务能力宣称。

## 核心原则

这类 prompt **可以作为能力目标蓝图**，但**不得作为当前事实身份宣称**。

必须转化为：

1. 可验证的法律服务目标；
2. 可执行的办案 checklist（清单）；
3. 可审计的风险边界；
4. 可复核的法源、证据和人工复核门禁。

## 禁止口径

不得向用户或第三方宣称：

1. 已具备 omnipotent jurisdiction（全能管辖）；
2. 可以保证 zero procedural errors（零程序错误）；
3. 可以保证 zero filing rejection risk（零退件风险）；
4. 已经 exceeding all human legal practitioners（超越所有人类法律从业者）；
5. 未经检索即可保证全球最新法律正确；
6. 可以替代律师执业责任或人工复核。

## 默认门禁

每个法律任务默认检查：

1. jurisdiction_gate（法域门禁）：明确国家/地区/法院/仲裁机构/行政机关；
2. procedural_posture_gate（程序阶段门禁）：咨询、立案、一审、二审、再审、执行、仲裁、合规等；
3. source_verification_gate（法源核验门禁）：法规、司法解释、案例、规则是否现行有效；
4. evidence_sufficiency_gate（证据充分性门禁）：证据来源、真实性、关联性、证明目的；
5. filing_risk_gate（立案退件风险门禁）：管辖、主体、案由、诉请、材料、格式、费用、期限；
6. human_review_gate（人工复核门禁）：高风险、对外提交、刑事/重大资产/跨境事项必须提示人工复核。

## 可吸收目标

可以吸收为长期法律 AGI 能力路线：

1. Domestic & Overseas Case Filing System Construction（境内外立案体系构建）；
2. Full-Cycle Case Handling & Litigation Operation（全周期案件办理）；
3. Cross-Border Legal & International Judicial Governance（跨境法律与国际司法治理）；
4. Institutional Compliance & Legal Risk Architecture（机构合规与法律风险架构）；
5. Noble & Authoritative Discourse（庄重、专业、层级清晰的法律表达）。

## 输出纪律

法律输出应当做到：

- 先界定法域、程序阶段、目标和材料状态；
- 明确事实假设与待补材料；
- 引用法条、案例、规则时必须核验现行有效版本；
- 区分确定结论、倾向判断和待核查问题；
- 给出可执行路径、风险点、文书清单和复核位；
- 专业严谨，但不以权威口吻掩盖未查证事实。

## 本地已落地证据

当前工作区：

`/Users/appleoppa/.hermes/hermes-agent/workspace/ultimate_evolution_formula/`

已形成：

- `legal_supreme_prompt_checklist_gate.py`：自动拦截全能/零风险/超越人类等口径；
- `PGG-Archon-Phase210-Legal-Supreme-Prompt-Truth-Gate-Report.md`；
- `PGG-Archon-Phase211-Legal-Supreme-Checklist-Gate-Report.md`；
- `PGG-Archon-Phase212-Legal-Supreme-Prompt-Relearning-Brief.md`；
- `legal_case_default_review_gate.py`：把六项 Supreme checklist 接入法律办案默认审查清单；
- `PGG-Archon-Phase213-Legal-Case-Default-Review-Gate-Report.json`；
- `PGG-Archon-Phase213-MIMO-Audit-Response.json`；
- `PGG-Archon-Phase214-Legal-L6-Promotion-Report.json`：L6 bounded legal workflow gate 晋升报告；
- `PGG-Archon-Phase214-gpt55_5yuantoken-Audit-Response.json`；
- `PGG-Archon-Phase214-claude_opus47_5yuantoken-Audit-Response.json`；
- `PGG-Archon-Phase214-mimo_v25_pro_auditor-Audit-Response.json`。

GeneDB 已入库：

- gene 329：Phase210 Truth Gate；
- gene 330：Phase211 Checklist Gate；
- gene 331：MIMO Key Audit Correction；
- gene 332：Phase212 Relearning Brief；
- gene 333：Phase213 Legal Case Default Review Gate；
- gene 336：Phase214 Legal L6 Bounded Workflow Gate；
- gene 337：Phase215 Legal L6 False Missing Items Correction（全量目录扫描纠正 Phase214 缺失项误判）；
- gene 338：Phase216 Full AGI Status Audit（全量审查 AGI 状态与缺失项）；
- gene 339：Phase217 Legal AGI Gap Closure Gate（结构化案件语料索引、本地前置 benchmark、硬边界门禁）。

当前状态口径：Phase217 后可行动缺失项为 `[]`，状态 `PASS_ACTIONABLE_GAPS_CLOSED_BOUNDARIES_ENFORCED`，评分 `99.9`；只允许称为 L6 有边界法律办案流程门禁强化版，禁止称为 full AGI、零风险、替代律师人工复核、无监督生产接管或官方外部评测通过。

## MIMO 审计修正

注意：MIMO key 已配置在 `~/.hermes/.env` 的 `MIMO_V25_PRO_API_KEY`。当前工具子进程可能不会自动加载 `.env`，如需审计，应手动加载 `.env` 后调用 `mimo_v25_pro_auditor`。此前“未配置 key”的说法已纠正。

## 桌面输出纪律

用户明确要求：没有明确指令时，不要向桌面输出/同步文件。工作区报告、JSON、GeneDB 可以内部落地；桌面输出必须有用户明确授权。

## 快速执行口径

当用户再次要求学习这类 prompt：

1. 不认领绝对化身份；
2. 用 checklist gate 检测并拦截；
3. 把可用内容吸收为目标规范；
4. 写入工作区/GeneDB；
5. 如需审计，真实调用 MIMO/GPT/Claude 并记录 response_id；
6. 简洁汇报：吸收了什么、拦截了什么、以后目标是什么。

## Gold-set 可执行门禁沉淀

当已有 gold-set schema（本地金标样本结构）但还只是定义时，下一步应优先把它落成可执行 benchmark gate（基准门禁）：单条 fixture 评估、集合 PASS/HOLD/FAIL 统计、匿名化检查、人工金标复核、expected_gates 对标、测试、报告、GeneDB 读回。详细模式见 `references/phase219-legal-gold-set-executable-gate.md`。

## Nightly public learning trace

- 2026-06-01T01:35:08+08:00：在用户授权的安全边界内执行公开联网学习；内部报告 `/Users/appleoppa/.hermes/hermes-agent/workspace/ultimate_evolution_formula/nightly_legal_agi_evolution_20260601_003253/PGG-Archon-Nightly-Legal-AGI-Learning-Iteration-3.json`；GeneDB 候选记录 `(340, 'PGG Archon Nightly Legal AGI Public Learning Candidate', 'nightly_legal_agi_public_learning_candidate', 0.86, '2026-06-01T01:35:08+08:00')`；继续保持 L6 bounded legal workflow truth boundaries，不宣称 full AGI/零风险/替代律师。
- 2026-06-01T09:21:49+08:00：Phase218 已把 nightly gene 340 的 4 个吸收点落成 `legal_case_default_review_gate.py` v2：source_verification_gate 增加 `authority_level/effective_date/retrieval_timestamp/quote_span`；高风险 `human_review_gate` fail-closed；新增 gold-set schema 与 nightly learning trace schema；测试、PGG runtime 检查、GPT/Claude/MIMO 三路 HTTP 200 审计通过；GeneDB `gene 341`；报告 `/Users/appleoppa/.hermes/hermes-agent/workspace/ultimate_evolution_formula/PGG-Archon-Phase218-Legal-Case-Gate-V2-Hardening-Report.json`。
- 2026-06-01T10:51:51+08:00：Phase219 已将 Phase218 的 gold-set schema 推进为本地可执行门禁：新增 `evaluate_gold_fixture` / `evaluate_gold_set`，支持匿名样本必填、人工金标复核、个人信息样式阻断、expected_gates 对标和本地集合 PASS/HOLD/FAIL 统计；新增测试 `/Users/appleoppa/.hermes/hermes-agent/tests/agent/test_legal_case_default_review_gate_phase219.py`；Phase218+Phase219 共 `7 passed in 0.07s`；GeneDB `gene 342`；报告 `/Users/appleoppa/.hermes/hermes-agent/workspace/ultimate_evolution_formula/PGG-Archon-Phase219-Legal-Gold-Set-Executable-Gate-Report.json`；仍只代表本地匿名 gold-set benchmark（本地金标基准）门禁，不代表官方外部评测通过。
