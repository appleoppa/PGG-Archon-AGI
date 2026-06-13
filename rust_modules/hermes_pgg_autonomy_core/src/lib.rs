use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Probe {
    pub name: String,
    pub status: String,
    pub summary: String,
    pub details: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BacklogItem {
    pub id: String,
    pub priority: String,
    pub title: String,
    pub reason: String,
    pub evidence: Vec<String>,
    pub proposed_next_step: String,
    pub risk: String,
    pub allowed_auto_action: bool,
    pub blocked_by: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirtyFileClassification {
    pub raw: String,
    pub path: String,
    pub git_status: String,
    pub category: String,
    pub risk: String,
    pub owner_hint: String,
    pub safe_checks: Vec<String>,
    pub recommended_action: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyItem {
    pub id: String,
    pub severity: String,
    pub source: String,
    pub status: String,
    pub summary: String,
    pub allowed_auto_action: Option<bool>,
    pub blocked_by: Option<Vec<String>>,
    pub boundary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalySummary {
    pub schema: String,
    pub status: String,
    pub count: usize,
    pub severity_counts: std::collections::HashMap<String, usize>,
    pub items: Vec<AnomalyItem>,
    pub boundary: String,
}

// ──────────────────────────────────────────────
// Dirty classification — pure string logic
// ──────────────────────────────────────────────

const HARDCODED_LOW_RISK_PATHS: &[(&str, &str, &str, &str)] = &[
    ("agent/pgg_archon_autonomy_controller.py", "current_autonomy_controller", "LOW_CURRENT_TASK", "current_session"),
    ("tests/test_pgg_archon_autonomy_controller.py", "current_autonomy_controller", "LOW_CURRENT_TASK", "current_session"),
];

const OMNIROUTE_PATHS: &[&str] = &[
    "agent/pgg_archon_external_benchmark_provider_run.py",
    "agent/pgg_archon_quantum_channel_router.py",
    "hermes_cli/web_server.py",
];

fn classify_dirty_line(line: &str) -> DirtyFileClassification {
    let raw = line.trim_end_matches('\n');
    let chars: Vec<char> = raw.chars().collect();
    let (git_status, path_str) = if raw.len() >= 3 {
        let st = if raw.len() >= 2 { raw[..2].trim().to_string() } else { String::new() };
        let pth = if raw.len() > 3 { raw[3..].trim().to_string() } else { raw.trim().to_string() };
        (if st.is_empty() { "??".to_string() } else { st }, pth)
    } else {
        ("??".to_string(), raw.trim().to_string())
    };

    let (category, risk, owner_hint, recommended) = categorize(&path_str);

    let mut safe_checks: Vec<String> = Vec::new();

    if path_str.ends_with(".py") {
        safe_checks.push(format!("py_compile:{}", path_str));
    }
    if path_str.starts_with("tests/") && path_str.ends_with(".py") {
        safe_checks.push(format!("pytest:{}", path_str));
    }
    if path_str.ends_with("package-lock.json") {
        safe_checks.push("npm_audit_scope".to_string());
    }
    if path_str.ends_with("Cargo.lock") || path_str.ends_with("Cargo.toml") {
        safe_checks.push("cargo_test_or_audit_scope".to_string());
    }

    DirtyFileClassification {
        raw: raw.to_string(),
        path: path_str,
        git_status,
        category,
        risk,
        owner_hint,
        safe_checks,
        recommended_action: recommended,
    }
}

fn categorize(path: &str) -> (String, String, String, String) {
    for (p, cat, risk, hint) in HARDCODED_LOW_RISK_PATHS {
        if *p == path {
            return (
                cat.to_string(),
                risk.to_string(),
                hint.to_string(),
                "Run py_compile/pytest, then scoped commit if clean.".to_string(),
            );
        }
    }
    if OMNIROUTE_PATHS.contains(&path) {
        return (
            "omniroute_provider_trace_or_status".to_string(),
            "LOW_TO_MEDIUM_FOREIGN_SESSION".to_string(),
            "likely_other_session_or_adjacent_omniroute_work".to_string(),
            "Do not mix into autonomy commit; run focused diff/tests in separate batch.".to_string(),
        );
    }
    if path.ends_with("package-lock.json") || path.ends_with("Cargo.lock") {
        return (
            "lockfile_supply_chain".to_string(),
            "LOW_TO_MEDIUM_LOCKFILE".to_string(),
            "dependency_governance".to_string(),
            "Run scoped audit/build tests before commit.".to_string(),
        );
    }
    if path.ends_with(".py") {
        return (
            "python_code".to_string(),
            "MEDIUM_CODE".to_string(),
            "unknown_python_change".to_string(),
            "Run py_compile and focused pytest before commit.".to_string(),
        );
    }
    if path.contains("/target/") || path.ends_with(".pyc") || path.contains("__pycache__") {
        return (
            "generated_artifact".to_string(),
            "LOW_SHOULD_IGNORE_OR_REMOVE".to_string(),
            "generated".to_string(),
            "Do not commit; remove or add ignore rule if appropriate.".to_string(),
        );
    }
    (
        "unknown_dirty".to_string(),
        "MEDIUM_REVIEW_REQUIRED".to_string(),
        "unknown_or_foreign_session".to_string(),
        "Inspect scoped diff before any add/commit/revert.".to_string(),
    )
}

fn classify_dirty_lines(lines: Vec<String>) -> Vec<DirtyFileClassification> {
    lines
        .into_iter()
        .filter(|l| !l.trim().is_empty())
        .map(|l| classify_dirty_line(&l))
        .collect()
}

fn dirty_summary(classifications: &[DirtyFileClassification]) -> serde_json::Value {
    let mut by_category: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    let mut by_risk: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    for item in classifications {
        *by_category.entry(item.category.clone()).or_insert(0) += 1;
        *by_risk.entry(item.risk.clone()).or_insert(0) += 1;
    }
    let items: Vec<serde_json::Value> = classifications
        .iter()
        .take(50)
        .map(|x| serde_json::to_value(x).unwrap_or_default())
        .collect();
    serde_json::json!({
        "count": classifications.len(),
        "by_category": by_category,
        "by_risk": by_risk,
        "items": items,
    })
}

fn dirty_priority(classifications: &[DirtyFileClassification]) -> String {
    if classifications.is_empty() {
        return "PASS".to_string();
    }
    let p0_risks = ["LOW_CURRENT_TASK", "HIGH_CREDENTIAL", "HIGH_SECURITY"];
    let has_p0 = classifications
        .iter()
        .any(|c| p0_risks.contains(&c.risk.as_str()) || c.owner_hint == "current_session");
    if has_p0 {
        "P0".to_string()
    } else {
        "P1".to_string()
    }
}

// ──────────────────────────────────────────────
// Backlog from probes — pure aggregation
// ──────────────────────────────────────────────

fn backlog_from_probes(probes: Vec<Probe>) -> Vec<BacklogItem> {
    let by_name: std::collections::HashMap<String, Probe> = probes
        .into_iter()
        .map(|p| (p.name.clone(), p))
        .collect();

    let mut items: Vec<BacklogItem> = Vec::new();

    // Git probe
    if let Some(git) = by_name.get("git_status") {
        if git.status != "PASS_CLEAN" {
            let classification = git.details.get("classification").and_then(|v| v.as_object());
            let category_bits: Vec<String> = classification
                .and_then(|c| c.get("by_category"))
                .and_then(|v| v.as_object())
                .map(|obj| {
                    obj.iter()
                        .map(|(k, v)| format!("category:{}={}", k, v.as_i64().unwrap_or(0)))
                        .collect()
                })
                .unwrap_or_default();
            let priority = git
                .details
                .get("dirty_priority")
                .and_then(|v| v.as_str())
                .map(|s| if s == "P0" { "P0" } else { "P1" })
                .unwrap_or("P1");
            let evidence: Vec<String> = std::iter::once(git.summary.clone())
                .chain(category_bits.clone())
                .collect();
            items.push(BacklogItem {
                id: format!("{}_dirty_repo_classify", priority),
                priority: priority.to_string(),
                title: "Classify dirty repository changes before further autonomous writes".to_string(),
                reason: "dirty worktree can contaminate future commits and completion claims".to_string(),
                evidence,
                proposed_next_step: "Use dirty classification to separate current_task vs foreign_session; run safe_checks only, then scoped commit/quarantine in separate batches.".to_string(),
                risk: "LOW_READ_ONLY".to_string(),
                allowed_auto_action: true,
                blocked_by: vec![],
            });
        }
    }

    // Memory probe
    if let Some(mem) = by_name.get("memory_runtime_health") {
        if mem.status != "PASS" {
            items.push(BacklogItem {
                id: "P0_memory_health_watch".to_string(),
                priority: "P0".to_string(),
                title: "Restore prompt memory health with backup-preserving compaction".to_string(),
                reason: "memory health WATCH risks prompt drift or oversized injected context".to_string(),
                evidence: vec![mem.summary.clone()],
                proposed_next_step: "Create preimage archive, merge duplicate USER/MEMORY entries only, run memory_runtime_health readback.".to_string(),
                risk: "MEDIUM_MEMORY_WRITE".to_string(),
                allowed_auto_action: false,
                blocked_by: vec!["requires backup and explicit memory-write gate".to_string()],
            });
        }
    }

    // NPM audit probe
    if let Some(npm) = by_name.get("root_npm_audit") {
        if npm.status == "WATCH" {
            let vulns_str = npm
                .details
                .get("vulnerabilities")
                .map(|v| serde_json::to_string(v).unwrap_or_default())
                .unwrap_or_default();
            items.push(BacklogItem {
                id: "P1_root_npm_audit_watch".to_string(),
                priority: "P1".to_string(),
                title: "Triage root npm audit vulnerabilities".to_string(),
                reason: "supply-chain vulnerabilities remain in lockfile".to_string(),
                evidence: vec![vulns_str],
                proposed_next_step: "Run scoped npm audit detail; prefer package-lock-only minimal update; build/test before commit.".to_string(),
                risk: "LOW_TO_MEDIUM_LOCKFILE".to_string(),
                allowed_auto_action: true,
                blocked_by: vec![],
            });
        }
    }

    // Skillflow probe
    if let Some(sf) = by_name.get("skillflow_readiness") {
        if sf.status == "HOLD" {
            items.push(BacklogItem {
                id: "P1_skillflow_hold_truth_boundary".to_string(),
                priority: "P1".to_string(),
                title: "Keep SkillFlow in HOLD until corrected live evidence exists".to_string(),
                reason: "user flagged real_live counters as possibly fabricated/drifted".to_string(),
                evidence: vec![sf.summary.clone()],
                proposed_next_step: "Read corrected readiness ledgers only; do not promote route_enforce or production answer-chain.".to_string(),
                risk: "LOW_READ_ONLY".to_string(),
                allowed_auto_action: true,
                blocked_by: vec![],
            });
        }
    }

    // System map probe
    if let Some(sm) = by_name.get("system_map") {
        if sm.status != "PASS" {
            items.push(BacklogItem {
                id: "P1_system_map_unavailable".to_string(),
                priority: "P1".to_string(),
                title: "Repair or regenerate pgg_system_map_status read-only entrypoint".to_string(),
                reason: "autonomy controller depends on stable system map status".to_string(),
                evidence: vec![sm.summary.clone()],
                proposed_next_step: "Inspect CLI path, run py_compile, restore from manifest report if needed.".to_string(),
                risk: "LOW_TO_MEDIUM_CODE_FIX".to_string(),
                allowed_auto_action: true,
                blocked_by: vec![],
            });
        }
    }

    // Default P2 item if nothing found
    if items.is_empty() {
        items.push(BacklogItem {
            id: "P2_autonomy_observation_loop".to_string(),
            priority: "P2".to_string(),
            title: "Enable periodic read-only autonomy planning observation".to_string(),
            reason: "no P0/P1 blockers detected; next autonomy gap is cross-session proactive planning".to_string(),
            evidence: vec!["all core probes PASS/HOLD-expected".to_string()],
            proposed_next_step: "Create low-frequency read-only launchd/LIGHT plan runner after one more manual observation cycle.".to_string(),
            risk: "MEDIUM_SCHEDULER_WRITE".to_string(),
            allowed_auto_action: false,
            blocked_by: vec!["scheduler/launchd write requires explicit scoped landing gate".to_string()],
        });
    }

    // Sort by priority
    let priority_order = |p: &str| -> u8 {
        match p {
            "P0" => 0,
            "P1" => 1,
            "P2" => 2,
            _ => 9,
        }
    };
    items.sort_by_key(|x| (priority_order(&x.priority), x.id.clone()));
    items
}

// ──────────────────────────────────────────────
// Anomaly summary
// ──────────────────────────────────────────────

fn anomaly_summary(probes: Vec<Probe>, backlog: Vec<BacklogItem>) -> AnomalySummary {
    let mut anomalies: Vec<AnomalyItem> = Vec::new();

    for probe in &probes {
        if !probe.status.starts_with("WATCH") {
            continue;
        }
        let severity = if probe.name == "memory_runtime_health" {
            "P0"
        } else if probe.name == "git_status" {
            let dp = probe
                .details
                .get("dirty_priority")
                .and_then(|v| v.as_str());
            if dp == Some("P0") {
                "P0"
            } else {
                "P1"
            }
        } else {
            "P1"
        };
        anomalies.push(AnomalyItem {
            id: format!("{}_{}", severity, probe.name),
            severity: severity.to_string(),
            source: probe.name.clone(),
            status: probe.status.clone(),
            summary: probe.summary.clone(),
            allowed_auto_action: None,
            blocked_by: None,
            boundary: "read_only_observation_no_mutation".to_string(),
        });
    }

    for item in &backlog {
        if item.priority == "P0" || item.priority == "P1" {
            anomalies.push(AnomalyItem {
                id: item.id.clone(),
                severity: item.priority.clone(),
                source: "backlog".to_string(),
                status: "OPEN".to_string(),
                summary: item.title.clone(),
                allowed_auto_action: Some(item.allowed_auto_action),
                blocked_by: Some(item.blocked_by.clone()),
                boundary: "backlog_item_only_no_mutation".to_string(),
            });
        }
    }

    let mut severity_counts: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    for item in &anomalies {
        *severity_counts.entry(item.severity.clone()).or_insert(0) += 1;
    }

    let has_p0 = anomalies.iter().any(|x| x.severity == "P0");
    AnomalySummary {
        schema: "PGGAutonomyAnomalySummary/v0.4".to_string(),
        status: if has_p0 {
            "WATCH_P0_PRESENT".to_string()
        } else {
            "PASS_NO_P0".to_string()
        },
        count: anomalies.len(),
        severity_counts,
        items: anomalies.into_iter().take(50).collect(),
        boundary: "read-only anomaly summary; does not execute fixes or mutate scheduler/security/provider/credentials".to_string(),
    }
}

// ──────────────────────────────────────────────
// Compact observation payload
// ──────────────────────────────────────────────

fn compact_observation_payload(
    probes: Vec<Probe>,
    backlog: Vec<BacklogItem>,
    summary: &serde_json::Value,
    anomaly: &AnomalySummary,
) -> serde_json::Value {
    let p0_items: Vec<serde_json::Value> = anomaly
        .items
        .iter()
        .filter(|x| x.severity == "P0")
        .map(|x| serde_json::to_value(x).unwrap_or_default())
        .collect();

    serde_json::json!({
        "schema": "PGGAutonomyCompactObservation/v0.8",
        "status": if p0_items.is_empty() { "HEARTBEAT_OK" } else { "ALERT_P0" },
        "anomaly_status": anomaly.status,
        "severity_counts": anomaly.severity_counts,
        "priority_counts": summary.get("priority_counts"),
        "p0_count": p0_items.len(),
        "probe_count": probes.len(),
        "backlog_count": backlog.len(),
        "boundary": "compact read-only heartbeat/alert; no fixes, no commits, no provider/config/scheduler/security/production/legal mutation",
    })
}

// ──────────────────────────────────────────────
// PyO3 exports
// ──────────────────────────────────────────────

#[pyfunction]
fn native_classify_dirty_line(line: &str) -> PyResult<String> {
    let result = classify_dirty_line(line);
    serde_json::to_string(&result).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn native_classify_dirty_lines(lines: Vec<String>) -> PyResult<String> {
    let results = classify_dirty_lines(lines);
    serde_json::to_string(&results).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn native_dirty_summary(json_str: &str) -> PyResult<String> {
    let classifications: Vec<DirtyFileClassification> =
        serde_json::from_str(json_str).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let result = dirty_summary(&classifications);
    serde_json::to_string(&result).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn native_dirty_priority(json_str: &str) -> PyResult<String> {
    let classifications: Vec<DirtyFileClassification> =
        serde_json::from_str(json_str).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok(dirty_priority(&classifications))
}

#[pyfunction]
fn native_backlog_from_probes(json_str: &str) -> PyResult<String> {
    let probes: Vec<Probe> =
        serde_json::from_str(json_str).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let result = backlog_from_probes(probes);
    serde_json::to_string(&result).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn native_anomaly_summary(probes_json: &str, backlog_json: &str) -> PyResult<String> {
    let probes: Vec<Probe> =
        serde_json::from_str(probes_json).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let backlog: Vec<BacklogItem> =
        serde_json::from_str(backlog_json).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let result = anomaly_summary(probes, backlog);
    serde_json::to_string(&result).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn native_compact_observation(probes_json: &str, backlog_json: &str, summary_json: &str, anomaly_json: &str) -> PyResult<String> {
    let probes: Vec<Probe> =
        serde_json::from_str(probes_json).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let backlog: Vec<BacklogItem> =
        serde_json::from_str(backlog_json).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let summary: serde_json::Value =
        serde_json::from_str(summary_json).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let anomaly: AnomalySummary =
        serde_json::from_str(anomaly_json).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let result = compact_observation_payload(probes, backlog, &summary, &anomaly);
    serde_json::to_string(&result).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn native_info() -> String {
    format!(
        "hermes_pgg_autonomy_core v{} | {} functions | {} lines",
        "0.1.0",
        "7",
        env!("CARGO_PKG_NAME")
    )
}

#[pymodule]
fn hermes_pgg_autonomy_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_classify_dirty_line, m)?)?;
    m.add_function(wrap_pyfunction!(native_classify_dirty_lines, m)?)?;
    m.add_function(wrap_pyfunction!(native_dirty_summary, m)?)?;
    m.add_function(wrap_pyfunction!(native_dirty_priority, m)?)?;
    m.add_function(wrap_pyfunction!(native_backlog_from_probes, m)?)?;
    m.add_function(wrap_pyfunction!(native_anomaly_summary, m)?)?;
    m.add_function(wrap_pyfunction!(native_compact_observation, m)?)?;
    m.add_function(wrap_pyfunction!(native_info, m)?)?;
    Ok(())
}

// ──────────────────────────────────────────────
// Tests
// ──────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_classify_dirty_line_known_path() {
        let r = classify_dirty_line(" M agent/pgg_archon_autonomy_controller.py");
        assert_eq!(r.category, "current_autonomy_controller");
        assert_eq!(r.risk, "LOW_CURRENT_TASK");
        assert_eq!(r.owner_hint, "current_session");
        assert!(r.safe_checks.contains(&"py_compile:agent/pgg_archon_autonomy_controller.py".to_string()));
    }

    #[test]
    fn test_classify_dirty_line_test_path() {
        let r = classify_dirty_line(" M tests/test_pgg_archon_autonomy_controller.py");
        assert_eq!(r.category, "current_autonomy_controller");
        assert!(r.safe_checks.contains(&"pytest:tests/test_pgg_archon_autonomy_controller.py".to_string()));
    }

    #[test]
    fn test_classify_dirty_line_omniroute() {
        let r = classify_dirty_line(" M agent/pgg_archon_external_benchmark_provider_run.py");
        assert_eq!(r.category, "omniroute_provider_trace_or_status");
    }

    #[test]
    fn test_classify_dirty_line_python() {
        let r = classify_dirty_line(" M agent/some_other_module.py");
        assert_eq!(r.category, "python_code");
        assert_eq!(r.risk, "MEDIUM_CODE");
    }

    #[test]
    fn test_classify_dirty_line_lockfile() {
        let r = classify_dirty_line(" M package-lock.json");
        assert_eq!(r.category, "lockfile_supply_chain");
        assert!(r.safe_checks.contains(&"npm_audit_scope".to_string()));
    }

    #[test]
    fn test_classify_dirty_line_cargo_lock() {
        let r = classify_dirty_line(" M Cargo.lock");
        assert_eq!(r.category, "lockfile_supply_chain");
        assert!(r.safe_checks.contains(&"cargo_test_or_audit_scope".to_string()));
    }

    #[test]
    fn test_classify_dirty_line_generated() {
        let r = classify_dirty_line("?? rust_modules/target/debug/build/");
        assert_eq!(r.category, "generated_artifact");
    }

    #[test]
    fn test_classify_dirty_line_pyc() {
        let r = classify_dirty_line("?? __pycache__/foo.pyc");
        assert_eq!(r.category, "generated_artifact");
    }

    #[test]
    fn test_classify_dirty_line_unknown() {
        let r = classify_dirty_line("?? random_file.txt");
        assert_eq!(r.category, "unknown_dirty");
        assert_eq!(r.risk, "MEDIUM_REVIEW_REQUIRED");
    }

    #[test]
    fn test_classify_dirty_line_untracked() {
        let r = classify_dirty_line("?? new_file.py");
        assert_eq!(r.git_status, "??");
        assert_eq!(r.category, "python_code");
    }

    #[test]
    fn test_classify_dirty_lines_empty() {
        let r = classify_dirty_lines(vec![]);
        assert!(r.is_empty());
    }

    #[test]
    fn test_classify_dirty_lines_filters_empty() {
        let r = classify_dirty_lines(vec!["".to_string(), " M foo.py".to_string(), "  ".to_string()]);
        assert_eq!(r.len(), 1);
    }

    #[test]
    fn test_dirty_priority_empty() {
        assert_eq!(dirty_priority(&[]), "PASS");
    }

    #[test]
    fn test_dirty_priority_p0() {
        let c = classify_dirty_line(" M agent/pgg_archon_autonomy_controller.py");
        assert_eq!(dirty_priority(&[c]), "P0");
    }

    #[test]
    fn test_dirty_priority_p1() {
        let c = classify_dirty_line(" M package-lock.json");
        assert_eq!(dirty_priority(&[c]), "P1");
    }

    #[test]
    fn test_dirty_summary_counts() {
        let lines = vec![
            " M agent/pgg_archon_autonomy_controller.py".to_string(),
            " M package-lock.json".to_string(),
            "?? unknown.xyz".to_string(),
        ];
        let cfgs = classify_dirty_lines(lines);
        let s = dirty_summary(&cfgs);
        assert_eq!(s["count"].as_i64().unwrap(), 3);
        assert!(s["by_category"].as_object().unwrap().contains_key("current_autonomy_controller"));
        assert!(s["by_category"].as_object().unwrap().contains_key("lockfile_supply_chain"));
        assert!(s["by_category"].as_object().unwrap().contains_key("unknown_dirty"));
    }

    #[test]
    fn test_backlog_from_probes_git_dirty() {
        let probes = vec![Probe {
            name: "git_status".to_string(),
            status: "WATCH_DIRTY_P0_CURRENT_TASK".to_string(),
            summary: "dirty_lines=1".to_string(),
            details: serde_json::json!({
                "dirty_priority": "P0",
                "classification": {"by_category": {"current_autonomy_controller": 1}}
            }),
        }];
        let items = backlog_from_probes(probes);
        assert!(!items.is_empty());
        assert!(items[0].id.starts_with("P0"));
    }

    #[test]
    fn test_backlog_from_probes_git_clean() {
        let probes = vec![Probe {
            name: "git_status".to_string(),
            status: "PASS_CLEAN".to_string(),
            summary: "dirty_lines=0".to_string(),
            details: serde_json::json!({}),
        }];
        let items = backlog_from_probes(probes);
        assert_eq!(items.len(), 1); // P2 default
        assert_eq!(items[0].priority, "P2");
    }

    #[test]
    fn test_backlog_from_probes_memory_watch() {
        let probes = vec![
            Probe {
                name: "git_status".to_string(),
                status: "PASS_CLEAN".to_string(),
                summary: "clean".to_string(),
                details: serde_json::json!({}),
            },
            Probe {
                name: "memory_runtime_health".to_string(),
                status: "WATCH".to_string(),
                summary: "memory high".to_string(),
                details: serde_json::json!({}),
            },
        ];
        let items = backlog_from_probes(probes);
        let has_memory = items.iter().any(|i| i.id == "P0_memory_health_watch");
        assert!(has_memory);
    }

    #[test]
    fn test_backlog_npm_watch() {
        let probes = vec![
            Probe {
                name: "git_status".to_string(),
                status: "PASS_CLEAN".to_string(),
                summary: "clean".to_string(),
                details: serde_json::json!({}),
            },
            Probe {
                name: "root_npm_audit".to_string(),
                status: "WATCH".to_string(),
                summary: "vulns=3".to_string(),
                details: serde_json::json!({"vulnerabilities": {"total": 3}}),
            },
        ];
        let items = backlog_from_probes(probes);
        let has_npm = items.iter().any(|i| i.id == "P1_root_npm_audit_watch");
        assert!(has_npm);
    }

    #[test]
    fn test_backlog_skillflow_hold() {
        let probes = vec![
            Probe {
                name: "git_status".to_string(),
                status: "PASS_CLEAN".to_string(),
                summary: "clean".to_string(),
                details: serde_json::json!({}),
            },
            Probe {
                name: "skillflow_readiness".to_string(),
                status: "HOLD".to_string(),
                summary: "HOLD".to_string(),
                details: serde_json::json!({}),
            },
        ];
        let items = backlog_from_probes(probes);
        let has_sf = items.iter().any(|i| i.id == "P1_skillflow_hold_truth_boundary");
        assert!(has_sf);
    }

    #[test]
    fn test_backlog_sort_order() {
        let probes = vec![
            Probe {
                name: "git_status".to_string(),
                status: "WATCH_DIRTY_P0".to_string(),
                summary: "dirty".to_string(),
                details: serde_json::json!({"dirty_priority": "P0", "classification": {"by_category": {"current_autonomy_controller": 1}}}),
            },
            Probe {
                name: "root_npm_audit".to_string(),
                status: "WATCH".to_string(),
                summary: "vulns".to_string(),
                details: serde_json::json!({"vulnerabilities": {"total": 2}}),
            },
        ];
        let items = backlog_from_probes(probes);
        assert_eq!(items[0].priority, "P0");
        assert_eq!(items[1].priority, "P1");
    }

    #[test]
    fn test_anomaly_summary_p0() {
        let probes = vec![Probe {
            name: "memory_runtime_health".to_string(),
            status: "WATCH".to_string(),
            summary: "memory high".to_string(),
            details: serde_json::json!({}),
        }];
        let backlog = vec![BacklogItem {
            id: "P0_memory_health_watch".to_string(),
            priority: "P0".to_string(),
            title: "test".to_string(),
            reason: "test".to_string(),
            evidence: vec![],
            proposed_next_step: "test".to_string(),
            risk: "MEDIUM".to_string(),
            allowed_auto_action: false,
            blocked_by: vec!["test".to_string()],
        }];
        let result = anomaly_summary(probes, backlog);
        assert_eq!(result.status, "WATCH_P0_PRESENT");
    }

    #[test]
    fn test_anomaly_summary_no_p0() {
        let probes = vec![Probe {
            name: "git_status".to_string(),
            status: "PASS_CLEAN".to_string(),
            summary: "clean".to_string(),
            details: serde_json::json!({}),
        }];
        let result = anomaly_summary(probes, vec![]);
        assert_eq!(result.status, "PASS_NO_P0");
    }

    #[test]
    fn test_compact_heartbeat_ok() {
        let probes = vec![Probe {
            name: "git_status".to_string(),
            status: "PASS_CLEAN".to_string(),
            summary: "clean".to_string(),
            details: serde_json::json!({}),
        }];
        let summary = serde_json::json!({"priority_counts": {}});
        let anomaly = anomaly_summary(probes.clone(), vec![]);
        let result = compact_observation_payload(probes, vec![], &summary, &anomaly);
        assert_eq!(result["status"], "HEARTBEAT_OK");
        assert_eq!(result["p0_count"].as_i64().unwrap(), 0);
    }

    #[test]
    fn test_round_trip_serialization() {
        let r = classify_dirty_line(" M foo.py");
        let json = serde_json::to_string(&r).unwrap();
        let back: DirtyFileClassification = serde_json::from_str(&json).unwrap();
        assert_eq!(r.path, back.path);
        assert_eq!(r.category, back.category);
    }
}