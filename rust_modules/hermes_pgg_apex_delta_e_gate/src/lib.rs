//! Hermes PGG APEX ΔE gate v0.1 — Super Evolution 13 bounded evidence gate.
//!
//! Boundary: deterministic read-only evaluation only. No LLM/provider calls,
//! no network crawling, no filesystem writes, no dependency upgrade, no code
//! mutation, no Hermes scheduler/security-boundary mutation, and no full-AGI
//! or self-awareness claim.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlphaPsiInput {
    pub goal_formula_present: bool,
    pub harness_policy_present: bool,
    pub safety_boundary_present: bool,
    pub anti_overclaim_tests_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BetaOmegaInput {
    pub rust_or_core_module_present: bool,
    pub compile_gate_passed: bool,
    pub py_bridge_import_passed: bool,
    pub integration_tests_passed: bool,
    pub rollback_path_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LambdaPhiInput {
    pub github_scout_manifest_present: bool,
    pub academic_or_docs_sources_present: bool,
    pub source_license_or_boundary_recorded: bool,
    pub source_hashes_or_urls_recorded: bool,
    pub external_code_imported: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NablaThetaInput {
    pub before_state_recorded: bool,
    pub after_state_recorded: bool,
    pub delta_metrics_present: bool,
    pub regression_checks_passed: bool,
    pub manifest_readback_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvolCodeInput {
    pub autonomous_loop_present: bool,
    pub patch_sandbox_present: bool,
    pub human_or_gate_approval_required: bool,
    pub no_core_security_mutation: bool,
    pub no_unbounded_auto_update: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApexDeltaEInput {
    pub alpha: AlphaPsiInput,
    pub beta: BetaOmegaInput,
    pub lambda: LambdaPhiInput,
    pub nabla: NablaThetaInput,
    pub evol: EvolCodeInput,
    pub weights: Option<ApexWeights>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApexWeights {
    pub alpha: f64,
    pub beta: f64,
    pub lambda: f64,
    pub nabla: f64,
    pub evol: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComponentScore {
    pub name: String,
    pub score: f64,
    pub checks: Vec<String>,
    pub gaps: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApexDeltaEOutput {
    pub schema: String,
    pub formula: String,
    pub state: String,
    pub score: f64,
    pub weighted_delta_e: f64,
    pub components: Vec<ComponentScore>,
    pub safety_flags: Vec<String>,
    pub recommended_next: Vec<String>,
    pub audit_hash: String,
    pub boundary: String,
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

fn ratio_score(present: usize, total: usize) -> f64 {
    if total == 0 {
        0.0
    } else {
        present as f64 / total as f64
    }
}

fn comp(name: &str, items: &[(&str, bool)], pass_name: &str, gap_prefix: &str) -> ComponentScore {
    let mut checks = Vec::new();
    let mut gaps = Vec::new();
    let present = items.iter().filter(|(_, ok)| *ok).count();
    for (label, ok) in items {
        if *ok {
            checks.push((*label).to_string());
        } else {
            gaps.push(format!("{}:{}", gap_prefix, label));
        }
    }
    if present == items.len() {
        checks.push(pass_name.to_string());
    }
    ComponentScore {
        name: name.to_string(),
        score: round4(ratio_score(present, items.len())),
        checks,
        gaps,
    }
}

fn normalized_weights(w: Option<ApexWeights>) -> ApexWeights {
    let mut x = w.unwrap_or(ApexWeights {
        alpha: 0.20,
        beta: 0.25,
        lambda: 0.15,
        nabla: 0.20,
        evol: 0.20,
    });
    let values = [x.alpha, x.beta, x.lambda, x.nabla, x.evol];
    if values.iter().any(|v| !v.is_finite() || *v < 0.0) {
        return ApexWeights {
            alpha: 0.20,
            beta: 0.25,
            lambda: 0.15,
            nabla: 0.20,
            evol: 0.20,
        };
    }
    let sum = x.alpha + x.beta + x.lambda + x.nabla + x.evol;
    if sum <= 0.0 {
        return ApexWeights {
            alpha: 0.20,
            beta: 0.25,
            lambda: 0.15,
            nabla: 0.20,
            evol: 0.20,
        };
    }
    x.alpha /= sum;
    x.beta /= sum;
    x.lambda /= sum;
    x.nabla /= sum;
    x.evol /= sum;
    x
}

pub fn evaluate(input: ApexDeltaEInput) -> ApexDeltaEOutput {
    let alpha = comp(
        "alpha_psi_logic_baseline",
        &[
            ("goal_formula_present", input.alpha.goal_formula_present),
            ("harness_policy_present", input.alpha.harness_policy_present),
            (
                "safety_boundary_present",
                input.alpha.safety_boundary_present,
            ),
            (
                "anti_overclaim_tests_present",
                input.alpha.anti_overclaim_tests_present,
            ),
        ],
        "alpha_psi_baseline_ready",
        "alpha_gap",
    );
    let beta = comp(
        "beta_omega_code_architecture",
        &[
            (
                "rust_or_core_module_present",
                input.beta.rust_or_core_module_present,
            ),
            ("compile_gate_passed", input.beta.compile_gate_passed),
            (
                "py_bridge_import_passed",
                input.beta.py_bridge_import_passed,
            ),
            (
                "integration_tests_passed",
                input.beta.integration_tests_passed,
            ),
            ("rollback_path_present", input.beta.rollback_path_present),
        ],
        "beta_omega_core_gate_ready",
        "beta_gap",
    );
    let lambda = comp(
        "lambda_phi_external_traceability",
        &[
            (
                "github_scout_manifest_present",
                input.lambda.github_scout_manifest_present,
            ),
            (
                "academic_or_docs_sources_present",
                input.lambda.academic_or_docs_sources_present,
            ),
            (
                "source_license_or_boundary_recorded",
                input.lambda.source_license_or_boundary_recorded,
            ),
            (
                "source_hashes_or_urls_recorded",
                input.lambda.source_hashes_or_urls_recorded,
            ),
            (
                "external_code_not_imported",
                !input.lambda.external_code_imported,
            ),
        ],
        "lambda_phi_readonly_trace_ready",
        "lambda_gap",
    );
    let nabla = comp(
        "nabla_theta_cognitive_delta",
        &[
            ("before_state_recorded", input.nabla.before_state_recorded),
            ("after_state_recorded", input.nabla.after_state_recorded),
            ("delta_metrics_present", input.nabla.delta_metrics_present),
            (
                "regression_checks_passed",
                input.nabla.regression_checks_passed,
            ),
            (
                "manifest_readback_present",
                input.nabla.manifest_readback_present,
            ),
        ],
        "nabla_theta_delta_verified",
        "nabla_gap",
    );
    let evol = comp(
        "evol_code_bounded_evolution",
        &[
            (
                "autonomous_loop_present",
                input.evol.autonomous_loop_present,
            ),
            ("patch_sandbox_present", input.evol.patch_sandbox_present),
            (
                "human_or_gate_approval_required",
                input.evol.human_or_gate_approval_required,
            ),
            (
                "no_core_security_mutation",
                input.evol.no_core_security_mutation,
            ),
            (
                "no_unbounded_auto_update",
                input.evol.no_unbounded_auto_update,
            ),
        ],
        "evol_code_bounded_guard_ready",
        "evol_gap",
    );
    let weights = normalized_weights(input.weights);
    let components = vec![alpha, beta, lambda, nabla, evol];
    let weighted_delta_e = round4(
        components[0].score * weights.alpha
            + components[1].score * weights.beta
            + components[2].score * weights.lambda
            + components[3].score * weights.nabla
            + components[4].score * weights.evol,
    );
    let mut safety_flags = Vec::new();
    if input.lambda.external_code_imported {
        safety_flags.push("external_code_imported_requires_security_review".to_string());
    }
    if !input.evol.no_core_security_mutation {
        safety_flags.push("core_security_mutation_not_allowed".to_string());
    }
    if !input.evol.no_unbounded_auto_update {
        safety_flags.push("unbounded_auto_update_not_allowed".to_string());
    }
    if !input.evol.human_or_gate_approval_required {
        safety_flags.push("missing_human_or_gate_approval".to_string());
    }
    let gap_count: usize = components.iter().map(|c| c.gaps.len()).sum();
    let state = if weighted_delta_e >= 0.95 && gap_count == 0 && safety_flags.is_empty() {
        "PASS_BOUNDED_APEX_DELTA_E_GATE"
    } else if weighted_delta_e >= 0.70 && safety_flags.is_empty() {
        "WATCH_PARTIAL_APEX_DELTA_E_GATE"
    } else if !safety_flags.is_empty() {
        "BLOCKED_BY_SAFETY_BOUNDARY"
    } else {
        "SKELETON_OR_NOT_LANDED"
    }
    .to_string();
    let mut recommended_next = Vec::new();
    for c in &components {
        if !c.gaps.is_empty() {
            recommended_next.push(format!("close {} gaps: {}", c.name, c.gaps.join(",")));
        }
    }
    if !safety_flags.is_empty() {
        recommended_next.push("remove unsafe autonomy before promotion: no external code auto-import, no core security mutation, no unbounded auto-update".to_string());
    }
    let hash_payload = serde_json::json!({"state":state,"score":weighted_delta_e,"components":components,"safety_flags":safety_flags});
    let mut hasher = Sha256::new();
    hasher.update(hash_payload.to_string().as_bytes());
    let audit_hash = format!("sha256:{:x}", hasher.finalize());
    ApexDeltaEOutput {
        schema: "HermesPGGApexDeltaEGate/v1".to_string(),
        formula: "APEX_{ΔE}=αΨ+βΩ+λΦ+∇Θ+Evol_{code}".to_string(),
        state,
        score: weighted_delta_e,
        weighted_delta_e,
        components,
        safety_flags,
        recommended_next,
        audit_hash,
        boundary: "Local deterministic Rust/PyO3 evidence gate for Super Evolution 13 only; no provider calls, no crawling, no code mutation, no scheduler/security mutation, no official benchmark, no self-awareness or full AGI claim.".to_string(),
    }
}

#[pyfunction]
fn version() -> PyResult<String> {
    Ok(
        "hermes_pgg_apex_delta_e_gate 0.1.0 (Super Evolution 13 bounded Rust evidence gate)"
            .to_string(),
    )
}

#[pyfunction]
fn evaluate_json(input_json: &str) -> PyResult<String> {
    let input: ApexDeltaEInput = serde_json::from_str(input_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let out = evaluate(input);
    serde_json::to_string_pretty(&out)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn sample_input_json() -> PyResult<String> {
    let input = ApexDeltaEInput {
        alpha: AlphaPsiInput {
            goal_formula_present: true,
            harness_policy_present: true,
            safety_boundary_present: true,
            anti_overclaim_tests_present: true,
        },
        beta: BetaOmegaInput {
            rust_or_core_module_present: true,
            compile_gate_passed: true,
            py_bridge_import_passed: true,
            integration_tests_passed: true,
            rollback_path_present: true,
        },
        lambda: LambdaPhiInput {
            github_scout_manifest_present: true,
            academic_or_docs_sources_present: true,
            source_license_or_boundary_recorded: true,
            source_hashes_or_urls_recorded: true,
            external_code_imported: false,
        },
        nabla: NablaThetaInput {
            before_state_recorded: true,
            after_state_recorded: true,
            delta_metrics_present: true,
            regression_checks_passed: true,
            manifest_readback_present: true,
        },
        evol: EvolCodeInput {
            autonomous_loop_present: true,
            patch_sandbox_present: true,
            human_or_gate_approval_required: true,
            no_core_security_mutation: true,
            no_unbounded_auto_update: true,
        },
        weights: None,
    };
    serde_json::to_string_pretty(&input)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pymodule]
fn hermes_pgg_apex_delta_e_gate(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_json, m)?)?;
    m.add_function(wrap_pyfunction!(sample_input_json, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    #[test]
    fn sample_passes_bounded_gate() {
        let raw = sample_input_json().unwrap();
        let input: ApexDeltaEInput = serde_json::from_str(&raw).unwrap();
        let out = evaluate(input);
        assert_eq!(out.state, "PASS_BOUNDED_APEX_DELTA_E_GATE");
        assert!(out.score >= 0.99);
        assert!(out.safety_flags.is_empty());
        assert!(out.audit_hash.starts_with("sha256:"));
        assert!(out.boundary.contains("no self-awareness"));
    }

    #[test]
    fn unsafe_external_code_blocks_gate() {
        let raw = sample_input_json().unwrap();
        let mut input: ApexDeltaEInput = serde_json::from_str(&raw).unwrap();
        input.lambda.external_code_imported = true;
        let out = evaluate(input);
        assert_eq!(out.state, "BLOCKED_BY_SAFETY_BOUNDARY");
        assert!(out
            .safety_flags
            .iter()
            .any(|x| x.contains("external_code_imported")));
    }

    #[test]
    fn missing_rust_compile_is_watch_not_pass() {
        let raw = sample_input_json().unwrap();
        let mut input: ApexDeltaEInput = serde_json::from_str(&raw).unwrap();
        input.beta.compile_gate_passed = false;
        let out = evaluate(input);
        assert_ne!(out.state, "PASS_BOUNDED_APEX_DELTA_E_GATE");
        assert!(out
            .components
            .iter()
            .any(|c| c.name.contains("beta") && !c.gaps.is_empty()));
    }

    proptest! {
        #[test]
        fn weighted_score_stays_bounded(a in 0.0f64..10.0, b in 0.0f64..10.0, l in 0.0f64..10.0, n in 0.0f64..10.0, e in 0.0f64..10.0) {
            let raw = sample_input_json().unwrap();
            let mut input: ApexDeltaEInput = serde_json::from_str(&raw).unwrap();
            input.weights = Some(ApexWeights { alpha:a, beta:b, lambda:l, nabla:n, evol:e });
            let out = evaluate(input);
            prop_assert!(out.score >= 0.0 && out.score <= 1.0);
        }
    }
}
