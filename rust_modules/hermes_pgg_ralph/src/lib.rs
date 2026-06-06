//! Hermes PGG Ralph core v0.1
//!
//! Additive Rust-native controller inspired by the Ralph formula:
//! S_{t+1} = F(S_t, G) while HarnessVerify(S_t) is false.
//!
//! Boundary: pure computation and JSON serialization only. This module does not
//! call LLM providers, touch Hermes scheduler/security boundaries, or prove AGI.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

const EPSILON: f64 = 1e-6;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RalphDecision {
    Iterate,
    Converged,
    HarnessFailed,
    InvalidState,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OmegaRef {
    pub id: String,
    pub version: String,
    pub checksum: String,
    pub storage_hint: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RalphState {
    pub step: u64,
    pub energy_g: f64,
    pub delta_g: f64,
    pub objective_score: f64,
    pub harness_score: f64,
    pub omega: OmegaRef,
    pub converged: bool,
    pub phase: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HarnessPolicy {
    pub min_harness_score: f64,
    pub min_objective_score: f64,
    pub max_delta_abs: f64,
    pub require_omega_checksum: bool,
}

impl Default for HarnessPolicy {
    fn default() -> Self {
        Self {
            min_harness_score: 0.95,
            min_objective_score: 0.95,
            max_delta_abs: EPSILON,
            require_omega_checksum: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HarnessVerdict {
    pub schema: String,
    pub passed: bool,
    pub checks: Vec<String>,
    pub failures: Vec<String>,
    pub boundary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RalphOutput {
    pub schema: String,
    pub decision: RalphDecision,
    pub next_state: RalphState,
    pub harness: HarnessVerdict,
    pub corrected_formula: String,
    pub audit_hash: String,
    pub boundary: String,
}

fn finite01(v: f64) -> bool {
    v.is_finite() && (0.0..=1.0).contains(&v)
}

fn round6(v: f64) -> f64 {
    (v * 1_000_000.0).round() / 1_000_000.0
}

fn hash_state(state: &RalphState, decision: &RalphDecision, failures: &[String]) -> String {
    let payload = serde_json::json!({
        "step": state.step,
        "energy_g": round6(state.energy_g),
        "delta_g": round6(state.delta_g),
        "objective_score": round6(state.objective_score),
        "harness_score": round6(state.harness_score),
        "omega": state.omega,
        "decision": decision,
        "failures": failures,
    });
    let mut hasher = Sha256::new();
    hasher.update(payload.to_string().as_bytes());
    format!("sha256:{:x}", hasher.finalize())
}

pub fn harness_verify(state: &RalphState, policy: &HarnessPolicy) -> HarnessVerdict {
    let mut checks = Vec::new();
    let mut failures = Vec::new();

    if state.energy_g.is_finite() && state.delta_g.is_finite() {
        checks.push("finite_energy_delta".to_string());
    } else {
        failures.push("energy_or_delta_not_finite".to_string());
    }

    if finite01(state.objective_score) {
        checks.push("objective_score_in_0_1".to_string());
    } else {
        failures.push("objective_score_out_of_range".to_string());
    }

    if finite01(state.harness_score) {
        checks.push("harness_score_in_0_1".to_string());
    } else {
        failures.push("harness_score_out_of_range".to_string());
    }

    if state.harness_score >= policy.min_harness_score {
        checks.push("harness_score_threshold".to_string());
    } else {
        failures.push("harness_score_below_threshold".to_string());
    }

    if state.objective_score >= policy.min_objective_score {
        checks.push("objective_score_threshold".to_string());
    } else {
        failures.push("objective_score_below_threshold".to_string());
    }

    if state.delta_g.abs() <= policy.max_delta_abs {
        checks.push("delta_g_converged".to_string());
    } else {
        failures.push("delta_g_not_converged".to_string());
    }

    if !policy.require_omega_checksum || state.omega.checksum.starts_with("sha256:") {
        checks.push("omega_checksum_present".to_string());
    } else {
        failures.push("omega_checksum_missing_or_invalid".to_string());
    }

    HarnessVerdict {
        schema: "HermesPGGRalphHarness/v1".to_string(),
        passed: failures.is_empty(),
        checks,
        failures,
        boundary: "Harness verdict is deterministic structural verification, not proof of full AGI or external benchmark success.".to_string(),
    }
}

pub fn ralph_step(mut state: RalphState, policy: HarnessPolicy) -> RalphOutput {
    let invalid = !state.energy_g.is_finite()
        || !state.delta_g.is_finite()
        || !finite01(state.objective_score)
        || !finite01(state.harness_score);

    let decision = if invalid {
        state.converged = false;
        state.phase = "invalid_state".to_string();
        RalphDecision::InvalidState
    } else {
        let harness = harness_verify(&state, &policy);
        if harness.passed {
            // Correct Ralph semantics: validated state is preserved, not multiplied to zero.
            state.converged = true;
            state.phase = "converged_preserve_state".to_string();
            RalphDecision::Converged
        } else if state.harness_score < 0.5 {
            state.converged = false;
            state.phase = "harness_failed".to_string();
            RalphDecision::HarnessFailed
        } else {
            state.step = state.step.saturating_add(1);
            state.converged = false;
            state.phase = "iterate".to_string();
            RalphDecision::Iterate
        }
    };

    let harness = harness_verify(&state, &policy);
    let audit_hash = hash_state(&state, &decision, &harness.failures);

    RalphOutput {
        schema: "HermesPGGRalphCore/v1".to_string(),
        decision,
        next_state: state,
        harness,
        corrected_formula: "S_{t+1}=I(not V_H(S_t))*H[ΔG*F(S_t,G,Ω_A)] + I(V_H(S_t))*S_t".to_string(),
        audit_hash,
        boundary: "Additive pure Rust Ralph/Harness/Omega controller; no scheduler/security mutation, no provider calls, no full AGI claim.".to_string(),
    }
}

#[pyfunction]
fn version() -> PyResult<String> {
    Ok("hermes_pgg_ralph 0.1.0 (additive Ralph/Harness/Omega Rust core)".to_string())
}

#[pyfunction]
fn evaluate_state_json(state_json: &str, policy_json: Option<&str>) -> PyResult<String> {
    let state: RalphState = serde_json::from_str(state_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let policy: HarnessPolicy = match policy_json {
        Some(raw) if !raw.trim().is_empty() => serde_json::from_str(raw)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?,
        _ => HarnessPolicy::default(),
    };
    let out = ralph_step(state, policy);
    serde_json::to_string_pretty(&out)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn sample_state_json() -> PyResult<String> {
    let state = RalphState {
        step: 0,
        energy_g: 0.0,
        delta_g: 0.0,
        objective_score: 0.99,
        harness_score: 0.99,
        omega: OmegaRef {
            id: "omega-default".to_string(),
            version: "v1".to_string(),
            checksum: "sha256:sample".to_string(),
            storage_hint: "manifest+skill+archive+retrieval".to_string(),
        },
        converged: false,
        phase: "candidate".to_string(),
    };
    serde_json::to_string_pretty(&state)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pymodule]
fn hermes_pgg_ralph(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_state_json, m)?)?;
    m.add_function(wrap_pyfunction!(sample_state_json, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;
    use serde_json::Value;

    fn omega() -> OmegaRef {
        OmegaRef {
            id: "omega-test".to_string(),
            version: "v1".to_string(),
            checksum: "sha256:test".to_string(),
            storage_hint: "test".to_string(),
        }
    }

    #[test]
    fn converged_preserves_state_not_zero() {
        let state = RalphState {
            step: 7,
            energy_g: 0.0,
            delta_g: 0.0,
            objective_score: 1.0,
            harness_score: 1.0,
            omega: omega(),
            converged: false,
            phase: "candidate".to_string(),
        };
        let out = ralph_step(state, HarnessPolicy::default());
        assert_eq!(out.decision, RalphDecision::Converged);
        assert_eq!(out.next_state.step, 7);
        assert_eq!(out.next_state.objective_score, 1.0);
        assert!(out.next_state.converged);
    }

    #[test]
    fn iterate_when_delta_not_converged_but_harness_healthy() {
        let state = RalphState {
            step: 0,
            energy_g: 0.2,
            delta_g: -0.1,
            objective_score: 0.99,
            harness_score: 0.99,
            omega: omega(),
            converged: false,
            phase: "candidate".to_string(),
        };
        let out = ralph_step(state, HarnessPolicy::default());
        assert_eq!(out.decision, RalphDecision::Iterate);
        assert_eq!(out.next_state.step, 1);
        assert!(!out.next_state.converged);
    }

    #[test]
    fn harness_failed_blocks_low_harness_score() {
        let state = RalphState {
            step: 0,
            energy_g: 0.0,
            delta_g: 0.0,
            objective_score: 1.0,
            harness_score: 0.2,
            omega: omega(),
            converged: false,
            phase: "candidate".to_string(),
        };
        let out = ralph_step(state, HarnessPolicy::default());
        assert_eq!(out.decision, RalphDecision::HarnessFailed);
        assert!(out
            .harness
            .failures
            .contains(&"harness_score_below_threshold".to_string()));
    }

    #[test]
    fn py_json_surface_is_valid_json() {
        let state = sample_state_json().unwrap();
        let out = evaluate_state_json(&state, None).unwrap();
        let v: Value = serde_json::from_str(&out).unwrap();
        assert_eq!(v["schema"], "HermesPGGRalphCore/v1");
        assert_eq!(v["decision"], "converged");
        assert!(v["audit_hash"].as_str().unwrap().starts_with("sha256:"));
    }

    proptest! {
        #[test]
        fn invalid_scores_never_converge(
            objective_score in -10.0f64..10.0,
            harness_score in -10.0f64..10.0,
        ) {
            let state = RalphState {
                step: 0,
                energy_g: 0.0,
                delta_g: 0.0,
                objective_score,
                harness_score,
                omega: omega(),
                converged: false,
                phase: "candidate".to_string(),
            };
            let out = ralph_step(state, HarnessPolicy::default());
            if !(0.0..=1.0).contains(&objective_score) || !(0.0..=1.0).contains(&harness_score) {
                prop_assert_eq!(out.decision, RalphDecision::InvalidState);
                prop_assert!(!out.next_state.converged);
            }
        }
    }
}
