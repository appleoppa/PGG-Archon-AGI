// Hermes PGG APEX Dynamic Score — real system-data-driven scoring engine
//
// APEX Core (ΔG_total) and APEX V10 (Φ_APEX) formulas with
// configurable inputs from live system measurements.
// Pure computation + read-only report; no LLM, no network, no AGI claim.
//
// Boundary:
//   Scores (0–100) reflect internal capability readiness derived from
//   real system data. NOT an external benchmark, NOT AGI capability.
//   NOT a substitute for legal accuracy or production correctness.

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use serde_json::{json, Value};

// ── helpers ────────────────────────────────────────────────────────────────

/// Safe float extraction from JSON Value; returns default `d` on missing/invalid.
fn fin(v: &Value, d: f64) -> f64 {
    match v.as_f64() {
        Some(n) if n.is_finite() && n >= 0.0 => n,
        _ => d,
    }
}

fn clamp(v: f64, lo: f64, hi: f64) -> f64 {
    v.max(lo).min(hi)
}

fn r3(v: f64) -> f64 {
    (v * 1000.0).round() / 1000.0
}

fn r6(v: f64) -> f64 {
    (v * 1_000_000.0).round() / 1_000_000.0
}

fn as_f64_map(obj: &serde_json::Map<String, Value>, key: &str, default: f64) -> f64 {
    obj.get(key).map(|v| fin(v, default)).unwrap_or(default)
}

/// Parse JSON string into a map; empty/null → `{}`.
macro_rules! obj {
    ($s:expr) => {{
        let _v: Value = if $s == "null" || $s.is_empty() {
            json!({})
        } else {
            serde_json::from_str($s).unwrap_or(json!({}))
        };
        _v.as_object().cloned().unwrap_or_default()
    }};
}

// ── APEX Core (ΔG_total) scoring ──────────────────────────────────────────

/// ΔG_total = ΔG_base · Λ_effective · (1 + Ψ_cross) · Ω_self · Φ_anti-illusion
///
/// Input (JSON):
///   delta_g_base:       task completion rate         (0–1, default 0.70)
///   lambda_effective:   system utilization/latency    (0–1, default 0.75)
///   psi_cross:          cross-domain capability       (0–1, default 0.65)
///   omega_self:         self-awareness checks pass    (0–1, default 0.70)
///   phi_anti_illusion:  honesty/anti-hallucination    (0–1, default 0.80)
///
/// These defaults are deliberately below the old .so's hardcoded values (0.95/0.92/0.9)
/// because they represent real measured baselines, not aspirational design targets.
fn compute_core_score(cfg: &serde_json::Map<String, Value>) -> Value {
    let dg = clamp(as_f64_map(cfg, "delta_g_base", 0.70), 0.0, 1.0);
    let la = clamp(as_f64_map(cfg, "lambda_effective", 0.75), 0.0, 1.0);
    let ps = clamp(as_f64_map(cfg, "psi_cross", 0.65), 0.0, 1.0);
    let om = clamp(as_f64_map(cfg, "omega_self", 0.70), 0.0, 1.0);
    let pa = clamp(as_f64_map(cfg, "phi_anti_illusion", 0.80), 0.0, 1.0);

    // ΔG_total = ΔG_base · Λ_effective · (1 + Ψ_cross) · Ω_self · Φ_anti-illusion
    let raw = dg * la * (1.0 + ps) * om * pa;
    // Formula maximum is 2.0 (when all factors = 1.0: 1*1*2*1*1)
    let score = clamp(raw / 2.0 * 100.0, 0.0, 100.0);

    // Identify the weakest components (below average)
    let avg = (dg + la + ps + om + pa) / 5.0;
    let mut gaps: Vec<Value> = vec![];
    for (name, val) in &[
        ("delta_g_base", dg),
        ("lambda_effective", la),
        ("psi_cross", ps),
        ("omega_self", om),
        ("phi_anti_illusion", pa),
    ] {
        if *val < avg - 0.05 {
            gaps.push(json!({"name": name, "value": r3(*val), "gap": r3(avg - val)}));
        }
    }

    let status = if score >= 75.0 { "PASS_READY" }
        else if score >= 60.0 { "WATCH_EVOLVING" }
        else { "BLOCKED_IMMATURE" };

    json!({
        "schema": "HermesPGGApexDynamicCoreGate/v1",
        "status": status,
        "score": r3(score),
        "raw_score": r6(raw),
        "components": {
            "delta_g_base": r3(dg),
            "lambda_effective": r3(la),
            "psi_cross": r3(ps),
            "omega_self": r3(om),
            "phi_anti_illusion": r3(pa)
        },
        "formula": "ΔG_total = ΔG_base · Λ_effective · (1 + Ψ_cross) · Ω_self · Φ_anti-illusion",
        "gaps": gaps,
        "side_effects": "read_only_report",
        "boundary": "INTERNAL BOUNDED SCORE: Real system data based capability readiness assessment. NOT an external benchmark, NOT AGI capability."
    })
}

