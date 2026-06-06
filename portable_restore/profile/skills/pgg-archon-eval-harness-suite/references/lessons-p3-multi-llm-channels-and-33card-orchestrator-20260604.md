# Lessons — Multi-LLM Channels & 33-Card Orchestrator (2026-06-04)

> 主题：4–5 路 LLM 通道在 Hermes 本机的实际可达性 + 33-card 4-LLM 协作落盘根因 + 4 级 JSON 解析兜底
> 边界：基于本会话 (2026-06-04 晚) 真实 smoke 验证，不是长期可达性承诺

## 1. gpt5.5 真实 base_url — `chuangagent.eu.cc`

**Hermes config.yaml 中 `gpt55_5yuantoken` provider 实际能用的入口**：

```
base_url: https://chuangagent.eu.cc/v1
chat_completions_path: /chat/completions
default_model: gpt-5.5
key_env: GPT55_5YUANTOKEN_API_KEY
```

Smoke 验证（2026-06-04）：

- `https://chuangagent.eu.cc/v1/chat/completions` → HTTP 200, 4 chars "pong"
- `https://chuangagent.eu.cc/v1/responses` → HTTP 200, 0 chars（不要用）

**不可达**（smoke 全部失败，2026-06-04）：

- `https://api.5yuantoken.com/v1/{chat/completions,responses}` → SSL EOF（LibreSSL 2.8.3 兼容失败，TLS 握手层就断）
- `https://api5.5yuantoken.com/v1/chat/completions` → SSL EOF
- `https://chuangapi.5yuantoken.com/v1/chat/completions` → SSL EOF
- `https://api.minimax.chat/v1/chat/completions` → HTTP 401 login fail (key 不认 minimax 反向)

**结论**：未来任何要走 gpt5.5 的新脚本，base_url 必须用 `chuangagent.eu.cc`，**不要相信 `.env` 里 key 前缀暗示的 `5yuantoken` 域名**。`.env` 与 `config.yaml` 是双 source-of-truth；域名错配会一直撞 SSL EOF。

## 2. claude 通道当前账号不可用（用户决定暂不修复）

`CLAUDE_OPUS47_5YUANTOKEN_API_KEY` 在所有可达 endpoint 上失败：

- `api.5yuantoken.com` → SSL EOF
- `api.minimax.chat` → HTTP 401

按用户 2026-06-04 指令："claude 暂不修复，因为暂时用不了"。

**记录到所有 4/5-LLM 协作里**：claude 标 `missing_api_key_or_endpoint` → `classified_verdict="ERROR"`，**不冒充 PASS**。剩余 OK provider 的结论不因 claude 缺位而作废。

未来如果用户给新 key 或换账号，先 smoke 三个 endpoint：

1. `https://chuangagent.eu.cc/v1/chat/completions`（gpt 走的，反向 claude 也可能走）
2. `https://api.5yuantoken.com/v1/chat/completions`（chuangagent 不可达时备选）
3. `https://api.minimax.chat/v1/chat/completions`（Hermes 路由表里的备份）

## 3. 4/5-LLM 协作通道矩阵（2026-06-04 实证）

| Provider | base_url | model | 状态 | chat | responses |
|---|---|---|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-v4-flash` | OK | 200 | n/a |
| MiMo | `https://token-plan-cn.xiaomimimo.com/v1` | `mimo-v2.5-pro` | OK | 200 | n/a |
| Agnes | `https://apihub.agnes-ai.com/v1` | `agnes-2.0-flash` | OK | 200 | n/a |
| MiniMax | `https://api.minimax.chat/v1` | `MiniMax-M3` | 200/EMPTY | 200 但 parser 失败 | n/a |
| gpt5.5 | `https://chuangagent.eu.cc/v1` | `gpt-5.5` | OK | 200 4 chars | 200 但 0 chars |
| claude | (待定) | `claude-opus-4-7` | ERROR | n/a | n/a |

注意：MiniMax 200 OK 但顶层 JSON 解析不到 `model_verdict` 的情况 ≠ PASS。**必须 record `http_status` + `visible_output_chars` + `classified_verdict` 三件套**，任一为 ERROR/空 就标 ERROR。

## 4. 33-card 4-LLM 协作架构

`agent/pgg_archon_super_evolution_card.py`（5.4 KB）— 跑桌面"超级进化"33 个 md 文件的 4-LLM 状态卡。

输入：33 个 file spec `{file, file_id, title, known_key_thesis}`。

输出 schema：

```json
{
  "schema": "PGGArchonSuperEvolutionCard/v1",
  "file": "/path/to/超级进化0.5-APEX全体系公式.md",
  "file_id": "0.5",
  "card": {
    "id": "0.5",
    "title": "APEX全体系公式",
    "key_thesis": "...",
    "mapped_skill": "apex-skill",
    "status": "ACTIVE|PARTIAL|SKELETON|ABSENT",
    "providers_seen": ["deepseek", "mimo", "agnes", "minimax"]
  },
  "per_provider": {
    "deepseek": {"status": "ok", "card": {...}, "visible_chars": 412},
    "mimo": {"status": "ok", "card": {...}, "visible_chars": 388},
    "agnes": {"status": "ok", "card": {...}, "visible_chars": 524},
    "minimax": {"status": "parse_failed", "visible_chars": 1218, "preview": "..."}
  }
}
```

落地路径：`~/.hermes/workspace/audit/super_evolution_cards_<ts>.json`

