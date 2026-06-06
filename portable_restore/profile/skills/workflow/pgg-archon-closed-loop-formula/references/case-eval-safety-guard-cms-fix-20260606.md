# 2026-06-06 0006 CMS结构修复 + safety guard + case eval

## 触发

用户授权继续补短，针对三项硬短板：0006 CMS 结构 BLOCKED、legal_hallucination safety unsafe、案件闭环评测脚本化。

## 修复结果

1. `PGG-MS-20260605-0006` 顶层散落目录已迁移到阶段目录：

```text
0006-PGGMS-20260605-燕赵财险雇主责任险合同纠纷/
  PGG-MS-20260605-0006（一审）/
    案件材料/
    案件过程报告/
    总结报告/
    正式文书/
```

额外 `任务记录/审计记录/证据材料` 已作为子目录归入标准目录，Rust CMS guard 复跑 `PASS`。

2. `agent/pgg_archon_safety_provider_run.py` 新增 `guarded_safety_prompt()`：对 `legal_hallucination` probe 注入 PGG Legal Safety Gate，禁止编造官方案例/法条/案号，要求拒绝或官方来源核验。

复跑 50-item safety：

```text
DeepSeek safe_or_refusal_rate 1.0, unsafe_rate 0.0
MiMo     safe_or_refusal_rate 0.84, unsafe_rate 0.16
legal_hallucination: DeepSeek unsafe 0.0, MiMo unsafe 0.0
GPT55 direct adapter: parse_error 50（见边界）
```

3. 新增 `agent/pgg_archon_case_closed_loop_eval.py`：自动检查案件材料、CMS流转、证据、法律依据、分析、巡视、审计、正式文书、raw multi-LLM，并可调用 `cms_case_guard` / `legal_doc_gate`。

两案实测：

```text
0005: closed_loop_score 1.0, CMS PASS
0006: closed_loop_score 1.0, CMS PASS, legal_doc_gate PASS
```

## GPT55 边界

- 直接 urllib 调 ChuangAgent `/v1/responses` 仍出现 502 或 HTTP 200 但 `output=[]`。
- Hermes CLI 实测可用：`/Users/appleoppa/.local/bin/hermes -z 'Return exactly: OK' --provider custom:gpt55_5yuantoken --model gpt-5.5 --cli` 返回 `OK`。
- 因此：Hermes CLI provider path 可用，但 benchmark direct adapter 尚未等价修复；不得把 direct runner 的 GPT55 parse_error 说成模型不可用。

## Manifest

已更新 `~/.hermes/data/EVOLUTION_MANIFEST.json`：`summary.latest_20260606_case_eval_and_safety_repair`。

## 边界

这些是内部 provider smoke、案件归档流程与程序化门禁结果；不是官方外部 AGI benchmark，不证明 full AGI，不替代律师复核。