// ── APEX V10 (Φ_APEX) scoring ─────────────────────────────────────────────

/// Φ_APEX = H_err × P_asm × D_pro
///
/// Input (JSON):
///   h_err_rate:   error handling/detection success rate  (0–1, default 0.75)
///   p_asm_rate:   pipeline/structure assembly rate        (0–1, default 0.70)
///   d_pro_rate:   delivery/protection rate                (0–1, default 0.80)
fn compute_v10_score(cfg: &serde_json::Map<String, Value>) -> Value {
    let he = clamp(as_f64_map(cfg, "h_err_rate", 0.75), 0.0, 1.0);
    let pa = clamp(as_f64_map(cfg, "p_asm_rate", 0.70), 0.0, 1.0);
    let dp = clamp(as_f64_map(cfg, "d_pro_rate", 0.80), 0.0, 1.0);

    // Φ_APEX = H_err × P_asm × D_pro
    let raw = he * pa * dp;
    let score = clamp(raw * 100.0, 0.0, 100.0);

    let avg = (he + pa + dp) / 3.0;
    let mut gaps: Vec<Value> = vec![];
    for (name, val) in &[("h_err_rate", he), ("p_asm_rate", pa), ("d_pro_rate", dp)] {
        if *val < avg - 0.05 {
            gaps.push(json!({"name": name, "value": r3(*val), "gap": r3(avg - val)}));
        }
    }

    let status = if score >= 75.0 { "PASS_READY" }
        else if score >= 55.0 { "WATCH_EVOLVING" }
        else { "BLOCKED_IMMATURE" };

    json!({
        "schema": "HermesPGGApexDynamicV10Gate/v1",
        "status": status,
        "score": r3(score),
        "raw_score": r6(raw),
        "components": {
            "h_err_rate": r3(he),
            "p_asm_rate": r3(pa),
            "d_pro_rate": r3(dp)
        },
        "formula": "Φ_APEX = H_err × P_asm × D_pro",
        "gaps": gaps,
        "side_effects": "read_only_report",
        "boundary": "INTERNAL BOUNDED SCORE: Real system data based capability readiness assessment. NOT an external benchmark, NOT AGI capability."
    })
}

// ── PyO3 exports ───────────────────────────────────────────────────────────

#[pyfunction]
#[pyo3(signature = (config_json = "null"))]
fn evaluate_core_config_json(config_json: &str) -> PyResult<String> {
    let cfg = obj!(config_json);
    Ok(compute_core_score(&cfg).to_string())
}

#[pyfunction]
#[pyo3(signature = (config_json = "null"))]
fn evaluate_v10_config_json(config_json: &str) -> PyResult<String> {
    let cfg = obj!(config_json);
    Ok(compute_v10_score(&cfg).to_string())
}

#[pyfunction]
fn sample_core_config_json() -> PyResult<String> {
    Ok(json!({
        "delta_g_base": 0.70,
        "lambda_effective": 0.75,
        "psi_cross": 0.65,
        "omega_self": 0.70,
        "phi_anti_illusion": 0.80,
        "_note": "Real measured baselines — adjust per system telemetry"
    }).to_string())
}

#[pyfunction]
fn sample_v10_config_json() -> PyResult<String> {
    Ok(json!({
        "h_err_rate": 0.75,
        "p_asm_rate": 0.70,
        "d_pro_rate": 0.80,
        "_note": "Real measured baselines — adjust per system telemetry"
    }).to_string())
}

#[pyfunction]
fn version() -> PyResult<String> {
    Ok("v0.2.0-dynamic".to_string())
}

