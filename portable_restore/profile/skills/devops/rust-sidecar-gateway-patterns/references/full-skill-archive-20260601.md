---
name: rust-sidecar-gateway-patterns
description: Rust sidecar gateway 的可吸收架构模式：多 provider、飞书/聊天上下文、错误分诊、持久化账本、部署清理
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [rust, sidecar, gateway, feishu, llm, deployment, cleanup]
---

# Rust Sidecar Gateway Patterns

## 适用场景

当一个 Rust sidecar（边车服务）承担聊天入口、LLM provider 调度、webhook 回调、轻量记忆或进化账本时，按本模式吸收可复用能力，避免把半成品项目当成完整 agent（智能体）。

## 可吸收能力

### NanoGPT-claw 吞噬后保留的通用模式

> 仅保留可复用架构基因；不保留 nanoGPT-claw 品牌、仓库、二进制、运行态文件、GitHub 仓库或半成品入口。

- **CLI 统一入口**：`send/status/start/stop/task/skill/memory` 这类命令可作为轻量 agent（智能体）本地控制面；消息入口应统一转成 `MessageContext`，带 `source/user/session_id/timestamp`。
- **主模型 + 辅助模型调度**：保留 `main_provider/main_model + aux_providers` 的编排模式；最终必须有收敛器、证据等级和失败降级，不把并行调用数量冒充质量。
- **ProviderRegistry**：用 trait（特征）/adapter（适配器）统一 OpenAI-compatible、Anthropic、Ollama 等 provider；错误按 `401/429/5xx/context_overflow/timeout` 分类后进入 retry/fallback/compress/abort 策略。
- **step budget + confidence gate**：可吸收“步骤预算 + 置信度门禁 + 自审查”的推理流程；对外不得输出私有 chain-of-thought（思维链），只输出简短 rationale（理由摘要）和可验证结论。
- **双层记忆**：session memory（会话记忆）+ persistent SQLite memory（持久记忆）值得吸收；生产化必须加入 namespace/source/sensitivity/ttl/schema migration/加密或脱敏。
- **Skill trait + registry**：技能应声明 metadata（元数据）、参数 schema、副作用、权限、超时、dry-run、审计日志；命令型技能必须白名单工作目录和命令。
- **daemon + PID 门禁**：PID 文件只能作线索，必须 `kill -0` 验证存活；macOS 长驻进程优先 launchd 或受控后台进程，日志用用户态目录。
- **webhook 快速 ACK**：飞书/GitHub 等 webhook 应快速验签/验 token/去重/ACK，后台异步处理，避免平台重试风暴。
- **Web UI router 与 server 分离风险**：有 router 不等于已监听端口；部署报告必须验证端口、health endpoint 和真实业务路径。

1. **真实 provider 调度**
   - 把 mock/格式化回复替换成真实 scheduler/provider 调用。
   - provider registry（注册表）从环境变量构建，但必须区分“配置存在”和“运行态可用”。
   - GPT/Claude 类 Responses API、DeepSeek chat completions、MiniMax Anthropic messages 要按各自协议分开适配。

2. **聊天上下文最小闭环**
   - webhook 收到消息后按 `chat_id` 写入 SQLite。
   - 回复前读取同一 `chat_id` 最近 N 条消息注入 prompt。
   - 用户说“继续 / 修复 / 还是报错 / 不对”时，默认关联上一轮上下文。

3. **错误分诊闭环**
   - 报错文本先分类：provider_auth、provider_rate_limit、provider_timeout、gateway_config、encrypted_event、payload_parse、runtime_panic、unknown。
   - 记录 incident（错误事件）：chat_id、message_id、category、evidence、status、timestamp。
   - 回复必须包含：状态、分类、依据、修复步骤、需要用户提供的信息。

4. **持久化账本**
   - 对多模型/evolution/benchmark 运行建立 SQLite ledger（账本）。
   - 记录 input、main_result、aux_results、final_output、score、status、error、timestamp。
   - 交付前必须 CLI 查询和 SQLite 读回验证，不能只看 stdout。

5. **macOS Rust CLI 部署门禁**
   - `cargo test` → `cargo build --release` → 复制到目标路径 → `chmod 755` → `codesign --remove-signature` → `codesign --force --sign -` → 目标路径最小命令验证 → launchd restart → health check → 真实业务烟测。
   - copied binary 出现 `Killed: 9` 优先检查 codesign，不要误判业务逻辑崩溃。
   - daemon start 不能只看 pid file；必须 `kill -0 <pid>` 验证进程真实存活，发现 stale pid file 自动清理。

6. **webhook 快速 ACK**
   - webhook handler 先验 token、解析事件、去重，然后快速返回 accepted。
   - LLM 处理放后台任务，避免平台重试风暴。
   - 对 encrypted payload 必须明确支持解密或在配置上关闭加密，不能模糊失败。

7. **能力边界**
   - sidecar 链路打通不等于拥有主 agent 的工具权限、技能库、记忆或自动修复能力。
   - 若需要真实文件修改、命令执行、部署、办案流程，应生成 escalation request（升级请求）交给主编排器。
   - 不要把“能回答”说成“已执行/已修复”。

## 不应吸收的部分

- 半成品项目的品牌、仓库结构、临时脚本、专用 secrets、飞书 app 绑定、localtunnel 地址、运行态 DB、日志。
- 未经门禁的“自动全量学习”设想。
- 会让 sidecar 冒充主 agent 权限的 prompt。

## 验证清单

- [ ] provider 调用是真实 API，不是 mock。
- [ ] 同一 chat_id 的上下文能读回。
- [ ] 错误 incident 能落库并查询。
- [ ] release 二进制是目标路径执行成功，不只是 target/release 成功。
- [ ] 本地部署前先跑 `cargo test`，不要相信远端 CI/README 宣称；daemon 入口可能触发测试未覆盖的配置构造器。
- [ ] macOS 部署复制 binary 后执行 `chmod 755` + ad-hoc codesign，再用目标路径最小命令验证。
- [ ] daemon 验证必须包括 PID 文件、`kill -0 <pid>`、CLI `status` 和一个业务命令（如 `skill run status`），不能只看进程启动。
- [ ] 外部 gateway 默认禁用，除非显式 env 开关启用；从 env 读取 secret，不写入代码或报告。
- [ ] 提交前清理 `target/` 变更、本地 SQLite DB 等 runtime artifact，只提交本轮最小源码修复。
- [ ] launchd、端口、health endpoint、业务路径均验证。
- [ ] 仓库未混入 runtime DB、target 产物或 secrets。
- [ ] sidecar 对超权限任务会升级，不冒充执行。

## 参考资料

- `references/nanogpt-claw-local-deployment.md`：nanoGPT-claw 本地 Rust sidecar 部署中遇到的 `GatewayConfig::from_env()` 缺失、macOS codesign、daemon/PID 验证和 git diff 清理模式。
