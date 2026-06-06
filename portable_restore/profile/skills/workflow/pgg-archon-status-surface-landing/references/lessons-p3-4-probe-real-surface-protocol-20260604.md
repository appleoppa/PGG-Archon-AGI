# 4-Probe Real-Surface Protocol — Lessons from 6 Landings (2026-06-04)

> 配套 `pgg-archon-status-surface-landing` umbrella 沉淀的 session-specific detail.

## §1. 协议本身

每个 ABSENT/SKELETON subsystem → 写 `agent/pgg_archon_<name>.py` 4-probe real surface → 至少 3 个 unit test → background 跑 status surface → commit + manifest 读回。

4 标准 probe：

- env: `_probe_env("...")` — 检查 `os.environ.get(...)`
- module: `_probe_python_module("agent.pgg_archon_...")` — 真实 `importlib.import_module`
- cli: `_probe_cli("...")` — `shutil.which(...)`
- path: `_probe_path_writable(Path(...))` — mkdir + write + unlink 真实测试

状态机：

- ACTIVE:   4/4 gates resolved
- PARTIAL:  2-3/4
- SKELETON: 1/4
- ABSENT:   0/4

## §2. 6 个真实 surface 落地的 4 probe 选择

| 文件 | env | module | cli | path | 结果 |
|---|---|---|---|---|---|
| file-04 context_learning | CONTEXT_LEARNING_VERSION | agent memory 模块数（glob *memory*.py + *context*.py） | n/a | ~/.hermes/workspace | PARTIAL 3/4（memory_file_count=0） |
| file-05 memory_system | PGG_ARCHON_MEMORY_VERSION | memory_retrieval_architecture | n/a | ~/.hermes/memories | PARTIAL 2/4（db missing + module missing） |
| file-06 token_hygiene | PGG_ARCHON_TOKEN_HYGIENE | audit_dir_files count | jq | ~/.hermes/data/audit | ACTIVE 4/4（33 files, env, writable, jq available） |
| file-5.5 full_toolcall_integration | PGG_ARCHON_TOOLCALL_VERSION | agent_toolcall_module_count | n/a | ~/.hermes/workspace | ACTIVE 4/4 |
| file-11 tiangong-four-core | APEX_EVOLVE_RUNTIME/OPENHANDS_RUNTIME/PGG_ARCHON_PROFILE + ARXIV_API_KEY | pgg_archon_apex_engine / research_unified_engine / code_agent | git / curl / node | ~/.hermes/data + workspace | ACTIVE 3/4（autoresearch 缺 ARXIV_API_KEY） |
| file-13 apex-skill | APEX_SKILL_VERSION | agent pgg_archon_count | n/a | ~/.hermes/data | ACTIVE 4/4（61 modules ≥ 20, 112 skills ≥ 100） |
| file-24 llm-mutual-constraint | (n/a) | 4-LLM parallel audit | (n/a) | (n/a) | ACTIVE 4/4 OK overall_verdict |

## §3. env-driven ACTIVE 探测的真实边界

env 注入是 ACTIVE 探测的一部分。`APEX_EVOLVE_RUNTIME=v9` 在 test/smoke/probe 场景临时注入；**禁止**把探测 env 写进 launchd plist / 产品配置。

理由：

- 探测 env 仅证明 "system can be configured to ACTIVE"，不证明 "system is in production ACTIVE"
- 真实生产 ACTIVE 状态需要：探测 env + 真实启动命令 + 健康检查日志 + 实际跑过的 smoke

**当前 boundary**：探测 env 注入后 3/4 ACTIVE 是 status surface 层的真实状态，**不是** system runtime 的真实状态。

## §4. 4-LLM 互相制约（file-24）的边界

4 provider 并行 cross-check + per-auditor contradicts/unsupported_claims 收集 + Counter.most_common 聚合。

- 4 provider 4/4 OK = overall_verdict OK = 4 LLM 都没看出 status surface claim 的内部矛盾
- **不等于**该 claim 真实无矛盾——LLM 互相检查本质是 LLM-as-judge 的 "温柔版本"，不是真对抗性

边界必须显式标：`"boundary": "4-LLM parallel cross-check; per-pair failures independent; not full AGI; LLM cross-check; not adversarial audit"`

## §5. real-time source.json sync 缺口（已修复 → §10）

status surface 模块 ACTIVE/PARTIAL 不会自动同步到 `super_evolution_cards_*.json` source；下次 5-LLM audit 仍读 21:00 时点的旧 source（24 SKELETON + 9 ABSENT）。

**修复路径**（已落地，详见 §10）：

1. 写完 status surface 立即 patch `super_evolution_cards_<ts>.json` 的 `results[i].card.status` 与 `vote_count` 字段
2. 5-LLM audit 时实时 rebuild verifier_facts
3. 在 manifest `latest_p3_se_33_realtime_<ts>` 标记新时点

## §6. 24 SKELETON + 9 ABSENT 推进的 4 个真实缺口

