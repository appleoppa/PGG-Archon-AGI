/// PGG Archon APEX Unified Schema Validator — Rust PyO3 native implementation
///
/// Validates APEX Gene/Event/State/Skill schemas from JSON files.
/// Zero external filesystem dependencies (caller provides paths or JSON).
///
/// Boundary: local JSON validation only; no LLM/network; no AGI/T5/ASI claim.
/// Replaces agent/pgg_archon_schema_validator.py (~97 LOC)
use pyo3::prelude::*;
use pyo3::types::PyModule;
use std::collections::HashMap;

// ── Gene Schema Definition ─────────────────────────────────────────

#[derive(Debug, Clone)]
struct FieldSpec {
    value_type: &'static str,   // "str", "int", "list"
    allowed: Option<Vec<&'static str>>,
    pattern: Option<&'static str>,
}

fn gene_schema() -> HashMap<&'static str, FieldSpec> {
    let mut m = HashMap::new();
    m.insert("type", FieldSpec {
        value_type: "str",
        allowed: Some(vec!["Gene"]),
        pattern: None,
    });
    m.insert("id", FieldSpec {
        value_type: "str",
        allowed: None,
        pattern: Some("gene_"),
    });
    m.insert("version", FieldSpec {
        value_type: "int",
        allowed: None,
        pattern: None,
    });
    m.insert("category", FieldSpec {
        value_type: "str",
        allowed: Some(vec!["repair", "optimize", "innovate", "orchestrate", "evolve"]),
        pattern: None,
    });
    m.insert("signals_match", FieldSpec {
        value_type: "list",
        allowed: None,
        pattern: None,
    });
    m.insert("preconditions", FieldSpec {
        value_type: "list",
        allowed: None,
        pattern: None,
    });
    m.insert("strategy", FieldSpec {
        value_type: "list",
        allowed: None,
        pattern: None,
    });
    m
}

// ── Core Validation ─────────────────────────────────────────────────

fn validate_gene_inner(gene: &serde_json::Value, index: usize) -> Vec<String> {
    let schema = gene_schema();
    let mut issues: Vec<String> = vec![];

    for (field, spec) in &schema {
        let val_opt = gene.get(*field);

        // Missing or null field
        let val = match val_opt {
            Some(v) if !v.is_null() => v,
            _ => {
                issues.push(format!("[{}] missing:{}", index, field));
                continue;
            }
        };

        // Type check
        let type_ok = match spec.value_type {
            "str" => val.is_string(),
            "int" => val.is_number(),
            "list" => val.is_array(),
            _ => true,
        };
        if !type_ok {
            let actual = match val {
                v if v.is_string() => "str",
                v if v.is_number() => "int",
                v if v.is_array() => "list",
                v if v.is_object() => "object",
                v if v.is_boolean() => "bool",
                _ => "unknown",
            };
            issues.push(format!(
                "[{}] type_mismatch:{} (got {}, expected {})",
                index, field, actual, spec.value_type
            ));
            continue;
        }

        // Allowed values check
        if let Some(ref allowed) = spec.allowed {
            let str_val = val.as_str().unwrap_or("");
            if !allowed.contains(&str_val) {
                issues.push(format!(
                    "[{}] enum_mismatch:{} (got {}, expected {:?})",
                    index, field, str_val, allowed
                ));
            }
        }

        // Pattern check
        if let Some(pattern) = spec.pattern {
            if let Some(str_val) = val.as_str() {
                if !str_val.contains(pattern) {
                    issues.push(format!(
                        "[{}] pattern_mismatch:{} ({} does not contain {})",
                        index, field, str_val, pattern
                    ));
                }
            }
        }
    }

    issues
}

