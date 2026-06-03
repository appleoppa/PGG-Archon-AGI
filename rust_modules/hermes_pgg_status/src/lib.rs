use pyo3::prelude::*;
use serde::Serialize;

#[derive(Serialize)]
struct StatusSummary<'a> {
    schema: &'a str,
    status: &'a str,
    checked_count: usize,
    ok_count: usize,
    failed_count: usize,
    boundary: &'a str,
}

#[pyfunction]
fn version() -> PyResult<String> {
    Ok("hermes_pgg_status 0.1.0 (read-only Rust status surface)".to_string())
}

#[pyfunction]
fn summarize(ok_count: usize, checked_count: usize) -> PyResult<String> {
    let failed_count = checked_count.saturating_sub(ok_count);
    let status = if checked_count > 0 && failed_count == 0 {
        "PASS"
    } else {
        "WATCH"
    };
    let summary = StatusSummary {
        schema: "HermesPGGStatusRust/v1",
        status,
        checked_count,
        ok_count,
        failed_count,
        boundary: "Read-only Rust summary; not proof of runtime participation, full AGI, or external benchmark.",
    };
    serde_json::to_string_pretty(&summary)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pymodule]
fn hermes_pgg_status(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(summarize, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    #[test]
    fn summarize_pass_when_all_checked_items_ok() {
        let out = summarize(4, 4).expect("summary json");
        let v: Value = serde_json::from_str(&out).expect("valid json");
        assert_eq!(v["schema"], "HermesPGGStatusRust/v1");
        assert_eq!(v["status"], "PASS");
        assert_eq!(v["ok_count"], 4);
        assert_eq!(v["failed_count"], 0);
    }

    #[test]
    fn summarize_watch_when_failed_items_exist() {
        let out = summarize(2, 4).expect("summary json");
        let v: Value = serde_json::from_str(&out).expect("valid json");
        assert_eq!(v["status"], "WATCH");
        assert_eq!(v["failed_count"], 2);
    }

    #[test]
    fn summarize_saturates_failed_count_when_ok_exceeds_checked() {
        let out = summarize(99, 4).expect("summary json");
        let v: Value = serde_json::from_str(&out).expect("valid json");
        assert_eq!(v["status"], "PASS");
        assert_eq!(v["failed_count"], 0);
        assert_eq!(v["ok_count"], 99);
        assert_eq!(v["checked_count"], 4);
    }
}
