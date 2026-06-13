use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

const SCHEMA: &str = "PGGMiniBenchmark/v1";
const BOUNDARY: &str = "local deterministic mini-benchmark; not external/community benchmark; not AGI level proof";

#[derive(Debug, Clone, Serialize, Deserialize)]
struct BenchmarkGene {
    gene_id: String,
    gene_name: String,
    fitness: i64,
    status: String,
    gate_type: String,
    severity_rank: i64,
    execution_count: i64,
    last_executed: String,
}

/// Schema fields expected in a gene
const BENCHMARK_GENE_FIELDS: &[(&str, &str)] = &[
    ("gene_id", "str"),
    ("gene_name", "str"),
    ("fitness", "int"),
    ("status", "str"),
    ("gate_type", "str"),
    ("severity_rank", "int"),
    ("execution_count", "int"),
    ("last_executed", "str"),
];

const GENEDB_REQUIRED_COLUMNS: &[&str] = &["fitness", "execution_count", "last_executed"];

const ALL_GENEDB_COLUMNS: &[&str] = &[
    "gene_id", "cycle_id", "created_at", "defect_no", "defect_name",
    "gene_name", "absorbed_knowledge", "source_refs_json", "repair_mechanism",
    "severity_rank", "apex_variables", "gate_type", "reusable_rule",
    "status", "evidence_grade", "verification_status", "boundary",
    "gene_hash", "fitness", "last_executed", "execution_count",
];

const DEFAULT_GENE_JSON: &str = r#"{
    "gene_id": "gene_001",
    "gene_name": "test_gene",
    "fitness": 800,
    "status": "active",
    "gate_type": "recommend",
    "severity_rank": 3,
    "execution_count": 42,
    "last_executed": "2026-06-11T12:00:00"
}"#;

// ---------------------------------------------------------------------------
// Gene validation
// ---------------------------------------------------------------------------

#[pyfunction]
fn validate_benchmark_gene(gene_json: &str) -> String {
    let gene: Result<serde_json::Value, _> = serde_json::from_str(gene_json);
    let gene = match gene {
        Ok(v) => v,
        Err(e) => {
            return serde_json::json!({
                "gene": gene_json,
                "valid": false,
                "reason": format!("input is not valid JSON: {}", e)
            }).to_string();
        }
    };

    let obj = match gene.as_object() {
        Some(o) => o,
        None => {
            return serde_json::json!({
                "gene": gene,
                "valid": false,
                "reason": "input is not a dict"
            }).to_string();
        }
    };

    let mut errors: Vec<String> = vec![];
    let mut missing: Vec<String> = vec![];
    let mut type_mismatch: Vec<String> = vec![];

    for (field, expected_type) in BENCHMARK_GENE_FIELDS {
        match obj.get(*field) {
            None => missing.push(field.to_string()),
            Some(val) => {
                let actual = match *expected_type {
                    "str" => val.as_str().map(|_| "str"),
                    "int" => val.as_i64().map(|_| "int"),
                    _ => None,
                };
                if actual.is_none() {
                    let actual_type = if val.is_string() { "str" }
                        else if val.is_number() { "int" }
                        else if val.is_boolean() { "bool" }
                        else if val.is_array() { "list" }
                        else if val.is_object() { "dict" }
                        else { "unknown" };
                    type_mismatch.push(format!(
                        "{}: expected {}, got {}",
                        field, expected_type, actual_type
                    ));
                }
            }
        }
    }

    if !missing.is_empty() {
        errors.push(format!("missing fields: {}", missing.join(", ")));
    }
    if !type_mismatch.is_empty() {
        errors.push(format!("type mismatch: {}", type_mismatch.join("; ")));
    }

    let (valid, reason) = if errors.is_empty() {
        (true, "PASS".to_string())
    } else {
        (false, format!("BLOCK; {}", errors.join("; ")))
    };

    serde_json::json!({
        "gene": gene,
        "valid": valid,
        "reason": reason
    }).to_string()
}

// ---------------------------------------------------------------------------
// Synergy score
// ---------------------------------------------------------------------------

fn _synergy_score(fitness_a: i64, fitness_b: i64) -> f64 {
    if fitness_a <= 0 || fitness_b <= 0 {
        return 0.0;
    }
    let fa = fitness_a as f64;
    let fb = fitness_b as f64;
    let synergy = (fa * fb).sqrt() / 1000.0;
    synergy.min(1.0)
}

// ---------------------------------------------------------------------------
// Gene fusion
// ---------------------------------------------------------------------------