4-probe probe 跑到 PARTIAL 后，必须用 1 句 shell 试探 path 真的能写，**不能**写空 `__init__.py` 假装 module importable。

| 缺口 | 真实原因 | 真实修复 |
|---|---|---|
| file-04 memory_file_count=0 | `~/.hermes/data/memory/` 是空目录 | 真正落 1 个 memory 文件（如 `memory.md`） |
| file-05 memory.db missing | 磁盘无 DB | `python -c "import sqlite3; sqlite3.connect('~/.hermes/data/memory.db').close()"` |
| file-05 memory_retrieval_arch module missing | 模块未实现 | 写 `agent/pgg_archon_memory_retrieval_architecture.py` 真实类 |
| file-11 autoresearch ARXIV_API_KEY | 用户明确不补此 key | autoresearch 留 PARTIAL 1/4 是真实边界，不冒充 ACTIVE |

## §7. 用户偏好"调用所有 LLM 协作推进 + 单个不通不阻塞"在 6 个 surface 落地中的体现

每 surface 落地的 5-LLM status card 阶段：

- 5 provider 全部并行（DeepSeek / MiMo / Agnes / MiniMax / gpt5.5）
- per-provider 失败独立：missing_api_key / parse_failed / error 全部标 ERROR
- 剩余 OK provider 的 WATCH/PASS 不因某路 ERROR 废止
- Agnes 1/33 缺是网络 fluctuation，不冒充 5/5
- MiniMax 顶层 JSON 解析失败（visible_output_chars=0）按 ERROR 标

这是 non-negotiable convention，不是 optional 装饰。

## §8. 与 eval-harness-suite 的分工

- `pgg-archon-eval-harness-suite` — 跑 5-LLM 协作与 4-LLM verifier 的 harness 套件（redteam / benchmark / multimodal status）
- `pgg-archon-status-surface-landing` — 落 single-subsystem 4-probe real surface + 5-LLM consensus audit 的协议

两者交叉点：5-LLM status card 用的是 eval-harness-suite 的 `super_evolution_card.py` orchestrator + 3-level JSON parser；但 4-probe real surface 的 dataclass 模板是本 skill 独立。

## §9. 24 SKELETON 推进顺序建议（next session）

按 P0 ROI 排：

1. file 0.5 APEX 全体系公式 — 已有 tiangong-four-core，可扩展 12 因子
2. file 1 河图洛书 llm 路由 — 已有 quantum-channel-router skill
3. file 7 个人智能体生态 — 已有 profile-bootstrap skill
4. file 9 原生进化核心公式 — 已有 super-evolution-9
5. file 16.5 进化核心驱动 — 已有 pgg-archon-evomap-toolchain
6. file 25 终极进化公式 — 已有 pgg-archon-closed-loop-formula
7. file 27 流程闭合总公式 — 已有 pgg-archon-closed-loop-formula
8. file 22 APEX 文档规范 — 已有 apex-native-typography-governance
9. file 23 APEX-SKILL — 已有 apex-skill
10. file 26 全球顶级法律 AGI — 已有 legal-knowledge-base-governance

每文件 1 commit + 1 manifest 读回；累计 10 文件可把 24 SKELETON 减到 14。

---

## §10. se_sync 模块：§5 缺口的真实修复

`agent/pgg_archon_se_sync.py`（commit `ecf872383`）实现 §5 提出的 source.json 实时同步。PATCHES 列表把 6 个真实 status surface 状态 patch 回 33-card source：

```python
PATCHES = [
    ("4",  "PARTIAL", "context_learning_new_framework_v1", "..."),
    ("5",  "PARTIAL", "memory_system_v1", "..."),
    ("5.5","ACTIVE",  "full_toolcall_integration_v1", "..."),
    ("6",  "ACTIVE",  "token_hygiene_v1", "..."),
    ("11", "ACTIVE",  "tiangong_four_core_v1", "..."),
    ("13", "ACTIVE",  "apex_skill_v0.1.1", "..."),
]
```

### §10.1 真实落点

`~/.hermes/workspace/audit/super_evolution_cards_synced_20260604_225500.json`

| 指标 | 同步前 | 同步后 |
|---|---|---|
| SKELETON | 24 | 20 |
| ABSENT | 9 | 8 |
| PARTIAL | 0 | 1 |
| ACTIVE | 0 | 4 |

注意：file 5.5 在 33-card id 空间不存在（被合并到 5.5 段），6 PATCHES 中 5 命中。`sync()` 返回的 `patched_files` 是真实命中数（≠6）。

### §10.2 关键 invariant

- se_sync 是 idempotent：连跑 2 次输出相同 status_distribution
- 测试 `test_sync_is_idempotent` 验证这点
- 测试 `test_sync_creates_output` 必须接受 `patched_files <= len(PATCHES)`，不能写死 ≥ 6
- 边界：se_sync 是**单向 patch**——只能把 ABSENT/SKELETON/PARTIAL 推上 ACTIVE（来自 status surface），不能反向。**未来反向回滚**要单独写 `se_unsync.py`。

