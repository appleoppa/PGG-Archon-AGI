---
name: quantum-channel-router
description: 量子通道路由 — Rust 实现的多模型智能路由引擎，支持分级路由、健康检查、轨迹缓存
version: 1.2.0
author: Hermes Agent
trigger_conditions:
  - 用户下达任何涉及多步骤、复杂推理或法律分析的任务
  - 用户下达代码开发、分析、研究、写作或办案任务
  - 任何非纯聊天的实质性任务（任务涉及执行、生成、分析、研究）
  - 当当前模型能力不足或用户对输出质量不满时考虑切换模型
metadata:
  hermes:
    tags: [router, routing, llm, trajectory, cache, quantum, rust]
---

# 量子通道路由 (Quantum Channel Router)

## 架构概览

Rust 实现的 LLM 多模型路由引擎。核心路由由 Hermes 主脑决策，量子路由器作为多任务配套工具提供分级路由、健康监控和轨迹缓存。

**安装路径**: `~/.hermes/quantum-router/`
**CLI 命令**: `qr`

## ⚠️ 加载此 skill 时的强制指令

当你（Hermes Agent）加载这个 skill 时，必须遵守以下规则。

### 超级进化1吸收规则：河图洛书 LLM 路由

来源：`/Users/appleoppa/Desktop/进化文件/超级进化1-河图洛书llm路由.md`。

该文件的核心要求已经吸收为以下执行规则：

1. 用户提供多个 LLM key 后，Hermes 不等待用户逐个指定模型，而是主动用 `qr route` 自行分配模型。
2. **新架构（A=主脑/审计，B=办案主流程，C=编程，D=杂活）**：
   - A = GPT-5.5：主脑统筹 / 最终审计 / 复杂综合判断
   - B = DeepSeek：办案主流程（法律检索/合同审查/诉讼材料/案例分析/文书生成），完成后由 A(GPT) 审计
   - C = Claude：编程（代码开发/调试/重构/测试/架构实现），完成后由 A(GPT) 审计
   - D = MiniMax：杂活（彩票查询/天气/翻译/摘要/格式化/普通查询），低成本快速通道
   - 当 A 级不可用时，按 `qr route` 的 live health 自动降级，不虚报 A 级参与。
3. 复杂进化任务必须用“河图洛书五段链”组织：主脑统筹 → 反证审错 → 修复落地 → 旁证压缩 → 主脑收束。
4. 每次进化/学习任务中，量子路由不只是通路检查，必须产生实际增量：暴露短板、选择学习资源、指导修复或参与仲裁之一。
5. 若某一层模型 down，记录降级事实和剩余可用模型；不能把本地单模型推演说成多模型反证。
6. 新增模型或 key 后，先 `qr config` / `qr health` / 分类样例路由三重核验，再宣称已接入。

### 入口规则

**在接受用户任务后、开始执行前，先调用 `qr route "<任务描述>"` 决定使用哪个 LLM。** 这条绝对不能跳过。2026-05-22 因跳过被用户指出，已记入违规记录。

具体流程：
1. 解析用户任务 → 提取任务关键词
2. 调用 `terminal("qr route '<任务描述>'")` 获取 JSON 输出
3. 解析 JSON 中的 `selected`（provider 名）和 `tier`（分级）
4. **如果返回 cache 结果**（`source: "cache"`），直接复用缓存轨迹
5. **否则**按路由结果使用对应 provider 执行任务
6. 成功后调用 `qr cache set <fingerprint> "<trajectory_json>"` 存入轨迹

**不使用此 skill 时 → 用默认 LLM（当前 default profile 的模型，通常是 gpt-5.5）**

### 选型冲突规则

当 `qr route` 返回的 provider 与当前会话 model 不一致时，**不强制切换 provider**。
qr 的 health check 决策与 Hermes 实际路由是两条独立路径。qr 用作辅助决策参考：

