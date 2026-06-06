# PilotDeck 8-Step Self-Evolution Pipeline

## Trigger

Use when continuing, auditing, or claiming completion for PilotDeck self-evolution work. The user explicitly expects this sequence to be run before any `DONE` claim.

## Required order

1. **文件扫描 / file_scan** — scan PilotDeck hidden home and repo scope; count files/bytes/extensions; flag suspicious temp/backup/fake-success artifacts.
2. **Karpathy 检查 / karpathy_check** — sanity check for fake-success signals such as `mock`, `simulated`, `dry_run`, `time.sleep`, hardcoded `status: done`, plus duplicate-line hotspots.
3. **Import 解析 / import_parse** — parse Python with AST and verify TS/JS with `npm run build` or the project’s equivalent build gate.
4. **综合报告 / integrated_report** — summarize providers, main model, memory model, fallback, config hash, scan/build statuses.
5. **EVM 监控 / evm_monitor** — check live ports/services, main-model invariants, build status, Karpathy status; require score >= 75.
6. **Tao 纠偏 / tao_correction** — if EVM/Karpathy/build fails, stop mutation and generate corrective actions; do not proceed as completed.
7. **β_bg 进化 / beta_bg_evolution** — compute evolution confidence; require beta_bg >= 0.75 for PASS; identify next actions.
8. **Pipeline 完成 / pipeline_completion** — only PASS if all prior gates passed in order.

## Current PilotDeck implementation

- Script: `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/reports/pilotdeck_evolution_pipeline_round7.py`
- JSON output: `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/reports/pilotdeck_evolution_pipeline_round7_20260603.json`
- Report output: `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/reports/pilotdeck_evolution_pipeline_round7_20260603.md`
- PilotDeck absorption report: `/Users/appleoppa/.pilotdeck-agi/home/.pilotdeck/reports/pilotdeck_pipeline_sequence_absorption_round7_20260603.md`

## Expected PASS evidence

- `invariants_ok = true`
- PilotDeck services ready: 18789, 3001, 5173, 18888
- `npm run build` exit code 0
- Karpathy fake-success signals all zero or explained as harmless
- `EVM >= 75`
- `β_bg >= 0.75`
- Model boundary unchanged: MIMO main/tools; GPT advisory-only/no-tools; Agnes chat-only/no-tools

## Pitfalls

- Do not treat a written report as completion unless the pipeline was actually run and read back.
- Do not skip or reorder the eight stages. The user explicitly corrected the workflow to this sequence.
- Do not mutate model routing during this pipeline; it is a verification/evolution gate, not a provider migration.
- If a gate fails, report `PARTIAL` or `BLOCKED` with the failing stage and evidence, then apply Tao correction before retrying.
