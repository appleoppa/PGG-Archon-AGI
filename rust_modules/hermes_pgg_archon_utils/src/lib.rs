/// P14: `hermes_pgg_archon_utils` — Batch 4 small pure-logic modules
///
/// Aggregates: provenance (node_id/repo_sha/integrity), doubt_gamma (risk classification),
/// planning_runner (task scheduler), memory_trace (scorer).
///
/// Boundary: pure computation + local filesystem reads; no LLM, no network, no AGI claim.
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use serde::{Deserialize, Serialize};
use sha2::Digest;

// ── Module: provenance ──────────────────────────────────────────────────────

/// Stable node identifier from hostname + username.
fn stable_node_id() -> String {
    let host = std::env::var("HOSTNAME")
        .or_else(|_| std::env::var("COMPUTERNAME"))
        .unwrap_or_else(|_| "unknown_host".into());
    let user = std::env::var("USER")
        .or_else(|_| std::env::var("USERNAME"))
        .unwrap_or_else(|_| "unknown_user".into());
    let raw = format!("pgg_archon_{}@{}", user, host);
    let hash = sha2::Sha256::digest(raw.as_bytes());
    format!(
        "node_{}",
        hash.iter()
            .map(|b| format!("{:02x}", b))
            .take(8)
            .collect::<String>()
    )
}

/// Latest git SHA in the Hermes agent directory.
fn repo_head(root: &str) -> String {
    let cwd = std::path::Path::new(root).join("hermes-agent");
    match std::process::Command::new("git")
        .args(["rev-parse", "HEAD"])
        .current_dir(&cwd)
        .output()
    {
        Ok(out) if out.status.success() => {
            let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
            s.chars().take(16).collect()
        }
        _ => "no_git".into(),
    }
}

/// Count pgg_archon_*.py files under agent/.
fn pgg_file_count(root: &str) -> usize {
    let agent_dir = std::path::Path::new(root)
        .join("hermes-agent")
        .join("agent");
    if !agent_dir.is_dir() {
        return 0;
    }
    match std::fs::read_dir(&agent_dir) {
        Ok(entries) => entries
            .filter_map(|e| e.ok())
            .filter(|e| {
                e.path()
                    .file_name()
                    .and_then(|n| n.to_str())
                    .map(|n| n.starts_with("pgg_archon_") && n.ends_with(".py"))
                    .unwrap_or(false)
            })
            .count(),
        Err(_) => 0,
    }
}

/// Integrity check: core modules exist and are non-empty.
fn integrity_check(root: &str) -> (bool, Vec<String>) {
    let agent_dir = std::path::Path::new(root)
        .join("hermes-agent")
        .join("agent");
    let core = [
        "pgg_archon_delta_gate.py",
        "pgg_archon_codegenesis_scanner.py",
        "pgg_archon_memory_trace.py",
        "pgg_archon_v103_self_loop.py",
    ];
    let mut warnings = Vec::new();
    for name in &core {
        let path = agent_dir.join(name);
        if !path.is_file() {
            warnings.push(format!("missing: {}", name));
        } else if std::fs::metadata(&path)
            .map(|m| m.len() == 0)
            .unwrap_or(true)
        {
            warnings.push(format!("empty: {}", name));
        }
    }
    (warnings.is_empty(), warnings)
}

#[pyfunction]
#[pyo3(signature = (root="~/.hermes"))]
/// Build a provenance report: node_id, repo_sha, file_count, integrity.
fn provenance(root: &str) -> PyResult<String> {
    let expanded = if root.starts_with('~') {
        let home = std::env::var("HOME").unwrap_or_else(|_| "/root".into());
        root.replacen('~', &home, 1)
    } else {
        root.to_string()
    };
    let node = stable_node_id();
    let sha = repo_head(&expanded);
    let count = pgg_file_count(&expanded);
    let (integrity_ok, warns) = integrity_check(&expanded);
    let status = if integrity_ok { "PASS" } else { "WATCH" };

    let payload = format!("{}|{}|{}|{}", node, sha, count, integrity_ok);
    let evidence_hash = {
        let hash = sha2::Sha256::digest(payload.as_bytes());
        hash.iter()
            .map(|b| format!("{:02x}", b))
            .collect::<String>()
    };

    let report = serde_json::json!({
        "schema": "PGGArchonProvenance/v1",
        "status": status,
        "node_id": node,
        "repo_sha": sha,
        "file_count": count,
        "integrity_ok": integrity_ok,
        "evidence_hash": evidence_hash,
        "warnings": warns,
    });
    Ok(serde_json::to_string(&report).unwrap_or_default())
}

// ── Module: doubt_gamma ─────────────────────────────────────────────────────

/// Risk keywords with weights.
const RISK_KEYWORDS: &[(&str, f64)] = &[
    ("delete", 0.2),
    ("drop", 0.2),
    ("destroy", 0.25),
    ("production", 0.2),
    ("deploy", 0.15),
    ("override", 0.15),
    ("force", 0.15),
    ("credential", 0.25),
    ("secret", 0.25),
    ("security", 0.2),
];

