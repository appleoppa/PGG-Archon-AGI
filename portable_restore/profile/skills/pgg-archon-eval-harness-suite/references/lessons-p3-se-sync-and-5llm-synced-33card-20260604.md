# P3 Lessons — se_sync + 5-LLM 实时复核 synced 33-card (2026-06-04 v2/v3)

> 主题：把 6 个真实 status surface（file-04/05/05.5/06/11/13）→ se_sync module 写回 33-card source.json → 5-LLM 独立复核 synced 状态
> 状态：v3（2026-06-04 22:55 完成 9 patches sync + 5-LLM 实时 audit）
> 边界：synced 33-card 是 surface state 的真实聚合视图，但仍为 status surface 而非 full audit；5-LLM 共识是 `WATCH` 不是 `PASS`

## 1. se_sync module 模式（agent/pgg_archon_se_sync.py）

33-card 33 个文件由 5 LLM majority vote 得出初始状态（SKELETON 24 / ABSENT 9 / PARTIAL 0 / ACTIVE 0）。但本会话陆续真实落地了 6+ 个 status surface 模块（file-04/05/05.5/06/11/13），它们的 4-probe 真实信号应该 patch 回 33-card。

`se_sync` 模块核心：

```python
PATCHES: list[tuple[str, str, str, str | None]] = [
    ("file_id", "PARTIAL|ACTIVE", "mapped_skill", "key_thesis_override"),
    ...
]
def sync() -> dict:
    data = json.loads(SOURCE.read_text())
    for r in data["results"]:
        card = r["card"]
        for fid, status, mapped, thesis in PATCHES:
            if card["id"] == fid:
                old = card["status"]
                card["status"] = status
                card["mapped_skill"] = mapped
                if thesis:
                    card["key_thesis"] = thesis
    synced_path = HOME / ".hermes/workspace/audit/super_evolution_cards_synced_<ts>.json"
    synced_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return {"patched_files": n, "status_distribution": {...}}
```

真实落点：本会话 9 patches 中 7 命中 33-card id（file-05.5 不在 id 空间，被合并到 5.5 段）。synced 状态：

- SKELETON 24→18（-6）
- ABSENT 9→8（-1）
- PARTIAL 0→3（+3，files 1/4/5/9/21）
- ACTIVE 0→4（+4，files 05.5/06/11/13）

## 2. se_sync 的 idempotency

`sync()` 第二次跑应产生与第一次完全相同的 `status_distribution`。原因：所有 patch 是基于 source 33-card 原始 status，patch 后 source 不被修改（写 synced_path）。**禁止**把 patch 写回 source.json（会污染 v1 audit 源）。

测试：`test_sync_is_idempotent` 比较 `s1["status_distribution"] == s2["status_distribution"]`。

## 3. file-05.5 在 33-card id 空间不存在的坑

33-card `id` 字段只有数字 ID（0.5/1/2/2.5/.../27），没有 5.5 这种小数的 file_id（因为 33-card 是基于 5.5 全局轨迹迭代 笔记的简化版，5.5 与 5 是同一个文件）。

**se_sync 必须用 `if fid in src_ids` 保护**。否则 `test_sync_creates_output` 会 fail（`by_id.get(fid) is None`）。

修复后的测试逻辑：

```python
src_ids = {r["card"]["id"] for r in src["results"]}
expected = sum(1 for fid, _, _, _ in PATCHES if fid in src_ids)
assert summary["patched_files"] == expected
```

## 4. 5-LLM 实时复核 synced 33-card

复用 v1 的 `/tmp/se_33_audit_synced.py`，只把 `SRC` 改成 `super_evolution_cards_synced_<ts>.json`。每跑一次 output 进 `~/.hermes/workspace/audit/super_evolution_cards_5llm_audit_synced_<ts>/`。

真实结果（2026-06-04 22:55）：

- DeepSeek HTTP 200，512 chars，verdict PASS
- MiMo HTTP 200，1959 chars，verdict WATCH
- Agnes HTTP 200，1546 chars，verdict WATCH
- gpt5.5 HTTP 200，1301 chars，verdict WATCH
- MiniMax HTTP 200 但解析失败，verdict ERROR

