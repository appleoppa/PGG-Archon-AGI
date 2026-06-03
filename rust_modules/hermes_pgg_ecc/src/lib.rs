use pyo3::prelude::*;
use serde::Serialize;
use serde_json::Value;

#[derive(Serialize)]
struct EccReport<'a> {
    schema: &'a str,
    status: &'a str,
    score: f64,
    total_penalty: f64,
    boundary: &'a str,
}

fn clamp01(v: f64) -> f64 {
    if v < 0.0 {
        0.0
    } else if v > 1.0 {
        1.0
    } else {
        v
    }
}

#[pyfunction]
fn version() -> PyResult<String> {
    Ok("hermes_pgg_ecc 0.1.0 (read-only Rust ECC surface)".to_string())
}

#[pyfunction]
fn evaluate(signals_json: &str) -> PyResult<String> {
    let parsed: Value =
        serde_json::from_str(signals_json).unwrap_or(Value::Object(Default::default()));
    let weights = [
        ("hallucination", 30.0),
        ("security", 25.0),
        ("unverified_completion", 20.0),
        ("missing_evidence", 15.0),
        ("cost_or_latency", 5.0),
        ("governance_debt", 5.0),
    ];
    let mut penalty = 0.0;
    for (name, weight) in weights {
        let sev = parsed
            .get(name)
            .and_then(|v| v.as_f64())
            .map(clamp01)
            .unwrap_or(0.0);
        penalty += sev * weight;
    }
    let score = (100.0_f64 - penalty).max(0.0_f64);
    let status = if score < 60.0 {
        "BLOCKED"
    } else if score < 85.0 || penalty > 0.0 {
        "WATCH"
    } else {
        "PASS"
    };
    let report = EccReport {
        schema: "HermesPGGEccRust/v1",
        status,
        score: (score * 100.0).round() / 100.0,
        total_penalty: (penalty * 100.0).round() / 100.0,
        boundary:
            "Read-only Rust ECC scoring; does not auto-repair or prove legal/system correctness.",
    };
    serde_json::to_string_pretty(&report)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pymodule]
fn hermes_pgg_ecc(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    #[test]
    fn evaluate_passes_empty_signal_set() {
        let out = evaluate("{}").expect("ecc json");
        let v: Value = serde_json::from_str(&out).expect("valid json");
        assert_eq!(v["schema"], "HermesPGGEccRust/v1");
        assert_eq!(v["status"], "PASS");
        assert_eq!(v["score"], 100.0);
    }

    #[test]
    fn evaluate_blocks_critical_high_penalty_set() {
        let out = evaluate(r#"{"hallucination":1.0,"security":1.0,"unverified_completion":1.0}"#)
            .expect("ecc json");
        let v: Value = serde_json::from_str(&out).expect("valid json");
        assert_eq!(v["status"], "BLOCKED");
        assert_eq!(v["total_penalty"], 75.0);
    }

    #[test]
    fn evaluate_treats_invalid_json_as_empty_signals() {
        let out = evaluate("not-json").expect("ecc json");
        let v: Value = serde_json::from_str(&out).expect("valid json");
        assert_eq!(v["status"], "PASS");
        assert_eq!(v["total_penalty"], 0.0);
    }
}