#[pyfunction]
#[pyo3(signature = (decision, crosses_boundary=false))]
/// Classify decision risk: returns JSON with doubt_level, gamma, risk_factors.
fn classify_decision(decision: &str, crosses_boundary: bool) -> PyResult<String> {
    let lower = decision.to_lowercase();
    let mut score = 0.0_f64;
    let mut risk_factors: Vec<String> = Vec::new();

    for (kw, w) in RISK_KEYWORDS {
        if lower.contains(kw) {
            risk_factors.push(kw.to_string());
            score += w;
        }
    }
    if crosses_boundary {
        risk_factors.push("crosses_boundary".into());
        score += 0.4;
    }
    if decision.trim().is_empty() {
        risk_factors.push("empty_decision".into());
        score += 0.5;
    }

    let gamma = score.clamp(0.0, 1.0);
    let level = if gamma >= 0.7 {
        "high"
    } else if gamma >= 0.4 {
        "medium"
    } else if gamma > 0.0 {
        "low"
    } else {
        "none"
    };

    let result = serde_json::json!({
        "requires_review": crosses_boundary || gamma >= 0.4,
        "doubt_level": level,
        "gamma": (gamma * 10000.0).round() / 10000.0,
        "risk_factors": risk_factors,
    });
    Ok(serde_json::to_string(&result).unwrap_or_default())
}

// ── Module: planning_runner ─────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Task {
    id: String,
    name: String,
    dependencies: Vec<String>,
}

#[pyfunction]
/// Build a topological plan from a JSON task list. Returns JSON plan.
fn build_plan(tasks_json: &str) -> PyResult<String> {
    let tasks: Vec<Task> = match serde_json::from_str(tasks_json) {
        Ok(t) => t,
        Err(e) => {
            let err = serde_json::json!({
                "total_tasks": 0,
                "slice_count": 0,
                "slices": [],
                "warnings": [format!("parse error: {}", e)],
            });
            return Ok(serde_json::to_string(&err).unwrap_or_default());
        }
    };

    let mut warnings: Vec<String> = Vec::new();
    let mut normalized: Vec<Task> = Vec::new();
    let mut seen = std::collections::HashSet::new();

    for (i, t) in tasks.iter().enumerate() {
        let tid = if t.id.is_empty() && t.name.is_empty() {
            format!("task_{}", i)
        } else if t.id.is_empty() {
            t.name.clone()
        } else {
            t.id.clone()
        };
        if seen.contains(&tid) {
            warnings.push(format!("duplicate task id {}", tid));
            continue;
        }
        seen.insert(tid.clone());
        normalized.push(Task {
            id: tid,
            name: t.name.clone(),
            dependencies: t.dependencies.clone(),
        });
    }

    if normalized.is_empty() {
        let empty = serde_json::json!({
            "total_tasks": 0, "slice_count": 0, "slices": [],
            "warnings": warnings,
        });
        return Ok(serde_json::to_string(&empty).unwrap_or_default());
    }

    // Topological sort
    let mut remaining: std::collections::HashMap<String, Task> =
        normalized.into_iter().map(|t| (t.id.clone(), t)).collect();
    let mut done: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut slices: Vec<serde_json::Value> = Vec::new();
    let dep_set: std::collections::HashSet<String> = remaining.keys().cloned().collect();

    while !remaining.is_empty() {
        let ready: Vec<String> = remaining
            .iter()
            .filter(|(_tid, t)| {
                t.dependencies
                    .iter()
                    .all(|dep| done.contains(dep) || !dep_set.contains(dep))
            })
            .map(|(tid, _)| tid.clone())
            .collect();

        if ready.is_empty() {
            warnings.push("cycle_or_unresolved_dependencies".into());
            let all_ids: Vec<String> = remaining.keys().cloned().collect();
            slices.push(serde_json::json!({
                "slice_index": slices.len(),
                "task_ids": all_ids,
                "tasks": remaining.values().map(|t| serde_json::json!({
                    "id": t.id, "name": t.name, "dependencies": t.dependencies,
                })).collect::<Vec<_>>(),
            }));
            break;
        }

        let slice_tasks: Vec<serde_json::Value> = ready
            .iter()
            .map(|tid| {
                let t = &remaining[tid];
                serde_json::json!({
                    "id": t.id, "name": t.name, "dependencies": t.dependencies,
                })
            })
            .collect();

        slices.push(serde_json::json!({
            "slice_index": slices.len(),
            "task_ids": ready.clone(),
            "tasks": slice_tasks,
        }));

        for tid in &ready {
            done.insert(tid.clone());
            remaining.remove(tid);
        }
    }

    let result = serde_json::json!({
        "total_tasks": done.len(),
        "slice_count": slices.len(),
        "slices": slices,
        "warnings": warnings,
    });
    Ok(serde_json::to_string(&result).unwrap_or_default())
}

// ── Module: memory_trace ────────────────────────────────────────────────────

