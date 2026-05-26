# APEX 基因生命周期 WARN 治理清单

生成时间：2026-05-26 23:55:11

## 状态

- 报告类型：只读分类，不写库
- 门禁状态：WARN
- 分类状态：WATCH
- 基因数：122
- 问题类型数：1
- SQLite读取：PASS
- 来源表：evolution_genes

## 问题分类

- verified_without_validation：4 条
  - 样例：GENE-SUPER-002-GITHUB-EVOLUTION-LOOP, GENE-SUPER-001-HETU-LUOSHU-LLM-ROUTER, GENE-R09-SPEC, manual_round_026_backtest_quality_gate

## 修复候选

- hold_unvalidated_verified
  - 风险：medium
  - 影响数量：4
  - 动作：verified 但缺验证证据的基因应降级 HOLD 或补验证证据；不能自动通过

## 边界

- 本报告未修改 SQLite。
- 本报告未晋升基因。
- 后续如执行修复，必须先备份数据库，再逐条读回验证。
