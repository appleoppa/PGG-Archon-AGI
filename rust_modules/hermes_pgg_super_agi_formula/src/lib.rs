/// P16: `hermes_pgg_super_agi_formula` — Ψ_SUPER_AGI formula score & gate
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use serde_json::{json, Value};
use std::collections::BTreeMap;

fn fin(v: &Value, d: f64) -> f64 { match v.as_f64() { Some(n) if n.is_finite() => n, _ => d } }
fn clamp(v: f64, lo: f64, hi: f64) -> f64 { v.max(lo).min(hi) }
fn r3(v: f64) -> f64 { (v * 1000.0).round() / 1000.0 }
fn r6(v: f64) -> f64 { (v * 1_000_000.0).round() / 1_000_000.0 }

macro_rules! obj {
    ($s:expr) => {{
        let _v: Value = if $s.is_empty() || $s == "null" { json!({}) } else { serde_json::from_str($s).unwrap_or(json!({})) };
        _v.as_object().cloned().unwrap_or_default()
    }};
}

fn unit(v: &Value, d: f64) -> f64 { clamp(fin(v, d), 0.0, 2.0) }

static DEFAULT_WEIGHTS: &[(&str, f64)] = &[
    ("delta_g_apex", 1.0), ("m_mimo", 1.0), ("phi_mcp", 1.0),
    ("f_github", 1.0), ("s_fix", 1.0), ("omega_rust_go", 1.0),
    ("error_decay", 1.0), ("hallucination_noise", 1.4), ("system_drag", 1.0),
];

static BOTTOM_SAFETY_KEYS: &[&str] = &[
    "manual_git_commit_review", "no_secret_reading", "no_production_skill_override",
    "no_core_loop_forced_modify", "no_untrusted_mcp_auto_register", "rollback_required",
];

fn fingerprint(o: &BTreeMap<String, Value>) -> String {
    let s = serde_json::to_string(o).unwrap_or_default();
    let hash = blake3::hash(s.as_bytes());
    hash.to_hex()[..24].to_string()
}

#[pyfunction]
fn build_super_agi_formula_report(s: &str) -> PyResult<String> {
    let o = obj!(s);

    // weights
    let w_sig = o.get("weights").and_then(|x| x.as_object()).cloned().unwrap_or_default();
    let mut w = BTreeMap::new();
    for (k, def) in DEFAULT_WEIGHTS {
        w.insert(k.to_string(), unit(w_sig.get(*k).unwrap_or(&json!(def)), *def));
    }

    let delta_g_apex = fin(o.get("delta_g_apex").unwrap_or(&json!(75.0)), 75.0);
    let m_mimo = unit(o.get("m_mimo").unwrap_or(&json!(1.0)), 1.0);
    let phi_mcp = unit(o.get("phi_mcp").unwrap_or(&json!(1.0)), 1.0);
    let f_github = unit(o.get("f_github").unwrap_or(&json!(0.5)), 0.5);
    let s_fix = fin(o.get("s_fix").unwrap_or(&json!(80.0)), 80.0);
    let omega_rust_go = unit(o.get("omega_rust_go").unwrap_or(&json!(0.5)), 0.5);

    let error_decay = fin(o.get("error_decay").unwrap_or(&json!(10.0)), 10.0);
    let hallucination_noise = fin(o.get("hallucination_noise").unwrap_or(&json!(15.0)), 15.0);
    let system_drag = fin(o.get("system_drag").unwrap_or(&json!(10.0)), 10.0);

    let spiral_gain = delta_g_apex * m_mimo * phi_mcp * f_github;
    let self_fix_kernel = s_fix * omega_rust_go;
    let drag = error_decay * w.get("error_decay").copied().unwrap_or(1.0)
        + hallucination_noise * w.get("hallucination_noise").copied().unwrap_or(1.4)
        + system_drag * w.get("system_drag").copied().unwrap_or(1.0);
    let raw_score = spiral_gain + self_fix_kernel - drag;
    let normalized = clamp(raw_score / 2.0, 0.0, 100.0);

    let mut report = BTreeMap::new();
    report.insert("schema".to_string(), json!("PGGArchonSuperAGIFormulaReport/v1"));
    report.insert("formula".to_string(), json!("Ψ_SUPER_AGI(t+1)=ΔG_APEX·M_MIMO·Φ_MCP·F_GitHub + S_fix·Ω_RustGo - Σ(ErrorDecay+HallucinationNoise+SystemDrag)"));

    let mut inputs = BTreeMap::new();
    inputs.insert("delta_g_apex".to_string(), json!(r3(delta_g_apex)));
    inputs.insert("m_mimo".to_string(), json!(r3(m_mimo)));
    inputs.insert("phi_mcp".to_string(), json!(r3(phi_mcp)));
    inputs.insert("f_github".to_string(), json!(r3(f_github)));
    inputs.insert("s_fix".to_string(), json!(r3(s_fix)));
    inputs.insert("omega_rust_go".to_string(), json!(r3(omega_rust_go)));
    inputs.insert("error_decay".to_string(), json!(r3(error_decay)));
    inputs.insert("hallucination_noise".to_string(), json!(r3(hallucination_noise)));
    inputs.insert("system_drag".to_string(), json!(r3(system_drag)));
    report.insert("inputs".to_string(), json!(inputs));

    let mut comp = BTreeMap::new();
    comp.insert("spiral_gain".to_string(), json!(r6(spiral_gain)));
    comp.insert("self_fix_kernel_gain".to_string(), json!(r6(self_fix_kernel)));
    comp.insert("drag".to_string(), json!(r6(drag)));
    comp.insert("raw_score".to_string(), json!(r6(raw_score)));
    comp.insert("normalized_score".to_string(), json!(r3(normalized)));
    report.insert("components".to_string(), json!(comp));

    report.insert("side_effects".to_string(), json!("read_only_report"));
    report.insert("capability_boundary".to_string(),
        json!("Engineering score/gate only; not AGI completion, not core takeover, not production promotion."));
    report.insert("ts".to_string(), json!(std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs_f64()));

    let fp = fingerprint(&report);
    report.insert("fingerprint".to_string(), json!(fp));

    Ok(serde_json::to_string(&report).unwrap_or_default())
}

