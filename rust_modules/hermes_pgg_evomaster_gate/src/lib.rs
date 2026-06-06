//! Hermes PGG EvoMaster / Super Evolution 9 bounded evidence gate.
//!
//! Boundary: deterministic local evidence evaluation only. No LLM/provider calls,
//! no scheduler/security mutation, no credential access, no sandbox command
//! execution, and no claim of full CLAW/Hermes native self-evolution.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceEvidence {
    pub status_surface_importable: bool,
    pub core_cycle_importable: bool,
    pub hashpool_sidecar_present: bool,
    pub rust_gate_integrated: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceEvidence {
    pub total_traces: u64,
    pub valid_traces: u64,
    pub invalid_traces: u64,
    pub duplicate_traces: u64,
    pub hash_algorithm: String,
    pub stable_hash_readback: bool,
    pub eval_center_source_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RewardEvidence {
    pub tool_success_count: u64,
    pub tool_total_count: u64,
    pub exec_reward: f64,
    pub lambda: f64,
    pub k_claw_score: f64,
    pub objective_score: f64,
    pub bounded_reward: bool,
    pub objective_used_for_ranking: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyEvidence {
    pub llm_provider_call_visible: bool,
    pub provider_count_visible: u64,
    pub gpt_or_claude_visible: bool,
    pub pi_next_written: bool,
    pub pi_next_differs_from_previous: bool,
    pub core_reads_k_claw: bool,
    pub sandbox_constraint_declared: bool,
    pub sandbox_execution_evidence: bool,
    pub loop_rounds: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AntiMockEvidence {
    pub hardcoded_pass_detected: bool,
    pub fixed_score_only_detected: bool,
    pub dry_run_only: bool,
    pub boundary_statement_present: bool,
    pub audit_readback_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExternalLearningEvidence {
    pub github_search_attempted: bool,
    pub repo_hits: u64,
    pub readonly_patterns_absorbed: u64,
    pub patterns_recorded_path_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvoMasterEvidence {
    pub source: SourceEvidence,
    pub trace: TraceEvidence,
    pub reward: RewardEvidence,
    pub policy: PolicyEvidence,
    pub anti_mock: AntiMockEvidence,
    pub external_learning: ExternalLearningEvidence,
    pub manifest_integration_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvoMasterDecision {
    pub schema: String,
    pub status: String,
    pub score: f64,
    pub source_score: f64,
    pub trace_score: f64,
    pub reward_score: f64,
    pub policy_score: f64,
    pub anti_mock_score: f64,
    pub external_learning_score: f64,
    pub checks: Vec<String>,
    pub gaps: Vec<String>,
    pub recommended_next: Vec<String>,
    pub audit_hash: String,
    pub formula: String,
    pub boundary: String,
}

fn ratio(present: usize, total: usize) -> f64 {
    if total == 0 {
        0.0
    } else {
        present as f64 / total as f64
    }
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

fn finite_unit(v: f64) -> bool {
    v.is_finite() && v >= 0.0 && v <= 1.0
}

pub fn evaluate(e: EvoMasterEvidence) -> EvoMasterDecision {
    let mut checks = Vec::new();
    let mut gaps = Vec::new();
    let mut recommended_next = Vec::new();

    let source_items = [
        e.source.status_surface_importable,
        e.source.core_cycle_importable,
        e.source.hashpool_sidecar_present,
        e.source.rust_gate_integrated,
    ];
    let source_present = source_items.iter().filter(|x| **x).count();
    let source_score = ratio(source_present, source_items.len());
    if source_score >= 1.0 {
        checks.push("source_surfaces_and_rust_gate_present".to_string());
    } else {
        gaps.push(format!("source_surface_partial_{}/4", source_present));
    }

    let trace_nonzero = e.trace.total_traces > 0 && e.trace.valid_traces > 0;
    let trace_counts_consistent =
        e.trace.valid_traces + e.trace.invalid_traces >= e.trace.total_traces;
    let hash_is_sha256 = e
        .trace
        .hash_algorithm
        .to_ascii_lowercase()
        .contains("sha256");
    let valid_ratio_ok = e.trace.total_traces > 0
        && (e.trace.valid_traces as f64 / e.trace.total_traces as f64) >= 0.5;
    let trace_items = [
        trace_nonzero,
        trace_counts_consistent,
        hash_is_sha256,
        e.trace.stable_hash_readback,
        e.trace.eval_center_source_present,
        valid_ratio_ok,
    ];
    let trace_present = trace_items.iter().filter(|x| **x).count();
    let trace_score = ratio(trace_present, trace_items.len());
    if trace_score >= 0.84 {
        checks.push("k_claw_hashpool_filter_readback_ready".to_string());
    } else {
        gaps.push(format!("trace_hashpool_gate_low_{}/6", trace_present));
        recommended_next.push("Connect real eval_center/tool traces into K_claw HashPool and read back stable SHA256 records.".to_string());
    }

    let tool_rate = if e.reward.tool_total_count > 0 {
        e.reward.tool_success_count as f64 / e.reward.tool_total_count as f64
    } else {
        0.0
    };
    let reward_matches_tools =
        e.reward.tool_total_count > 0 && (tool_rate - e.reward.exec_reward).abs() <= 0.25;
    let lambda_ok = finite_unit(e.reward.lambda);
    let k_ok = finite_unit(e.reward.k_claw_score);
    let objective_ok = e.reward.objective_score.is_finite()
        && e.reward.objective_score >= 0.0
        && e.reward.objective_score <= 2.0;
    let reward_items = [
        reward_matches_tools,
        lambda_ok,
        k_ok,
        objective_ok,
        e.reward.bounded_reward,
        e.reward.objective_used_for_ranking,
    ];
    let reward_present = reward_items.iter().filter(|x| **x).count();
    let reward_score = ratio(reward_present, reward_items.len());
    if reward_score >= 0.84 {
        checks.push("r_exec_plus_lambda_k_claw_objective_bounded".to_string());
    } else {
        gaps.push(format!("reward_objective_gate_low_{}/6", reward_present));
        recommended_next.push("Derive R_exec from real tool success/failure counters and use R_exec + lambda*K_claw for strategy ranking.".to_string());
    }

    let policy_items = [
        e.policy.llm_provider_call_visible,
        e.policy.provider_count_visible >= 2,
        e.policy.gpt_or_claude_visible,
        e.policy.pi_next_written,
        e.policy.pi_next_differs_from_previous,
        e.policy.core_reads_k_claw,
        e.policy.sandbox_constraint_declared,
        e.policy.sandbox_execution_evidence,
        e.policy.loop_rounds >= 2,
    ];
    let policy_present = policy_items.iter().filter(|x| **x).count();
    let policy_score = ratio(policy_present, policy_items.len());
    if policy_score >= 0.89 {
        checks.push("pi_next_trace_k_claw_sandbox_loop_ready".to_string());
    } else {
        gaps.push(format!("policy_update_loop_gate_low_{}/9", policy_present));
        recommended_next.push("Add a bounded two-round policy-update harness: trace -> K_claw -> LLM pi_next -> sandbox -> reward -> state readback.".to_string());
    }

    let anti_items = [
        !e.anti_mock.hardcoded_pass_detected,
        !e.anti_mock.fixed_score_only_detected,
        !e.anti_mock.dry_run_only,
        e.anti_mock.boundary_statement_present,
        e.anti_mock.audit_readback_present,
    ];
    let anti_present = anti_items.iter().filter(|x| **x).count();
    let anti_mock_score = ratio(anti_present, anti_items.len());
    if anti_mock_score >= 1.0 {
        checks.push("anti_mock_boundary_audit_clean".to_string());
    } else {
        gaps.push(format!("anti_mock_gate_low_{}/5", anti_present));
    }

    let ext_items = [
        e.external_learning.github_search_attempted,
        e.external_learning.readonly_patterns_absorbed >= 3,
        e.external_learning.patterns_recorded_path_present,
    ];
    let ext_present = ext_items.iter().filter(|x| **x).count();
    let external_learning_score = ratio(ext_present, ext_items.len());
    if external_learning_score >= 0.67 {
        checks.push("external_agent_memory_patterns_absorbed_readonly".to_string());
    } else {
        gaps.push(format!("external_learning_low_{}/3", ext_present));
    }

    if e.manifest_integration_present {
        checks.push("manifest_integration_present".to_string());
    } else {
        gaps.push("manifest_integration_missing".to_string());
    }

    let manifest_score = if e.manifest_integration_present {
        1.0
    } else {
        0.0
    };
    let score = round4(
        source_score * 0.12
            + trace_score * 0.18
            + reward_score * 0.18
            + policy_score * 0.24
            + anti_mock_score * 0.12
            + external_learning_score * 0.06
            + manifest_score * 0.10,
    );

    let full_core_loop = trace_score >= 0.84
        && reward_score >= 0.84
        && policy_score >= 0.89
        && anti_mock_score >= 1.0;
    let status = if score >= 0.90 && full_core_loop && gaps.is_empty() {
        "PASS_BOUNDED_EVOMASTER_CORE_EVIDENCE_GATE"
    } else if score >= 0.72 && trace_score >= 0.84 && anti_mock_score >= 0.8 {
        "PARTIAL_HASHPOOL_AND_STATUS_GATE_POLICY_LOOP_WATCH"
    } else if score >= 0.45 {
        "WATCH_PARTIAL_SURFACES_ONLY"
    } else {
        "BLOCKED_INSUFFICIENT_EVIDENCE"
    }
    .to_string();

    let canonical = serde_json::to_string(&e).unwrap_or_default();
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    hasher.update(status.as_bytes());
    let audit_hash = format!("sha256:{:x}", hasher.finalize());

    EvoMasterDecision {
        schema: "HermesPGGEvoMasterGate/v1".to_string(),
        status,
        score,
        source_score: round4(source_score),
        trace_score: round4(trace_score),
        reward_score: round4(reward_score),
        policy_score: round4(policy_score),
        anti_mock_score: round4(anti_mock_score),
        external_learning_score: round4(external_learning_score),
        checks,
        gaps,
        recommended_next,
        audit_hash,
        formula: "max_{pi_claw} E[R_exec(tau)+lambda*K_claw(tau)]; pi_next=GPT-Stream(tau,K_claw,Constraint_sandbox); K_claw=HashPool(Filter(tau_valid))".to_string(),
        boundary: "Bounded deterministic Rust/PyO3 evidence gate only. It scores local evidence for EvoMaster/Super Evolution 9 formula coverage; it does not call LLMs, execute sandbox commands, mutate Hermes/CLAW core scheduler/security, prove production runtime participation, external benchmark success, or full AGI.".to_string(),
    }
}

#[pyfunction]
fn version() -> &'static str {
    "hermes_pgg_evomaster_gate 0.1.0 (Super Evolution 9 bounded evidence gate)"
}

#[pyfunction]
fn evaluate_evidence_json(evidence_json: &str) -> PyResult<String> {
    let evidence: EvoMasterEvidence = serde_json::from_str(evidence_json)
        .map_err(|err| pyo3::exceptions::PyValueError::new_err(err.to_string()))?;
    serde_json::to_string_pretty(&evaluate(evidence))
        .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))
}

#[pyfunction]
fn sample_input_json() -> PyResult<String> {
    let sample = EvoMasterEvidence {
        source: SourceEvidence {
            status_surface_importable: true,
            core_cycle_importable: true,
            hashpool_sidecar_present: true,
            rust_gate_integrated: true,
        },
        trace: TraceEvidence {
            total_traces: 12,
            valid_traces: 8,
            invalid_traces: 4,
            duplicate_traces: 1,
            hash_algorithm: "sha256".to_string(),
            stable_hash_readback: true,
            eval_center_source_present: true,
        },
        reward: RewardEvidence {
            tool_success_count: 8,
            tool_total_count: 10,
            exec_reward: 0.8,
            lambda: 0.35,
            k_claw_score: 0.75,
            objective_score: 1.0625,
            bounded_reward: true,
            objective_used_for_ranking: true,
        },
        policy: PolicyEvidence {
            llm_provider_call_visible: true,
            provider_count_visible: 3,
            gpt_or_claude_visible: true,
            pi_next_written: true,
            pi_next_differs_from_previous: true,
            core_reads_k_claw: true,
            sandbox_constraint_declared: true,
            sandbox_execution_evidence: true,
            loop_rounds: 2,
        },
        anti_mock: AntiMockEvidence {
            hardcoded_pass_detected: false,
            fixed_score_only_detected: false,
            dry_run_only: false,
            boundary_statement_present: true,
            audit_readback_present: true,
        },
        external_learning: ExternalLearningEvidence {
            github_search_attempted: true,
            repo_hits: 0,
            readonly_patterns_absorbed: 5,
            patterns_recorded_path_present: true,
        },
        manifest_integration_present: true,
    };
    serde_json::to_string_pretty(&sample)
        .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))
}

#[pymodule]
fn hermes_pgg_evomaster_gate(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_evidence_json, m)?)?;
    m.add_function(wrap_pyfunction!(sample_input_json, m)?)?;
    m.add("__version__", "0.1.0")?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn full_sample() -> EvoMasterEvidence {
        serde_json::from_str(&sample_input_json().unwrap()).unwrap()
    }

    #[test]
    fn full_sample_passes_bounded_gate() {
        let d = evaluate(full_sample());
        assert_eq!(d.status, "PASS_BOUNDED_EVOMASTER_CORE_EVIDENCE_GATE");
        assert!(d.score >= 0.90);
        assert!(d.gaps.is_empty());
    }

    #[test]
    fn current_partial_state_does_not_overclaim() {
        let e = EvoMasterEvidence {
            source: SourceEvidence {
                status_surface_importable: true,
                core_cycle_importable: true,
                hashpool_sidecar_present: true,
                rust_gate_integrated: true,
            },
            trace: TraceEvidence {
                total_traces: 2,
                valid_traces: 1,
                invalid_traces: 1,
                duplicate_traces: 0,
                hash_algorithm: "sha256".to_string(),
                stable_hash_readback: true,
                eval_center_source_present: true,
            },
            reward: RewardEvidence {
                tool_success_count: 0,
                tool_total_count: 0,
                exec_reward: 0.0,
                lambda: 0.0,
                k_claw_score: 0.0,
                objective_score: 0.0,
                bounded_reward: false,
                objective_used_for_ranking: false,
            },
            policy: PolicyEvidence {
                llm_provider_call_visible: true,
                provider_count_visible: 5,
                gpt_or_claude_visible: true,
                pi_next_written: false,
                pi_next_differs_from_previous: false,
                core_reads_k_claw: false,
                sandbox_constraint_declared: true,
                sandbox_execution_evidence: false,
                loop_rounds: 0,
            },
            anti_mock: AntiMockEvidence {
                hardcoded_pass_detected: false,
                fixed_score_only_detected: false,
                dry_run_only: false,
                boundary_statement_present: true,
                audit_readback_present: true,
            },
            external_learning: ExternalLearningEvidence {
                github_search_attempted: true,
                repo_hits: 0,
                readonly_patterns_absorbed: 5,
                patterns_recorded_path_present: true,
            },
            manifest_integration_present: true,
        };
        let d = evaluate(e);
        assert_ne!(d.status, "PASS_BOUNDED_EVOMASTER_CORE_EVIDENCE_GATE");
        assert!(d
            .gaps
            .iter()
            .any(|g| g.contains("policy_update_loop_gate_low")));
        assert!(d
            .gaps
            .iter()
            .any(|g| g.contains("reward_objective_gate_low")));
    }
}
