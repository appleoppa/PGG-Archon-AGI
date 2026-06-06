# Hermes Agent 上下文系统全量审计 Runbook

> 首次执行: 2026-06-03 | 公式 score=34.94 (HOLD), EVM=74.94, Δ=40.0

## 触发条件

用户要求"调用所有LLM、代入公式、分析上下文系统"或类似的上下文工程全面审计。

## APEX 序列选择

`21354`（审计优先、防幻觉）— 先审计证据，再修复，再固化。

## 第一步：盘点上下文架构核心文件

路径基座: `~/.hermes/hermes-agent/agent/`

| 文件 | 行数 | 角色 |
|------|------|------|
| `context_engine.py` | ~226 | 可插拔抽象基类 (ContextEngine ABC) |
| `context_compressor.py` | ~2147 | 默认压缩器 (ContextCompressor) |
| `conversation_compression.py` | ~732 | 压缩编排 (session split/lock) |
| `memory_manager.py` | ~640 | 记忆编排器 (MemoryManager) |
| `akashic_memory.py` | ~980 | 5D向量记忆 (AkashicMemory) |
| `pgg_archon_context_formula.py` | ~172 | APEX_MAX 公式评分 |
| `pgg_archon_memory_trace.py` | ~65 | Σ_memory + τ_trace 评分 |
| `pgg_archon_phase48_memory_context_bridge.py` | ~54 | 记忆-上下文连续性 manifest |
| `context_references.py` | ~518 | @file/@git/@url 引用展开 |
| `system_prompt.py` | ~407 | 系统提示词组装 (stable/context/volatile 三层) |
| `prompt_builder.py` | ~1507 | 技能索引注入 (lazy loading) |

## 第二步：运行上下文相关测试

```bash
cd ~/.hermes/hermes-agent

# 核心上下文测试套件
venv/bin/python -m pytest \
  tests/agent/test_context_engine.py \
  tests/agent/test_context_compressor.py \
  tests/agent/test_pgg_archon_context_formula.py \
  tests/agent/test_pgg_archon_memory_trace.py \
  tests/agent/test_compress_focus.py \
  tests/agent/test_context_compressor_summary_continuity.py \
  tests/agent/test_compression_concurrent_fork.py \
  tests/agent/test_pgg_archon_phase48_memory_context_bridge.py \
  tests/agent/test_memory_provider.py \
  tests/agent/test_memory_user_id.py \
  tests/agent/test_context_references.py \
  -v --tb=short
```

预期: 241+ tests PASS。如果出现 FAIL，先修复再继续审计。

## 第三步：运行 APEX_MAX 公式计算

```python
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))

from agent.pgg_archon_context_formula import (
    build_context_formula_report,
    build_context_budget_policy,
)

signals = {
    "token_savings": 78.0,    # Token Kernel 测试结果
    "efficiency": 72.0,        # 压缩器工作但有改进空间
    "accuracy": 85.0,          # 测试通过率
    "completeness": 70.0,      # 组件可导入率
    "logic_flow": 75.0,        # 序列逻辑状态
    "response_speed": 68.0,    # 默认模型延迟
    # 乘子默认 1.0
    "omega_a": 1.0, "beta_bg": 1.0, "alpha_ack": 1.0,
    "theta_tri": 1.0, "nabla_k": 1.0, "zeta_sigma": 1.0,
    "eta_lambda": 1.0, "A": 1.0, "B": 1.0, "tdhlgwb": 1.0,
}

delta_signals = {
    "skill_bloat": 0.6,          # 技能加载量
    "tool_output_bloat": 0.4,    # 工具输出限制
    "compression_lag": 0.3,      # 压缩触发延迟
    "context_pollution": 0.5,    # MEMORY/USER 注入量
    "logic_fragmentation": 0.3,  # 跨技能逻辑碎片
    "latency_drag": 0.4,         # 多LLM调用延迟
    "accuracy_loss": 0.2,        # 压缩准确性损失
}

report = build_context_formula_report(signals=signals, delta_signals=delta_signals)
policy = build_context_budget_policy(report)
```

**评分解读**:
- score >= 75 → PASS (lean_default 预算)
- 50 <= score < 75 → WATCH (balanced_repair 预算)
- score < 50 → HOLD (strict_recovery 预算)
- critical_active → BLOCKED (score 强制为 0)

## 第四步：多 LLM 交叉审计

### DeepSeek (chat_completions)
```bash
source ~/.hermes/.env 2>/dev/null
curl -s https://api.deepseek.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_V4_FLASH_API_KEY" \
  -d '{"model":"deepseek-v4-flash","messages":[...],"max_tokens":3000,"temperature":0.3}'
```

### MIMO (chat_completions)
```bash
curl -s https://token-plan-cn.xiaomimimo.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MIMO_V25_PRO_API_KEY" \
  -d '{"model":"mimo-v2.5-pro","messages":[...],"max_tokens":2500,"temperature":0.3}'
```

