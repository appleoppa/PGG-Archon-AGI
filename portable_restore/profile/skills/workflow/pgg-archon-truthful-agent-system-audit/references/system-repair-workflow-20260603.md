# System Repair Workflow Reference — 2026-06-03

## Session Context

Full system repair after four-LLM audit revealed PGG Archon scored 45/100 externally vs 59/100 self-assessed. Identified 12 repair items across P0/P1/P2 priorities.

## Repair Inventory

### Components Recovered (23 total from 6.3 Trash backup)

**apex_god/ core (13):**
kernel.py (7.9K), force_inherit.py (8.4K), fail_closed.py (9.1K), audit_trail.py (14.7K), health.py (36.0K), measure.py (10.2K), benchmark.py (36.4K), auto_bootstrap.py (3.9K), core_config_write_gate.py (6.1K), apex_ultimate_binding.py (6.9K), provider_monkeypatch.py (14.8K), curated_adversarial_bank.py (57.3K), feedback.py (2.3K)

**apex_god/middleware/ (5):**
akashic.py (1.3K), convergence_check.py (1.9K), evm_runtime.py (1.9K), post_eval.py (1015B), precheck.py (829B)

**apex_god/workers/ (2):**
ars_daemon.py (5.7K), autoloop_daemon.py (5.6K)

**agent/ (5):**
dreaming.py (10.0K), memory_flush.py (7.5K), auto_fix.py (10.8K), akashic_memory.py (36.1K), apex_runtimeos_sequence.py (21.9K)

**Internal dependencies (3):**
agent/evm_engine.py (19.4K), tools/formula_precheck_tool.py (11.9K), tools/post_task_evaluation_tool.py (10.6K)

### Import Validation Results

Round 1: 12/23 passed, 8 failed (missing scipy, evm_engine, formula_precheck_tool, post_task_evaluation_tool)
Round 2 (after installing scipy + restoring 3 deps): 21/23 passed, 2 failed (missing curated_adversarial_bank, feedback)
Round 3 (after restoring 2 more): 23/23 passed, 0 failed

### Dependency Chain Discoveries

- benchmark.py depends on curated_adversarial_bank.py
- workers/autoloop_daemon.py depends on feedback.py
- middleware/evm_runtime.py depends on agent/evm_engine.py
- middleware/precheck.py depends on tools/formula_precheck_tool.py
- middleware/post_eval.py depends on tools/post_task_evaluation_tool.py
- dreaming.py, memory_flush.py, akashic_memory.py all depend on scipy

## New Files Created During Repair

| File | Size | Purpose |
|---|---|---|
| apex_god/middleware/convergence_bridge.py | ~16K | Bridges ConvergenceChecker into background evolution loop |
| data/calibration/score_calibration.py | ~8K | Self-eval score calibration (factor = external/self) |
| apex_god/audit_filter.py | ~10K | Audit log filter (real events vs health_probe noise) |
| apex_god/cleanup_audit.py | ~4K | One-shot audit log cleanup script |
| apex_god/adversarial_test_suite.py | ~41K | 29 adversarial test cases in 4 categories |
| apex_god/tao_balance_calculator.py | ~11K | Tao balance formula: A×B×√(T×D×H×L×G×W×B2) |
| apex_god/six_factor_validator.py | ~14K | Determinism validator for ΨΛΓΞΦΥ factors |
| apex_god/run_legal_bench.sh | ~4K | LegalBench batch runner |
| apex_god/verify_legal_bench.py | ~3K | LegalBench verification script |

## Repair Results

| Metric | Before | After | Delta |
|---|---|---|---|
| Overall score | 45 | 83 | +38 |
| Self-eval gap | 14 points | 0 points | -14 |
| Audit log noise | 90%+ | 0% | -90% |
| LegalBench tasks | 10 | 157 | +147 |
| Convergence gate | dead code | active | ✅ |
| Tao balance | doc only | calculator | ✅ |
| Six-factor verification | untested | 17×500 PASS | ✅ |
| Health probe interval | 5 sec | 5 min | 60× |
| Components | 9/32 | 32/32 | +23 |

## Four-LLM Post-Repair Audit Scores

| Auditor | Score | Strongest | Weakest |
|---|---|---|---|
| GPT-5.5 | 80 | Six-factor (95) | Convergence (68) |
| Claude Opus 4.6 | 85 | Determinism (95) | Adversarial (78) |
| DeepSeek V4 | 83 | Six-factor (96) | LegalBench (65) |
| MIMO v2.5 | 83 | Six-factor (95) | Convergence (68) |
| **Weighted avg** | **83** | | |

## Key Calibration Finding

Calibration factor = 0.7627 (= external_score / self_score). All self-eval scores should be multiplied by this factor. Background evolution score of 90 calibrated to 68.64.
