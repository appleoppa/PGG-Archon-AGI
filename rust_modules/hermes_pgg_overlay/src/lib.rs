use pyo3::prelude::*;
use serde::Serialize;
use serde_json::Value;

#[derive(Serialize)]
struct OverlaySummary<'a> {
    schema: &'a str,
    status: &'a str,
    item_count: usize,
    importable_files: usize,
    dirs: usize,
    recommendation: &'a str,
    boundary: &'a str,
}

#[pyfunction]
fn version() -> PyResult<String> {
    Ok("hermes_pgg_overlay 0.1.0 (read-only Rust overlay inventory surface)".to_string())
}

#[pyfunction]
fn summarize_inventory(inventory_json: &str) -> PyResult<String> {
    let parsed: Value = serde_json::from_str(inventory_json).unwrap_or(Value::Object(Default::default()));
    let summary = parsed.get("summary").cloned().unwrap_or(Value::Object(Default::default()));
    let item_count = summary.get("items").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
    let importable_files = summary.get("importable_files").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
    let dirs = summary.get("dirs").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
    let status = if item_count > 0 && importable_files + dirs >= item_count { "WATCH" } else { "WATCH" };
    let report = OverlaySummary {
        schema: "HermesPGGOverlayRust/v1",
        status,
        item_count,
        importable_files,
        dirs,
        recommendation: "Keep read-only governance; do not bulk delete or bulk commit ignored overlays.",
        boundary: "Inventory summarization only; no filesystem mutation and no capability claim.",
    };
    serde_json::to_string_pretty(&report)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pymodule]
fn hermes_pgg_overlay(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(summarize_inventory, m)?)?;
    Ok(())
}
