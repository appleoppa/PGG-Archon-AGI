# Provider 版本纪律：GPT/Claude 审计前先读当前配置

## 触发

用于外部 AGI/进化仓库吸收、多模型审计、GPT/Claude 交叉验证、量子路由前置核验。

## 本次会话暴露的问题

在 APEX-SKILL 吸收审计中，旧记忆和旧配置仍写着 `claude_opus47_5yuantoken / claude-opus-4-7`。用户纠正：Claude 早已改为 4.6。随后读回当前配置并修复为 `claude_opus46_5yuantoken / claude-opus-4-6`，使用 Responses API smoke test 返回 HTTP 200，响应 model 字段为 `claude-opus-4-6`。

## 可复用规则

1. 不用记忆决定 provider 版本；只用当前 `~/.hermes/config.yaml` 读回结果。
2. GPT/Claude 审计前记录四项：provider name、model、api_mode、key_env 是否存在。
3. GPT/Claude 必须调用 `/v1/responses`，payload 使用 `model/input/instructions/max_output_tokens`。
4. 若审计报告引用了旧模型，修复 provider 后同步修正报告口径，避免历史错误继续传播。
5. `key_env` 名称可能沿用旧版本命名；只要当前 env 可调用目标 model，不要为了好看强改成不存在的新 env。

## 最小 smoke test 标准

- HTTP status = 200
- 响应 JSON 的 `model` 字段等于当前配置 model
- 输出文件保存在进化证据目录
- 不把 URL 可达或配置存在冒充真实模型调用
