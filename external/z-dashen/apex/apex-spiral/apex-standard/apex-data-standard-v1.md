# APEX Unified Data Standard Framework v1.0

**Date:** 2026-05-08  
**Status:** Draft → Active  
**Author:** 璇玑帝国 · 墨羽

---

## 1. APEX-Gene Standard (基因标准)

### 1.1 Gene Entity Schema

```json
{
  "type": "Gene",
  "id": "gene_<category>_<name>",
  "version": 1,
  "category": "repair|optimize|innovate|orchestrate|evolve",
  "signals_match": ["signal_key_1", "signal_key_2"],
  "preconditions": ["condition_expression"],
  "strategy": ["step_1", "step_2"],
  "constraints": {
    "max_files": 12,
    "forbidden_paths": [".git", "node_modules"],
    "risk_level": "low|medium|high"
  },
  "validation": ["validation_command_or_script"],
  "fitness": {
    "score": 0.0,
    "cycles": 0,
    "success_rate": 0.0
  },
  "learning_history": [
    {
      "at": "ISO8601_timestamp",
      "outcome": "success|failed",
      "mode": "none|soft|hard",
      "reason_class": "unknown|validation|protocol|constraint_destructive",
      "retryable": true|false,
      "learning_signals": ["signal_key"]
    }
  ],
  "metadata": {
    "created_at": "ISO8601_timestamp",
    "updated_at": "ISO8601_timestamp",
    "created_by": "evolver|manual",
    "tags": ["tag1", "tag2"]
  }
}
```

### 1.2 Gene Category Enum

| Category | Description | Signals Pattern |
|----------|-------------|-----------------|
| repair | 修复错误/异常 | error, exception, failed, unstable |
| optimize | 优化性能 | perf_bottleneck, capability_gap |
| innovate | 创新突破 | stagnation, saturation, empty_cycle |
| orchestrate | 协调调度 | coordination, multi_agent |
| evolve | 进化控制 | evolution_cycle, gene_selection |

---

## 2. APEX-Event Standard (事件标准)

### 2.1 Event Type Enum

| Type | Kind | Description |
|------|------|-------------|
| MemoryGraphEvent | signal | 信号检测事件 |
| MemoryGraphEvent | hypothesis | 假设生成事件 |
| MemoryGraphEvent | attempt | 行动尝试事件 |
| MemoryGraphEvent | outcome | 结果记录事件 |
| MemoryGraphEvent | confidence_edge | 置信度更新事件 |
| EvolutionEvent | gene_emit | 基因发射事件 |
| EvolutionEvent | sense_fusion_sync | 感知融合同步事件 |
| EvolutionEvent | behavior_release | 行为释放事件 |
| ReflectionEvent | reflection | 反思事件 |

### 2.2 Base Event Schema

```json
{
  "schema_version": "1.0",
  "type": "EventType",
  "id": "<prefix>_<timestamp>_<random_id>",
  "ts": "ISO8601_timestamp",
  "actor": {
    "agent_id": "string",
    "session_scope": "string|null",
    "personality": {
      "rigor": 0.0,
      "creativity": 0.0,
      "verbosity": 0.0,
      "risk_tolerance": 0.0,
      "obedience": 0.0
    }
  },
  "context": {
    "signals": ["signal_key"],
    "signals_raw": "pipe_delimited_signals",
    "gene_id": "string",
    "gene_category": "string",
    "cycle_count": 0
  },
  "data": {},
  "observed": {
    "system_health": "string",
    "mood": "string",
    "scan_ms": 0,
    "memory_size_bytes": 0,
    "recent_error_count": 0,
    "cwd": "string"
  },
  "confidence": {
    "half_life_days": 30
  }
}
```

### 2.3 Signal Event Data

```json
{
  "kind": "signal",
  "signal": {
    "key": "pipe_delimited_signal_keys",
    "signals": ["array_of_signal_keys"],
    "error_signature": "string|null"
  },
  "observed": {}
}
```

### 2.4 Hypothesis Event Data

```json
{
  "kind": "hypothesis",
  "signal": {},
  "hypothesis": {
    "id": "hyp_<ts>_<id>",
    "text": "hypothesis_description",
    "predicted_outcome": {
      "status": "string|null",
      "score": "number|null"
    }
  },
  "mutation": {
    "id": "mut_<ts>_<id>",
    "category": "string",
    "trigger_signals": [],
    "target": "gene:gene_id",
    "expected_effect": "string",
    "risk_level": "low|medium|high"
  },
  "action": {
    "drift": false,
    "selected_by": "selector",
    "selector": {
      "selected": "gene_id",
      "reason": [],
      "alternatives": [],
      "selectionPath": "string",
      "memoryUsed": false
    }
  }
}
```

### 2.5 Outcome Event Data

```json
{
  "kind": "outcome",
  "outcome": {
    "status": "success|failed|partial",
    "score": 0.0,
    "note": "string",
    "observed": {},
    "predictive": {
      "signal_clarity": 0.0,
      "trajectory_trend": 0.0,
      "frontier_touched": false
    }
  },
  "baseline": {}
}
```

---

## 3. APEX-State Standard (状态标准)

### 3.1 Evolution State Schema