| 场景 | 处理策略 |
|------|---------|
| qr 返回其他可用 provider | 将 qr 结果作为**建议**记录，本次继续使用当前会话 model |
| qr 返回同 provider 同 model | 继续使用当前会话，记录"路由匹配" |
| qr 全部 offline | 不更改选型，继续使用当前会话 model |

### 进化循环中的使用

在开智进化循环（manual-evolution-loop）中，`qr route` 在公式审错前执行。
当进行 APEX 三顺序代入（21354/12534/14325）时：

- **每遍必须产生**：代入点、触发判断、暴露信号、本遍观察
- **最少遍数**：每个顺序至少 **3遍**（用户确认的标准，低于此数会被退回）

## Web UI Profile 关系说明

量子路由是**我（Hermes Agent）自动调用的决策引擎**，与 Web UI 的手动 Profile 选择是两条独立路线：

| 路线 | 谁决定 | 使用场景 |
|------|--------|---------|
| Web UI Profile | 你手动切换到 gpt55 Profile | 你想固定用某个模型聊天 |
| 量子路由 `qr route` | 我自动按任务分类选 | 你说任务，我分配合适的 LLM |

**互不干扰**：Web UI 选了什么 Profile 不影响我调用 `qr route` 的能力。我可以在使用 gpt55 Profile 的 Web UI 会话中，仍然通过 `qr route` 为 subagent 选择其他 LLM。

## 超级进化10吸收：超级路由执行边界

来源：`/Users/appleoppa/Desktop/进化文件/超级进化10-超级路由.md`。

吸收为以下新增规则：

1. `qr` 是 Hermes 主脑的多模型配套工具，不替代主脑裁决；核心主路由仍由当前 Hermes 会话负责。
2. Full Tool-Call Trajectory 表示“任务前全局轨迹 + 并行点 + 验证点 + 回退路径”，不是跳过验证、不是无条件一次性盲跑。
3. 健康检查和降级必须写入报告：A/C down 时不能虚报 GPT/Claude 参与。
4. 轨迹缓存分两层：
   - `qr cache`：路由决策/任务轨迹缓存；
   - `trace_hashpool`：执行轨迹过滤、哈希去重、技能候选/失败反例。
5. 成功轨迹转正式技能前必须经过验证门禁；失败轨迹必须进入反例库。
6. token调控当前主要由 APEX token hygiene 规则承担，`qr` 本体只提供模型context_limit和路由参考，不得宣称已完成细粒度token预算器。

当前状态：Rust CLI、5-provider配置、health/route/cache入口已存在；但真实cache条目积累、HashPool桥接、多Agent线程池级调度和全自动技能化仍是未完成项。

## 超级进化11吸收：天工四核编排矩阵

来源：`/Users/appleoppa/Desktop/进化文件/超级进化11-天工技能.md`。

吸收为以下执行规则：

1. 量子路由与四核编排协作，但量子路由不替代主脑裁决；它只负责任务层分配。
2. 天工技能的核心是“认知→规划→执行→验证→沉淀→进化”的治理矩阵，不是虚构外部 GitHub 项目已被底层吞噬。
3. evolver/autoresearch/openhands/superpowers 四核应映射到可执行产物：缺陷表、来源清单、命令输出、验收报告。
4. 外部开源只读采集后才能进入候选技能/基因门禁，不可直接说“已自动学会并补全一切能力”。
5. 所有核心源码改造仍需明确授权、回滚与审计；天工技能只是一层编排与门禁，不是底层替换。

## 超级进化12吸收：吞噬式自进化只读采集边界

来源：`/Users/appleoppa/Desktop/进化文件/超级进化12-吞噬自进化.md`。

吸收为以下执行规则：

