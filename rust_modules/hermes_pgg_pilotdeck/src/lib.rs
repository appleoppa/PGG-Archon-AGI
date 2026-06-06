//! Hermes PGG PilotDeck absorption core v0.1
//!
//! Rust-native, additive evaluator for PilotDeck-derived modular runtime patterns.
//! Boundary: pure computation / JSON config generation only. This module does not
//! run PilotDeck, call providers, or mutate Hermes scheduler/security boundaries.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

const SCHEMA: &str = "HermesPGGPilotDeckAbsorption/v1";
const GATE_SEQUENCE: [&str; 7] = [
    "SourceExists",
    "ConfigEnabled",
    "BuildTest",
    "RuntimeHealth",
    "ProtocolSmoke",
    "EvidenceReport",
    "ManifestUpdate",
];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "UPPERCASE")]
pub enum ModuleStatus {
    Pass,
    Watch,
    Blocked,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateEvidence {
    pub source_exists: bool,
    pub config_enabled: bool,
    pub build_test_passed: bool,
    pub runtime_health_passed: bool,
    pub protocol_smoke_passed: bool,
    pub evidence_report_written: bool,
    pub manifest_updated: bool,
}

impl GateEvidence {
    fn all_pass(&self) -> bool {
        self.source_exists
            && self.config_enabled
            && self.build_test_passed
            && self.runtime_health_passed
            && self.protocol_smoke_passed
            && self.evidence_report_written
            && self.manifest_updated
    }

    fn any_runtime(&self) -> bool {
        self.config_enabled || self.runtime_health_passed || self.protocol_smoke_passed
    }