/// Average numeric values from a JSON metrics object by key list.
fn avg_metrics(metrics: &serde_json::Value, keys: &[&str]) -> Option<(f64, Vec<String>)> {
    let mut vals = Vec::new();
    let mut warns = Vec::new();
    let obj = metrics.as_object()?;
    for k in keys {
        if let Some(v) = obj.get(*k) {
            if let Some(n) = v.as_f64() {
                vals.push(n.clamp(0.0, 1.0));
            } else {
                warns.push(format!("{}.{} not numeric", "obj", k));
            }
        }
    }
    if vals.is_empty() {
        None
    } else {
        Some((vals.iter().sum::<f64>() / vals.len() as f64, warns))
    }
}

#[pyfunction]
#[pyo3(signature = (memory_metrics_json, trace_metrics_json))]
/// Score memory + trace metrics. Returns JSON with status/sigma/tau/combined.
fn score(memory_metrics_json: &str, trace_metrics_json: &str) -> PyResult<String> {
    let mut warnings: Vec<String> = Vec::new();
    let mem: serde_json::Value =
        serde_json::from_str(memory_metrics_json).unwrap_or(serde_json::Value::Null);
    let trace: serde_json::Value =
        serde_json::from_str(trace_metrics_json).unwrap_or(serde_json::Value::Null);

    if !mem.is_object() || !trace.is_object() {
        let err = serde_json::json!({
            "status": "BLOCKED",
            "sigma_memory": 0.0,
            "tau_trace": 0.0,
            "combined": 0.0,
            "warnings": ["metrics must be dicts"],
        });
        return Ok(serde_json::to_string(&err).unwrap_or_default());
    }

    let mem_keys = &[
        "learn",
        "search",
        "multimodal",
        "profile",
        "retention",
        "diversity",
    ];
    let trace_keys = &["decision", "reason", "result", "evidence"];

    let (sigma, mem_warns) = avg_metrics(&mem, mem_keys).unwrap_or_else(|| {
        warnings.push("no valid memory metrics".into());
        (0.0, vec![])
    });
    warnings.extend(mem_warns);

    let (tau, trace_warns) = avg_metrics(&trace, trace_keys).unwrap_or_else(|| {
        warnings.push("no valid trace metrics".into());
        (0.0, vec![])
    });
    warnings.extend(trace_warns);

    let combined = ((sigma * 0.6 + tau * 0.4) * 1_000_000.0).round() / 1_000_000.0;

    let status = if !mem.is_object() || !trace.is_object() {
        "BLOCKED"
    } else if combined >= 0.7 {
        "PASS"
    } else if combined >= 0.4 {
        "WATCH"
    } else {
        "BLOCKED"
    };

    let result = serde_json::json!({
        "status": status,
        "sigma_memory": (sigma * 1_000_000.0).round() / 1_000_000.0,
        "tau_trace": (tau * 1_000_000.0).round() / 1_000_000.0,
        "combined": combined,
        "warnings": warnings,
    });
    Ok(serde_json::to_string(&result).unwrap_or_default())
}

// ── Module: harmrate_gate ───────────────────────────────────────────────────

const HARM_BOUNDARY: &str = "PGG_internal_HarmRate_gate; APEX_MOSS_VERIFIED=false; no_zero_risk_claim; no_external_safety_certification";

fn harm_f64(task: &serde_json::Value, key: &str, default: f64) -> f64 {
    task.get(key).and_then(|v| v.as_f64()).unwrap_or(default)
}

fn harm_bool(task: &serde_json::Value, key: &str, default: bool) -> bool {
    task.get(key).and_then(|v| v.as_bool()).unwrap_or(default)
}

fn harm_str(task: &serde_json::Value, key: &str, default: &str) -> String {
    task.get(key)
        .and_then(|v| v.as_str())
        .unwrap_or(default)
        .to_string()
}

fn now_epoch_isoish() -> String {
    chrono::Local::now()
        .format("%Y-%m-%dT%H:%M:%S%z")
        .to_string()
}

