//! Hermes PGG EVM Runtime Gate — Rust native implementation.
//!
//! EVM = E × V × M × A × Base × Ancient × (1 - defect_rate)
//! EVM_Gate = 1 - weighted_residual_defect_rate
//!
//! Boundary: deterministic local evidence evaluation only. No provider calls,
//! no network, no scheduler/security mutation, no AGI/ASI claim.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

// ── Evidence / Config types ─────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeEvidence {
    pub skillflow_route_enforce: Option<bool>,
    pub route_enforce_by_design: Option<bool>,
    #[serde(flatten)]
    pub extra: std::collections::HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvmConfig {
    #[serde(alias = "eval_e")]
    pub e: Option<f64>,
    #[serde(alias = "eval_v")]
    pub v: Option<f64>,
    #[serde(alias = "eval_m")]
    pub m: Option<f64>,
    #[serde(alias = "eval_a")]
    pub a: Option<f64>,
    #[serde(alias = "eval_base")]
    pub base: Option<f64>,
    #[serde(alias = "eval_ancient")]
    pub ancient: Option<f64>,
    pub defects_before: Option<Vec<f64>>,
    pub defects_after: Option<Vec<f64>>,
    pub boost_coeff: Option<f64>,
    pub epsilon: Option<f64>,
    pub runtime_evidence: Option<RuntimeEvidence>,
}

impl Default for EvmConfig {
    fn default() -> Self {
        Self {
            e: Some(0.8),
            v: Some(0.7),
            m: Some(0.6),
            a: Some(0.5),
            base: Some(0.9),
            ancient: Some(0.5),
            defects_before: Some(vec![0.3, 0.2, 0.4, 0.1, 0.3, 0.2, 0.1, 0.4, 0.2, 0.3, 0.1, 0.2]),
            defects_after: Some(vec![0.2, 0.1, 0.3, 0.05, 0.2, 0.1, 0.05, 0.3, 0.1, 0.2, 0.05, 0.1]),
            boost_coeff: Some(1.5),
            epsilon: Some(0.001),
            runtime_evidence: None,
        }
    }
}

// ── Evidence file loader (fallback) ─────────────────────────────────

fn load_evidence_from_file() -> Option<EvmConfig> {
    let home = std::env::var("HOME").ok()?;
    let path = format!("{}/.hermes/data/evm_runtime_evidence.json", home);
    let content = std::fs::read_to_string(&path).ok()?;
    let raw: serde_json::Value = serde_json::from_str(&content).ok()?;

    let e = raw.get("eval_e").and_then(|v| v.as_f64());
    let v = raw.get("eval_v").and_then(|v| v.as_f64());
    let m = raw.get("eval_m").and_then(|v| v.as_f64());
    let a = raw.get("eval_a").and_then(|v| v.as_f64());
    let base = raw.get("eval_base").and_then(|v| v.as_f64());
    let ancient = raw.get("eval_ancient").and_then(|v| v.as_f64());

    let defects_before: Option<Vec<f64>> = raw
        .get("defects_before")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect());

    let defects_after: Option<Vec<f64>> = raw
        .get("defects_after")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect());

    let boost_coeff = raw.get("boost_coeff").and_then(|v| v.as_f64());
    let epsilon = raw.get("epsilon").and_then(|v| v.as_f64());

    let runtime_evidence = raw.get("runtime_evidence").and_then(|v| {
        Some(RuntimeEvidence {
            skillflow_route_enforce: v.get("skillflow_route_enforce").and_then(|x| x.as_bool()),
            route_enforce_by_design: v.get("route_enforce_by_design").and_then(|x| x.as_bool()),
            extra: std::collections::HashMap::new(),
        })
    });

    Some(EvmConfig {
        e,
        v,
        m,
        a,
        base,
        ancient,
        defects_before,
        defects_after,
        boost_coeff,
        epsilon,
        runtime_evidence,
    })
}

// ── Core EVM evaluation ─────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvmResult {
    pub schema: String,
    pub status: String,
    pub evm_gate: f64,
    pub evm_value: f64,
    pub score: f64,
    pub gaps: Vec<String>,
    pub boundary: String,
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