### GPT-5.5 (codex_responses — Responses API)
```bash
# 注意: GPT-5.5 使用 /v1/responses 端点，不是 /v1/chat/completions
curl -s https://chuangagent.eu.cc/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GPT55_5YUANTOKEN_API_KEY" \
  -d '{"model":"gpt-5.5","input":"...","max_output_tokens":2500}'
# 解析: data.output[].content[] -> type=output_text
```

**审计提示词模板**:
```
作为上下文工程审计专家，分析以下 Hermes Agent 上下文系统：
[架构摘要 + 公式评分 + 配置参数 + 测试结果]
请从完整性、压缩质量、记忆桥接、性能瓶颈维度分析，给出TOP3短板+具体修复方案。
```

## 第五步：配置优化基线

基于 2026-06-03 审计的证据驱动配置建议:

| 参数 | 当前值 | 建议值 | 理由 |
|------|--------|--------|------|
| `always_load_skills` | `[pgg-reasonix-apex-fusion]` | `[]` | 减少 ~3000 tokens 固定注入 |
| `memory.memory_char_limit` | 5000 | 3000 | 减少 ~500 tokens/轮 |
| `memory.user_char_limit` | 3000 | 2000 | 减少 ~250 tokens/轮 |
| `tool_output.max_bytes` | 12000 | 8000 | 减少工具输出膨胀 |
| `tool_output.max_lines` | 600 | 400 | 同上 |
| `compression.threshold` | 0.30 | 0.20 | 更早触发压缩 |
| `compression.protect_last_n` | 6 | 8 | 保护更多近期上下文 |
| `compression.target_ratio` | 0.12 | 0.15 | 保留更多压缩后上下文 |
| `compression.absolute_threshold_tokens` | 150000 | 100000 | 更早触发 |

**注意**: 这些建议基于特定时间点的系统状态，下次审计时应重新评估。

## 第六步：输出审计报告

报告写入: `~/.hermes/workspace/进化/证据/context-audit-YYYYMMDD/上下文系统全量审计报告.md`

报告结构:
1. 公式评分 (EVM/Δ/Final)
2. 代码架构盘点 (文件/行数/测试覆盖)
3. 三模型审计结论汇总
4. 真实短板诊断 (按 Δ 权重排序)
5. 已验证优势
6. 可执行改进清单 (立即/短期/中期)
7. 诚实边界

## 压缩器关键实现细节

`context_compressor.py` compress() 5阶段:
1. `_prune_old_tool_results()` — 无LLM的工具输出修剪（智能摘要而非粗暴截断）
2. `_protect_head_size()` + `_align_boundary_forward()` — 头部保护
3. `_find_tail_cut_by_tokens()` — token预算尾部保护
4. `_generate_summary()` — LLM结构化摘要（iterative update 支持）
5. 角色交替修复 + session split + session_id rotation

关键配置常量 (context_compressor.py 内部):
- `_MIN_SUMMARY_TOKENS = 2000`
- `_SUMMARY_RATIO = 0.20`
- `_SUMMARY_TOKENS_CEILING = 12000`
- `_IMAGE_TOKEN_ESTIMATE = 1600`
- `_SUMMARY_INPUT_MAX_CHARS = 80000`
- `_FALLBACK_SUMMARY_MAX_CHARS = 8000`

## 记忆系统关键实现细节

`akashic_memory.py` AkashicMemory:
- Embedder: fastembed BAAI/bge-small-zh-v1.5 (512d)
- HybridRetriever: TF-IDF + Dense + BM25 + FTS5 + Graph → RRF fusion
- 5D Tiers: Working(1h) / Episodic(7d) / Semantic(6mo) / Procedural(1yr) / Declarative(5yr)
- Decay: exponential 0.5^(elapsed/halflife)
- Consolidation: dreaming(decay/merge/promote/relation)

`memory_manager.py`:
- `build_memory_context_block()` — `<memory-context>` 围栏注入
- `StreamingContextScrubber` — 流式输出中防止 memory-context 泄漏
- 最多 1 个 external provider + builtin provider

## 系统提示词组装

`system_prompt.py` build_system_prompt_parts() 三层:
- **stable**: SOUL.md + 技能索引 + 工具指导 + 环境提示 + 模型族指导
- **context**: AGENTS.md + .cursorrules + system_message
- **volatile**: memory snapshot + user profile + external memory block + timestamp

技能注入: `build_skills_system_prompt()` 只注入 name+description 索引，完整内容通过 `skill_view()` 按需加载。

## Pitfall

1. **GPT-5.5 不走 chat_completions**: 必须用 `/v1/responses` (Responses API)，否则返回 INVALID_API_KEY
2. **Delta 信号值是估算**: 基于实测数据的合理推断，非精确测量；下次审计应重新采集
3. **241/241 PASS 是功能测试**: 不是性能基准；PASS 不代表性能最优
4. **配置改动需逐项验证**: 不可批量实施后声称完成
5. **always_load_skills 的影响**: 当 SKILL.md 很大时（如 pgg-reasonix-apex-fusion ~8000 chars），每轮固定消耗显著
