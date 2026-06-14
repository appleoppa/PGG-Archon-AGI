/// PGG PicoAPEX Saturation — Rust PyO3 native implementation
///
/// Reads active gene fitness distribution from GeneDB, computes elite
/// saturation ratio, and writes a rotated optimization target to the
/// self-evolution loop state file when the active pool is saturated.
///
/// Boundary: local SQLite + local JSON state only; no LLM/network calls.
/// Replaces pgg_picoapex_saturation.py (230 LOC)
use pyo3::prelude::*;
use pyo3::types::PyModule;
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

// ── Constants ─────────────────────────────────────────────────────

const ENGINE_VERSION: &str = "pgg_picoapex_saturation_rust/v1";
const BOUNDARY: &str = "pgg_picoapex_saturation_rust; local GeneDB read + latest.json target write; no LLM/network";
const SATURATION_THRESHOLD: f64 = 0.30;
const ELITE_FITNESS_THRESHOLD: f64 = 800.0;
const DEFAULT_DB: &str = "/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3";
const DEFAULT_STATE: &str = "/Users/appleoppa/.hermes/data/self-evolution-loop/latest.json";
const DIMENSION_ORDER: [&str; 5] = ["creativity", "reasoning", "planning", "coding", "analysis"];

// ── Data structures ──────────────────────────────────────────────

