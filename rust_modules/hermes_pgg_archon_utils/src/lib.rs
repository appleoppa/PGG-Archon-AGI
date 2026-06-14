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
    format!("node_{}", hash.iter().map(|b| format!("{:02x}", b)).take(8).collect::<String>())
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
    let agent_dir = std::path::Path::new(root).join("hermes-agent").join("agent");
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
    let agent_dir = std::path::Path::new(root).join("hermes-agent").join("agent");
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
        } else if std::fs::metadata(&path).map(|m| m.len() == 0).unwrap_or(true) {
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
        hash.iter().map(|b| format!("{:02x}", b)).collect::<String>()
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
    let mut remaining: std::collections::HashMap<String, Task> = normalized
        .into_iter()
        .map(|t| (t.id.clone(), t))
        .collect();
    let mut done: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut slices: Vec<serde_json::Value> = Vec::new();
    let dep_set: std::collections::HashSet<String> = remaining.keys().cloned().collect();

    while !remaining.is_empty() {
        let ready: Vec<String> = remaining
            .iter()
            .filter(|(tid, t)| {
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
    let mem: serde_json::Value = serde_json::from_str(memory_metrics_json)
        .unwrap_or(serde_json::Value::Null);
    let trace: serde_json::Value = serde_json::from_str(trace_metrics_json)
        .unwrap_or(serde_json::Value::Null);

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

    let mem_keys = &["learn", "search", "multimodal", "profile", "retention", "diversity"];
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
        assert!(v["risk_factors"].as_array().unwrap().contains(&"delete".into()));
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
        assert!(v["warnings"].as_array().map(|w| w.len() > 0).unwrap_or(false));
    }

    // ── memory_trace tests ──

    #[test]
    fn test_score_empty_metrics() {
        let r = score("{}", "{}").unwrap();
        let v: serde_json::Value = serde_json::from_str(&r).unwrap();
        assert_eq!(v["status"], "BLOCKED");
        assert!(v["warnings"].as_array().map(|w| w.len() > 0).unwrap_or(false));
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
}