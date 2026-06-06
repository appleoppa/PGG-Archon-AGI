# 终极进化公式（Phase3/4/5）落地模式参考

## 概述

终极进化公式（`pgg_archon_ultimate_evolution_ars_cycle.py`）是 PGG Archon 的开智闭环实现，核心产物：

- Phase3：周期性 ARS sidecar（Assess → Recommend → Stabilize）
- Phase4：趋势回放 + semantic fingerprint 去重门禁
- Phase5：Phase3/4 融合晋升门禁（promotion gate）

**文件位置**：`agent/pgg_archon_ultimate_evolution_ars_cycle.py`

---

## Phase3 ARS Cycle

### 核心函数

| 函数 | 作用 |
|------|------|
| `collect_phase3_native_evidence()` | 从 SessionDB/cron/workspace 收集本地证据 |
| `call_pgg_ultimate_evolution_tool()` | 通过 ToolRegistry 调用原生 tool |
| `build_phase3_ars_cycle()` | 组装完整 Phase3 payload（含 score/decision/next_actions） |
| `write_phase3_report()` | 写 JSON + Markdown 报告到 workspace |
| `persist_phase3_to_pgg_db()` | 写入 PGG SQLite（experiments + genes 表） |
| `run_phase3_cycle()` | 端到端运行，支持 `persist` 和 `idempotent` 参数 |

### ARS Sidecar 边界（强制，不可突破）

```
boundary: "cron/runtime-loop sidecar; no run_agent.py mutation;
          no provider call; no secret read; no deploy; no git push"
```

### 关键 pattern：idempotent persistence

```python
# 语义指纹去重：相同 schema+status+score+decision+boundary 的 payload
# 不会重复写入 gene，只返回 deduped=True
def persist_phase3_to_pgg_db_idempotent(payload, paths, *, db_path):
    fingerprint = _canonical_json_hash({
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "score": round(float(payload.get("score") or 0.0), 3),
        "decision": payload.get("decision"),
        "boundary": payload.get("boundary"),
    })
    # 查询现有 genes 表中是否有相同 fingerprint
    # 有则返回 deduped=True，无则插入
```

### DB schema

```sql
CREATE TABLE experiments(
  id INTEGER PRIMARY KEY,
  name TEXT,
  hypothesis TEXT,
  result TEXT,
  score REAL,
  created_at TEXT,
  tags TEXT
);
CREATE TABLE genes(
  id INTEGER PRIMARY KEY,
  name TEXT,
  pattern_type TEXT,
  source_repo TEXT,
  code_snippet TEXT,
  quality_score REAL,
  extracted_at TEXT
);
```

---

## Phase4 ARS Trend Replay

### 核心函数

| 函数 | 作用 |
|------|------|
| `build_phase4_ars_trend_replay()` | 读取 Phase3 报告 + DB，分类 trend/dedup risk |
| `persist_phase4_to_pgg_db()` | 写入 Phase4 gene（含 fingerprint/dedup_gate 状态） |
| `run_phase4_cycle()` | 端到端运行 |

### Phase4 payload 关键字段

```python
{
  "schema": "PGGArchonUltimateEvolutionPhase4ARSTrendReplay/v1",
  "trend": "stable" | "insufficient" | "watch",
  "duplicate_gene_count": N,          # 检测到重复 gene 数
  "payload_fingerprint": "<sha256>",  # Phase3 payload 语义指纹
  "risk": "cron_duplicate_gene_pollution" | "none_detected"
}
```

### 去重 gate 状态

```python
"dedup_gate": {
    "status": "active",
    "strategy": "phase3_semantic_fingerprint_skip_existing_gene",
    "blocked_duplicate_gene_count": N
}
```

---

## Phase5 Promotion Gate（融合晋升门禁）

### 核心函数

| 函数 | 作用 |
|------|------|
| `build_phase5_promotion_gate()` | 融合 Phase3/4 报告 + 多模型审查证据，输出 7 项门禁结果 |
| `write_phase5_report()` | 写 JSON + Markdown 报告 |
| `persist_phase5_to_pgg_db()` | 写入 Phase5 gene（含 gates 结构和 inputs 路径） |
| `run_phase5_cycle()` | 端到端运行 |

### 7 项晋升门禁

```python
gates = {
    "phase3_verified":      phase3.status == "verified",
    "phase4_verified":      phase4.status == "verified",
    "score_threshold":      score >= 75,
    "trend_stable":         phase4.trend == "stable",
    "dedup_gate_active":    phase4.dedup_gate.status == "active",
    "dual_model_review_ok": review.ok_count >= 2,
    "p0_blocker_absent":    not (phase4.p0_blocker or phase3.p0_blocker),
}
passed = all(gates.values())
decision = "allow_candidate_promotion" if passed else "hold_candidate_promotion"
```

