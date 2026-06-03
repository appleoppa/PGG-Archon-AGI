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
    let parsed: Value =
        serde_json::from_str(inventory_json).unwrap_or(Value::Object(Default::default()));
    let summary = parsed
        .get("summary")
        .cloned()
        .unwrap_or(Value::Object(Default::default()));
    let item_count = summary.get("items").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
    let importable_files = summary
        .get("importable_files")
        .and_then(|v| v.as_u64())
        .unwrap_or(0) as usize;
    let dirs = summary.get("dirs").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
    let status = if item_count > 0 && importable_files + dirs >= item_count {
        "WATCH"
    } else {
        "WATCH"
    };
    let report = OverlaySummary {
        schema: "HermesPGGOverlayRust/v1",
        status,
        item_count,
        importable_files,
        dirs,
        recommendation:
            "Keep read-only governance; do not bulk delete or bulk commit ignored overlays.",
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

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;
    use serde_json::Value;

    #[test]
    fn summarize_inventory_extracts_counts() {
        let inv = r#"{"summary":{"items":23,"importable_files":22,"dirs":1}}"#;
        let out = summarize_inventory(inv).expect("overlay json");
        let v: Value = serde_json::from_str(&out).expect("valid json");
        assert_eq!(v["schema"], "HermesPGGOverlayRust/v1");
        assert_eq!(v["item_count"], 23);
        assert_eq!(v["importable_files"], 22);
        assert_eq!(v["dirs"], 1);
    }

    #[test]
    fn summarize_inventory_handles_invalid_json() {
        let out = summarize_inventory("not-json").expect("overlay json");
        let v: Value = serde_json::from_str(&out).expect("valid json");
        assert_eq!(v["item_count"], 0);
        assert_eq!(v["status"], "WATCH");
    }

    #[test]
    fn summarize_inventory_handles_missing_or_weird_summary_shapes() {
        for sample in [
            "{}",
            r#"{"summary":null}"#,
            r#"{"summary":{"items":"many","dirs":true}}"#,
        ] {
            let out = summarize_inventory(sample).expect("overlay json");
            let v: Value = serde_json::from_str(&out).expect("valid json");
            assert_eq!(v["schema"], "HermesPGGOverlayRust/v1");
            assert_eq!(v["status"], "WATCH");
        }
    }

    proptest! {
        #[test]
        fn summarize_inventory_property_counts_are_extracted_or_zero(
            items in 0u64..10_000,
            importable_files in 0u64..10_000,
            dirs in 0u64..10_000,
        ) {
            let input = serde_json::json!({
                "summary": {
                    "items": items,
                    "importable_files": importable_files,
                    "dirs": dirs,
                }
            }).to_string();
            let out = summarize_inventory(&input).expect("overlay json");
            let v: Value = serde_json::from_str(&out).expect("valid json");
            prop_assert_eq!(v["item_count"].as_u64(), Some(items));
            prop_assert_eq!(v["importable_files"].as_u64(), Some(importable_files));
            prop_assert_eq!(v["dirs"].as_u64(), Some(dirs));
            prop_assert_eq!(v["status"].as_str(), Some("WATCH"));
        }
    }
}