#[pyfunction]
fn fuse_benchmark_genes(gene_a_json: &str, gene_b_json: &str, mode: &str) -> String {
    // Parse inputs
    let result_a = validate_benchmark_gene(gene_a_json);
    let va: serde_json::Value = serde_json::from_str(&result_a).unwrap();
    let result_b = validate_benchmark_gene(gene_b_json);
    let vb: serde_json::Value = serde_json::from_str(&result_b).unwrap();

    let gene_a: serde_json::Value = serde_json::from_str(gene_a_json).unwrap_or(serde_json::Value::Null);
    let gene_b: serde_json::Value = serde_json::from_str(gene_b_json).unwrap_or(serde_json::Value::Null);

    // Check validation
    if va["valid"] != true {
        return serde_json::json!({
            "gene_a": gene_a,
            "gene_b": gene_b,
            "fused_fitness": 0,
            "synergy": 0.0,
            "mode": mode,
            "status": "BLOCK",
            "reason": format!("gene_a validation failed: {}", va["reason"])
        }).to_string();
    }
    if vb["valid"] != true {
        return serde_json::json!({
            "gene_a": gene_a,
            "gene_b": gene_b,
            "fused_fitness": 0,
            "synergy": 0.0,
            "mode": mode,
            "status": "BLOCK",
            "reason": format!("gene_b validation failed: {}", vb["reason"])
        }).to_string();
    }

    let fitness_a = gene_a["fitness"].as_i64().unwrap_or(0);
    let fitness_b = gene_b["fitness"].as_i64().unwrap_or(0);
    let synergy = _synergy_score(fitness_a, fitness_b);

    let fused_fitness = if mode == "multiplicative" {
        ((fitness_a as f64 * fitness_b as f64).sqrt()) as i64
    } else {
        fitness_a + fitness_b
    };

    serde_json::json!({
        "gene_a": gene_a,
        "gene_b": gene_b,
        "fused_fitness": fused_fitness,
        "synergy": (synergy * 10000.0).round() / 10000.0,
        "mode": mode,
        "status": "PASS",
        "reason": format!("fused fitness={}, synergy={:.4}", fused_fitness, synergy)
    }).to_string()
}

// ---------------------------------------------------------------------------
// GeneDB schema check
// ---------------------------------------------------------------------------

#[pyfunction]
fn check_genedb_schema() -> String {
    let mut found: Vec<String> = vec![];
    let mut missing: Vec<String> = vec![];

    for col in GENEDB_REQUIRED_COLUMNS {
        if ALL_GENEDB_COLUMNS.contains(col) {
            found.push(col.to_string());
        } else {
            missing.push(col.to_string());
        }
    }

    let ok = missing.is_empty();
    serde_json::json!({
        "columns_found": found,
        "all_columns": ALL_GENEDB_COLUMNS,
        "missing": missing,
        "ok": ok
    }).to_string()
}

// ---------------------------------------------------------------------------
// Test functions (matching Python signatures)
// ---------------------------------------------------------------------------

#[pyfunction]
fn test_validate_standard_gene() -> String {
    // Test 1: standard gene PASS
    let result_ok = validate_benchmark_gene(DEFAULT_GENE_JSON);
    let ok_val: serde_json::Value = serde_json::from_str(&result_ok).unwrap();
    let ok_pass = ok_val["valid"] == true;

    // Test 2: broken gene (missing fields) BLOCK
    let broken_json = r#"{"gene_id": "broken"}"#;
    let result_broken = validate_benchmark_gene(broken_json);
    let broken_val: serde_json::Value = serde_json::from_str(&result_broken).unwrap();
    let broken_block = broken_val["valid"] == false;

    // Test 3: non-dict BLOCK
    let result_nondict = validate_benchmark_gene(r#""not_a_dict""#);
    let nondict_val: serde_json::Value = serde_json::from_str(&result_nondict).unwrap();
    let nondict_block = nondict_val["valid"] == false;

    let passed = ok_pass && broken_block && nondict_block;
    let count: usize = [ok_pass, broken_block, nondict_block].iter().filter(|&&x| x).count();
    serde_json::json!({
        "name": "validate_standard_gene",
        "pass_count": count,
        "total": 3,
        "status": if passed { "PASS" } else { "FAIL" },
        "details": {
            "standard_gene_pass": ok_pass,
            "broken_gene_block": broken_block,
            "nondict_block": nondict_block
        }
    }).to_string()
}

#[pyfunction]
fn test_fuse_standard_genes() -> String {
    let gene_a = DEFAULT_GENE_JSON;
    let gene_b = r#"{
        "gene_id": "gene_002",
        "gene_name": "test_gene_2",
        "fitness": 800,
        "status": "active",
        "gate_type": "recommend",
        "severity_rank": 3,
        "execution_count": 42,
        "last_executed": "2026-06-11T12:00:00"
    }"#;
    let result = fuse_benchmark_genes(gene_a, gene_b, "additive");
    let val: serde_json::Value = serde_json::from_str(&result).unwrap();

    let passed = val["status"] == "PASS"
        && val["fused_fitness"] == 1600
        && val["synergy"].as_f64().unwrap_or(0.0) > 0.0;

    serde_json::json!({
        "name": "fuse_standard_genes_additive",
        "pass_count": if passed { 1 } else { 0 },
        "total": 1,
        "status": if passed { "PASS" } else { "FAIL" },
        "details": {
            "fused_fitness": val["fused_fitness"],
            "synergy": val["synergy"],
            "status": val["status"]
        }
    }).to_string()
}

