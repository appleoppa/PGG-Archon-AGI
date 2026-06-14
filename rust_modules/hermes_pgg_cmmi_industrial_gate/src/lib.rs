//! Super Evolution 18 / CMMI industrial delivery bounded evidence gate.
//!
//! Boundary: deterministic local evidence evaluation only. No provider calls,
//! no Docker/GitHub side effects, no scheduler/security mutation, no formal CMMI
//! certification claim, and no full AGI claim.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SourceDocumentEvidence {
    pub source_document_read: bool,
    pub requirement_extracted: bool,
    pub current_surface_audited: bool,
    pub overclaim_boundary_recorded: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MultiLlmEvidence {
    pub provider_calls_attempted: u64,
    pub visible_provider_outputs: u64,
    pub gpt_planning_audit_visible: bool,
    pub claude_compile_audit_attempted: bool,
    pub claude_compile_audit_visible: bool,
    pub judge_visible: bool,
    pub failed_channels_recorded: bool,
    pub no_roleplay_provider_participation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ExternalLearningEvidence {
    pub github_api_repos_verified: u64,
    pub patterns_absorbed: Vec<String>,
    pub no_external_code_ingested: bool,
    pub vx_or_other_community_boundary_recorded: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct IndustrialLoopEvidence {
    pub background_or_container_lane_defined: bool,
    pub gpt_plan_schema_present: bool,
    pub coding_diff_trace_schema_present: bool,
    pub pr_review_gate_schema_present: bool,
    pub automated_test_gate_schema_present: bool,
    pub github_release_gate_schema_present: bool,
    pub auto_report_schema_present: bool,
    pub rollback_or_kill_switch_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RuntimeEvidence {
    pub python_status_surface_present: bool,
    pub rust_gate_integrated: bool,
    pub build_script_includes_gate: bool,
    pub rust_compile_passed: bool,
    pub python_import_smoke_passed: bool,
    pub pytest_passed: bool,
    pub manifest_readback_present: bool,
    pub skill_reference_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct LiveAutomationEvidence {
    pub docker_build_passed: bool,
    pub github_push_or_release_passed: bool,
    pub ci_pipeline_run_passed: bool,
    pub pr_created_or_reviewed: bool,
    pub production_publish_authorized: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CmmiEvidence {
    pub source: SourceDocumentEvidence,
    pub llm: MultiLlmEvidence,
    pub external_learning: ExternalLearningEvidence,
    pub industrial_loop: IndustrialLoopEvidence,
    pub runtime: RuntimeEvidence,
    pub live_automation: LiveAutomationEvidence,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CmmiDecision {
    pub schema: String,
    pub status: String,
    pub score: f64,
    pub subscores: serde_json::Value,
    pub checks: Vec<String>,
    pub gaps: Vec<String>,
    pub recommended_next: Vec<String>,
    pub absorbed_external_patterns: Vec<String>,
    pub audit_hash: String,
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

fn bool_score(items: &[bool]) -> f64 {
    ratio(items.iter().filter(|v| **v).count(), items.len())
}

pub fn evaluate(e: CmmiEvidence) -> CmmiDecision {
    let mut checks = Vec::new();
    let mut gaps = Vec::new();
    let mut recommended_next = Vec::new();

    let source_items = [
        e.source.source_document_read,
        e.source.requirement_extracted,
        e.source.current_surface_audited,
        e.source.overclaim_boundary_recorded,
    ];
    let source_score = bool_score(&source_items);
    if source_score >= 1.0 {
        checks.push("source_document_and_current_surface_audited".to_string());
    } else {
        gaps.push(format!(
            "source_audit_partial_{}/4",
            source_items.iter().filter(|v| **v).count()
        ));
    }

    let llm_items = [
        e.llm.provider_calls_attempted >= 3,
        e.llm.visible_provider_outputs >= 3,
        e.llm.gpt_planning_audit_visible,
        e.llm.claude_compile_audit_attempted,
        e.llm.failed_channels_recorded,
        e.llm.no_roleplay_provider_participation,
        e.llm.judge_visible,
    ];
    let llm_score = bool_score(&llm_items);
    if llm_score >= 0.85 {
        checks.push("multi_llm_audit_visible_with_failures_recorded".to_string());
    } else {
        gaps.push(format!(
            "multi_llm_audit_partial_{}/7",
            llm_items.iter().filter(|v| **v).count()
        ));
    }
    if e.llm.claude_compile_audit_attempted && !e.llm.claude_compile_audit_visible {
        recommended_next.push("Claude compile/code-review channel was attempted but not visible; do not count it as effective until provider returns visible output.".to_string());
    }

    let ext_items = [
        e.external_learning.github_api_repos_verified >= 5,
        e.external_learning.patterns_absorbed.len() >= 5,
        e.external_learning.no_external_code_ingested,
        e.external_learning.vx_or_other_community_boundary_recorded,
    ];
    let external_score = bool_score(&ext_items);
    if external_score >= 1.0 {
        checks.push("read_only_external_patterns_absorbed".to_string());
    } else {
        gaps.push(format!(
            "external_learning_partial_{}/4",
            ext_items.iter().filter(|v| **v).count()
        ));
    }

    let loop_items = [
        e.industrial_loop.background_or_container_lane_defined,
        e.industrial_loop.gpt_plan_schema_present,
        e.industrial_loop.coding_diff_trace_schema_present,
        e.industrial_loop.pr_review_gate_schema_present,
        e.industrial_loop.automated_test_gate_schema_present,
        e.industrial_loop.github_release_gate_schema_present,
        e.industrial_loop.auto_report_schema_present,
        e.industrial_loop.rollback_or_kill_switch_present,
    ];
    let loop_score = bool_score(&loop_items);
    if loop_score >= 0.875 {
        checks.push("industrial_delivery_loop_schema_ready".to_string());
    } else {
        gaps.push(format!(
            "industrial_loop_schema_partial_{}/8",
            loop_items.iter().filter(|v| **v).count()
        ));
        recommended_next.push("Close missing GPT plan / Claude diff / PR review / tests / GitHub release / report schemas before claiming industrial loop readiness.".to_string());
    }

    let runtime_items = [
        e.runtime.python_status_surface_present,
        e.runtime.rust_gate_integrated,
        e.runtime.build_script_includes_gate,
        e.runtime.rust_compile_passed,
        e.runtime.python_import_smoke_passed,
        e.runtime.pytest_passed,
        e.runtime.manifest_readback_present,
        e.runtime.skill_reference_present,
    ];
    let runtime_score = bool_score(&runtime_items);
    if runtime_score >= 0.875 {
        checks.push("rust_python_manifest_skill_fusion_verified".to_string());
    } else {
        gaps.push(format!(
            "runtime_fusion_partial_{}/8",
            runtime_items.iter().filter(|v| **v).count()
        ));
    }

    let live_items = [
        e.live_automation.docker_build_passed,
        e.live_automation.github_push_or_release_passed,
        e.live_automation.ci_pipeline_run_passed,
        e.live_automation.pr_created_or_reviewed,
        e.live_automation.production_publish_authorized,
    ];
    let live_score = bool_score(&live_items);
    if live_score >= 1.0 {
        checks.push("authorized_live_automation_release_passed".to_string());
    } else {
        gaps.push(format!(
            "live_automation_not_fully_authorized_or_not_run_{}/5",
            live_items.iter().filter(|v| **v).count()
        ));
        recommended_next.push("Keep GitHub push/release/Docker build as HOLD unless explicitly authorized and verified by real CI/release readback.".to_string());
    }

    let score = round4(
        source_score * 0.15
            + llm_score * 0.15
            + external_score * 0.15
            + loop_score * 0.25
            + runtime_score * 0.20
            + live_score * 0.10,
    );
    let status = if source_score >= 1.0
        && llm_score >= 0.85
        && external_score >= 1.0
        && loop_score >= 0.875
        && runtime_score >= 0.875
    {
        if live_score >= 1.0 {
            "PASS_FULLY_VERIFIED_AUTHORIZED_INDUSTRIAL_LOOP"
        } else {
            "PASS_BOUNDED_CMMI18_CORE_FUSION_LIVE_AUTOMATION_HOLD"
        }
    } else if score >= 0.60 {
        "WATCH_PARTIAL_CMMI18_GATE"
    } else {
        "FAIL_INSUFFICIENT_CMMI18_EVIDENCE"
    };

    let mut hasher = Sha256::new();
    hasher.update(serde_json::to_vec(&e).unwrap_or_default());
    let audit_hash = format!("{:x}", hasher.finalize());

    CmmiDecision {
        schema: "HermesPGGCMMIIndustrialGate/v1".to_string(),
        status: status.to_string(),
        score,
        subscores: serde_json::json!({
            "source": round4(source_score),
            "multi_llm": round4(llm_score),
            "external_learning": round4(external_score),
            "industrial_loop_schema": round4(loop_score),
            "runtime_fusion": round4(runtime_score),
            "live_automation": round4(live_score)
        }),
        checks,
        gaps,
        recommended_next,
        absorbed_external_patterns: e.external_learning.patterns_absorbed,
        audit_hash,
        boundary: "Internal bounded CMMI-inspired industrial delivery evidence gate; not formal CMMI certification, not full AGI, not proof of live GitHub/Docker/CI release unless live_automation gates are true.".to_string(),
    }
}

fn sample_evidence() -> CmmiEvidence {
    CmmiEvidence {
        source: SourceDocumentEvidence {
            source_document_read: true,
            requirement_extracted: true,
            current_surface_audited: true,
            overclaim_boundary_recorded: true,
        },
        llm: MultiLlmEvidence {
            provider_calls_attempted: 5,
            visible_provider_outputs: 4,
            gpt_planning_audit_visible: true,
            claude_compile_audit_attempted: true,
            claude_compile_audit_visible: false,
            judge_visible: true,
            failed_channels_recorded: true,
            no_roleplay_provider_participation: true,
        },
        external_learning: ExternalLearningEvidence {
            github_api_repos_verified: 8,
            patterns_absorbed: vec![
                "OpenSSF Scorecard evidence gate".to_string(),
                "CodeQL/SonarQube CI quality gate".to_string(),
                "OPA policy-as-code".to_string(),
                "Danger/reviewdog PR automation".to_string(),
                "Sigstore/SBOM supply-chain provenance".to_string(),
                "DORA/Four Keys maturity metrics".to_string(),
            ],
            no_external_code_ingested: true,
            vx_or_other_community_boundary_recorded: true,
        },
        industrial_loop: IndustrialLoopEvidence {
            background_or_container_lane_defined: true,
            gpt_plan_schema_present: true,
            coding_diff_trace_schema_present: true,
            pr_review_gate_schema_present: true,
            automated_test_gate_schema_present: true,
            github_release_gate_schema_present: true,
            auto_report_schema_present: true,
            rollback_or_kill_switch_present: true,
        },
        runtime: RuntimeEvidence {
            python_status_surface_present: true,
            rust_gate_integrated: true,
            build_script_includes_gate: true,
            rust_compile_passed: true,
            python_import_smoke_passed: true,
            pytest_passed: true,
            manifest_readback_present: true,
            skill_reference_present: true,
        },
        live_automation: LiveAutomationEvidence {
            docker_build_passed: false,
            github_push_or_release_passed: false,
            ci_pipeline_run_passed: false,
            pr_created_or_reviewed: false,
            production_publish_authorized: false,
        },
    }
}

#[pyfunction]
fn evaluate_evidence_json(input: &str) -> PyResult<String> {
    let evidence: CmmiEvidence = serde_json::from_str(input)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let decision = evaluate(evidence);
    serde_json::to_string(&decision)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn sample_input_json() -> PyResult<String> {
    serde_json::to_string(&sample_evidence())
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn version() -> PyResult<String> {
    Ok("Hermes PGG CMMI Industrial Gate / Super Evolution 18 v0.1.0".to_string())
}

#[pymodule]
fn hermes_pgg_cmmi_industrial_gate(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(evaluate_evidence_json, m)?)?;
    m.add_function(wrap_pyfunction!(sample_input_json, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}