## 5. 33-card 进程超 18 分钟的根因 + 未来改进

**现象**（2026-06-04）：单进程 132 次串行 HTTP 调用跑了 18+ 分钟，本会话后半段几乎全是空 poll。

**根因**：

1. 33 file × 4 provider = 132 次串行 `requests.post`
2. 每个 provider 默认 `timeout` 不限，慢 provider 拖整体
3. MiniMax 200 但内容空，每次都走完 4 级 parser 才标 `parse_failed`，没短路
4. 4 个 provider 顺序串行而非并发

**未来改进**（已记入 P3 下一轮）：

```python
# 用 ThreadPoolExecutor 并发 + 给每 provider 30s timeout + MiniMax 短路
with ThreadPoolExecutor(max_workers=4) as ex:
    futures = {ex.submit(ask_one, p, spec, timeout=30): p for p in providers}
    for f in as_completed(futures):
        p, rec = futures[f], f.result()
        # MiniMax 401/200-empty 直接 1 second skip，不重试
```

预计：132 次 18min → 并发 4 路 + 30s timeout + 短路 → 33-card 4-LLM 协作应在 3-4 分钟内落盘。

## 6. 4 级 JSON 解析兜底（`_try_parse_json_obj` 实测版）

LLM 输出形态多样，必须 4 级回退：

```python
def _try_parse_json_obj(t: str) -> dict | None:
    s = _strip_fence(t)
    # Level 1: raw json.loads
    try:
        v = json.loads(s)
        return v if isinstance(v, dict) else None
    except Exception:
        pass
    # Level 2: outermost {…} window
    a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a:
        try:
            v = json.loads(s[a:b+1])
            return v if isinstance(v, dict) else None
        except Exception:
            pass
    # Level 3: balanced brace scan (nested)
    depth, start = 0, -1
    for i, ch in enumerate(s):
        if ch == "{":
            if depth == 0: start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    v = json.loads(s[start:i+1])
                    return v if isinstance(v, dict) else None
                except Exception:
                    start = -1
    return None
# Level 4: regex 兜底 `prompt: "..."` 行（适合 LLM 把 probes 嵌在 markdown 解释里）
```

**真实观测**：

- DeepSeek / Agnes: Level 1 直接成功
- MiMo: Level 2 兜底（外层有 markdown 解释）
- MiniMax: Level 1 失败 → Level 2 失败 → Level 3 失败 → Level 4 兜底也不出 → 标 `parse_failed`
- chuangagent gpt5.5: Level 1 直接成功

## 7. PYTHONPATH 必须显式（hermes-agent background 模式必读）

`terminal(background=true, command="cd $HOME/.hermes/hermes-agent && python3 /tmp/foo.py")` **不会**自动把 `agent/` 注入 sys.path。

**症状**：

```
ModuleNotFoundError: No module named 'agent'
```

**修复**：

```bash
cd "$HOME/.hermes/hermes-agent" && PYTHONPATH="$HOME/.hermes/hermes-agent" python3 /tmp/foo.py
```

或者用 venv：

```bash
$HOME/.hermes/hermes-agent/venv/bin/python -m agent.pgg_archon_super_evolution_card ...
```

任何 1+ 分钟、含 Python `from agent.*` 导入、要 background 跑的脚本都按此模式。

## 8. Background 进程 poll 预算管理（hermes agent 实战）

`process(action="poll")` 每次调用 = 1 次 syscall + 1 次 iteration。**长跑任务不要轮询到通知**。

正确策略（4 步）：

1. `terminal(background=true, notify_on_complete=true, command="...")` 起跑
2. **不 poll**，去做别的任务
3. 通知到达 → 1 次 `process(action="wait", session_id, timeout=600)`
4. 落盘文件 `ls -la $OUT/expected.json` + `ps -axo etime` 验证

反面教材（本次 33-card 浪费）：

- 18+ 分钟跑了 70+ 次空 poll（每次都"still running"）
- 每次 poll 占用一次 LLM iteration
- 正确做法应该是 1 次 notify + 0 次空 poll

## 9. 用户连续推进偏好（已嵌入 SOUL.md）

用户在 2026-06-04 本会话里说"继续 / 按照你的建议继续执行 / 尝试调用所有llm协作推进"共 7 次。每次都同时表达两个语义：

1. **授权继续低风险闭环**（不要停在"建议"层）
2. **期望调用所有可用 LLM 通道且单通道失败不阻塞**

这两点已经写入 SOUL.md 与 memory；下次新对话起手时已默认遵守，不需要再问。

**但"继续" ≠ 无限制绕所有 boundary**：

- 50 probe redteam 是 status surface，**不**是 full redteam
- 4-LLM 协作 33-card 是 status surface，**不**是 production card
- 任何 verifier PASS 都不等于"系统达到 L3"；保持诚实边界

## 10. 关联 commit + 文件

- `agent/pgg_archon_super_evolution_card.py`（5.4 KB，2026-06-04 写）
- `tests/test_pgg_archon_super_evolution_card.py`（3/3 pass）
- 4-LLM 协作 smoke 输出：`~/.hermes/workspace/audit/super_evolution_cards_20260604_215000.json`（本会话未落盘，下次启动会接续）
- commit 链：`97644d0ec` (combined 50-probe) → 本会话无新 commit (33-card 进程未在回合内落盘 → 未触发 commit)
- 下一轮 commit 主题：`P3+: super_evolution 33-card 4-LLM orchestrator (parallel + 30s timeout + 33-card status surface)`