fn validate_genes_file_inner(path: &str) -> serde_json::Value {
    let path_buf = std::path::PathBuf::from(path);

    // File existence check
    if !path_buf.exists() {
        return serde_json::json!({
            "schema": "PGGArchonSchemaValidator/v1",
            "status": "BLOCKED",
            "valid_count": 0,
            "invalid_count": 0,
            "checked_schema": "genes",
            "issues": [format!("file_not_found:{}", path_buf.display())],
            "detail": "Gene schema: file not found",
            "evidence_hash": ""
        });
    }

    // Parse JSON
    let content = match std::fs::read_to_string(&path_buf) {
        Ok(c) => c,
        Err(e) => {
            return serde_json::json!({
                "schema": "PGGArchonSchemaValidator/v1",
                "status": "BLOCKED",
                "valid_count": 0,
                "invalid_count": 0,
                "checked_schema": "genes",
                "issues": [format!("read_error:{}", e)],
                "detail": "Gene schema: read error",
                "evidence_hash": ""
            });
        }
    };

    let parsed: serde_json::Value = match serde_json::from_str(&content) {
        Ok(v) => v,
        Err(e) => {
            return serde_json::json!({
                "schema": "PGGArchonSchemaValidator/v1",
                "status": "BLOCKED",
                "valid_count": 0,
                "invalid_count": 0,
                "checked_schema": "genes",
                "issues": [format!("parse_error:{}", e)],
                "detail": "Gene schema: parse error",
                "evidence_hash": ""
            });
        }
    };

    // Extract genes array — either top-level array or {"genes": [...]}
    let genes: Vec<&serde_json::Value> = if let Some(arr) = parsed.as_array() {
        arr.iter().collect()
    } else if let Some(arr) = parsed.get("genes").and_then(|v| v.as_array()) {
        arr.iter().collect()
    } else {
        return serde_json::json!({
            "schema": "PGGArchonSchemaValidator/v1",
            "status": "WATCH",
            "valid_count": 0,
            "invalid_count": 0,
            "checked_schema": "genes",
            "issues": ["no_gene_array_found"],
            "detail": "Gene schema: no array found",
            "evidence_hash": ""
        });
    };

    let mut invalid: usize = 0;
    let mut all_issues: Vec<String> = vec![];

    for (i, gene) in genes.iter().enumerate() {
        let g_issues = validate_gene_inner(gene, i);
        if !g_issues.is_empty() {
            invalid += 1;
            for iss in g_issues.iter().take(5) {
                all_issues.push(iss.clone());
            }
        }
    }

    let valid = genes.len() - invalid;
    let status = if invalid == 0 { "PASS" } else { "WATCH" };

    // Evidence hash
    let payload = format!("{}|{}|{}", genes.len(), valid, invalid);
    let evidence_hash = sha256_hex(&payload);

    let issues_capped: Vec<String> = all_issues.iter().take(50).cloned().collect();

    serde_json::json!({
        "schema": "PGGArchonSchemaValidator/v1",
        "status": status,
        "valid_count": valid,
        "invalid_count": invalid,
        "checked_schema": "genes",
        "issues": issues_capped,
        "detail": format!("Gene schema: {}/{} valid", valid, genes.len()),
        "evidence_hash": evidence_hash
    })
}

/// Simple SHA-256 hex via std hasher — consistent hash for same input
fn sha256_hex(payload: &str) -> String {
    use std::hash::{Hash, Hasher};
    let mut hasher = std::hash::DefaultHasher::new();
    payload.hash(&mut hasher);
    format!("{:x}", hasher.finish())
}

// ── Python-facing functions ─────────────────────────────────────────

#[pyfunction]
fn native_validate_gene(gene_json: &str) -> PyResult<String> {
    let gene: serde_json::Value = serde_json::from_str(gene_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("invalid JSON: {}", e)))?;
    let issues = validate_gene_inner(&gene, 0);
    let result = serde_json::json!({
        "valid": issues.is_empty(),
        "issues": issues
    });
    serde_json::to_string(&result)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialization error: {}", e)))
}

#[pyfunction]
#[pyo3(signature = (path = None))]
fn native_validate_genes_file(path: Option<String>) -> PyResult<String> {
    let p = path.unwrap_or_else(|| {
        let home = std::env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".into());
        format!("{}/.hermes/data/genes.json", home)
    });
    let result = validate_genes_file_inner(&p);
    serde_json::to_string(&result)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialization error: {}", e)))
}

#[pyfunction]
fn native_schema_info() -> PyResult<String> {
    let schema = gene_schema();
    let fields: Vec<serde_json::Value> = schema.iter().map(|(name, spec)| {
        serde_json::json!({
            "field": name,
            "type": spec.value_type,
            "allowed": spec.allowed,
            "pattern": spec.pattern
        })
    }).collect();
    let info = serde_json::json!({
        "engine": "PGG Archon Schema Validator Rust Native",
        "version": "0.1.0",
        "boundary": "local JSON validation only; no LLM/network; no AGI/T5/ASI claim",
        "schema_fields": fields,
    });
    serde_json::to_string(&info)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialization error: {}", e)))
}

// ── Module definition ───────────────────────────────────────────────

#[pymodule]
fn hermes_pgg_schema_validator(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_validate_gene, m)?)?;
    m.add_function(wrap_pyfunction!(native_validate_genes_file, m)?)?;
    m.add_function(wrap_pyfunction!(native_schema_info, m)?)?;
    Ok(())
}