#[derive(Debug, Clone, Serialize)]
struct EliteDistribution {
    active_count: u64,
    elite_count: u64,
    min_fitness: f64,
    avg_fitness: f64,
    max_fitness: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct PicoAPEXTarget {
    schema: String,
    created_at: String,
    from_dim: String,
    dimension: String,
    reason: String,
    elite_ratio: f64,
    active_count: u64,
    elite_count: u64,
    objective: String,
    rotation_order: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
struct PicoAPEXEntry {
    schema: String,
    updated_at: String,
    current_dim: String,
    previous_dim: String,
    elite_ratio: f64,
    saturated: bool,
    action: String,
}

#[derive(Debug, Clone, Serialize)]
struct CheckResult {
    schema: String,
    created_at: String,
    current_dim: String,
    elite_ratio: f64,
    saturated: bool,
    next_dim: String,
    action: String,
    active_count: u64,
    elite_count: u64,
    thresholds: HashMap<String, f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
    db_path: String,
    state_path: String,
    boundary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StateFile {
    #[serde(skip_serializing_if = "Option::is_none")]
    current_dim: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    target_dimension: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    dimension: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    picoapex: Option<HashMap<String, serde_json::Value>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    picoapex_goal: Option<HashMap<String, serde_json::Value>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    goal: Option<HashMap<String, serde_json::Value>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    target: Option<HashMap<String, serde_json::Value>>,
    // Catch remaining fields
    #[serde(flatten)]
    extra: HashMap<String, serde_json::Value>,
}

// ── Helpers ──────────────────────────────────────────────────────

fn now_iso() -> String {
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = duration.as_secs();
    let days = secs / 86400;
    let time_secs = secs % 86400;
    let hours = time_secs / 3600;
    let mins = (time_secs % 3600) / 60;
    let s = time_secs % 60;

    let mut y = 1970i64;
    let mut remaining = days as i64;
    loop {
        let days_in_year = if is_leap(y) { 366 } else { 365 };
        if remaining < days_in_year {
            break;
        }
        remaining -= days_in_year;
        y += 1;
    }
    let month_days = if is_leap(y) {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut m = 1;
    for &md in month_days.iter() {
        if remaining < md {
            break;
        }
        remaining -= md;
        m += 1;
    }
    let d = remaining + 1;
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}+0000",
        y, m, d, hours, mins, s
    )
}

fn is_leap(y: i64) -> bool {
    (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0)
}

fn safe_float(val: Option<f64>) -> f64 {
    match val {
        Some(v) if !v.is_nan() && !v.is_infinite() => v,
        _ => 0.0,
    }
}

fn current_dimension(state: &StateFile) -> String {
    // Check known state keys
    for candidate in [
        &state.current_dim,
        &state.target_dimension,
        &state.dimension,
    ]
    .iter()
    {
        if let Some(val) = candidate {
            if DIMENSION_ORDER.contains(&val.as_str()) {
                return val.clone();
            }
        }
    }

    // Check nested maps
    let nested_keys = [
        &state.picoapex,
        &state.picoapex_goal,
        &state.goal,
        &state.target,
    ];
    for nested in nested_keys.iter() {
        if let Some(map) = nested {
            for field in ["current_dim", "dimension", "target_dimension"].iter() {
                if let Some(serde_json::Value::String(val)) = map.get(*field) {
                    if DIMENSION_ORDER.contains(&val.as_str()) {
                        return val.clone();
                    }
                }
            }
        }
    }

    // Also check extra fields
    for field in ["current_dim", "dimension", "target_dimension"].iter() {
        if let Some(serde_json::Value::String(val)) = state.extra.get(*field) {
            if DIMENSION_ORDER.contains(&val.as_str()) {
                return val.clone();
            }
        }
    }
    for field in ["picoapex", "picoapex_goal", "goal", "target"] {
        if let Some(serde_json::Value::Object(map)) = state.extra.get(field) {
            for sub in ["current_dim", "dimension", "target_dimension"].iter() {
                if let Some(serde_json::Value::String(val)) = map.get(*sub) {
                    if DIMENSION_ORDER.contains(&val.as_str()) {
                        return val.clone();
                    }
                }
            }
        }
    }

    DIMENSION_ORDER[0].to_string()
}

fn next_dimension(current: &str) -> String {
    let idx = DIMENSION_ORDER
        .iter()
        .position(|&d| d == current)
        .unwrap_or(0);
    DIMENSION_ORDER[(idx + 1) % DIMENSION_ORDER.len()].to_string()
}

// ── SQLite: active fitness distribution ──────────────────────────

fn active_fitness_distribution(db_path: &str) -> Result<EliteDistribution, String> {
    let path = PathBuf::from(db_path);
    if !path.exists() {
        return Err(format!("GeneDB not found: {}", db_path));
    }

    let conn = Connection::open(db_path)
        .map_err(|e| format!("SQLite open: {}", e))?;

    let mut stmt = conn
        .prepare(
            "SELECT \
               COUNT(*) AS active_count, \
               SUM(CASE WHEN COALESCE(fitness, 0) > ?1 THEN 1 ELSE 0 END) AS elite_count, \
               MIN(fitness) AS min_fitness, \
               AVG(fitness) AS avg_fitness, \
               MAX(fitness) AS max_fitness \
             FROM evolution_genes \
             WHERE status = 'active'",
        )
        .map_err(|e| format!("SQL prepare: {}", e))?;

    let row = stmt
        .query_row([ELITE_FITNESS_THRESHOLD], |row| {
            let active_count: u64 = row.get(0).unwrap_or(0);
            let elite_count: u64 = row.get(1).unwrap_or(0);
            let min_fitness: Option<f64> = row.get(2).ok();
            let avg_fitness: Option<f64> = row.get(3).ok();
            let max_fitness: Option<f64> = row.get(4).ok();
            Ok(EliteDistribution {
                active_count,
                elite_count,
                min_fitness: safe_float(min_fitness),
                avg_fitness: safe_float(avg_fitness),
                max_fitness: safe_float(max_fitness),
            })
        })
        .map_err(|e| format!("SQL query: {}", e))?;

    Ok(row)
}

// ── State file read ──────────────────────────────────────────────

fn read_state(state_path: &str) -> StateFile {
    let path = PathBuf::from(state_path);
    if !path.exists() {
        return StateFile {
            current_dim: None,
            target_dimension: None,
            dimension: None,
            picoapex: None,
            picoapex_goal: None,
            goal: None,
            target: None,
            extra: HashMap::new(),
        };
    }

    match std::fs::read_to_string(state_path) {
        Ok(content) => serde_json::from_str(&content).unwrap_or(StateFile {
            current_dim: None,
            target_dimension: None,
            dimension: None,
            picoapex: None,
            picoapex_goal: None,
            goal: None,
            target: None,
            extra: HashMap::new(),
        }),
        Err(_) => StateFile {
            current_dim: None,
            target_dimension: None,
            dimension: None,
            picoapex: None,
            picoapex_goal: None,
            goal: None,
            target: None,
            extra: HashMap::new(),
        },
    }
}

// ── State file write ─────────────────────────────────────────────

fn write_new_target(
    state: &mut StateFile,
    state_path: &str,
    current_dim: &str,
    next_dim: &str,
    elite_ratio: f64,
    active_count: u64,
    elite_count: u64,
) -> Result<(), String> {
    let target = PicoAPEXTarget {
        schema: format!("{}/target", ENGINE_VERSION),
        created_at: now_iso(),
        from_dim: current_dim.to_string(),
        dimension: next_dim.to_string(),
        reason: "active_gene_elite_ratio_saturated".to_string(),
        elite_ratio: (elite_ratio * 1_000_000.0).round() / 1_000_000.0,
        active_count,
        elite_count,
        objective: format!(
            "PicoAPEX saturated on {}; rotate optimization target to {}.",
            current_dim, next_dim
        ),
        rotation_order: DIMENSION_ORDER.iter().map(|&s| s.to_string()).collect(),
    };

    let entry = PicoAPEXEntry {
        schema: ENGINE_VERSION.to_string(),
        updated_at: now_iso(),
        current_dim: next_dim.to_string(),
        previous_dim: current_dim.to_string(),
        elite_ratio: (elite_ratio * 1_000_000.0).round() / 1_000_000.0,
        saturated: true,
        action: format!("switched_target_to_{}", next_dim),
    };

    // Serialize to Value for merging
    let target_json = serde_json::to_value(&target).unwrap_or_default();
    let entry_json = serde_json::to_value(&entry).unwrap_or_default();
    let state_value = serde_json::to_value(&state).unwrap_or(serde_json::Value::Object(Default::default()));

    let mut merged = if let serde_json::Value::Object(map) = state_value {
        map
    } else {
        serde_json::Map::new()
    };

    merged.insert("picoapex_goal".to_string(), target_json);

    if let serde_json::Value::Object(entry_map) = entry_json {
        merged.insert("picoapex".to_string(), serde_json::Value::Object(entry_map));
    }

    // Write atomically via temp file
    let path = PathBuf::from(state_path);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("mkdir state dir: {}", e))?;
    }

