# 2026-06-02 — 全 LLM 推进 run_conversation 契约门禁

## 适用场景

用户要求“调用所有 LLM 系统执行”“快速解决这个问题”时，尤其是 PGG Archon / Hermes-Agent 进化任务、核心大函数治理、CodeGenesis WATCH triage（观察态分诊）等场景。

## 本次可复用模式

1. **先盘点可用 provider（供应商）**
   - 从 `~/.hermes/config.yaml` 的 `custom_providers` 读取 provider 名称、`api_mode`、model、`key_env` 是否存在。
   - 不打印密钥值。
   - GPT / Claude 走 Responses API：`/v1/responses`，payload 使用 `model/input/instructions/max_output_tokens`。
   - DeepSeek / MIMO 走 Chat Completions：`/v1/chat/completions`。

2. **多 LLM 调用必须留证据**
   - 每个 provider 单独写 JSON 证据文件：provider、model、api_mode、status_code、ok、response/text preview。
   - 写 summary JSON，列出 path 和 SHA-256。
   - 如果串行网络调用耗时，完成后必须主动读回证据目录，避免工具输出压缩造成“像是卡住/停了”的假象。

3. **核心大函数不要直接重构**
   - 对 `agent/conversation_loop.py::run_conversation` 这类 4000+ 行 / 600+ 分支核心循环，所有 LLM 一致建议：先做 read-only characterization contract（只读特征契约）和 trace gate（轨迹门禁），不要直接抽取/批量重写。
   - `run_conversation` 本体不 import（导入）、不 execute（执行）、不 patch（修改）。

4. **契约门禁落地方式**
   - 在独立 slicer（切片器）中用 AST window（抽象语法树窗口）抽取 calls / assigns / name signals。
   - 每个 slice（切片）输出：contract、contract_status、characterization_tests、trace_probe_candidates、mutation_boundary。
   - 测试真实源码只读读回：断言 contract_status 为 PASS，且 mutation_boundary 明确阻止未验证抽取。

5. **本次固化的 slice contract 示例**
   - RC-S01：session context、stdio guard、retry counters、turn exit reason、stream callback、persist override。
   - RC-S02：message sanitization、api_messages、api_kwargs、retry state、streaming decision、pre-api steer、response slot。
   - RC-S03：finish reason、failure hint、invalid response gate、provider error surface、fallback path、persistence/cleanup、usage normalization、assistant message。

## 必跑验证

- Targeted pytest：slicer tests + CodeGenesis scanner tests。
- `py_compile` edited Python files。
- `git diff --check`。
- `python -m apex_god.health` from Hermes-Agent venv/workdir。
- `python -m apex_god.evolution_manifest --update`。
- Scoped commit：只提交本轮相关文件。

## 汇报纪律

用户追问“为什么卡了/为什么不继续了”时，不要解释完就停。应立即：

1. 读回证据文件是否已生成；
2. 若有缺失，换短超时或逐 provider 继续；
3. 落地低风险实现；
4. 测试、health、manifest、commit；
5. 最后用字段化清单交付：LLM status、测试结果、commit、证据 hash、真实边界。

## 边界

- 不宣称 CodeGenesis PASS：高重复率未降时仍是 WATCH。
- 不宣称 `run_conversation` 已重构：只读契约门禁不是行为重构。
- 不把 LLM 角色扮演当作真实调用：必须有 HTTP status、文件路径、hash。