    fn missing(&self) -> Vec<&'static str> {
        let pairs = [
            ("SourceExists", self.source_exists),
            ("ConfigEnabled", self.config_enabled),
            ("BuildTest", self.build_test_passed),
            ("RuntimeHealth", self.runtime_health_passed),
            ("ProtocolSmoke", self.protocol_smoke_passed),
            ("EvidenceReport", self.evidence_report_written),
            ("ManifestUpdate", self.manifest_updated),
        ];
        pairs
            .iter()
            .filter_map(|(name, ok)| if *ok { None } else { Some(*name) })
            .collect()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PilotDeckModule {
    pub name: String,
    pub source_path: String,
    pub hermes_pattern: String,
    pub evidence: GateEvidence,
    pub boundary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleVerdict {
    pub name: String,
    pub status: ModuleStatus,
    pub missing_gates: Vec<String>,
    pub hermes_pattern: String,
    pub boundary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AbsorptionOutput {
    pub schema: String,
    pub total: usize,
    pub pass: usize,
    pub watch: usize,
    pub blocked: usize,
    pub verdicts: Vec<ModuleVerdict>,
    pub gate_sequence: Vec<String>,
    pub recommended_config: serde_json::Value,
    pub audit_hash: String,
    pub evidence_semantics: String,
    pub boundary: String,
}

fn decide_status(module: &PilotDeckModule) -> ModuleStatus {
    if !module.evidence.source_exists {
        return ModuleStatus::Blocked;
    }
    if module.evidence.all_pass() {
        ModuleStatus::Pass
    } else if module.evidence.any_runtime() {
        ModuleStatus::Watch
    } else {
        ModuleStatus::Watch
    }
}

fn hash_output(verdicts: &[ModuleVerdict], config: &serde_json::Value) -> String {
    let payload = serde_json::json!({
        "schema": SCHEMA,
        "verdicts": verdicts,
        "config": config,
    });
    let mut hasher = Sha256::new();
    hasher.update(payload.to_string().as_bytes());
    format!("sha256:{:x}", hasher.finalize())
}

pub fn default_modules() -> Vec<PilotDeckModule> {
    let source_only = GateEvidence {
        source_exists: true,
        config_enabled: false,
        build_test_passed: false,
        runtime_health_passed: false,
        protocol_smoke_passed: false,
        evidence_report_written: false,
        manifest_updated: false,
    };
    let blocked = GateEvidence {
        source_exists: false,
        config_enabled: false,
        build_test_passed: true,
        runtime_health_passed: false,
        protocol_smoke_passed: false,
        evidence_report_written: true,
        manifest_updated: true,
    };
    let b = "Sample/declared source evidence only; this Rust crate does not prove Hermes runtime integration.";
    vec![
        module("Always-On Discovery", "src/always-on", "bounded_background_trigger", source_only.clone(), b),
        module("Evolution", "src/evolution", "blocked_missing_source_do_not_claim", blocked, "Current PilotDeck repo lacks src/evolution; Hermes uses its own PGG/Rust evolution modules."),
        module("Router Orchestrator", "src/router/orchestrate", "orchestrator_tool_allowlist", source_only.clone(), b),
        module("Token Saver", "src/router/tokenSaver", "tiered_token_hygiene", source_only.clone(), b),
        module("Router Retry", "src/router/retry", "bounded_retry", source_only.clone(), b),
        module("Router Fallback", "src/router/fallback", "scenario_fallback_tool_capability", source_only.clone(), b),
        module("Router Stats", "src/router/stats", "usage_cost_evidence", source_only.clone(), b),
        module("Custom Router", "src/router/customRouter", "tagged_reversible_router_hook", source_only.clone(), b),
        module("SubAgent", "src/agent/sub", "subagent_parent_verification", source_only.clone(), b),
        module("Lifecycle Hooks", "src/lifecycle", "reload_changed_paths_readback", source_only.clone(), b),
        module("Permission", "src/permission", "allow_deny_normalized_rules", source_only.clone(), b),
        module("MCP", "src/mcp", "runtime_ready_listtools_smoke", source_only.clone(), b),
        module("Turn", "src/agent/turn", "turn_state_not_history_only", source_only.clone(), b),
        module("Gateway", "src/gateway", "protocol_smoke_not_port_only", source_only.clone(), b),
        module("Workspace Provider", "src/always-on/workspace", "isolated_workspace_snapshot", source_only, b),
    ]
}

fn module(
    name: &str,
    source_path: &str,
    hermes_pattern: &str,
    evidence: GateEvidence,
    boundary: &str,
) -> PilotDeckModule {
    PilotDeckModule {
        name: name.to_string(),
        source_path: source_path.to_string(),
        hermes_pattern: hermes_pattern.to_string(),
        evidence,
        boundary: boundary.to_string(),
    }
}

pub fn recommended_config() -> serde_json::Value {
    serde_json::json!({
        "schema": "HermesPilotDeckAbsorbedPatterns/v1",
        "gate_sequence": GATE_SEQUENCE,
        "routing": {
            "orchestrator_tool_allowlist": ["delegate_task", "read_file", "search_files", "skill_view"],
            "fallback_requires_tool_capability": true,
            "retry": { "max_attempts": 2, "transient_only": true },
            "custom_router_hooks": { "tagged_only": true, "reversible": true, "smoke_required": true }
        },
        "permissions": {
            "allow_read_only_smoke": true,
            "deny_destructive_without_scope": ["rm*", "sudo*", "credential edits", "scheduler/security boundary"]
        },
        "mcp_bridge_gate": ["config_parse", "runtime_ready", "list_tools", "optional_call_smoke"],
        "workspace": {
            "hermes_artifacts_root": "~/.hermes/workspace/",
            "independent_agents_hidden_home": true,
            "retain_snapshots_for_audit": true
        },
        "completion_language": {
            "PASS": "source/config/runtime/protocol/evidence/manifest all verified",
            "WATCH": "partial evidence; do not claim complete",
            "BLOCKED": "source or dependency absent"
        }
    })
}

pub fn evaluate_modules(modules: &[PilotDeckModule]) -> AbsorptionOutput {
    let verdicts: Vec<ModuleVerdict> = modules
        .iter()
        .map(|m| ModuleVerdict {
            name: m.name.clone(),
            status: decide_status(m),
            missing_gates: m
                .evidence
                .missing()
                .into_iter()
                .map(str::to_string)
                .collect(),
            hermes_pattern: m.hermes_pattern.clone(),
            boundary: m.boundary.clone(),
        })
        .collect();
    let mut counts: BTreeMap<String, usize> = BTreeMap::new();
    for v in &verdicts {
        let key = format!("{:?}", v.status).to_uppercase();
        *counts.entry(key).or_insert(0) += 1;
    }
    let config = recommended_config();
    AbsorptionOutput {
        schema: SCHEMA.to_string(),
        total: verdicts.len(),
        pass: *counts.get("PASS").unwrap_or(&0),
        watch: *counts.get("WATCH").unwrap_or(&0),
        blocked: *counts.get("BLOCKED").unwrap_or(&0),
        audit_hash: hash_output(&verdicts, &config),
        verdicts,
        gate_sequence: GATE_SEQUENCE.iter().map(|s| s.to_string()).collect(),
        recommended_config: config,
        evidence_semantics: "Default modules are sample declared-source fixtures. PASS requires caller-supplied evidence that every gate is actually verified; this crate does not prove runtime integration by itself.".to_string(),
        boundary: "Rust-native additive evaluator/config generator only; does not run PilotDeck, call providers, mutate Hermes scheduler/security, prove runtime integration, or prove AGI.".to_string(),
    }
}

#[pyfunction]
fn version() -> PyResult<String> {
    Ok("hermes_pgg_pilotdeck 0.1.0 (PilotDeck-derived Hermes governance core)".to_string())
}

#[pyfunction]
fn default_modules_json() -> PyResult<String> {
    serde_json::to_string_pretty(&default_modules())
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn recommended_config_json() -> PyResult<String> {
    serde_json::to_string_pretty(&recommended_config())
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn evaluate_default_json() -> PyResult<String> {
    serde_json::to_string_pretty(&evaluate_modules(&default_modules()))
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn evaluate_modules_json(modules_json: &str) -> PyResult<String> {
    let modules: Vec<PilotDeckModule> = serde_json::from_str(modules_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    serde_json::to_string_pretty(&evaluate_modules(&modules))
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pymodule]
fn hermes_pgg_pilotdeck(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(default_modules_json, m)?)?;
    m.add_function(wrap_pyfunction!(recommended_config_json, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_default_json, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_modules_json, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_sample_is_watch_not_runtime_pass() {
        let out = evaluate_modules(&default_modules());
        assert_eq!(out.total, 15);
        assert_eq!(out.pass, 0);
        assert_eq!(out.watch, 14);
        assert_eq!(out.blocked, 1);
        assert!(out.evidence_semantics.contains("sample declared-source"));
        assert!(out
            .verdicts
            .iter()
            .any(|v| v.name == "Evolution" && v.status == ModuleStatus::Blocked));
    }

    #[test]
    fn missing_protocol_is_watch_not_pass() {
        let mut modules = default_modules();
        modules[0].evidence.protocol_smoke_passed = false;
        let out = evaluate_modules(&modules);
        assert_eq!(out.pass, 0);
        assert_eq!(out.watch, 14);
        assert_eq!(out.blocked, 1);
        let v = out
            .verdicts
            .iter()
            .find(|v| v.name == "Always-On Discovery")
            .unwrap();
        assert_eq!(v.status, ModuleStatus::Watch);
        assert!(v.missing_gates.contains(&"ProtocolSmoke".to_string()));
    }

    #[test]
    fn config_contains_gateway_and_mcp_gates() {
        let cfg = recommended_config();
        assert_eq!(cfg["mcp_bridge_gate"][0], "config_parse");
        assert_eq!(cfg["routing"]["fallback_requires_tool_capability"], true);
    }

    #[test]
    fn custom_json_roundtrip() {
        let modules = default_modules();
        let text = serde_json::to_string(&modules).unwrap();
        let parsed: Vec<PilotDeckModule> = serde_json::from_str(&text).unwrap();
        assert_eq!(evaluate_modules(&parsed).watch, 14);
    }
}