#[pyfunction]
#[pyo3(signature = (task_json, block_threshold=0.34, watch_threshold=0.20))]
/// Native PGG internal HarmRate gate. Input/output are JSON strings.
fn compute_harmrate_json(
    task_json: &str,
    block_threshold: f64,
    watch_threshold: f64,
) -> PyResult<String> {
    let task: serde_json::Value = serde_json::from_str(task_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("invalid task json: {}", e))
    })?;

    let risk = harm_f64(&task, "risk", 0.0);
    let uncertainty = harm_f64(&task, "uncertainty", 0.0);
    let source_confidence = harm_f64(&task, "source_confidence", 1.0);
    let regression_risk = harm_f64(&task, "regression_risk", 0.0);
    let overclaim_risk = harm_f64(&task, "overclaim_risk", 0.0);
    let task_type = harm_str(&task, "task_type", "general");
    let external_authority_claim = harm_bool(&task, "external_authority_claim", false);
    let apex_moss_claim = harm_bool(&task, "apex_moss_verified_claim", false);

    let missing_source_penalty = (1.0 - source_confidence).max(0.0);
    let sensitive = matches!(
        task_type.as_str(),
        "legal" | "production" | "security" | "credential" | "external_public"
    );
    let sensitive_multiplier = if sensitive { 1.25 } else { 1.0 };
    let raw = (0.30 * risk
        + 0.20 * uncertainty
        + 0.20 * missing_source_penalty
        + 0.15 * regression_risk
        + 0.15 * overclaim_risk)
        * sensitive_multiplier;
    let harmrate = raw.max(0.0).min(1.0);

    let mut reasons: Vec<String> = Vec::new();
    if external_authority_claim && source_confidence < 0.95 {
        reasons.push("external_authority_claim_without_high_source_confidence".into());
    }
    if apex_moss_claim {
        reasons.push("apex_moss_verified_claim_blocked_until_independent_source".into());
    }
    if source_confidence < 0.5 {
        reasons.push("low_source_confidence".into());
    }
    if sensitive {
        reasons.push("sensitive_task_stricter_threshold".into());
    }

    let decision = if apex_moss_claim || (external_authority_claim && source_confidence < 0.95) {
        "BLOCK"
    } else if harmrate >= block_threshold {
        "BLOCK"
    } else if harmrate >= watch_threshold || source_confidence < 0.75 {
        "WATCH"
    } else {
        "ALLOW"
    };

    let result = serde_json::json!({
        "schema": "PGGInternalHarmRateGate/v1",
        "created_at": now_epoch_isoish(),
        "decision": decision,
        "harmrate": (harmrate * 1_000_000.0).round() / 1_000_000.0,
        "thresholds": {"watch": watch_threshold, "block": block_threshold},
        "reasons": reasons,
        "inputs": {
            "risk": risk,
            "uncertainty": uncertainty,
            "source_confidence": source_confidence,
            "regression_risk": regression_risk,
            "overclaim_risk": overclaim_risk,
            "task_type": task_type,
            "external_authority_claim": external_authority_claim,
            "apex_moss_verified_claim": apex_moss_claim,
        },
        "boundary": HARM_BOUNDARY,
        "APEX_MOSS_VERIFIED": false,
        "zero_risk_claim": false,
    });
    Ok(serde_json::to_string(&result).unwrap_or_default())
}

#[pyfunction]
/// Write HarmRate report JSON to output_dir; returns file path.
fn write_harmrate_report_json(report_json: &str, output_dir: &str) -> PyResult<String> {
    let report: serde_json::Value = serde_json::from_str(report_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("invalid report json: {}", e))
    })?;
    let out_dir = if output_dir.starts_with('~') {
        let home = std::env::var("HOME").unwrap_or_default();
        std::path::PathBuf::from(output_dir.replacen('~', &home, 1))
    } else {
        std::path::PathBuf::from(output_dir)
    };
    std::fs::create_dir_all(&out_dir)
        .map_err(|e| pyo3::exceptions::PyOSError::new_err(format!("create output dir: {}", e)))?;
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let path = out_dir.join(format!("{}_harmrate_gate.json", ts));
    let payload = serde_json::to_string_pretty(&report)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("serialize report: {}", e)))?;
    std::fs::write(&path, payload)
        .map_err(|e| pyo3::exceptions::PyOSError::new_err(format!("write report: {}", e)))?;
    Ok(path.to_string_lossy().to_string())
}



// ── Module: agent_loop_event_surface ────────────────────────────────────────

fn v_str(v: &serde_json::Value, key: &str) -> String {
    v.get(key).and_then(|x| x.as_str()).unwrap_or("").to_string()
}

fn v_i64(v: &serde_json::Value, key: &str) -> i64 {
    v.get(key).and_then(|x| x.as_i64()).unwrap_or(0)
}

fn v_f64(v: &serde_json::Value, key: &str) -> f64 {
    v.get(key).and_then(|x| x.as_f64()).unwrap_or(0.0)
}

fn map_role_to_event_type(role: &str, preview: &str, tool_name: &str) -> String {
    let r = role.to_lowercase();
    let p = preview.to_lowercase();
    if p.contains("compact_boundary") || p.contains("context compact") || p.contains("/compress") {
        return "compact_boundary".into();
    }
    match r.as_str() {
        "system" => "system".into(),
        "assistant" | "model" => "assistant".into(),
        "tool" => {
            if tool_name.is_empty() { "stream_event".into() } else { "tool_result".into() }
        }
        "user" => "user".into(),
        _ => "stream_event".into(),
    }
}

fn map_loop_result_subtype(session: &serde_json::Value) -> String {
    let ended_at = v_f64(session, "ended_at");
    let message_count = v_i64(session, "message_count");
    let tool_count = v_i64(session, "tool_call_count");
    let source = v_str(session, "source").to_lowercase();
    if ended_at > 0.0 && message_count > 0 {
        "success".into()
    } else if source.contains("blocked") {
        "blocked_policy".into()
    } else if message_count == 0 && tool_count == 0 {
        "partial_provider_empty".into()
    } else {
        "error_interrupted".into()
    }
}