1. 外部开源项目必须先只读采集元数据、README、license 和可见能力信号。
2. 只读采集后的结果只进入候选技能/候选基因，不可直接复制源码，不可宣称底层吞噬完成。
3. Agentic RL / 认知强化学习只作为评估和训练框架；没有真实数据、样本和验证前不能写完成。
4. 量子路由与吞噬式学习协作，但仍只负责任务层路由，不接管核心源码。
5. 任何“自动改 Hermes/Claw 核心”的想法在当前阶段明确不执行，只作为高风险未来议题。
6. 评估中心用于评分、训练、预测和审计，但当前模型仍是弱基线，不当主裁判。

## 超级进化13吸收：APEX ΔE 神技能边界

来源：`/Users/appleoppa/Desktop/进化文件/超级进化13-神技能开启.md`。

吸收为以下规则：

1. `APEX_ΔE = αΨ + βΩ + λΦ + ∇Θ + Evol_code` 只能作为变量拆解与治理公式，不是完成事实。
2. GPT/Claude 双核必须以 live health 或真实调用证据为准；当前 A/C down 时必须降级记录，不虚报参与。
3. 全网知识溯源只做只读 scout、来源清单、候选技能/基因，不自动实时吞噬。
4. 去冗余只能先做审计报告，不自动删除文件、技能、配置或记忆。
5. Go/C/Rust 底层重构、Claw/Hermes核心改造、AGI终极闭环均为高风险挂起项，需单独授权。

## 超级进化14吸收：ΔG负势工具分支门禁

来源：`/Users/appleoppa/Desktop/进化文件/超级进化14-ΔG演化范式叠加.md`。

吸收为以下执行规则：

1. `EV = BV + AV, sum(C_all) <= SV` 只作为工具分支收益-成本-风险门禁，不是 AGI/ZeroLang 已实现事实。
2. 每个高成本工具分支执行前，应估算任务必要性 BV、动作增益 AV、资源成本 C_all、预算上界 SV 和风险 risk。
3. `net_potential = EV - C_all - risk`；当 net_potential < 0、超预算或风险过高时，停止该分支或进入复核。
4. 原文 `HarmRate = 34%` 作为退化噪声警戒值，不当作本地实测幻觉率。
5. 已落地 CLI sidecar：`/Users/appleoppa/.hermes/scripts/super_evolution14_delta_g_gate.py`；它不改 Hermes/Claw 核心。
6. 除核心改造外，第14已落地 `ZeroLang-lite/0.1`、`ZLMessage` 自语言协议、`LocalA2ACluster` 本地多Agent协作模拟器：`/Users/appleoppa/.hermes/scripts/super_evolution14_zerolang_a2a.py`。这是本地可验证 sidecar，不等于真实AGI或全球网络集群。



当前有效标准以 `qr route` / `qr tier` 实测输出为准：

| 分级 | 用途 | 模型 | 说明 |
|------|------|------|------|
| **A** 🟢 | 最高主脑/综合裁判 | gpt-5.5 | 复杂系统设计、审计、最终裁决、长期规划 |
| **B** 🔵 | 高端推理/快速分析 | deepseek-v4-flash | 复杂推理、分析、逻辑、研究、方案比较 |
| **C** 🟣 | 深度代码开发 | claude-opus-4-6 | 代码编写、重构、调试、工程实现 |
| **D** ⚪ | 日常通道（所有杂活） | astron-code-latest | 简单任务、格式化、摘要、翻译、草稿、批量执行、默认兜底 |
| **E** 已移除 | — | — | 已删除 |

自动分类逻辑（关键词匹配）：
- **C-代码**: 代码/code/debug/compile/重构/refactor/Rust/python/java/写/编程/程序/implement/开发/函数/function/算法/algorithm
- **B-推理**: 推理/reason/分析/复杂/复杂推理/数学/math/逻辑/logic/研究/论证/策略/plan/设计/架构
- **D/E-廉价**: 简单/simple/翻译/format/格式化/draft/草稿/摘要/summary/列举/列出来
- **默认**: 由 `qr route` 的 live health 和任务分类决定；不要凭旧文档假定 A=MiniMax。