#[pyfunction]
#[pyo3(signature = (report_json = "null", requested_tier = "T0", safety_json = "null"))]
fn build_super_agi_progressive_gate(report_json: &str, requested_tier: &str, safety_json: &str) -> PyResult<String> {
    let rep: Value = serde_json::from_str(report_json).unwrap_or(json!({}));
    let score = fin(rep.get("components").and_then(|c| c.get("normalized_score")).unwrap_or(&json!(0.0)), 0.0);
    let requested = requested_tier.to_uppercase();

    let safe_obj = obj!(safety_json);
    let missing: Vec<String> = BOTTOM_SAFETY_KEYS.iter()
        .filter(|k| {
            let key = **k;
            let required = safe_obj.get(key).and_then(|x| x.as_bool()).unwrap_or(false);
            !required
        })
        .map(|k| k.to_string())
        .collect();

    let mut blockers: Vec<Value> = Vec::new();
    if !missing.is_empty() {
        let mut m = BTreeMap::new();
        m.insert("code".to_string(), json!("bottom_safety_missing"));
        m.insert("items".to_string(), json!(missing));
        blockers.push(json!(m));
    }
    if requested == "T4" || requested == "T5" {
        let mut m = BTreeMap::new();
        m.insert("code".to_string(), json!("human_review_required_for_runtime_or_production_tier"));
        m.insert("requested_tier".to_string(), json!(requested));
        blockers.push(json!(m));
    }
    if score < 75.0 {
        let mut m = BTreeMap::new();
        m.insert("code".to_string(), json!("formula_score_below_75"));
        m.insert("score".to_string(), json!(score));
        blockers.push(json!(m));
    }

    let has_bottom_safety = missing.is_empty();
    let max_open_tier = if score >= 75.0 && has_bottom_safety { "T3" } else { "T1" };
    let allowed_tiers = ["T0", "T1", "T2", "T3"];
    let status = if blockers.is_empty() && allowed_tiers.contains(&requested.as_str()) { "PASS" } else { "HOLD" };

    let allowed_actions = if status == "PASS" {
        json!(["read_only_formula_scoring", "draft_gene_skill_test_gate", "candidate_discovery_scoring_quarantine", "isolated_rust_go_prototype_with_tests"])
    } else {
        json!(["read_only_formula_scoring", "draft_only_report"])
    };

    let mut gate = BTreeMap::new();
    gate.insert("schema".to_string(), json!("PGGArchonSuperAGIProgressiveGate/v1"));
    gate.insert("status".to_string(), json!(status));
    gate.insert("requested_tier".to_string(), json!(requested));
    gate.insert("max_open_tier".to_string(), json!(max_open_tier));
    gate.insert("score".to_string(), json!(r3(score)));
    gate.insert("blockers".to_string(), json!(blockers));
    gate.insert("allowed_actions".to_string(), allowed_actions);
    gate.insert("forbidden_actions".to_string(), json!([
        "git_commit_without_manual_review", "production_skill_override",
        "core_loop_forced_modify", "untrusted_mcp_auto_register",
        "untrusted_github_code_execute", "secret_reading_or_exposure",
    ]));
    gate.insert("side_effects".to_string(), json!("read_only_gate"));
    gate.insert("ts".to_string(), json!(std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs_f64()));

    let fp = fingerprint(&gate);
    gate.insert("fingerprint".to_string(), json!(fp));

    Ok(serde_json::to_string(&gate).unwrap_or_default())
}

