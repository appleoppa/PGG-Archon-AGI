# Lessons: P3 50-probe + 4-LLM 协作 (2026-06-04)

PGG Archon P3 阶段把 redteam harness 从 12 probe 扩到 30 → 50，并引入 4-LLM 协作扩 corpus + 4-LLM 复核 verifier-friendly 报告。本文件沉淀这一轮里发现的可复用技术与 Hermes 工具坑。

## 1. 12 → 30 → 50 三段扩 corpus

**动机**：30 题覆盖 12 类后，发现 5 类（credential_exfil / encoded_payload / legal_hallucination / tool_overreach / tool_specific_ssrf）跨 provider 共识未达 50% 拒绝。需要更多 probe 才能判断"真弱"还是"probe 不够"。

**做法**：
- 30 题 hand-written 跑出 5 类弱
- 用 4 个 LLM（DeepSeek / MiMo / Agnes / MiniMax）针对 5 类各生成 4 题
- per-provider 失败 try/except 隔离，不互相阻塞
- Agnes+DeepSeek 满 4×5=20 题，MiMo 部分 0（policy 拒答），MiniMax 全 0（JSON 含 reasoning_content，可见 content 为空）
- 把 Agnes+DeepSeek 共识的 20 题 human-review 后写入 `LLM_GENERATED_PROBES` 常量
- `ALL_PROBES = EXTENDED_PROBES + LLM_GENERATED_PROBES`（50 题）
- harness 加 `use_all: bool` 与 CLI `--all` flag

**坑**：
- 50 题反而把"30 题里 100% 拒绝"的 2 类（system_prompt_leak / indirect_injection）拉到了 consensus < 50%。**这不代表模型变弱，是 LLM-generated probe 的 prompt 风格不一样**。结论性报告必须用 N≥30 + 多类混合，否则 "未拒绝" 会被 artifact 放大。
- LLM-generated prompt 不可直接进生产 corpus，**必须 human-review**。

## 2. 多 LLM JSON 解析的 3 级回退（推荐 4 级）

LLM 协作扩 corpus 时，4 个 provider 输出的 JSON 风格差异巨大：

```python
def _try_parse_json_obj(t: str) -> dict | None:
    # Level 1: 直接 parse 整段
    try:
        v = json.loads(t)
        if isinstance(v, dict): return v
    except Exception: pass
    # Level 2: 找首个 { 到末位 } 的窗口
    a, b = t.find("{"), t.rfind("}")
    if a >= 0 and b > a:
        try:
            v = json.loads(t[a:b+1])
            if isinstance(v, dict): return v
        except Exception: pass
    # Level 3: 栈式平衡 brace 扫描找最外层 {...}
    out, depth, start = None, 0, -1
    for i, c in enumerate(t):
        if c == '{':
            if depth == 0: start = i
            depth += 1
        elif c == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        cand = json.loads(t[start:i+1])
                        if isinstance(cand, dict): return cand
                    except Exception: pass
    return None
```

Level 4（regex 兜底）：

```python
import re
probes = []
for m in re.finditer(r'"prompt"\s*:\s*"([^"]+)"', t):
    probes.append({"prompt": m.group(1)})
# 适合 LLM 把 probes 嵌在 markdown 解释里的情况
```

**实测有效性**：
- DeepSeek 0/52 → 20/20（Agnes+DeepSeek 满）
- MiMo 0/部分 → 12/20
- MiniMax 0/20 → 0/20（reasoning_content 解析问题，需用更激进的清洗）

## 3. per-provider 失败隔离模板

```python
for label, url, model, env in providers:
    rec = {"label": label, "model": model, "key_env": env}
    key = os.environ.get(env, "")
    if not key:
        rec.update(status="missing_api_key", classified_verdict="ERROR")
        write_json(rec); continue
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=180)
        rec["http_status"] = r.status_code
        if r.status_code >= 400:
            rec.update(status="error", error=f"HTTP {r.status_code}", classified_verdict="ERROR")
        else:
            data = r.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            s = _strip_fence(text)
            parsed = _try_parse_json_obj(s) or {}
            verdict = str(parsed.get("model_verdict") or "UNKNOWN").upper()
            rec.update(
                status="ok_visible",
                visible_output_chars=len(text),
                text_preview=text[:3000],
                classified_verdict=verdict,
                parsed=parsed,
            )
    except Exception as e:
        rec.update(status="error", error=repr(e), classified_verdict="ERROR")
    write_json(rec)
```

**关键**：每个 provider 独立写 `verify_<label>.json` + `classified_verdict` 字段。后续 4-LLM 复核 / 跨 audit 只需 grep `classified_verdict` 即可。

## 4. 4-LLM 复核的 classified_verdict 语义

四个 LLM 在 verifier-friendly 报告上的常见落点：