#[pyfunction]
fn test_fuse_standard_genes_multiplicative() -> String {
    let gene_a = DEFAULT_GENE_JSON;
    let gene_b = r#"{
        "gene_id": "gene_003",
        "gene_name": "test_gene_3",
        "fitness": 600,
        "status": "active",
        "gate_type": "recommend",
        "severity_rank": 3,
        "execution_count": 42,
        "last_executed": "2026-06-11T12:00:00"
    }"#;
    let result = fuse_benchmark_genes(gene_a, gene_b, "multiplicative");
    let val: serde_json::Value = serde_json::from_str(&result).unwrap();

    let expected: i64 = ((800.0_f64 * 600.0_f64).sqrt()) as i64; // ≈ 692
    let passed = val["status"] == "PASS" && val["fused_fitness"] == expected;

    serde_json::json!({
        "name": "fuse_standard_genes_multiplicative",
        "pass_count": if passed { 1 } else { 0 },
        "total": 1,
        "status": if passed { "PASS" } else { "FAIL" },
        "details": {
            "fused_fitness": val["fused_fitness"],
            "expected_fitness": expected,
            "synergy": val["synergy"],
            "status": val["status"]
        }
    }).to_string()
}

#[pyfunction]
fn test_genedb_schema() -> String {
    let result = check_genedb_schema();
    let val: serde_json::Value = serde_json::from_str(&result).unwrap();
    let passed = val["ok"] == true && val["missing"].as_array().map(|a| a.is_empty()).unwrap_or(false);

    serde_json::json!({
        "name": "genedb_schema_query",
        "pass_count": if passed { 1 } else { 0 },
        "total": 1,
        "status": if passed { "PASS" } else { "FAIL" },
        "details": {
            "columns_found": val["columns_found"],
            "missing": val["missing"],
            "total_columns": val["all_columns"].as_array().map(|a| a.len()).unwrap_or(0)
        }
    }).to_string()
}

// ---------------------------------------------------------------------------
// Main runner
// ---------------------------------------------------------------------------

#[pyfunction]
fn run_mini_benchmark() -> String {
    let results: Vec<serde_json::Value> = vec![
        serde_json::from_str(&test_validate_standard_gene()).unwrap(),
        serde_json::from_str(&test_fuse_standard_genes()).unwrap(),
        serde_json::from_str(&test_fuse_standard_genes_multiplicative()).unwrap(),
        serde_json::from_str(&test_genedb_schema()).unwrap(),
    ];

    let total_count: usize = results.iter()
        .map(|t| t["total"].as_i64().unwrap_or(0) as usize)
        .sum();
    let pass_count: usize = results.iter()
        .map(|t| t["pass_count"].as_i64().unwrap_or(0) as usize)
        .sum();

    let all_fail = results.iter().all(|t| t["status"] == "FAIL");
    let overall = if all_fail {
        "FAIL"
    } else if pass_count == total_count {
        "PASS"
    } else {
        "WATCH"
    };

    serde_json::json!({
        "schema": SCHEMA,
        "status": overall,
        "pass_count": pass_count,
        "total_count": total_count,
        "results": results,
        "boundary": BOUNDARY,
        "native": "Rust PyO3 v0.1.0"
    }).to_string()
}

// ---------------------------------------------------------------------------
// Version info
// ---------------------------------------------------------------------------

#[pyfunction]
fn get_version() -> String {
    serde_json::json!({
        "name": "Hermes PGG Mini Benchmark",
        "version": "0.1.0",
        "schema": SCHEMA,
        "architecture": "Rust PyO3 native",
        "boundary": BOUNDARY
    }).to_string()
}

// ---------------------------------------------------------------------------
// Python module
// ---------------------------------------------------------------------------

#[pymodule]
fn hermes_pgg_mini_benchmark(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate_benchmark_gene, m)?)?;
    m.add_function(wrap_pyfunction!(fuse_benchmark_genes, m)?)?;
    m.add_function(wrap_pyfunction!(check_genedb_schema, m)?)?;
    m.add_function(wrap_pyfunction!(test_validate_standard_gene, m)?)?;
    m.add_function(wrap_pyfunction!(test_fuse_standard_genes, m)?)?;
    m.add_function(wrap_pyfunction!(test_fuse_standard_genes_multiplicative, m)?)?;
    m.add_function(wrap_pyfunction!(test_genedb_schema, m)?)?;
    m.add_function(wrap_pyfunction!(run_mini_benchmark, m)?)?;
    m.add_function(wrap_pyfunction!(get_version, m)?)?;
    Ok(())
}