注意：如果本技能其他段落或旧记忆仍写 A=MiniMax，以本节和 live `qr route` 输出为准。

## CLI 命令

```bash
# 健康检查所有 LLM
qr health

# 按任务描述自动路由
qr route "写一个Rust HTTP服务器"

# 指定分级
qr tier C

# 轨迹缓存
qr cache set <fingerprint> "<trajectory_json>"
qr cache get <fingerprint>
qr cache stats

# 查看路由配置
qr config
```

## Agent 工作流集成（每次任务自动执行）

```python
from hermes_tools import terminal
import json

# 1. 路由决策
result = terminal(f"qr route '{task_description}'")
route = json.loads(result["output"])

if route.get("source") == "cache":
    # 缓存命中 → 直接复用轨迹
    trajectory = route["cached_trajectory"]
    # ...复用逻辑...
else:
    selected_provider = route["selected"]
    model = route["model"]
    tier = route["tier"]
    print(f"量子路由: {tier}级 → {selected_provider} ({model})")
    # ...按路由结果执行任务...

# 2. 成功执行后缓存
fp = terminal("python3 -c \"import hashlib; print(hashlib.sha256((task+tier).encode()).hexdigest())\"")
terminal(f"qr cache set {fp.strip()} '{json.dumps(trajectory)}'")
```

## 缓存架构

轨迹指纹 = SHA256(task + tier)

缓存位置：`~/.hermes/quantum-router/cache/<fingerprint>.json`

缓存条目包含：fingerprint, trajectory JSON, created timestamp, hit_count

## 核心公式

```
ΔG = (C_total · Λ_gene · Ω_entropy · τ_traj) / (H_info · t)
```

**τ_traj** = 完整轨迹生成效率系数，代表 Agent 一次性任务闭环能力。

## 故障排错

### 健康检查全报 auth_error（即使 Hermes 正常使用）

**根因**：Hermes profile 机制会改写 `$HOME` 环境变量（如 `/Users/appleoppa/.hermes/profiles/deepseek-v4/home/`），导致 qr 的 `load_env_keys()` 读取 `$HOME/.hermes/.env` 时路径不存在，拿不到 API key → 全报 auth_error。

**修复**：2026-05-22 已修改 `src/health.rs`，同时尝试 `$HOME` 和 `/Users/$USER` 两个路径读取 `.env`，自动去重。需重新编译并覆盖二进制：
```bash
cd ~/.hermes/quantum-router && cargo build --release
cp target/release/qr ~/.cargo/bin/qr
```

### MiniMax A-tier 持续 not_supported（2026-05-23 修复）

**现象**：qr health 对 MiniMax 始终返回 `not_supported`（已修复，且 MiniMax 已替换为 讯飞星火 astron-code-latest）。

**根因**：MiniMax 的 base_url 配的是 anthropic-compatible 端点 `https://api.minimaxi.com/anthropic`，这个端点**没有 `/models` 接口**。qr 的健康检查用 `GET {base_url}/models` → 404 → `not_supported`。

**修复**：`src/health.rs` 中对 MiniMax provider 改用 `POST https://api.minimaxi.com/v1/chat/completions` 发最小请求（`max_tokens:1`）。MiniMax 的 OpenAI-compatible 接口正常工作，anthropic 兼容接口没有 models/messages 端点。

```rust
// health.rs 中 MiniMax 专用处理
if is_minimax {
    let body = serde_json::json!({
        "model": p.model,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}]
    });
    let mm_url = "https://api.minimaxi.com/v1/chat/completions";
    req = c.post(mm_url).json(&body);
    req = req.header("Authorization", format!("Bearer {}", api_key));
}
```

**验证**：`qr health` 返回 `minimax_m27_highspeed: ok`，延迟 ~1s。`qr route "默认任务"` 返回 A-tier 选中 MiniMax，无降级。

