# FINAL_v3 + 半外部法律任务集 runner + GPT55 分批策略 — 2026-06-06

## 本轮完成

1. `PGG-MS-20260605-0006` 生成：
   - `正式文书/PGG-MS-20260605-0006-民事起诉状_FINAL_v3.md`
   - `正式文书/PGG-MS-20260605-0006-民事起诉状_FINAL_v3_外部提交前待补版.md`

2. FINAL_v3 外部提交前待补版处理：
   - 删除 v2 中“合理构造示例·非真实案号”类案段。
   - 删除内部 LLM 协作记录与修正留痕。
   - 保留待补信息边界：当事人详细信息、具体管辖法院、代理人信息仍需补齐。
   - `legal_doc_gate` 复跑 PASS：`blocks=0 warnings=0 findings=0`。

3. 新增半外部法律任务集 runner：
   - `agent/pgg_archon_semi_external_legal_runner.py`
   - 测试：`tests/test_pgg_archon_semi_external_legal_runner.py`
   - 规则：不得编造事实/法条/案例/法院/案号；材料不足须标待补/核验路径。

4. 半外部法律任务集 100 项 DeepSeek/MiMo 实跑：
   - DeepSeek：`http_ok=100/100`, `scored_pass=88`, `pass_rate=0.88`
   - MiMo：`http_ok=100/100`, `scored_pass=95`, `pass_rate=0.95`
   - 弱项：jurisdiction（DeepSeek 0.7 / MiMo 0.6）、claim_amount_calculation（DeepSeek 0.5 / MiMo 0.9）。

5. GPT55 CLI runner 增加 `--offset/--limit` 分批策略：
   - 避免 raw urllib 误判 GPT55。
   - 避免一次性 full 100/50 的成本/耗时失控。
   - 分批实跑 offset=10 limit=5：`http_ok=5`, `scored_pass=4`, `pass_rate=0.8`。

## Manifest

已更新：`~/.hermes/data/EVOLUTION_MANIFEST.json`

- `summary.latest_20260606_final_v3_semi_external_legal_run`

## 边界

- FINAL_v3 外部提交前待补版仍需客户/主办律师补齐主体信息与具体法院。
- 半外部法律任务集不是官方 LegalBench。
- 分数是内部程序化过程评分，不证明法律观点正确、full AGI 或替代律师复核。