fn agent_loop_mapping_catalog() -> serde_json::Value {
    serde_json::json!({
        "schema": "PGGAgentLoopMappingCatalog/v1",
        "p0_event_type_map": {
            "system_role": "system",
            "assistant_or_model_role": "assistant",
            "tool_role_with_tool_name": "tool_result",
            "tool_request": "not directly present in state.db; reserved for live tool ledger/SSE",
            "user_role": "user",
            "compact_boundary": "detected from compact/compress markers; native event type reserved",
            "result": "synthesized per session from session metadata"
        },
        "p1_result_subtype_map": {
            "success": "ended_at present and message_count > 0",
            "partial_provider_empty": "no messages/tools in session metadata",
            "error_interrupted": "open or incomplete session without stronger error class",
            "error_max_turns": "reserved: map from max_iterations/iteration_budget exhaustion ledger",
            "error_budget_exhausted": "reserved: map from cost/budget ledger",
            "error_guardrail_halt": "reserved: map from guardrail/checkpoint denial ledger",
            "error_tool_invalid": "reserved: map from tool schema/registry errors",
            "error_tool_json": "reserved: map from JSON parse errors",
            "blocked_permission": "reserved: map from approval/checkpoint permission denials",
            "blocked_policy": "reserved: map from policy/hard-deny result"
        },
        "p1_turn_budget_map": {
            "turn_id": "model decision round; currently derived from user-message boundaries in state.db",
            "step_id": "deterministic/local step; currently message_id for stable ordering",
            "phase_id": "PGG governance phase; reserved, null until phase ledger is joined",
            "max_turns": "reserved from agent.max_iterations/config",
            "max_wall_seconds": "reserved from loop budget contract",
            "max_budget_usd": "reserved from OmniRoute/cost ledger",
            "max_tool_calls": "reserved from tool budget contract",
            "max_write_ops": "reserved from checkpoint/write-op ledger"
        },
        "p2_future_map": {
            "compact_boundary": "join compression ledger or message marker; include before_tokens/summary_hash/lossy when available",
            "continue_latest_task": "map to latest session_id/task_id lineage",
            "resume_task": "map to existing session_id/task_id from state.db/session_search",
            "fork_task": "map parent_task_id + variant_label; not inferred silently"
        },
        "boundary": "read-only mapping surface; no provider/config/scheduler/security mutation; state.db derived events are approximate where live ledgers are absent"
    })
}

#[pyfunction]
/// Build PGGAgentLoopEvent/v1 surface from session/message JSON arrays. Pure mapping; no IO/network.
fn agent_loop_event_surface_json(sessions_json: &str, messages_json: &str) -> PyResult<String> {
    agent_loop_event_surface_with_ledger_json(sessions_json, messages_json, "[]")
}