    let tmp_path = path.with_extension("json.tmp");
    let content = serde_json::to_string_pretty(&serde_json::Value::Object(merged))
        .map_err(|e| format!("serialize: {}", e))?;
    std::fs::write(&tmp_path, &content)
        .map_err(|e| format!("write tmp: {}", e))?;
    std::fs::rename(&tmp_path, &path)
        .map_err(|e| format!("rename tmp: {}", e))?;

    Ok(())
}

// ── Main check logic ─────────────────────────────────────────────

fn check_and_switch(
    db_path: &str,
    state_path: &str,
    saturation_threshold: f64,
    elite_fitness_threshold: f64,
) -> CheckResult {
    let mut state = read_state(state_path);
    let current = current_dimension(&state);
    let next = next_dimension(&current);

    match active_fitness_distribution(db_path) {
        Ok(dist) => {
            // elite_ratio = elite_count ÷ active_count
            let elite_ratio = if dist.active_count > 0 {
                dist.elite_count as f64 / dist.active_count as f64
            } else {
                0.0
            };
            
            let saturated = elite_ratio > saturation_threshold;

            let action = if saturated {
                match write_new_target(
                    &mut state,
                    state_path,
                    &current,
                    &next,
                    elite_ratio,
                    dist.active_count,
                    dist.elite_count,
                ) {
                    Ok(()) => format!("switched_target_to_{}", next),
                    Err(e) => format!("write_failed: {}", e),
                }
            } else {
                "noop_not_saturated".to_string()
            };

            let mut thresholds = HashMap::new();
            thresholds.insert("saturation".to_string(), saturation_threshold);
            thresholds.insert("elite_fitness".to_string(), elite_fitness_threshold);

            CheckResult {
                schema: ENGINE_VERSION.to_string(),
                created_at: now_iso(),
                current_dim: current,
                elite_ratio: (elite_ratio * 1_000_000.0).round() / 1_000_000.0,
                saturated,
                next_dim: next,
                action,
                active_count: dist.active_count,
                elite_count: dist.elite_count,
                thresholds,
                error: None,
                db_path: db_path.to_string(),
                state_path: state_path.to_string(),
                boundary: BOUNDARY.to_string(),
            }
        }
        Err(e) => CheckResult {
            schema: ENGINE_VERSION.to_string(),
            created_at: now_iso(),
            current_dim: current,
            elite_ratio: 0.0,
            saturated: false,
            next_dim: next,
            action: "error_no_switch".to_string(),
            active_count: 0,
            elite_count: 0,
            thresholds: {
                let mut t = HashMap::new();
                t.insert("saturation".to_string(), saturation_threshold);
                t.insert("elite_fitness".to_string(), elite_fitness_threshold);
                t
            },
            error: Some(e),
            db_path: db_path.to_string(),
            state_path: state_path.to_string(),
            boundary: BOUNDARY.to_string(),
        },
    }
}

// ── PyO3 exports ─────────────────────────────────────────────────

