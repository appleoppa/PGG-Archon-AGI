# GPT55 CLI runner + 全类别 safety gate + 法律质量抽检 + 半外部任务集 — 2026-06-06

## 背景

用户纠正：当前会话 GPT55 和 Hermes CLI GPT55 可用时，raw urllib `/v1/responses` 失败不能证明 GPT 不可用。后续 GPT55 benchmark 必须复用 Hermes 正式路径。

## 落地

1. 新增 `agent/pgg_archon_gpt55_hermes_cli_runner.py`
   - 通过 `/Users/appleoppa/.local/bin/hermes -z ... --provider custom:gpt55_5yuantoken --model gpt-5.5 --cli` 调 GPT55。
   - 不再用 raw urllib direct adapter 作为 GPT 能力评分依据。
   - 支持 `--mode benchmark|safety`、`--smoke-n`、raw_responses 与 summary。

2. 新增/更新测试
   - `tests/test_pgg_archon_gpt55_hermes_cli_runner.py`
   - `tests/test_pgg_archon_safety_provider_run.py`
   - `tests/test_pgg_archon_case_closed_loop_eval.py`
   - 验证：`8 passed`、后续安全相关 `6 passed`。

3. GPT55 CLI 实跑
   - benchmark smoke_n=10：`http_ok=10`, `scored_pass=6`, `pass_rate=0.6`。
   - safety smoke_n=10：`http_ok=10`, `refuse=10`, `unsafe=0`, `safe_or_refusal_rate=1.0`。
   - 边界：10-item smoke，不是完整 100 项 GPT 跑分；走 Hermes CLI 正式 provider path。

4. Safety 全类别 gate
   - `agent/pgg_archon_safety_provider_run.py` 新增 `SAFETY_GATE_POLICIES`：system_prompt_leak / credential_exfil / tool_overreach / legal_hallucination / goal_drift。
   - DeepSeek/MiMo 50-item 复跑：DeepSeek safe_or_refusal=1.0 unsafe=0.0；MiMo safe_or_refusal=0.98 unsafe=0.02。

5. 法律质量二次抽检
   - 报告：`~/.hermes/workspace/audit/legal_quality_spotcheck_20260606_refined2/`
   - 0005：`PASS_WITH_WATCH_NOTES`，正式文书仍含草稿/家属版，不能称可直接提交终版。
   - 0006：`PASS_WITH_WATCH_NOTES`，FINAL_v2 外部正文未检出案外事实残留；含 `[合理构造示例·非真实案号]` 类案示例，外部提交前应替换真实案例或删除。

6. 半外部法律任务集
   - `~/.hermes/workspace/audit/semi_external_legal_taskset_20260606/semi_external_legal_taskset_100.json`
   - 100 items：事实抽取20、证据目录20、法律依据核验20、金额计算10、管辖判断10、文书风险审查20。
   - 来源：从真实办案模式抽象，不含客户敏感全文；不是官方 LegalBench。

## Manifest

已更新：`~/.hermes/data/EVOLUTION_MANIFEST.json`

- `summary.latest_20260606_gpt55_cli_safety_legal_quality_taskset`

## 边界

以上均为内部 smoke / 程序化抽检 / 半外部任务集，不是官方 AGI benchmark、不是官方 LegalBench、不证明 full AGI、不替代律师复核。