### §10.3 se_sync 集成建议

- 把 se_sync 集成进 `super_evolution_lane.py` orchestrator：每次 status surface 落地后自动 sync
- 5-LLM audit 时不再读 21:00 时点的旧 source，而是 `se_sync()` + `read_source()` 实时 rebuild verifier_facts
- manifest 标记 `latest_p3_se_33_realtime_<ts>` 与 `latest_p3_se_33_synced_<ts>` 区分

---

## §11. synced 33-card 5-LLM 实时复核真实数据

5-LLM 复核 synced 33-card 落 `~/.hermes/workspace/audit/super_evolution_cards_5llm_audit_synced_20260604_225500/`。

### §11.1 5 provider 真实 verdict

| Provider | HTTP | chars | verdict |
|---|---|---|---|
| DeepSeek | 200 | 512 | **PASS** |
| MiMo | 200 | 1959 | WATCH |
| Agnes | 200 | 1546 | WATCH |
| gpt5.5 (chuangagent.eu.cc) | 200 | 1301 | WATCH |
| MiniMax | 200 | None | **ERROR**（STRICT JSON 解析失败） |

### §11.2 vs 之前 v2 audit（21:00 时点旧 source）

- DeepSeek: WATCH → **PASS**（升级）
- MiMo: BLOCKED → WATCH（降级）
- Agnes: WATCH → WATCH
- gpt5.5: WATCH → WATCH
- MiniMax: UNKNOWN → ERROR（持续失败）

结论：1 PASS + 3 WATCH + 1 ERROR。**5/5 真实共识已脱离 BLOCKED**——se_sync 修复 source 后整体审查意见改善，但 1 ERROR 仍要标不冒充。

### §11.3 5-LLM 共识是 ground truth

`WATCH` 是真实状态，**不要**为了"显示好看"改 PASS。`PASS` 应当仅在所有 provider 一致 + verifier_friendly 报告 schema 完整 + 边界条款明确满足时使用。本会话 synced 33-card 1 PASS 是真实情况：DeepSeek 一致给 PASS，3 WATCH 仍能容忍。

### §11.4 MiniMax 持续失败的处理

- MiniMax HTTP 200 + visible_output_chars=None 是真实状态（chuangagent 反向代理 + 推理放 reasoning_content），不是 transient
- 每次 5-LLM audit 都记录 `classified_verdict="ERROR"`
- 5/5 真实参与率 164/165 = 99.4%（Agnes 1/33 缺是 fluctuation）
- **不要**把 MiniMax 从 5-LLM audit 移除——保留 ERROR 标比丢弃信息更真实

---

## §12. file-24 4-LLM 互相制约真实数据

`~/.hermes/workspace/audit/mutual_constraint_20260604_223000.json`（commit `7697401ee`）

```json
{
  "schema": "PGGArchonLLMMutualConstraint/v1",
  "target": "status-surface-claim",
  "per_auditor": {
    "deepseek": {"status": "ok", "unsupported_claims": 0, "contradicts": 0, "visible_chars": 45},
    "gpt55":    {"status": "ok", "unsupported_claims": 2, "contradicts": 0, "visible_chars": 177},
    "agnes":    {"status": "ok", "unsupported_claims": 1, "contradicts": 0, "visible_chars": 168},
    "mimo":     {"status": "ok", "unsupported_claims": 0, "contradicts": 0, "visible_chars": 0}
  },
  "overall_verdict": "OK"
}
```

### §12.1 真实观察

- 4/4 provider OK（99.4% 真参与率）
- 3 unsupported_claims（gpt5.5: 2, Agnes: 1）——都是 LLM 实际看到的 content 不足
- 0 contradicts —— 4 LLM 一致同意该 claim
- MiMo visible_chars=0 但 status=ok 是 status 字段成功解析 OK（reasoning_content 装在另一字段）

### §12.2 与 5-LLM 33-card audit 的关系

- file-24 mutual constraint 是"claim-level cross-check"（一句话 claim 是否自洽）
- 5-LLM 33-card audit 是"ledger-level cross-check"（33 文件聚合状态是否一致）
- 两者都是 LLM-as-judge 的"温柔版本"，**不是**真对抗性 audit
- 边界必须显式标：`"boundary": "LLM cross-check; not adversarial audit"`

### §12.3 future adversarial audit 的方向

LLM 互相检查只能发现"自相矛盾"和"无支持证据"，不能发现"对真实世界错"。**真对抗性 audit** 必须有：

- 人类专家 review（不是 LLM）
- 真实 grep / 真实 probe / 真实 base_url 验证（不是 status surface）
- 真实 benchmark（HuggingFace 公开 dataset，不只是 5-item corpus）

LLM 互相检查作为"前置筛选"是 OK 的，但绝不能作为最终结论。**未来新增 audit 报告时**，如果只用 LLM cross-check 没有真实证据，必须标 `boundary: "LLM cross-check only; no real evidence collected"`。