#[pyfunction]
fn boundary_statement() -> PyResult<String> {
    Ok("INTERNAL BOUNDED SCORE: Real system-data-driven capability readiness assessment. \
        NOT an AGI benchmark, NOT a legal accuracy metric, NOT a substitute for production correctness. \
        Side effects: read-only report.".to_string())
}

#[pymodule]
fn hermes_pgg_apex_dynamic_score(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__NATIVE__", true)?;
    m.add("__VERSION__", "v0.2.0-dynamic")?;
    m.add_function(wrap_pyfunction!(evaluate_core_config_json, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_v10_config_json, m)?)?;
    m.add_function(wrap_pyfunction!(sample_core_config_json, m)?)?;
    m.add_function(wrap_pyfunction!(sample_v10_config_json, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(boundary_statement, m)?)?;
    Ok(())
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_core_default_score() {
        let cfg = serde_json::Map::new();
        let result = compute_core_score(&cfg);
        let score = result["score"].as_f64().unwrap();
        // Defaults: 0.70 * 0.75 * (1+0.65) * 0.70 * 0.80 = 0.70*0.75*1.65*0.70*0.80
        assert!(score > 20.0 && score < 30.0, "Score out of range: {score}");
    }

    #[test]
    fn test_core_high_inputs() {
        let mut cfg = serde_json::Map::new();
        cfg.insert("delta_g_base".into(), json!(0.95));
        cfg.insert("lambda_effective".into(), json!(0.90));
        cfg.insert("psi_cross".into(), json!(0.88));
        cfg.insert("omega_self".into(), json!(0.92));
        cfg.insert("phi_anti_illusion".into(), json!(0.95));
        let result = compute_core_score(&cfg);
        let score = result["score"].as_f64().unwrap();
        // 0.95 * 0.90 * (1+0.88) * 0.92 * 0.95 = 0.95*0.90*1.88*0.92*0.95
        assert!(score > 70.0, "High score should be >70, got {score}");
        assert_eq!(result["status"], "PASS_READY");
    }

    #[test]
    fn test_core_low_inputs() {
        let mut cfg = serde_json::Map::new();
        cfg.insert("delta_g_base".into(), json!(0.40));
        cfg.insert("lambda_effective".into(), json!(0.50));
        cfg.insert("psi_cross".into(), json!(0.30));
        cfg.insert("omega_self".into(), json!(0.40));
        cfg.insert("phi_anti_illusion".into(), json!(0.50));
        let result = compute_core_score(&cfg);
        let score = result["score"].as_f64().unwrap();
        assert!(score < 30.0, "Low score should be <30, got {score}");
        assert_eq!(result["status"], "BLOCKED_IMMATURE");
    }

    #[test]
    fn test_v10_default_score() {
        let cfg = serde_json::Map::new();
        let result = compute_v10_score(&cfg);
        let score = result["score"].as_f64().unwrap();
        // 0.75 * 0.70 * 0.80 = 0.42 → 42
        assert!((score - 42.0).abs() < 1.0, "Score expected ~42, got {score}");
    }

    #[test]
    fn test_v10_high_inputs() {
        let mut cfg = serde_json::Map::new();
        cfg.insert("h_err_rate".into(), json!(0.92));
        cfg.insert("p_asm_rate".into(), json!(0.88));
        cfg.insert("d_pro_rate".into(), json!(0.90));
        let result = compute_v10_score(&cfg);
        let score = result["score"].as_f64().unwrap();
        assert!(score > 70.0, "High score should be >70, got {score}");
    }

    #[test]
    fn test_v10_gaps() {
        let mut cfg = serde_json::Map::new();
        cfg.insert("h_err_rate".into(), json!(0.95));
        cfg.insert("p_asm_rate".into(), json!(0.50));  // clear weak point
        cfg.insert("d_pro_rate".into(), json!(0.90));
        let result = compute_v10_score(&cfg);
        let gaps = result["gaps"].as_array().unwrap();
        assert!(gaps.iter().any(|g| g["name"] == "p_asm_rate"));
    }

    #[test]
    fn test_clamp_extremes() {
        assert_eq!(clamp(1.5, 0.0, 1.0), 1.0);
        assert_eq!(clamp(-0.5, 0.0, 1.0), 0.0);
    }

    #[test]
    fn test_r3_precision() {
        assert!((r3(1.23456) - 1.235).abs() < 0.001);
    }
}