#[pymodule]
fn hermes_pgg_super_agi_formula(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__NATIVE__", true)?;
    m.add("__VERSION__", "0.1.0")?;
    m.add_function(wrap_pyfunction!(build_super_agi_formula_report, m)?)?;
    m.add_function(wrap_pyfunction!(build_super_agi_progressive_gate, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn j(s: &str) -> Value { serde_json::from_str(s).unwrap() }

    #[test] fn report_default() {
        let r = build_super_agi_formula_report("").unwrap();
        let v = j(&r);
        assert_eq!(v["schema"], "PGGArchonSuperAGIFormulaReport/v1");
        assert!(v["components"]["normalized_score"].as_f64().unwrap() > 0.0);
    }

    #[test] fn report_high_score() {
        let sig = r#"{"delta_g_apex":95,"m_mimo":1.5,"phi_mcp":1.2,"f_github":1.0,"s_fix":90,"omega_rust_go":1.0,"error_decay":5,"hallucination_noise":3,"system_drag":2}"#;
        let r = build_super_agi_formula_report(sig).unwrap();
        let v = j(&r);
        assert!(v["components"]["normalized_score"].as_f64().unwrap() > 80.0);
    }

    #[test] fn report_low_score() {
        let sig = r#"{"delta_g_apex":10,"m_mimo":0.3,"phi_mcp":0.2,"f_github":0.1,"s_fix":5,"omega_rust_go":0.1,"error_decay":50,"hallucination_noise":60,"system_drag":40}"#;
        let r = build_super_agi_formula_report(sig).unwrap();
        let v = j(&r);
        assert!(v["components"]["normalized_score"].as_f64().unwrap() < 20.0);
    }

    #[test] fn report_has_fingerprint() {
        let r = build_super_agi_formula_report("").unwrap();
        let v = j(&r);
        assert!(!v["fingerprint"].as_str().unwrap_or("").is_empty());
    }

    #[test] fn gate_pass_t0() {
        let rep = build_super_agi_formula_report(r#"{"delta_g_apex":100,"m_mimo":2.0,"phi_mcp":2.0,"f_github":2.0,"s_fix":100,"omega_rust_go":2.0,"error_decay":1,"hallucination_noise":1,"system_drag":1}"#).unwrap();
        let safety = r#"{"manual_git_commit_review":true,"no_secret_reading":true,"no_production_skill_override":true,"no_core_loop_forced_modify":true,"no_untrusted_mcp_auto_register":true,"rollback_required":true}"#;
        let g = build_super_agi_progressive_gate(&rep, "T0", safety).unwrap();
        let v = j(&g);
        assert_eq!(v["status"], "PASS");
    }

    #[test] fn gate_hold_missing_safety() {
        let rep = build_super_agi_formula_report(r#"{"delta_g_apex":90}"#).unwrap();
        let g = build_super_agi_progressive_gate(&rep, "T3", "{}").unwrap();
        let v = j(&g);
        assert_eq!(v["status"], "HOLD");
        assert!(!v["blockers"].as_array().unwrap().is_empty());
    }

    #[test] fn gate_hold_t4_no_human() {
        let rep = build_super_agi_formula_report(r#"{"delta_g_apex":90}"#).unwrap();
        let safety = r#"{"manual_git_commit_review":true,"no_secret_reading":true,"no_production_skill_override":true,"no_core_loop_forced_modify":true,"no_untrusted_mcp_auto_register":true,"rollback_required":true}"#;
        let g = build_super_agi_progressive_gate(&rep, "T4", safety).unwrap();
        let v = j(&g);
        assert_eq!(v["status"], "HOLD");
    }

    #[test] fn gate_hold_low_score() {
        let rep = build_super_agi_formula_report(r#"{"delta_g_apex":10}"#).unwrap();
        let safety = r#"{"manual_git_commit_review":true,"no_secret_reading":true,"no_production_skill_override":true,"no_core_loop_forced_modify":true,"no_untrusted_mcp_auto_register":true,"rollback_required":true}"#;
        let g = build_super_agi_progressive_gate(&rep, "T1", safety).unwrap();
        let v = j(&g);
        assert_eq!(v["status"], "HOLD");
    }

    #[test] fn gate_max_open_tier() {
        let rep = build_super_agi_formula_report(r#"{"delta_g_apex":100,"m_mimo":2.0,"phi_mcp":2.0,"f_github":2.0,"s_fix":100,"omega_rust_go":2.0,"error_decay":1,"hallucination_noise":1,"system_drag":1}"#).unwrap();
        let safety = r#"{"manual_git_commit_review":true,"no_secret_reading":true,"no_production_skill_override":true,"no_core_loop_forced_modify":true,"no_untrusted_mcp_auto_register":true,"rollback_required":true}"#;
        let g = build_super_agi_progressive_gate(&rep, "T1", safety).unwrap();
        let v = j(&g);
        assert_eq!(v["max_open_tier"], "T3");
    }

    #[test] fn gate_forbidden_actions() {
        let rep = build_super_agi_formula_report("").unwrap();
        let g = build_super_agi_progressive_gate(&rep, "T0", "{}").unwrap();
        let v = j(&g);
        assert!(v["forbidden_actions"].as_array().unwrap().len() >= 6);
    }

    #[test] fn gate_has_fingerprint() {
        let rep = build_super_agi_formula_report("").unwrap();
        let g = build_super_agi_progressive_gate(&rep, "T0", "{}").unwrap();
        let v = j(&g);
        assert!(!v["fingerprint"].as_str().unwrap_or("").is_empty());
    }
}