#[pyfunction]
fn native_check_and_switch(
    db_path: Option<String>,
    state_path: Option<String>,
    saturation_threshold: Option<f64>,
    elite_fitness_threshold: Option<f64>,
) -> PyResult<String> {
    let result = check_and_switch(
        &db_path.unwrap_or_else(|| DEFAULT_DB.to_string()),
        &state_path.unwrap_or_else(|| DEFAULT_STATE.to_string()),
        saturation_threshold.unwrap_or(SATURATION_THRESHOLD),
        elite_fitness_threshold.unwrap_or(ELITE_FITNESS_THRESHOLD),
    );
    serde_json::to_string_pretty(&result)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialize: {}", e)))
}

#[pyfunction]
fn native_info() -> PyResult<String> {
    Ok(format!(
        r#"{{"engine": "{}", "boundary": "{}", "default_db": "{}", "default_state": "{}"}}"#,
        ENGINE_VERSION, BOUNDARY, DEFAULT_DB, DEFAULT_STATE
    ))
}

// ── Python module ────────────────────────────────────────────────

#[pymodule]
fn hermes_pgg_picoapex_saturation(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_check_and_switch, m)?)?;
    m.add_function(wrap_pyfunction!(native_info, m)?)?;
    Ok(())
}

// ── Tests (pure Rust only — no PyO3 symbols) ─────────────────────

#[cfg(test)]
mod tests {
    use super::{
        active_fitness_distribution, check_and_switch, current_dimension,
        next_dimension, now_iso, read_state, safe_float, BOUNDARY, DIMENSION_ORDER,
        ENGINE_VERSION, SATURATION_THRESHOLD, ELITE_FITNESS_THRESHOLD,
        DEFAULT_DB, DEFAULT_STATE, StateFile,
    };
    use std::collections::HashMap;

    #[test]
    fn test_now_iso_format() {
        let ts = now_iso();
        assert!(ts.len() >= 20, "ISO string too short: {}", ts);
        assert!(ts.contains('T'), "Missing T separator: {}", ts);
    }

    #[test]
    fn test_safe_float_normal() {
        assert!((safe_float(Some(42.5)) - 42.5).abs() < 1e-10);
    }