fn evaluate_evm(cfg: &EvmConfig) -> EvmResult {
    let e = cfg.e.unwrap_or(0.8).clamp(0.0, 1.0);
    let v = cfg.v.unwrap_or(0.7).clamp(0.0, 1.0);
    let m = cfg.m.unwrap_or(0.6).clamp(0.0, 1.0);
    let a = cfg.a.unwrap_or(0.5).clamp(0.0, 1.0);
    let base = cfg.base.unwrap_or(0.9).clamp(0.0, 1.0);
    let ancient = cfg.ancient.unwrap_or(0.5).clamp(0.0, 1.0);
    let boost_coeff = cfg.boost_coeff.unwrap_or(1.5);
    let eps = cfg.epsilon.unwrap_or(0.001);

    let modern = e * v * m * a * base;

    let defects_before = cfg.defects_before.as_deref().unwrap_or(&[0.3; 12]);
    let defects_after = cfg.defects_after.as_deref().unwrap_or(&[0.2; 12]);
    let n_before = defects_before.len().max(1);
    let n_after = defects_after.len().max(1);
    let avg_before: f64 = defects_before.iter().sum::<f64>() / n_before as f64;
    let avg_after: f64 = defects_after.iter().sum::<f64>() / n_after as f64;

    let defect_rate = avg_after * 0.5 + boost_coeff * avg_after.powf(1.5);
    let residual = avg_after / avg_before.max(eps);
    let evm_gate = 1.0 - residual;

    let score = modern * ancient * (1.0 - defect_rate) * 100.0;
    let score = round4(score.max(0.0));

    let mut gaps: Vec<String> = Vec::new();
    if evm_gate < 0.80 {
        gaps.push("evm_gate_below_0_80".to_string());
    }

    // Route enforce check
    if let Some(ref re) = cfg.runtime_evidence {
        if re.skillflow_route_enforce != Some(true) {
            if re.route_enforce_by_design != Some(true) {
                gaps.push("route_enforce_not_active".to_string());
            }
        }
    }

    let status = if score >= 80.0 && gaps.is_empty() {
        "PASS".to_string()
    } else if score >= 50.0 {
        "WATCH".to_string()
    } else {
        "BLOCKED".to_string()
    };

    EvmResult {
        schema: "HermesPggEvmRuntimeGate/v1-rust".to_string(),
        status,
        evm_gate: round4(evm_gate),
        evm_value: round4(modern),
        score,
        gaps,
        boundary: "Internal bounded EVM runtime gate. Not full AGI, not external benchmark.".to_string(),
    }
}

fn build_config(input: &str) -> EvmConfig {
    // Try parsing input as JSON first
    if let Ok(cfg) = serde_json::from_str::<EvmConfig>(input) {
        return cfg;
    }
    // Try parsing as a full evidence file format
    if let Ok(raw) = serde_json::from_str::<serde_json::Value>(input) {
        if raw.get("eval_e").is_some() || raw.get("e").is_some() {
            // It has config fields
            if let Ok(cfg) = serde_json::from_str::<EvmConfig>(input) {
                return cfg;
            }
        }
    }
    // Fallback: try evidence file
    if let Some(cfg) = load_evidence_from_file() {
        return cfg;
    }
    EvmConfig::default()
}

// ── PyO3 exports ────────────────────────────────────────────────────

#[pyfunction]
fn evaluate_evidence_json(input: &str) -> PyResult<String> {
    let config = build_config(input);
    let result = evaluate_evm(&config);
    serde_json::to_string(&result)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn sample_evidence_json() -> PyResult<String> {
    let cfg = EvmConfig::default();
    serde_json::to_string(&cfg)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn version() -> PyResult<String> {
    Ok("Hermes PGG EVM Runtime Gate / Rust native v0.1.0".to_string())
}

#[pymodule]
fn hermes_pgg_evm_runtime_gate(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(evaluate_evidence_json, m)?)?;
    m.add_function(wrap_pyfunction!(sample_evidence_json, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}