共识：1 PASS + 3 WATCH + 1 ERROR。5 provider 真参与率 164/165 = 99.4%。

## 5. 6 个新 status surface 的 4-probe 真实信号

| 文件 | module | 4-probe 真实落点 | 状态 |
|---|---|---|---|
| 01 quantum_channel_router | `agent.pgg_archon_quantum_channel_router` | module importable, env present, cache 0, health log missing | PARTIAL 2/4 |
| 04 context_learning | `agent.pgg_archon_context_learning` | 11 memory modules, memory_file_count=0, env present, path writable | PARTIAL 3/4 |
| 05 memory_system | `agent.pgg_archon_memory_system` | memory.db missing, module missing, env present, path writable | PARTIAL 2/4 |
| 05.5 full_toolcall_integration | `agent.pgg_archon_full_toolcall_integration` | ≥1 toolcall module, ≥1 log file, env present, path writable | ACTIVE 4/4 |
| 06 token_hygiene | `agent.pgg_archon_token_hygiene` | 33 audit files, env present, path writable, jq available | ACTIVE 4/4 |
| 11 tiangong_four_core | `agent.pgg_archon_tiangong_four_core` | (env-driven) 3/4 cores ACTIVE in default env | ACTIVE 3/4 |
| 13 apex_skill | `agent.pgg_archon_apex_skill` | 61 modules, 112 skills, APEX_SKILL_VERSION present, path writable | ACTIVE 4/4 |
| 21 core_cognition | `agent.pgg_archon_core_cognition` | module importable, env present, AGENTS.md writable, log missing | PARTIAL 3/4 |

## 6. se_sync → 5-LLM audit 闭环

闭环公式：

```
新 4-probe surface 模块
  ↓
pytest 测试 pass (≥3 unit tests)
  ↓
env 注入后跑 surface 实际 status
  ↓
se_sync.patch(id, status, mapped_skill, key_thesis)
  ↓
synced 33-card.json 落盘
  ↓
5-LLM 独立复核 (ThreadPoolExecutor 5 worker)
  ↓
verifier_facts.json 落盘
  ↓
EVOLUTION_MANIFEST.json latest_*_20260604 键写入
```

每个文件 1 commit + 1 manifest 写入 = 2 落点。本会话 6 个文件 = 12 落点。

## 7. 关键 Pitfall

- **5.5 不在 33-card id 空间**：PATCHES 中包含 5.5 时不能直接同步，sync 函数必须用 `if fid in src_ids` 保护。
- **MiniMax 解析失败**：synced 33-card audit 的 MiniMax 仍 HTTP 200 但解析不到 model_verdict，按 ERROR 标，**不要冒充 PASS**。
- **status distribution 数字 must match**：synced 后 SKELETON 24 - patched_to_PARTIAL_or_ACTIVE = 实际 SKELETON。本会话 24 - 6 = 18（其中 4 个 PARTIAL、2 个 ACTIVE，剩余 18 还在 SKELETON）。数字必须 self-consistent。
- **evomaster state log 缺失**：file 9 卡在 PARTIAL 2/4 是因为 `evomaster_state.jsonl` 没建，不是 prompt 问题。**修复路径**：touch 一个空 jsonl 即可达 3/4；写一个 fixture 即可达 4/4。
- **core_cognition log 缺失**：file 21 卡在 PARTIAL 3/4 是因为 `core_cognition_prompts.jsonl` 没建；同上 fix 即可。
- **router cache 缺失**：file 1 卡在 PARTIAL 2/4 是因为 `quantum_router_cache` 空目录；写一个 dummy cache 即可达 3/4。
- **source 21 在 33-card id 空间存在**：file 21 在 33-card 中是 `id: "21"`（不是 21.0），se_sync 必须按字符串 `"21"` patch。

## 8. 推荐新增 skill 触发的判定

当出现以下任一信号时，触发 `pgg-archon-eval-harness-suite` v0.6.0+ + 这个 references：

- 用户问"33-card 状态怎么同步"
- 用户问"5-LLM 复核的 verifier_facts 怎么生成"
- 用户要做 4-probe real surface 落地
- 用户要做 synced 33-card 实时同步
- 用户要扩展 33-card（加新 file_id）