### State Surface（统一状态面）

```python
state_surface = {
    "phase3": {"status", "score", "decision"},
    "phase4": {"status", "trend", "duplicate_gene_count"},
    "model_review": {"ok_count", "called_at"},
}
```

### 多模型审查调用模式

```python
# 调用 GPT-5.5 + Claude Opus-4-7 双通道，Responses API（codex_responses）
# 证据存入 workspace/model_review_phase5/phase5_dual_model_review.json
def call_dual_model_review(context: str, workspace_dir: Path) -> dict:
    results = [
        call_responses("gpt55_5yuantoken"),   # GPT-5.5
        call_responses("claude_opus47_5yuantoken"),  # Claude Opus-4-7
    ]
    # 写入 JSON 证据
    # return {"ok_count": sum(r.ok for r in results), "results": results}
```

**Responses API payload 格式**（必须用 `/responses` 端点）：

```python
payload = {
    "model": p["model"],
    "instructions": "你是严谨的AGI/PGG Archon架构审查员...",
    "input": context,
    "max_output_tokens": 900,
}
```

---

## 多阶段 CLI 运行

```bash
# 单阶段
python scripts/run_pgg_ultimate_evolution_ars_cycle.py --persist

# Phase3 + Phase4
python scripts/run_pgg_ultimate_evolution_ars_cycle.py --persist --phase4

# Phase3 + Phase4 + Phase5（推荐生产路径）
python scripts/run_pgg_ultimate_evolution_ars_cycle.py --persist --phase4 --phase5
```

### cron wrapper 模板

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /Users/appleoppa/.hermes/hermes-agent
PYTHON="/path/to/venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then PYTHON="python3"; fi
"$PYTHON" scripts/run_pgg_ultimate_evolution_ars_cycle.py --persist --phase4 --phase5
```

---

## 验证命令

```bash
# 语法检查
venv/bin/python -m py_compile agent/pgg_archon_ultimate_evolution_ars_cycle.py

# 单元测试
venv/bin/python -m pytest tests/agent/test_pgg_archon_ultimate_evolution_ars_cycle.py -q

# 全量测试
venv/bin/python -m pytest \
  tests/agent/test_pgg_archon_ultimate_evolution_formula.py \
  tests/tools/test_pgg_archon_tools.py \
  tests/agent/test_pgg_archon_ultimate_evolution_ars_cycle.py -q

# 端到端运行（生产路径）
venv/bin/python scripts/run_pgg_ultimate_evolution_ars_cycle.py --persist --phase4 --phase5

# DB 读回验证
python - <<'PY'
import sqlite3, json
con = sqlite3.connect('/Users/appleoppa/.hermes/data/pgg_archon.db')
cur = con.cursor()
for row in cur.execute("SELECT id,name,quality_score,extracted_at FROM genes WHERE name LIKE 'ultimate_evolution_formula_phase%' ORDER BY id DESC LIMIT 5"):
    print(row)
PY
```

---

## 已知陷阱

1. **不要在 Phase3/4 重复调用 `persist_phase3_to_pgg_db`（非 idempotent 版本）**：cron 重复触发会导致 gene 表重复记录。使用 `persist_phase3_to_pgg_db_idempotent` 或 `run_phase3_cycle(persist=True, idempotent=True)`。

2. **Responses API 必须用 `/responses` 端点**：`/v1/chat/completions` 对 GPT-5.5 和 Claude Opus-4-7 会返回错误。

3. **Phase5 的 `dual_model_review_ok` gate 依赖外部 JSON 证据**：必须在运行前先调用双模型审查并写入 `workspace/model_review_phase5/phase5_dual_model_review.json`，否则 gate 为 False。

4. **PGG DB 默认路径**：`~/.hermes/data/pgg_archon.db`，需要 `experiments` 和 `genes` 两张表存在。

---

## 与 APEX 三顺序的对应关系

| Phase | 对应顺序 | 核心动作 |
|-------|---------|---------|
| Phase3 ARS Cycle | 21354（审错优先） | 验证 sidecar 边界、调 tool、跑 native evidence |
| Phase4 Trend Replay | 14325（规划反证） | 回放历史记录、识别重复污染风险 |
| Phase5 Promotion Gate | 12534（融合固化） | 融合多报告 + 多模型审查 → 固化晋升门禁 |
