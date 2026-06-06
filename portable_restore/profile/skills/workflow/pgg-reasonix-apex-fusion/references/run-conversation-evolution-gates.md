# run_conversation 进化门禁参考

适用场景：PGG Archon / APEX / AGI 类任务中，用户要求持续推进 Hermes `agent/conversation_loop.py::run_conversation` 或类似核心大函数的进化、拆分、重构、抽取。

## 用户偏好与执行纪律

- 用户说“继续”时，在低风险、可回滚、评分 >75 的前提下，继续自动推进；不要停在建议或下一步计划。
- 汇报必须区分真实状态：已生成门禁、已测试、已提交、尚未重构、CodeGenesis 仍 WATCH 等不能混淆。
- 专业英文术语保留并加中文括注，如 characterization contract（特征契约）、extraction readiness matrix（抽取就绪矩阵）。
- 不向桌面输出过程文件；证据归档到 `~/.hermes/workspace/进化/证据/...`。

## 安全推进模式

1. 不先直接改核心大函数；先用 AST/read-only slicer（只读切片器）建立 source-backed characterization contract（源码支撑的特征契约）。
2. 按窗口分段建立 RC-Sxx gate（门禁），每段必须包含：
   - slice_id / range / purpose
   - trace_probe_candidates（轨迹探针候选）
   - contract（契约字段）
   - contract_status
   - mutation_boundary（突变边界）
3. 每轮都要调用可用 LLM 系统做交叉审计，但最终以本地源码读回、测试、health、Manifest 为准。
4. 在 RC-S01..RC-S09 等核心窗口全部 PASS 前，不做抽取；全部 PASS 后先生成 extraction readiness matrix（抽取就绪矩阵）。
5. matrix（矩阵）只允许明确的最小范围，例如 `RC-S01 only`、mechanical helper/stage wrapper extraction（机械辅助函数/阶段包装器抽取）、no behavior change（无行为变化）。
6. 明确 blocked_scope（阻断范围）：RC-S02+ 抽取、批量重写、provider/tool 行为变更、scheduler/security boundary mutation（调度/安全边界突变）。

## 每轮验证闭环

- 运行 targeted pytest（至少相关 slicer/codegenesis 测试）。
- 运行 `py_compile` 检查编辑过的 Python 文件。
- 运行 `git diff --check`。
- 运行 APEX-GOD health，要求 `24/24 PASS` 或清楚标注失败。
- 更新 `EVOLUTION_MANIFEST.json`。
- 写证据报告，记录 LLM HTTP 状态、哈希、matrix/status、测试输出、manifest hash。
- commit 只包含本轮相关 repo 文件；不要混入 workspace 证据文件，除非仓库明确跟踪。

## 真实性边界

- URL 可达、工具安装、LLM 返回 HTTP 200 都不等于能力已部署。
- 没有修改 `conversation_loop.py` 就不能说 `run_conversation` 已重构。
- CodeGenesis WATCH 不能宣称 PASS；如果 high_duplication 未下降，必须继续标注 WATCH。
- LLM 分歧时采用保守裁决：先落地可验证门禁/矩阵，不跨越到核心行为变更。