#[pyfunction]
/// Build PGGAgentLoopEvent/v1 surface and join a pre-read external ledger JSON array.
fn agent_loop_event_surface_with_ledger_json(sessions_json: &str, messages_json: &str, ledger_json: &str) -> PyResult<String> {
    let sessions: Vec<serde_json::Value> = serde_json::from_str(sessions_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("invalid sessions json: {}", e))
    })?;
    let mut messages: Vec<serde_json::Value> = serde_json::from_str(messages_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("invalid messages json: {}", e))
    })?;
    let ledger_events: Vec<serde_json::Value> = serde_json::from_str(ledger_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("invalid ledger json: {}", e))
    })?;

    messages.sort_by(|a, b| {
        let sa = v_str(a, "session_id");
        let sb = v_str(b, "session_id");
        sa.cmp(&sb).then(v_i64(a, "id").cmp(&v_i64(b, "id")))
    });

    let mut events: Vec<serde_json::Value> = Vec::new();
    let mut current_session = String::new();
    let mut turn_id: i64 = 0;
    let mut counts: std::collections::BTreeMap<String, i64> = std::collections::BTreeMap::new();

    for m in messages.iter() {
        let sid = v_str(m, "session_id");
        if sid != current_session {
            current_session = sid.clone();
            turn_id = 0;
        }
        let role = v_str(m, "role");
        if role == "user" {
            turn_id += 1;
        }
        let tool_name = v_str(m, "tool_name");
        let preview = v_str(m, "content_preview");
        let typ = map_role_to_event_type(&role, &preview, &tool_name);
        *counts.entry(typ.clone()).or_insert(0) += 1;
        let status = if typ == "tool_result" || typ == "assistant" || typ == "user" || typ == "system" {
            "completed"
        } else {
            "observed"
        };
        let event = serde_json::json!({
            "schema": "PGGAgentLoopEvent/v1",
            "session_id": sid,
            "task_id": m.get("task_id").cloned().unwrap_or(serde_json::Value::Null),
            "turn_id": if turn_id > 0 { serde_json::json!(turn_id) } else { serde_json::Value::Null },
            "step_id": v_i64(m, "id"),
            "phase_id": serde_json::Value::Null,
            "type": typ,
            "timestamp": m.get("timestamp").cloned().unwrap_or(serde_json::Value::Null),
            "model": m.get("model").cloned().unwrap_or(serde_json::Value::Null),
            "provider": m.get("provider").cloned().unwrap_or(serde_json::Value::Null),
            "tool_name": if tool_name.is_empty() { serde_json::Value::Null } else { serde_json::json!(tool_name) },
            "status": status,
            "usage": {"token_count": v_i64(m, "token_count")},
            "cost_usd": serde_json::Value::Null,
            "boundary": "state.db/read-only derived event; live tool_request unavailable unless joined from tool ledger"
        });
        events.push(event);
    }

    let mut result_overrides: std::collections::BTreeMap<String, serde_json::Value> = std::collections::BTreeMap::new();

    for le in ledger_events.iter() {
        let typ = v_str(le, "type");
        let normalized_type = match typ.as_str() {
            "tool_request" | "tool_result" | "compact_boundary" | "loop_result" | "stream_event" => typ,
            _ => "stream_event".into(),
        };
        *counts.entry(normalized_type.clone()).or_insert(0) += 1;
        if normalized_type == "loop_result" {
            let sid = v_str(le, "session_id");
            if !sid.is_empty() {
                result_overrides.insert(sid, le.clone());
            }
        }
        let mut event = le.clone();
        if let Some(obj) = event.as_object_mut() {
            obj.insert("schema".into(), serde_json::json!("PGGAgentLoopEvent/v1"));
            obj.insert("type".into(), serde_json::json!(normalized_type));
            obj.entry("boundary").or_insert(serde_json::json!("external ledger joined by Rust mapper"));
        }
        events.push(event);
    }
    events.sort_by(|a, b| {
        let ta = a.get("timestamp").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let tb = b.get("timestamp").and_then(|v| v.as_f64()).unwrap_or(0.0);
        ta.partial_cmp(&tb).unwrap_or(std::cmp::Ordering::Equal)
    });

    let mut results: Vec<serde_json::Value> = Vec::new();
    for s in sessions.iter() {
        let sid = v_str(s, "id");
        let override_event = result_overrides.get(&sid);
        let subtype = override_event
            .map(|e| v_str(e, "result_subtype"))
            .filter(|x| !x.is_empty())
            .unwrap_or_else(|| map_loop_result_subtype(s));
        let default_budget = serde_json::json!({
            "max_turns": serde_json::Value::Null,
            "max_wall_seconds": serde_json::Value::Null,
            "max_budget_usd": serde_json::Value::Null,
            "max_tool_calls": serde_json::Value::Null,
            "max_write_ops": serde_json::Value::Null
        });
        let budget = override_event
            .and_then(|e| e.get("budget").cloned())
            .unwrap_or(default_budget);
        let api_calls = override_event
            .and_then(|e| e.get("api_calls").cloned())
            .unwrap_or(serde_json::Value::Null);
        results.push(serde_json::json!({
            "schema": "PGGAgentLoopResult/v1",
            "session_id": sid,
            "result_subtype": subtype,
            "turn_count": v_i64(s, "message_count"),
            "tool_call_count": v_i64(s, "tool_call_count"),
            "api_calls": api_calls,
            "turn_exit_reason": override_event.and_then(|e| e.get("turn_exit_reason").cloned()).unwrap_or(serde_json::Value::Null),
            "observed_wall_seconds": (v_f64(s, "ended_at") - v_f64(s, "started_at")).max(0.0),
            "estimated_cost_usd": v_f64(s, "estimated_cost_usd"),
            "budget": budget
        }));
    }

    let status = if events.is_empty() && results.is_empty() { "WATCH" } else { "PASS" };
    let output = serde_json::json!({
        "schema": "PGGAgentLoopEventSurface/v1",
        "status": status,
        "event_count": events.len(),
        "result_count": results.len(),
        "event_type_counts": counts,
        "events": events,
        "results": results,
        "mapping_catalog": agent_loop_mapping_catalog(),
        "native": true,
        "boundary": "read-only Exec Dashboard aggregation surface; no mutation; no AGI/external benchmark claim"
    });
    Ok(serde_json::to_string(&output).unwrap_or_default())
}

// ── PyO3 Module ─────────────────────────────────────────────────────────────

#[pymodule]
fn hermes_pgg_archon_utils(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Module info
    m.add("__NATIVE__", true)?;
    m.add("__VERSION__", "0.1.0")?;

    // provenance
    m.add_function(wrap_pyfunction!(provenance, m)?)?;
    // doubt_gamma
    m.add_function(wrap_pyfunction!(classify_decision, m)?)?;
    // planning_runner
    m.add_function(wrap_pyfunction!(build_plan, m)?)?;
    // memory_trace
    m.add_function(wrap_pyfunction!(score, m)?)?;
    // harmrate_gate
    m.add_function(wrap_pyfunction!(compute_harmrate_json, m)?)?;
    m.add_function(wrap_pyfunction!(write_harmrate_report_json, m)?)?;
    // agent_loop_event_surface
    m.add_function(wrap_pyfunction!(agent_loop_event_surface_json, m)?)?;
    m.add_function(wrap_pyfunction!(agent_loop_event_surface_with_ledger_json, m)?)?;

    Ok(())
}

// ── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── provenance tests ──

    #[test]
    fn test_provenance_returns_json() {
        let r = provenance("~/.hermes").unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["schema"], "PGGArchonProvenance/v1");
        assert!(v["node_id"].as_str().unwrap().starts_with("node_"));
        assert!(v["evidence_hash"].as_str().unwrap().len() >= 8);
    }

    #[test]
    fn test_provenance_file_count_non_negative() {
        let r = provenance("~/.hermes").unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        let count = v["file_count"].as_i64().unwrap_or(0);
        assert!(count >= 0, "file_count should be >= 0, got {}", count);
    }

    // ── doubt_gamma tests ──

    #[test]
    fn test_classify_empty_decision() {
        let r = classify_decision("", false).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["doubt_level"], "medium");
        assert!(v["requires_review"].as_bool().unwrap());
    }

    #[test]
    fn test_classify_safe_decision() {
        let r = classify_decision("read file and report", false).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["doubt_level"], "none");
        assert!(!v["requires_review"].as_bool().unwrap());
    }

    #[test]
    fn test_classify_delete() {
        let r = classify_decision("delete the record", false).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert!(v["gamma"].as_f64().unwrap() > 0.0);
        assert!(v["risk_factors"]
            .as_array()
            .unwrap()
            .contains(&"delete".into()));
    }

    #[test]
    fn test_classify_crosses_boundary() {
        let r = classify_decision("review permissions", true).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert!(v["requires_review"].as_bool().unwrap());
        assert!(v["gamma"].as_f64().unwrap() >= 0.4);
    }

    #[test]
    fn test_classify_credential_secret() {
        let r = classify_decision("check credential and secret rotation", false).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        let factors = v["risk_factors"].as_array().unwrap();
        assert!(factors.contains(&"credential".into()));
        assert!(factors.contains(&"secret".into()));
    }

    // ── planning_runner tests ──

    #[test]
    fn test_build_plan_empty() {
        let r = build_plan("[]").unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["total_tasks"], 0);
        assert_eq!(v["slice_count"], 0);
    }

    #[test]
    fn test_build_plan_single_task() {
        let input = r#"[{"id": "a", "name": "Task A", "dependencies": []}]"#;
        let r = build_plan(input).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["total_tasks"], 1);
        assert_eq!(v["slice_count"], 1);
        assert_eq!(v["slices"][0]["task_ids"][0], "a");
    }

    #[test]
    fn test_build_plan_dependency_order() {
        let input = r#"[
            {"id": "b", "name": "Task B", "dependencies": ["a"]},
            {"id": "a", "name": "Task A", "dependencies": []}
        ]"#;
        let r = build_plan(input).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["total_tasks"], 2);
        assert_eq!(v["slice_count"], 2);
        assert_eq!(v["slices"][0]["task_ids"][0], "a");
        assert_eq!(v["slices"][1]["task_ids"][0], "b");
    }

    #[test]
    fn test_build_plan_cycle_detection() {
        let input = r#"[
            {"id": "a", "name": "A", "dependencies": ["b"]},
            {"id": "b", "name": "B", "dependencies": ["a"]}
        ]"#;
        let r = build_plan(input).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        // Cycle should produce at least one warning
        assert!(!v["warnings"]
            .as_array()
            .map(|w| w.is_empty())
            .unwrap_or(true));
        assert_eq!(v["slice_count"], 1);
    }

    #[test]
    fn test_build_plan_duplicate_id() {
        let input = r#"[
            {"id": "a", "name": "A1", "dependencies": []},
            {"id": "a", "name": "A2", "dependencies": []}
        ]"#;
        let r = build_plan(input).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["total_tasks"], 1);
        assert!(v["warnings"]
            .as_array()
            .map(|w| w.len() > 0)
            .unwrap_or(false));
    }

    // ── memory_trace tests ──

    #[test]
    fn test_score_empty_metrics() {
        let r = score("{}", "{}").unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["status"], "BLOCKED");
        assert!(v["warnings"]
            .as_array()
            .map(|w| w.len() > 0)
            .unwrap_or(false));
    }

    #[test]
    fn test_score_non_dict_input() {
        let r = score(r#""not a dict""#, r#"[]"#).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["status"], "BLOCKED");
    }

    #[test]
    fn test_score_pass_combined() {
        let mem = r#"{"learn": 0.9, "search": 0.8, "multimodal": 0.7, "profile": 0.9, "retention": 0.8, "diversity": 0.7}"#;
        let trace = r#"{"decision": 0.8, "reason": 0.9, "result": 0.8, "evidence": 0.9}"#;
        let r = score(mem, trace).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["status"], "PASS");
        assert!(v["combined"].as_f64().unwrap() >= 0.7);
    }

    #[test]
    fn test_score_watch_combined() {
        let mem = r#"{"learn": 0.5, "search": 0.4, "multimodal": 0.3}"#;
        let trace = r#"{"decision": 0.5, "reason": 0.4}"#;
        let r = score(mem, trace).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["status"], "WATCH");
    }

    #[test]
    fn test_score_partial_keys() {
        let mem = r#"{"learn": 0.1}"#;
        let trace = r#"{"decision": 0.1}"#;
        let r = score(mem, trace).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["status"], "BLOCKED");
        assert!(v["sigma_memory"].as_f64().unwrap() >= 0.0);
    }

    // ── harmrate_gate tests ──

    #[test]
    fn test_harmrate_low_risk_allows() {
        let r = compute_harmrate_json(
            r#"{"risk":0.05,"uncertainty":0.05,"source_confidence":0.95}"#,
            0.34,
            0.20,
        )
        .unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["decision"], "ALLOW");
        assert_eq!(v["APEX_MOSS_VERIFIED"], false);
    }

    #[test]
    fn test_harmrate_apex_moss_claim_blocks() {
        let r = compute_harmrate_json(
            r#"{"risk":0.01,"source_confidence":1.0,"apex_moss_verified_claim":true}"#,
            0.34,
            0.20,
        )
        .unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["decision"], "BLOCK");
        assert!(v["reasons"]
            .as_array()
            .unwrap()
            .contains(&"apex_moss_verified_claim_blocked_until_independent_source".into()));
    }

    #[test]
    fn test_harmrate_sensitive_legal_reason() {
        let r = compute_harmrate_json(
            r#"{"risk":0.2,"uncertainty":0.2,"source_confidence":0.7,"task_type":"legal"}"#,
            0.34,
            0.20,
        )
        .unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert!(v["reasons"]
            .as_array()
            .unwrap()
            .contains(&"sensitive_task_stricter_threshold".into()));
    }

    // ── agent_loop_event_surface tests ──

    #[test]
    fn test_agent_loop_event_surface_basic_mapping() {
        let sessions = r#"[{"id":"s1","source":"cli","model":"m","started_at":1.0,"ended_at":3.0,"message_count":3,"tool_call_count":1,"estimated_cost_usd":0.01}]"#;
        let messages = r#"[
            {"id":1,"session_id":"s1","role":"user","timestamp":1.0,"content_preview":"hi","token_count":2,"model":"m"},
            {"id":2,"session_id":"s1","role":"assistant","timestamp":2.0,"content_preview":"thinking","token_count":3,"model":"m"},
            {"id":3,"session_id":"s1","role":"tool","tool_name":"read_file","timestamp":2.5,"content_preview":"ok","token_count":4,"model":"m"}
        ]"#;
        let r = agent_loop_event_surface_json(sessions, messages).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["status"], "PASS");
        assert_eq!(v["event_count"], 3);
        assert_eq!(v["event_type_counts"]["tool_result"], 1);
        assert_eq!(v["results"][0]["result_subtype"], "success");
        assert_eq!(v["events"][2]["turn_id"], 1);
    }

    #[test]
    fn test_agent_loop_event_surface_catalog_has_p1_p2_maps() {
        let r = agent_loop_event_surface_json("[]", "[]").unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["status"], "WATCH");
        assert!(v["mapping_catalog"]["p1_result_subtype_map"].is_object());
        assert!(v["mapping_catalog"]["p2_future_map"].is_object());
    }

    #[test]
    fn test_agent_loop_event_surface_joins_tool_request_ledger() {
        let ledger = r#"[{"schema":"PGGAgentLoopEvent/v1","type":"tool_request","session_id":"s1","timestamp":1.5,"tool_name":"read_file","status":"started"},{"type":"compact_boundary","session_id":"s1","timestamp":2.5,"status":"completed","lossy":true}]"#;
        let r = agent_loop_event_surface_with_ledger_json("[]", "[]", ledger).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["status"], "PASS");
        assert_eq!(v["event_type_counts"]["tool_request"], 1);
        assert_eq!(v["event_type_counts"]["compact_boundary"], 1);
    }

    #[test]
    fn test_agent_loop_event_surface_loop_result_ledger_overrides_subtype_and_budget() {
        let sessions = r#"[{"id":"s1","source":"cli","started_at":1.0,"ended_at":2.0,"message_count":3,"tool_call_count":1}]"#;
        let ledger = r#"[{"schema":"PGGAgentLoopEvent/v1","type":"loop_result","session_id":"s1","timestamp":2.5,"status":"completed","result_subtype":"error_max_turns","api_calls":3,"max_turns":3,"budget":{"max_turns":3,"max_tool_calls":9}}]"#;
        let r = agent_loop_event_surface_with_ledger_json(sessions, "[]", ledger).unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["event_type_counts"]["loop_result"], 1);
        assert_eq!(v["results"][0]["result_subtype"], "error_max_turns");
        assert_eq!(v["results"][0]["api_calls"], 3);
        assert_eq!(v["results"][0]["budget"]["max_turns"], 3);
        assert_eq!(v["results"][0]["budget"]["max_tool_calls"], 9);
    }

}