    #[test]
    fn test_safe_float_nan() {
        assert!((safe_float(Some(f64::NAN)) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_safe_float_inf() {
        assert!((safe_float(Some(f64::INFINITY)) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_safe_float_none() {
        assert!((safe_float(None) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_dimension_order_completeness() {
        assert_eq!(DIMENSION_ORDER.len(), 5);
    }

    #[test]
    fn test_dimension_rotation_forward() {
        assert_eq!(next_dimension("creativity"), "reasoning");
        assert_eq!(next_dimension("reasoning"), "planning");
        assert_eq!(next_dimension("planning"), "coding");
        assert_eq!(next_dimension("coding"), "analysis");
    }

    #[test]
    fn test_dimension_rotation_wraps() {
        assert_eq!(next_dimension("analysis"), "creativity");
    }

    #[test]
    fn test_dimension_rotation_unknown_defaults() {
        assert_eq!(next_dimension("unknown"), "reasoning"); // index 0 -> 1
    }

    #[test]
    fn test_current_dimension_default_when_empty() {
        let state = StateFile {
            current_dim: None,
            target_dimension: None,
            dimension: None,
            picoapex: None,
            picoapex_goal: None,
            goal: None,
            target: None,
            extra: HashMap::new(),
        };
        assert_eq!(current_dimension(&state), "creativity");
    }

    #[test]
    fn test_current_dimension_from_current_dim() {
        let mut extra = HashMap::new();
        extra.insert("current_dim".to_string(), serde_json::Value::String("coding".to_string()));
        let state = StateFile {
            current_dim: None,
            target_dimension: None,
            dimension: None,
            picoapex: None,
            picoapex_goal: None,
            goal: None,
            target: None,
            extra,
        };
        assert_eq!(current_dimension(&state), "coding");
    }

    #[test]
    fn test_current_dimension_from_target_dimension() {
        let state = StateFile {
            current_dim: None,
            target_dimension: Some("analysis".to_string()),
            dimension: None,
            picoapex: None,
            picoapex_goal: None,
            goal: None,
            target: None,
            extra: HashMap::new(),
        };
        assert_eq!(current_dimension(&state), "analysis");
    }

    #[test]
    fn test_current_dimension_from_dimension() {
        let state = StateFile {
            current_dim: None,
            target_dimension: None,
            dimension: Some("planning".to_string()),
            picoapex: None,
            picoapex_goal: None,
            goal: None,
            target: None,
            extra: HashMap::new(),
        };
        assert_eq!(current_dimension(&state), "planning");
    }

    #[test]
    fn test_current_dimension_from_nested_picoapex() {
        let mut picoapex = HashMap::new();
        picoapex.insert("current_dim".to_string(), serde_json::Value::String("reasoning".to_string()));
        let state = StateFile {
            current_dim: None,
            target_dimension: None,
            dimension: None,
            picoapex: Some(picoapex),
            picoapex_goal: None,
            goal: None,
            target: None,
            extra: HashMap::new(),
        };
        assert_eq!(current_dimension(&state), "reasoning");
    }

    #[test]
    fn test_current_dimension_from_extra_picoapex() {
        let mut picoapex = serde_json::Map::new();
        picoapex.insert("current_dim".to_string(), serde_json::Value::String("analysis".to_string()));
        let mut extra = HashMap::new();
        extra.insert("picoapex".to_string(), serde_json::Value::Object(picoapex));
        let state = StateFile {
            current_dim: None,
            target_dimension: None,
            dimension: None,
            picoapex: None,
            picoapex_goal: None,
            goal: None,
            target: None,
            extra,
        };
        assert_eq!(current_dimension(&state), "analysis");
    }

    #[test]
    fn test_read_state_absent_file() {
        let state = read_state("/tmp/nonexistent_picoapex_state_12345.json");
        assert_eq!(current_dimension(&state), "creativity");
    }

    #[test]
    fn test_active_fitness_distribution_nonexistent_db() {
        let result = active_fitness_distribution("/tmp/nonexistent_db_12345.sqlite3");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("not found"));
    }

    #[test]
    fn test_check_and_switch_nonexistent_db_default_dim() {
        let result = check_and_switch(
            "/tmp/nonexistent_db_12345.sqlite3",
            "/tmp/nonexistent_state_12345.json",
            SATURATION_THRESHOLD,
            ELITE_FITNESS_THRESHOLD,
        );
        assert_eq!(result.schema, ENGINE_VERSION);
        assert_eq!(result.boundary, BOUNDARY);
        assert_eq!(result.current_dim, "creativity");
        assert_eq!(result.action, "error_no_switch");
        assert!(result.error.is_some());
        assert!(result.error.as_ref().unwrap().contains("not found"));
    }

    #[test]
    fn test_check_and_switch_returns_json_shape() {
        let result = check_and_switch(
            "/tmp/missing_db_6789.sqlite3",
            "/tmp/missing_state_6789.json",
            0.30,
            800.0,
        );
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("creativity"));
        assert!(json.contains("error_no_switch"));
        assert!(json.contains(ENGINE_VERSION));
    }

    #[test]
    fn test_thresholds_in_result() {
        let result = check_and_switch(
            "/tmp/aaa.sqlite3",
            "/tmp/aaa.json",
            0.30,
            800.0,
        );
        assert_eq!(result.thresholds.get("saturation"), Some(&0.30));
        assert_eq!(result.thresholds.get("elite_fitness"), Some(&800.0));
    }

    #[test]
    fn test_next_dim_after_current_matches_rotation() {
        let result = check_and_switch(
            "/tmp/bbb.sqlite3",
            "/tmp/bbb.json",
            0.30,
            800.0,
        );
        assert_eq!(result.next_dim, "reasoning");
    }

    #[test]
    fn test_real_gene_db_reads() {
        let result = check_and_switch(
            DEFAULT_DB,
            "/tmp/test_real_db_read.json",
            SATURATION_THRESHOLD,
            ELITE_FITNESS_THRESHOLD,
        );
        // Real GeneDB should exist
        if result.active_count > 0 {
            assert!(result.action == "noop_not_saturated" || result.action.starts_with("switched_target_to_"));
            assert!(result.elite_ratio >= 0.0 && result.elite_ratio <= 1.0);
        } else {
            // If empty, should still be a valid noop
            assert!(result.action == "noop_not_saturated" || result.action == "error_no_switch");
        }
    }

    #[test]
    fn test_constants_are_defined() {
        assert!(!ENGINE_VERSION.is_empty());
        assert!(!BOUNDARY.is_empty());
        assert!(SATURATION_THRESHOLD > 0.0);
        assert!(ELITE_FITNESS_THRESHOLD > 0.0);
        assert!(!DEFAULT_DB.is_empty());
        assert!(!DEFAULT_STATE.is_empty());
    }
}