```json
{
  "schema_version": "1.0",
  "type": "EvolutionState",
  "cycleCount": 0,
  "lastRun": "unix_timestamp_ms",
  "status": "idle|running|paused|error",
  "current_cycle": {
    "start_time": "ISO8601",
    "signals": [],
    "selected_gene": "string",
    "mutations": []
  },
  "stats": {
    "total_cycles": 0,
    "success_cycles": 0,
    "failed_cycles": 0,
    "avg_score": 0.0
  }
}
```

### 3.2 Personality State Schema

```json
{
  "schema_version": "1.0",
  "type": "PersonalityState",
  "current": {
    "rigor": 0.7,
    "creativity": 1.0,
    "verbosity": 0.25,
    "risk_tolerance": 0.95,
    "obedience": 0.85
  },
  "stats": {
    "<personality_key>": {
      "success": 0,
      "fail": 0,
      "avg_score": 0.0,
      "n": 0,
      "updated_at": "ISO8601"
    }
  },
  "history": [
    {
      "at": "ISO8601",
      "key": "rigor=X|creativity=Y|verbosity=Z|...",
      "outcome": "success|failed",
      "score": 0.0,
      "notes": "event:evt_id"
    }
  ]
}
```

### 3.3 Memory Graph State Schema

```json
{
  "schema_version": "1.0",
  "type": "MemoryGraphState",
  "last_action": {
    "action_id": "act_<ts>_<id>",
    "signal_key": "pipe_delimited_signals",
    "signals": [],
    "mutation_id": "string",
    "mutation_category": "string",
    "mutation_risk_level": "string",
    "personality_key": "string",
    "personality_state": {},
    "gene_id": "string",
    "gene_category": "string",
    "hypothesis_id": "string",
    "capsules_used": [],
    "had_error": false,
    "created_at": "ISO8601",
    "outcome_recorded": false,
    "baseline_observed": {}
  }
}
```

---

## 4. APEX-Memory Standard (记忆标准)

### 4.1 Memory Record Schema

```json
{
  "schema_version": "1.0",
  "type": "memory.recall.recorded",
  "timestamp": "ISO8601_timestamp",
  "query": "string",
  "resultCount": 0,
  "results": [
    {
      "path": "string",
      "startLine": 0,
      "endLine": 0,
      "score": 0.0
    }
  ]
}
```

### 4.2 Daily Memory Schema

```json
{
  "schema_version": "1.0",
  "type": "daily_memory",
  "date": "YYYY-MM-DD",
  "summary": "string",
  "sections": [
    {
      "title": "string",
      "content": "string"
    }
  ],
  "tags": [],
  "confidence": 0.0
}
```

---

## 5. APEX-Capsule Standard (胶囊标准)

### 5.1 Capsule Asset Schema

```json
{
  "schema_version": "1.0",
  "type": "Capsule",
  "id": "capsule_<timestamp>",
  "name": "trigger_word_or_signal",
  "description": "capsule_description",
  "version": "1.0.0",
  "gene": {
    "id": "gene_id",
    "category": "string",
    "signals_match": []
  },
  "code_diff": "actual_code_changes",
  "test": "test_validation_command",
  "fitness": {
    "score": 0.0,
    "validated_at": "ISO8601"
  },
  "published": {
    "at": "ISO8601",
    "asset_id": "string",
    "status": "pending|accepted|quarantine|rejected",
    "reputation": 0.0
  },
  "metadata": {
    "author": "璇玑帝国",
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  }
}
```

---

## 6. Standard Enforcement Rules

### 6.1 Schema Version Declaration
- All JSON files MUST include `"schema_version": "1.0"` at root level
- All jsonl events MUST include `"schema_version": "1.0"` at root level

### 6.2 Timestamp Format
- All timestamps MUST use ISO8601 format with timezone: `YYYY-MM-DDTHH:mm:ss.SSSZ`
- Unix timestamps in milliseconds allowed for machine data only

### 6.3 ID Generation
- Gene IDs: `gene_<category>_<name>`
- Event IDs: `<prefix>_<timestamp>_<random_hex>`
- Hypothesis IDs: `hyp_<timestamp>_<random_hex>`
- Mutation IDs: `mut_<timestamp>_<random_hex>`
- Action IDs: `act_<timestamp>_<random_hex>`

### 6.4 Signal Key Format
- Pipe-delimited for composite signals: `signal_a|signal_b|signal_c`
- Array format for multiple signals: `["signal_a", "signal_b"]`

### 6.5 File Naming Convention
- Schema files: `apex-<type>-standard-v1.json`
- Data files: `<type>.<ext>`
- Log files: `<type>.jsonl`

---

## 7. Implementation Priority

| Priority | Standard | Files to Update |
|----------|----------|-----------------|
| P0 | Gene Standard | genes.json, genes.jsonl |
| P0 | Event Standard | memory_graph.jsonl, reflection_log.jsonl |
| P1 | State Standard | evolution_state.json, personality_state.json |
| P1 | Memory Standard | daily memory files |
| P2 | Capsule Standard | Capsule publish assets |

---

## 8. Validation Commands

```bash
# Validate gene schema
node -e "const s=require('./apex-gene-standard-v1.json'); console.log('Gene schema valid')"

# Validate event schema
node -e "const s=require('./apex-event-standard-v1.json'); console.log('Event schema valid')"

# Check schema compliance
find . -name "*.json" -exec node -e "try{JSON.parse(require('fs').readFileSync('{}'))}catch(e){console.error('Invalid JSON')}" \;
```