**修复**：2026-05-23 修改 `src/health.rs`，对 MiniMax 改用 `POST https://api.minimaxi.com/v1/chat/completions`（OpenAI 兼容端点）发送最小请求 `{"model":"MiniMax-M2.7-highspeed","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}`，Authorization: Bearer。verfiy_response后标记 ok 可用。

```bash
cd ~/.hermes/quantum-router && cargo build --release
cp target/release/qr ~/.cargo/bin/qr
```

### 5yuantoken/chuangagent provider 健康检查返回 down（配置未同步优先）

**优先根因**：Hermes 主配置已把 `gpt55_5yuantoken` / `claude_opus47_5yuantoken` 的 `base_url` 更新到 `https://chuangagent.eu.cc/v1`（Claude 在 `providers` 中可能为 `https://chuangagent.eu.cc`），但 `qr` 的默认 provider 仍写在 `~/.hermes/quantum-router/src/config.rs`。如果该文件还保留旧的 `https://5yuantoken.eu.cc/v1`，`qr health` 会把 A/C 错判为 down。

**诊断**：
```bash
qr config | jq '.providers.gpt55_5yuantoken.base_url, .providers.claude_opus47_5yuantoken.base_url'
python3 - <<'PY'
from pathlib import Path
import yaml
cfg=yaml.safe_load(Path('/Users/appleoppa/.hermes/config.yaml').read_text())
for name in ['gpt55_5yuantoken','claude_opus47_5yuantoken']:
    p=cfg['providers'][name]
    print(name, p.get('base_url'), p.get('model'), p.get('key_env'))
PY
```

**修复**：同步 `~/.hermes/quantum-router/src/config.rs` 中两个 base_url 后重新编译部署：
```bash
cd ~/.hermes/quantum-router && cargo build --release && cp target/release/qr ~/.cargo/bin/qr
qr config
qr health
qr route "A/C模型参与验证"
```

**验证标准**：`qr health` 中 `gpt55_5yuantoken` 和 `claude_opus47_5yuantoken` 均为 `ok`；`qr route` 的 `all_online` 包含 A/C，且没有 A/C 降级。

**次级可能**：若 base_url 已同步仍 down，再检查供应商服务状态、key_env 与 `.env` 是否一致，以及第三方代理 `/models` 或 chat completion 接口是否临时不可用。

### MiniMax 健康检查修复（2026-05-23）

**背景**：MiniMax M2.7 API 有两个协议入口：
- `https://api.minimaxi.com/anthropic/` — Anthropic 协议（`/messages` 和 `/models` 均返回 404）
- `https://api.minimaxi.com/v1/` — OpenAI-compatible 协议（`/chat/completions` 可用）

qr 代码原使用 `GET {base_url}/models` 做健康检查，MiniMax 的 base_url 指向 anthropic 端点 → 404 → `not_supported` → A-tier 持续断链。

**修复**（2026-05-23 `src/health.rs`）：对 MiniMax 单独使用 `POST https://api.minimaxi.com/v1/chat/completions` 发送最小请求（model=MiniMax-M2.7-highspeed, max_tokens=1, messages=["hi"]）测试 API 可用性。健康检查通过后 A-tier 恢复正常。

修复验证：
```bash
qr health | jq '.[] | select(.name=="minimax_m27_highspeed") | .status'
# 修复前: "not_supported"
# 修复后: "ok" (latency ~1s)

qr route "默认任务"
# → tier=A, selected=minimax_m27_highspeed, fallback=None
```

**如再次断链**：检查 `health.rs` 中 `mm_url` 常量是否仍为 `https://api.minimaxi.com/v1/chat/completions`。MiniMax 可能更新了 API 入口。重新编译：`cd ~/.hermes/quantum-router && cargo build --release && cp target/release/qr ~/.cargo/bin/qr`。

## 降级策略

当首选 LLM 不可用时，自动降级：A→D, B→A, C→B, D→A → 扫全部可用
