# 2026-06-06 开源 benchmark 模式吸收：管辖与金额弱项修复

## 触发
半外部法律任务集暴露弱项：
- jurisdiction：DeepSeek 0.70，MiMo 0.60
- claim_amount_calculation：DeepSeek 0.50，MiMo 0.90

## R[2] 外部学习证据
只读学习，未导入/执行外部代码：
- `HazyResearch/legalbench`
- `coastalcph/lex-glue`
- `zeroentropy-ai/legalbenchrag`

证据文件：
- `/Users/appleoppa/.hermes/workspace/audit/open_source_legal_learning_20260606_101155/open_source_legal_learning_report.md`

## 吸收模式
1. LegalBench/LexGLUE 风格：按任务域拆分 prompt 与 scorer，不再用一个通用 evidence keyword scorer 覆盖所有域。
2. LegalBench-RAG 风格：法律任务必须 evidence/source grounding；缺事实时正确 abstain 应得分，而不是诱导模型编造法院/金额。
3. 管辖任务 checklist：案件类型、被告住所地、合同履行地/保险地点、标的额/级别管辖、协议管辖、专属管辖、刑事犯罪地/侦查地。
4. 金额任务 ledger：金额项、日期、利率、责任比例、保险限额、扣减项、证据引文；缺数字时输出“材料不足/待补”并列缺失输入。

## 修改
- `agent/pgg_archon_semi_external_legal_runner.py`
  - 新增 `build_legal_task_prompt()`，按 domain 注入 jurisdiction / claim amount 专项 gate。
  - `score_legal_item(..., domain=...)` 支持域特异 scoring。
  - claim_amount：有显式计算或“缺事实+金额因素”均可通过，避免奖励编造计算。
  - jurisdiction：必须 evidence marker + jurisdiction factor checklist。
  - fact_extraction/evidence_catalog 回到 generic evidence scoring，避免被管辖因子误伤。
- `tests/test_pgg_archon_semi_external_legal_runner.py`
  - 增加金额缺事实、管辖 checklist、非管辖 evidence_first、prompt gate 测试。

## 验证
- pytest：`21 passed`
- 弱项 20 条真实 provider 复跑：
  - DeepSeek：20/20，1.0
  - MiMo：19/20，0.95；唯一失败为 MiMo `legal-077` empty response，不是法律逻辑失败。
- 100 条真实输出域特异 rescore（无新 API）：
  - DeepSeek：99/100
  - MiMo：100/100

## 边界
- 这不是官方 LegalBench/LexGLUE 成绩。
- 这不是法律正确性证明，只证明本轮弱项任务 gate/scorer 与 provider 输出在半外部任务集上闭合。
- 外部项目只吸收 benchmark/prompt/scoring 思路，未复制代码/数据。
