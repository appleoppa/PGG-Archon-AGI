# AGI 进程检查后的 Rust fusion 续跑门禁

## 适用场景

用户要求“全量查看现在的 AGI 进程”后继续推进，且 Reasonix/APEX-SKILL/Rust fusion 属于当前低风险、可回滚的下一阶段。

## 稳定执行顺序

1. 先区分 live process、launchd/cron、persisted manifest、repo working tree，不把文件存在冒充在线运行。
2. 检查 Hermes agent、DeepSeek-Reasonix、APEX-SKILL、Rust fusion crate 的 HEAD 和 working tree；遗留 sibling repo 改动不得混入本轮提交。
3. 执行 Rust crate：
   - `cargo test`
   - `scripts/self_evolution_token_gate.sh`
   - 必要时直接运行 Rust binary 生成 fusion manifest。
4. 执行上游回归：
   - DeepSeek-Reasonix：`make test` 或 `go test ./...`
   - APEX-SKILL：`/usr/bin/python3 -m pytest tests/ -q`
5. 从生成 JSON 的嵌套字段 `self_evolution_token_gate_report` 读取 gate 结果，不要误读顶层 fusion manifest 字段：
   - `readiness_band`
   - `next_stage_allowed`
   - `blockers`
   - `token_saving_ratio`
   - `field_recall`
   - `semantic_overlap`
   - `verdict_normalization_pass`
   - `ais_immune_score`
6. 当 `readiness_score >= 75`、`next_stage_allowed=true`、`blockers=[]` 且边界仍为 `hermes_core_mutation=false` 时，可继续低风险闭环。
7. 提交前执行：敏感信息扫描、`git diff --check`、重跑 `cargo test`。只 stage 本轮 crate 文件，不混入外部 repo 或 sibling working tree 改动。
8. 提交后再次检查 crate working tree clean，更新 `python -m apex_god.evolution_manifest --update`，再跑 `python -m apex_god.health`。
9. 最终报告与 manifest 的 SHA-256 必须在最后一次生成/补丁完成后重新计算；不要沿用脚本中较早一次输出的 hash。

## 关键坑点

- `self_evolution_token_gate_latest.json` 顶层 schema 是 `PGGArchonReasonixApexFusionManifest/v1`；真正门禁报告位于 `self_evolution_token_gate_report`。
- gate 脚本会覆盖 latest manifest。任何后续直接运行 binary、更新报告或补丁都可能改变 hash；交付前必须重新读回。
- Rust fusion 是 additive capability（附加能力），不是 Hermes core scheduler/security boundary 接管。即使 readiness 很高，也不得越界宣称核心已替换。
- workspace 证据目录未必是 Git repo。报告可归档并哈希，但只有明确属于本轮且位于独立 repo 的 crate 文件才进入本轮 commit。

## 验证口径

交付至少包含：

- crate HEAD / working tree clean
- Rust `cargo test` 结果
- Reasonix 与 APEX-SKILL 回归结果
- gate `readiness_score`、`readiness_band`、`next_stage_allowed`、`blockers`
- `hermes_core_mutation=false`
- EVOLUTION_MANIFEST 更新时间与 APEX-GOD health 读回
- 最终报告 hash 与 latest manifest hash