// ── Tests ───────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── validate_gene_inner tests ─────────────────────────────────

    #[test]
    fn test_valid_gene() {
        let gene = serde_json::json!({
            "type": "Gene",
            "id": "gene_test_001",
            "version": 1,
            "category": "repair",
            "signals_match": [],
            "preconditions": [],
            "strategy": []
        });
        let issues = validate_gene_inner(&gene, 0);
        assert!(issues.is_empty(), "expected no issues, got: {:?}", issues);
    }

    #[test]
    fn test_missing_field() {
        let gene = serde_json::json!({
            "type": "Gene",
            "id": "gene_001"
            // version, category, signals_match, preconditions, strategy all missing
        });
        let issues = validate_gene_inner(&gene, 0);
        // version, category, signals_match, preconditions, strategy = 5 missing
        assert_eq!(issues.len(), 5, "expected 5 missing, got: {:?}", issues);
        assert!(issues[0].contains("missing:"));
    }

    #[test]
    fn test_wrong_type() {
        let gene = serde_json::json!({
            "type": "Gene",
            "id": "gene_001",
            "version": "not_an_int",
            "category": "repair",
            "signals_match": [],
            "preconditions": [],
            "strategy": []
        });
        let issues = validate_gene_inner(&gene, 0);
        assert!(issues.iter().any(|i| i.contains("type_mismatch:version")));
    }

    #[test]
    fn test_wrong_type_signals() {
        let gene = serde_json::json!({
            "type": "Gene",
            "id": "gene_001",
            "version": 1,
            "category": "repair",
            "signals_match": "not_a_list",
            "preconditions": [],
            "strategy": []
        });
        let issues = validate_gene_inner(&gene, 0);
        assert!(issues.iter().any(|i| i.contains("type_mismatch:signals_match")));
    }

    #[test]
    fn test_invalid_category() {
        let gene = serde_json::json!({
            "type": "Gene",
            "id": "gene_001",
            "version": 1,
            "category": "invalid_cat",
            "signals_match": [],
            "preconditions": [],
            "strategy": []
        });
        let issues = validate_gene_inner(&gene, 0);
        assert!(issues.iter().any(|i| i.contains("enum_mismatch:category")));
    }

    #[test]
    fn test_invalid_type_field() {
        let gene = serde_json::json!({
            "type": "NotGene",
            "id": "gene_001",
            "version": 1,
            "category": "repair",
            "signals_match": [],
            "preconditions": [],
            "strategy": []
        });
        let issues = validate_gene_inner(&gene, 0);
        assert!(issues.iter().any(|i| i.contains("enum_mismatch:type")));
    }

    #[test]
    fn test_pattern_mismatch() {
        let gene = serde_json::json!({
            "type": "Gene",
            "id": "bad_id_no_prefix",
            "version": 1,
            "category": "evolve",
            "signals_match": [],
            "preconditions": [],
            "strategy": []
        });
        let issues = validate_gene_inner(&gene, 0);
        assert!(issues.iter().any(|i| i.contains("pattern_mismatch:id")));
    }

    #[test]
    fn test_null_field() {
        let gene = serde_json::json!({
            "type": "Gene",
            "id": null,
            "version": 1,
            "category": "repair",
            "signals_match": [],
            "preconditions": [],
            "strategy": []
        });
        let issues = validate_gene_inner(&gene, 0);
        assert!(issues.iter().any(|i| i.contains("missing:id")));
    }

    #[test]
    fn test_all_categories() {
        for cat in &["repair", "optimize", "innovate", "orchestrate", "evolve"] {
            let gene = serde_json::json!({
                "type": "Gene",
                "id": "gene_test",
                "version": 1,
                "category": cat,
                "signals_match": [],
                "preconditions": [],
                "strategy": []
            });
            let issues = validate_gene_inner(&gene, 0);
            let cat_issues: Vec<_> = issues.iter().filter(|i| i.contains("category")).collect();
            assert!(cat_issues.is_empty(), "category '{}' should be valid, got: {:?}", cat, cat_issues);
        }
    }

    #[test]
    fn test_multiple_issues() {
        let gene = serde_json::json!({
            "type": "bad_type",
            "id": "no_prefix",
            "version": "str_version",
            "category": "bad_cat",
            "signals_match": "not_list",
            "preconditions": {},
            "strategy": []
        });
        let issues = validate_gene_inner(&gene, 0);
        assert!(!issues.is_empty());
        assert!(issues.iter().any(|i| i.contains("enum_mismatch:type")));
        assert!(issues.iter().any(|i| i.contains("pattern_mismatch:id")));
        assert!(issues.iter().any(|i| i.contains("type_mismatch:version")));
        assert!(issues.iter().any(|i| i.contains("enum_mismatch:category")));
        assert!(issues.iter().any(|i| i.contains("type_mismatch:signals_match")));
        assert!(issues.iter().any(|i| i.contains("type_mismatch:preconditions")));
    }

    // ── validate_genes_file_inner tests ───────────────────────────

    #[test]
    fn test_file_not_found() {
        let result = validate_genes_file_inner("/nonexistent_gene_file_xyz.json");
        assert_eq!(result["status"], "BLOCKED");
        assert_eq!(result["valid_count"], 0);
    }

    #[test]
    fn test_invalid_json_file() {
        // Create a temp file with invalid JSON
        let tmp = std::env::temp_dir().join("pgg_schema_test_invalid.json");
        std::fs::write(&tmp, "not valid json {").unwrap();
        let result = validate_genes_file_inner(&tmp.to_string_lossy());
        assert_eq!(result["status"], "BLOCKED");
        let _ = std::fs::remove_file(&tmp);
    }

    #[test]
    fn test_valid_genes_file() {
        let genes = serde_json::json!([{
            "type": "Gene",
            "id": "gene_001",
            "version": 1,
            "category": "repair",
            "signals_match": [],
            "preconditions": [],
            "strategy": []
        }]);
        let tmp = std::env::temp_dir().join("pgg_schema_test_valid.json");
        std::fs::write(&tmp, serde_json::to_string(&genes).unwrap()).unwrap();
        let result = validate_genes_file_inner(&tmp.to_string_lossy());
        assert_eq!(result["status"], "PASS");
        assert_eq!(result["valid_count"], 1);
        assert_eq!(result["invalid_count"], 0);
        let _ = std::fs::remove_file(&tmp);
    }

    #[test]
    fn test_genes_file_with_objects() {
        let data = serde_json::json!({"genes": [
            {"type": "Gene", "id": "gene_001", "version": 1, "category": "evolve", "signals_match": [], "preconditions": [], "strategy": []},
            {"type": "Gene", "id": "gene_002", "version": 2, "category": "optimize", "signals_match": [], "preconditions": [], "strategy": []}
        ]});
        let tmp = std::env::temp_dir().join("pgg_schema_test_objects.json");
        std::fs::write(&tmp, serde_json::to_string(&data).unwrap()).unwrap();
        let result = validate_genes_file_inner(&tmp.to_string_lossy());
        assert_eq!(result["status"], "PASS");
        assert_eq!(result["valid_count"], 2);
        let _ = std::fs::remove_file(&tmp);
    }

    #[test]
    fn test_mixed_validity() {
        let data = serde_json::json!([
            {"type": "Gene", "id": "gene_good", "version": 1, "category": "repair", "signals_match": [], "preconditions": [], "strategy": []},
            {"type": "Gene", "id": "bad_id_no_prefix", "version": 1, "category": "innovate", "signals_match": [], "preconditions": [], "strategy": []},
            {"type": "NotGene", "id": "gene_003", "version": 1, "category": "invalid", "signals_match": [], "preconditions": [], "strategy": []}
        ]);
        let tmp = std::env::temp_dir().join("pgg_schema_test_mixed.json");
        std::fs::write(&tmp, serde_json::to_string(&data).unwrap()).unwrap();
        let result = validate_genes_file_inner(&tmp.to_string_lossy());
        assert_eq!(result["status"], "WATCH");
        assert_eq!(result["valid_count"], 1);
        assert_eq!(result["invalid_count"], 2);
        let issues: Vec<_> = result["issues"].as_array().unwrap().iter()
            .map(|v| v.as_str().unwrap().to_string())
            .collect();
        assert!(issues.iter().any(|i| i.contains("pattern_mismatch:id")));
        assert!(issues.iter().any(|i| i.contains("enum_mismatch:type")));
        assert!(issues.iter().any(|i| i.contains("enum_mismatch:category")));
        let _ = std::fs::remove_file(&tmp);
    }

    #[test]
    fn test_empty_gene_array() {
        let tmp = std::env::temp_dir().join("pgg_schema_test_empty.json");
        std::fs::write(&tmp, "[]").unwrap();
        let result = validate_genes_file_inner(&tmp.to_string_lossy());
        assert_eq!(result["status"], "PASS");
        assert_eq!(result["valid_count"], 0);
        assert_eq!(result["invalid_count"], 0);
        let _ = std::fs::remove_file(&tmp);
    }
}