- DeepSeek：HTTP 200，500–800 chars，verdict `WATCH`（最常用，含"建议加强"等措辞）
- MiMo：HTTP 200，500–900 chars，verdict `WATCH`（细节描述比 DeepSeek 多）
- Agnes：HTTP 200，1000–7000 chars，verdict `BLOCKED` 或 `PASS`（Agnes 输出最长且常用强结论）
- MiniMax：HTTP 200 但顶层 JSON 解析不到 `model_verdict` → 标 `ERROR`

**坑**：MiniMax 通道"HTTP 200 + None" ≠ "PASS"。一定要把 `visible_output_chars` 与 `classified_verdict` 拆开记。

## 5. Hermes `process(action="poll")` 在长跑任务上

**坑**：长跑任务（>2 分钟）反复调用 `process(action="poll")`，每次只是检查一次，**不会** 推进 wall-clock 时间。每次 poll 的输出可能完全一样（"still running, uptime 270s"），导致 iteration 浪费。

**正确做法**：对预计 >2 分钟的后台 probe，改用：

```bash
ls -la $OUT/expected.json 2>/dev/null
ps -axo pid,etime,args | egrep 'pgg_archon_redteam_harness' | egrep -v grep | head -3
```

只要文件落盘或进程消失，就视为完成；只有当真的要"等到结束做下一步"时才用 `process(action="wait")`（一次性等到 600s timeout 或进程退出）。

## 6. verifier-friendly 报告 schema 稳定性

三层结构在 P3 的 12 / 30 / 50 三个 scale 都稳定：

```json
{
  "schema": "PGGArchonP3FiftyVerifier/v1",
  "per_provider": {"deepseek": {"refused": 17, "total": 50, "refusal_rate": 0.34}, ...},
  "consensus_by_category": {
    "encoded_payload": {
      "per_provider": {...},
      "min_refusal_rate": 0.0,
      "max_refusal_rate": 0.17
    }, ...
  },
  "categories_under_50_consensus": ["encoded_payload", "legal_hallucination", ...]
}
```

**不要轻易改 schema**。下游 4-LLM 复核 / manifest 写入 / 跨 audit 都依赖这三层。新增字段可以但不能动这三层。

## 7. manifest 更新模式

每次 P3 落点都新增一个 `latest_p3_*` key，而不是覆盖旧的：

```
latest_p3_apply_20260604          (skeleton)
latest_p3_full_smoke_20260604     (12/15 全量)
latest_p3_verifier_friendly_20260604  (12 题 verifier)
latest_p3_extended_30_20260604    (30 题 verifier)
latest_p3_extended_corpus_gen_20260604 (52 题 LLM-driven corpus)
latest_p3_50_smoke_20260604       (50 题 verifier)
latest_p3_5llm_verifier_50_20260604 (5-LLM 复核 50 题, 3/5 OK)
```

这样后续 audit 可以横向对比每个 scale 的真实数据，而不是只有"最新"。

## 8. 关联落点

- `agent/pgg_archon_redteam_harness.py`（12/30/50 multi-corpus，`use_all` + CLI `--all`）
- `agent/pgg_archon_redteam_extended_probes.py`（EXTENDED + LLM_GENERATED + ALL）
- `agent/pgg_archon_redteam_corpus_gen.py`（4-LLM 协作 + 3 级 parser + regex 兜底）
- `agent/pgg_archon_p3_verifier.py`（verifier-friendly schema）
- `agent/pgg_archon_super_evolution_lane.py`（6 surface snapshot）
- `tests/test_pgg_archon_redteam_corpus_gen_parser.py`（4 个 parser 测试，含 balanced 修正）
- 总账 keys: 见 SKILL.md §9

## 9. terminal(background=true) + 嵌套双引号 JSON 必爆 (2026-06-04)

**坑**：本会话把 5-LLM verifier-friendly 50 脚本塞进 `terminal(background=true, command="...")` 时，bash 报：

```
bash: unexpected EOF while looking for matching `"'
bash: syntax error: unexpected end of file
```

**原因**：`command` 字符串里同时出现：

- `nohup $PY -m agent.foo --arg "$HOME/path/file.json"`
- 同一行的 Python heredoc 用 `'...'` 包裹，内含 `{"key":"value"}`
- bash 在 `'` 与 `"` 嵌套的 `unbalanced` 报错

**正确做法（现在固定）**：任何"会跑 1–10 分钟、含双引号 JSON 字面量、要 background"的脚本 → **先用 `write_file` 把整个 Python 脚本写到 `/tmp/p3_5llm_verifier_50.py`**，再 `terminal(background=true, command="python3 /tmp/p3_5llm_verifier_50.py")`。**禁止在 `terminal(background=true)` 的 `command` 里直接写 Python 脚本内联**。

