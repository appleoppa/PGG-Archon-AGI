# 2026-06-06 Legal Task Gate Core Fusion

## 触发
用户要求“将学习的知识落地，并融合进核心”。上一轮开源学习（LegalBench / LexGLUE / LegalBench-RAG）已修复半外部 runner，但知识仍停留在 runner 内，尚未成为可复用核心。

## 核心落地
新增核心模块：

```text
/Users/appleoppa/.hermes/hermes-agent/agent/pgg_archon_legal_task_gate.py
```

边界声明：
- deterministic prompt/scoring helpers only
- no LLM calls
- no network
- no filesystem writes
- no Hermes scheduler/security mutation
- not legal correctness proof
- not official LegalBench/LexGLUE evaluation

## 融合内容
模块固化以下开源 benchmark 吸收模式：

1. `build_legal_task_prompt(item)`
   - jurisdiction 注入 `JURISDICTION CHECKLIST`
   - claim_amount_calculation 注入 `CLAIM AMOUNT LEDGER`
   - 其他法律任务注入 evidence-first format

2. `score_legal_task(expected, text, domain=...)`
   - fake case/statute/court regex hard block
   - `no_fabrication`：要求核验/官方/本地法库/待补等 marker
   - `calculator_or_code`：有数字时要求计算；缺数字时“材料不足 + 金额/责任比例/扣减等缺失因素”也通过，防止为了得分编造总额
   - `evidence_first` + jurisdiction：要求 evidence marker + 管辖因子 checklist
   - 非 jurisdiction evidence task 回到通用 evidence/material marker，避免被管辖因子误伤

3. runner 接入
   - `agent/pgg_archon_semi_external_legal_runner.py` 改为从核心模块导入：
     - `build_legal_task_prompt`
     - `score_legal_task`
   - 保留 `score_legal_item()` wrapper，兼容旧测试/调用。

## 验证
单元测试：

```text
PYTHONPATH=$PWD pytest -q tests/test_pgg_archon_legal_task_gate.py tests/test_pgg_archon_semi_external_legal_runner.py tests/test_pgg_archon_legal_boundary_gate.py
17 passed in 0.15s
```

弱项真实 provider 复跑：

```text
/Users/appleoppa/.hermes/workspace/audit/legal_task_gate_core_fusion_20260606_105840/deepseek_mimo_weak20/run_summary.json
```

结果：
- DeepSeek：20/20，1.0
- MiMo：20/20，1.0
- claim_amount_calculation：DeepSeek 10/10，MiMo 10/10
- jurisdiction：DeepSeek 10/10，MiMo 10/10

## Manifest
已写入：

```text
latest_20260606_legal_task_gate_core_fusion
```

## 真实性边界
这次“融合进核心”指融合进 PGG Archon legal task gate core，不是 Hermes core scheduler/security boundary；未复制外部代码；未声称官方 LegalBench/LexGLUE 成绩；不能作为法律正确性证明。
