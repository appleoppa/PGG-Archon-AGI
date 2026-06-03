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
    let status = if checked_count > 0 && failed_count == 0 { "PASS" } else { "WATCH" };
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