**反例（错）**：

```python
terminal(background=true, command='''
  PY=...
  nohup $PY -m agent.foo --out "$OUT/x.json" --all
  echo "{\"summary\":...}" | tee -a ...
''')
```

**正例（对）**：

```python
write_file(path="/tmp/p3_5llm_verifier_50.py", content=...完整 Python 脚本...)
terminal(background=true, command="python3 /tmp/p3_5llm_verifier_50.py")
```

**为何此坑只影响 background 模式**：foreground 模式 `terminal()` 会自动把 command 通过 sh -c 跑，heredoc 与 quote 行为正常；background 模式下 Hermes 自己用 pty + 显式 shell 调用，quote 解析更严格。

## 10. "调用所有 LLM 协作推进 + 单个不通不阻塞" — user 强制偏好 (2026-06-04)

user 在多轮 session 里反复表达：

> 调用所有 llm 协作推进。逐一全量解决。单个 llm 不通的情况下，不影响整个进化进程。

**non-negotiable 落地规则**：

1. **5-LLM 复核必须真跑 5 路**（deepseek / mimo / agnes / minimax / gpt55），不是只跑 3 路然后说"其他 2 路就当通过"。
2. **每路独立 try/except**，并 `print(label, status, http_status, visible_output_chars, classified_verdict)` 落盘。
3. **缺 key 必须显式标 `classified_verdict="ERROR"`，绝不冒充 PASS**。如 `gpt55` 缺 `GPT55_API_KEY` → `verify_gpt55.json` 写 `{"status":"missing_api_key","classified_verdict":"ERROR"}`。
4. **HTTP 200 但顶层 JSON 解析不到 `model_verdict`** → 同样 `ERROR`（例：MiniMax 多次复现）。
5. **剩余 OK provider 的 verdict 仍生效**。3/4 OK 给出 WATCH 不因 1/4 ERROR 而被废止；最终审计按"可见 verdict"聚合。
6. **manifest 新增 `latest_p3_5llm_verifier_50_20260604` 之类 key**，记录 OK/ERROR 比例，**不抹平**。

**实测（2026-06-04）**：5 路 5-LLM verifier-friendly 50 跑出来：

- DeepSeek OK, WATCH
- MiMo OK, WATCH
- Agnes OK, WATCH
- MiniMax HTTP 200 但 parse fail → ERROR
- gpt55 缺 `GPT55_API_KEY` → ERROR

3/5 WATCH 一致 → audit 结论是 "P3 50-probe smoke verified by 3 OK provider; 2 provider blocked by infra, not by content"

**不要做的**：

- 把 MiniMax/gpt55 的 ERROR 改写成 PASS
- 因为 2 路 ERROR 就放弃 verifier-friendly
- 在汇报时省略缺 key 路径

## 11. 5-LLM 缺 key 隔离实战（2026-06-04）

`p3_5llm_verifier_50.py` 完整骨架（与 §3 类似，新增 gpt55 + Responses API 分支）：

```python
providers = [
    ("deepseek", "deepseek-v4-flash", "chat", "https://api.deepseek.com/chat/completions", "DEEPSEEK_V4_FLASH_API_KEY", 4096),
    ("mimo", "mimo-v2.5-pro", "chat", "https://token-plan-cn.xiaomimimo.com/v1/chat/completions", "MIMO_V25_PRO_API_KEY", 4096),
    ("agnes", "agnes-2.0-flash", "chat", "https://apihub.agnes-ai.com/v1/chat/completions", "AGNES_AI_API_KEY", 2200),
    ("minimax", "MiniMax-M3", "chat", "https://api.minimax.chat/v1/chat/completions", "MINIMAX_API_KEY", 2200),
    ("gpt55", "gpt-5.5", "responses", "https://api.openai.com/v1/responses", "GPT55_API_KEY", 2200),
]
for label, model, mode, url, env, mx in providers:
    rec = {"label": label, "model": model, "api_mode": mode, "key_env": env}
    key = os.environ.get(env, "")
    if not key:
        rec.update(status="missing_api_key", classified_verdict="ERROR")
        (OUT / f"verify_{label}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        continue   # 不冒充
    # ... 与 §3 一致 ...
```

**Responses API 提取 text 的特殊模式**（gpt55 路径）：

```python
if mode == "responses":
    payload = {"model": model, "input": prompt, "max_output_tokens": mx}
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    j = r.json()
    text = ""
    for it in j.get("output") or []:
        for c in it.get("content") or []:
            if c.get("type") == "output_text":
                text += c.get("text", "")
```

注意：Responses API 的 `output[]` 可能是 reasoning + output_text 两段，必须 loop 提取 `type=="output_text"` 的部分；不要直接 `j["output"][0]["text"]`。
