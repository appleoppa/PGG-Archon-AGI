# Provider 配置一致性修复：审计后收口流程

适用场景：Hermes 全面审计后发现 `model.provider`、`providers:`、`custom_providers:`、profile 配置、辅助模型或 router 引用不一致。

## 核心原则

- 先备份，再改配置；备份目录权限 `0700`，备份文件 `0600`。
- 不修改 `.env` / `auth.json`，除非用户明确授权；不打印密钥。
- `providers:` 作为唯一 provider 真源；`custom_providers:` 只作为 legacy 兼容层，避免长期保留影子重复配置。
- `model.provider` 如果使用命名自定义 provider，优先写成 `custom:<providers_key>`，并确认 `<providers_key>` 存在于 `providers:`。

## 必查项

1. root config：`~/.hermes/config.yaml`
2. profile config：`~/.hermes/profiles/<profile>/config.yaml`
3. `model.default` / `model.provider`
4. `providers:` key 列表
5. `custom_providers:` 是否重复定义同 endpoint/model
6. 每个 provider 的 `key_env` 是否是环境变量名，而不是红acted占位或 inline key
7. 每个 provider 是否同时有：
   - `model`
   - `default_model`
   - `api_mode`
   - `base_url`
   - `key_env`

## 关键坑：default_model

Hermes runtime 的 `_get_named_custom_provider()` 从 `providers:` 解析命名 provider 时会读取 `default_model`。如果只写 `model` 而缺少 `default_model`，runtime 可能解析到空 model。

修复规则：

```yaml
providers:
  gpt55_5yuantoken:
    model: gpt-5.5
    default_model: gpt-5.5
```

对所有自定义 provider 保持 `default_model == model`，除非确有多模型路由需求。

## 关键坑：key_env 被红acted占位污染

在某些 Hermes 工具输出中，`key_env` 字段可能显示为 `<REDACTED_SECRET>`。如果把这种已红acted的 YAML 重新写回配置，会破坏 provider 与 `.env` 的映射。

修复规则：

- `key_env` 必须是变量名，例如 `GPT55_5YUANTOKEN_API_KEY`。
- 不要把 `<REDACTED_SECRET>` 写回配置。
- 用 `.env` 的变量名集合做对齐验证，但不要输出变量值。

## 推荐修复顺序

1. 备份 root/profile config。
2. 修 `model.provider`：
   - root 示例：`custom:gpt55_5yuantoken`
   - deepseek profile 示例：`custom:deepseek_v4_flash`
3. 清理或清空重复 `custom_providers:`，保留 `providers:` 为真源。
4. 恢复/确认每个 provider 的 `key_env` 变量名。
5. 为每个 provider 补齐 `default_model`。
6. YAML 解析验证。
7. key_env 名称对齐验证。
8. runtime provider 解析验证：确认 `custom:<name>` 能解析出 base_url、api_key、model、api_mode。
9. provider 健康验证，例如 `qr route` 或轻量 chat completion。
10. 如 gateway 正在运行，提示需要新会话或按需重启 gateway 才能完全加载新配置。

## 完成态口径

- “配置已修复”：必须满足 YAML 可解析、provider 引用存在、key_env 名称存在、runtime 解析有 model。
- “运行态已生效”：还需要 gateway/新会话验证。
- 如果未重启 gateway，只能说“配置文件已修复并通过静态/轻量验证”，不能说所有运行态已完全生效。
