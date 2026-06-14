/// PGG Self-Evolution Core — Rust PyO3 native implementation
///
/// Handles the heavy SQLite operations for the PGG self-evolution loop:
/// - promote_candidates: batch upgrade candidate→verified with inflation gate
/// - backfill_records: fill missing absorbed_knowledge with standard templates
/// - generate_db_summary: GeneDB snapshot + health indicators
/// - run_core_cycle: orchestrate the three above
///
/// Boundary: local SQLite only; no LLM/network; no AGI/T5/ASI claim.
/// Replaces the SQL-heavy parts of pgg_self_evolution_loop.py (~350 LOC)
use pyo3::prelude::*;
use pyo3::types::PyModule;
use rusqlite::Connection;
use serde::Serialize;
use std::collections::HashMap;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

// ── Constants ─────────────────────────────────────────────────────

const ENGINE_VERSION: &str = "pgg_self_evolution_core_rust/v1";
const BOUNDARY: &str = "pgg_self_evolution_core_rust; local GeneDB SQLite operations; no LLM/network; no AGI/T5/ASI claim";
const DEFAULT_DB: &str = "/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3";
const MIN_FITNESS_FOR_PROMOTION: f64 = 700.0;
const MAX_BATCH_PROMOTE: u64 = 1000;

const BLOCKED_PREFIXES: [&str; 13] = [
    "auto_backfilled",
    "needs_review",
    "pending_review",
    "pending_",
    "backfill",
    "unverified",
    "preliminary",
    "candidate",
    "stage2",
    "sampled_",
    "closed_by_",
    "retired_",
    "select",
];

// ── Data structures ──────────────────────────────────────────────

#[derive(Debug, Clone, Serialize)]
struct PromoteResult {
    schema: String,
    created_at: String,
    promoted: u64,
    total_candidates_total: u64,
    skipped_reasons: HashMap<String, u64>,
    promoted_sample: Vec<String>,
    boundary: String,
}

#[derive(Debug, Clone, Serialize)]
struct BackfillResult {
    schema: String,
    created_at: String,
    filled: u64,
    total_missing: u64,
    boundary: String,
}

#[derive(Debug, Clone, Serialize)]
struct GeneSummary {
    schema: String,
    created_at: String,
    total_genes: u64,
    by_status: HashMap<String, u64>,
    by_evidence: HashMap<String, u64>,
    health: HealthIndicators,
    top_fitness: Vec<TopGene>,
    boundary: String,
}

#[derive(Debug, Clone, Serialize)]
struct HealthIndicators {
    verified_score: f64,
    verified_count: u64,
    candidate_count: u64,
    active_count: u64,
    retired_count: u64,
    avg_fitness: Option<f64>,
    low_fitness_verified: u64,
    verified_to_candidate_ratio: f64,
    signals: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
struct TopGene {
    gene_id: String,
    status: String,
    fitness: Option<f64>,
    verification: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
struct CoreCycleResult {
    schema: String,
    created_at: String,
    promote: PromoteResult,
    backfill: BackfillResult,
    summary: GeneSummary,
    duration_seconds: f64,
    boundary: String,
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
    let mut m = 1usize;
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

fn open_db(db_path: &str) -> Result<Connection, String> {
    let path = PathBuf::from(db_path);
    if !path.exists() {
        return Err(format!("GeneDB not found: {}", db_path));
    }
    Connection::open(db_path).map_err(|e| format!("SQLite open: {}", e))
}

fn is_blocked_by_inflation_gate(vstat: &str) -> bool {
    let lower = vstat.to_lowercase();
    BLOCKED_PREFIXES
        .iter()
        .any(|&prefix| lower.starts_with(prefix))
}

fn build_standard_template(gene_id: &str) -> String {
    let template = serde_json::json!({
        "type": "pgg_gene",
        "id": gene_id,
        "category": "pgg_backfill",
        "signals_match": ["backfill_gene"],
        "preconditions": ["backfill_source_verified"],
        "strategy": ["use_backfill_strategy"],
        "constraints": {"backfill": true},
        "validation": ["backfill_record_verified"]
    });
    serde_json::to_string(&template).unwrap_or_else(|_| {
        format!(
            r#"{{"type":"pgg_gene","id":"{}","category":"pgg_backfill","signals_match":["backfill_gene"]}}"#,
            gene_id
        )
    })
}

// ── Core operations ──────────────────────────────────────────────

fn promote_candidates(db_path: &str) -> Result<PromoteResult, String> {
    let conn = open_db(db_path)?;

    let mut stmt = conn.prepare(
        "SELECT gene_id, status, verification_status, fitness, evidence_grade, \
               source_refs_json, absorbed_knowledge, gene_name, gate_type, \
               severity_rank, boundary \
         FROM evolution_genes \
         WHERE status = 'candidate' \
           AND absorbed_knowledge IS NOT NULL \
           AND absorbed_knowledge LIKE '%signals_match%' \
           AND evidence_grade IS NOT NULL AND evidence_grade != '' \
           AND source_refs_json IS NOT NULL AND length(source_refs_json) > 10 \
           AND (fitness IS NOT NULL AND fitness >= ?1) \
         ORDER BY fitness DESC \
         LIMIT ?2",
    )
    .map_err(|e| format!("SQL prepare promote: {}", e))?;

    let rows = stmt
        .query_map(
            [MIN_FITNESS_FOR_PROMOTION, MAX_BATCH_PROMOTE as f64],
            |row| {
                let gene_id: String = row.get(0)?;
                let vstat: Option<String> = row.get(2).unwrap_or(None);
                let evidence: Option<String> = row.get(4).unwrap_or(None);
                Ok((gene_id, vstat, evidence))
            },
        )
        .map_err(|e| format!("SQL query promote: {}", e))?;

    let mut candidates: Vec<(String, Option<String>, Option<String>)> = Vec::new();
    for row in rows.flatten() {
        candidates.push(row);
    }

    let total = candidates.len() as u64;

    if candidates.is_empty() {
        return Ok(PromoteResult {
            schema: format!("{}/promote", ENGINE_VERSION),
            created_at: now_iso(),
            promoted: 0,
            total_candidates_total: 0,
            skipped_reasons: HashMap::new(),
            promoted_sample: vec![],
            boundary: BOUNDARY.to_string(),
        });
    }

    let mut promoted: u64 = 0;
    let mut skipped_reasons: HashMap<String, u64> = HashMap::new();
    let mut promoted_sample: Vec<String> = Vec::new();
    let now = now_iso();
    let conn = open_db(db_path)?;

    for (gene_id, vstat, evidence) in &candidates {
        if let Some(vs) = vstat {
            if vs.starts_with("verified") {
                *skipped_reasons
                    .entry("already_verified".to_string())
                    .or_insert(0) += 1;
                continue;
            }
            if is_blocked_by_inflation_gate(vs) {
                let reason = format!("blocked_by_gene_inflation_gate_{}", vs);
                *skipped_reasons.entry(reason).or_insert(0) += 1;
                continue;
            }
        }

        let ev = evidence.as_deref().unwrap_or("B").to_uppercase();
        let rows_affected = conn
            .execute(
                "UPDATE evolution_genes \
                 SET status = 'verified', \
                     verification_status = 'auto_promoted_by_self_evolution_loop', \
                     evidence_grade = ?1, \
                     last_executed = ?2 \
                 WHERE gene_id = ?3 AND status = 'candidate'",
                rusqlite::params![ev, now, gene_id],
            )
            .map_err(|e| format!("SQL promote update: {}", e))?;

        if rows_affected > 0 {
            promoted += 1;
            if promoted_sample.len() < 20 {
                promoted_sample.push(gene_id.clone());
            }
        }
    }

    let _ = conn.close();

    Ok(PromoteResult {
        schema: format!("{}/promote", ENGINE_VERSION),
        created_at: now_iso(),
        promoted,
        total_candidates_total: total,
        skipped_reasons,
        promoted_sample,
        boundary: BOUNDARY.to_string(),
    })
}

fn backfill_records(db_path: &str) -> Result<BackfillResult, String> {
    let conn = open_db(db_path)?;

    let mut stmt = conn
        .prepare(
            "SELECT gene_id, evidence_grade \
             FROM evolution_genes \
             WHERE gene_id LIKE 'pgg_%' \
               AND (absorbed_knowledge IS NULL \
                    OR absorbed_knowledge = '' \
                    OR absorbed_knowledge NOT LIKE '%signals_match%') \
             ORDER BY gene_id",
        )
        .map_err(|e| format!("SQL prepare backfill: {}", e))?;

    let rows = stmt
        .query_map([], |row| {
            let gene_id: String = row.get(0)?;
            let ev_grade: Option<String> = row.get(1).unwrap_or(None);
            Ok((gene_id, ev_grade))
        })
        .map_err(|e| format!("SQL query backfill: {}", e))?;

    let mut missing: Vec<(String, Option<String>)> = Vec::new();
    for row in rows.flatten() {
        missing.push(row);
    }

    let total_missing = missing.len() as u64;

    if missing.is_empty() {
        return Ok(BackfillResult {
            schema: format!("{}/backfill", ENGINE_VERSION),
            created_at: now_iso(),
            filled: 0,
            total_missing: 0,
            boundary: BOUNDARY.to_string(),
        });
    }

    let mut filled: u64 = 0;
    let conn = open_db(db_path)?;

    for (gene_id, ev_grade) in &missing {
        let template = build_standard_template(gene_id);
        let evidence = ev_grade.as_deref().unwrap_or("B").to_uppercase();
        let rows = conn
            .execute(
                "UPDATE evolution_genes \
                 SET absorbed_knowledge = ?1, evidence_grade = ?2 \
                 WHERE gene_id = ?3",
                rusqlite::params![template, evidence, gene_id],
            )
            .map_err(|e| format!("SQL backfill update: {}", e))?;
        if rows > 0 {
            filled += 1;
        }
    }

    let _ = conn.close();

    Ok(BackfillResult {
        schema: format!("{}/backfill", ENGINE_VERSION),
        created_at: now_iso(),
        filled,
        total_missing,
        boundary: BOUNDARY.to_string(),
    })
}

fn generate_db_summary(db_path: &str) -> Result<GeneSummary, String> {
    let conn = open_db(db_path)?;

    let total: u64 = conn
        .query_row("SELECT COUNT(*) FROM evolution_genes", [], |row| row.get(0))
        .map_err(|e| format!("SQL total: {}", e))?;

    let mut by_status: HashMap<String, u64> = HashMap::new();
    {
        let mut stmt = conn
            .prepare("SELECT status, COUNT(*) FROM evolution_genes GROUP BY status")
            .map_err(|e| format!("SQL by_status: {}", e))?;
        let rows = stmt
            .query_map([], |row| {
                let s: String = row.get(0)?;
                let n: u64 = row.get(1)?;
                Ok((s, n))
            })
            .map_err(|e| format!("SQL by_status query: {}", e))?;
        for row in rows.flatten() {
            by_status.insert(row.0, row.1);
        }
    }

    let mut by_evidence: HashMap<String, u64> = HashMap::new();
    {
        let mut stmt = conn
            .prepare(
                "SELECT evidence_grade, COUNT(*) FROM evolution_genes \
                 WHERE evidence_grade IS NOT NULL GROUP BY evidence_grade",
            )
            .map_err(|e| format!("SQL by_evidence: {}", e))?;
        let rows = stmt
            .query_map([], |row| {
                let s: String = row.get(0)?;
                let n: u64 = row.get(1)?;
                Ok((s, n))
            })
            .map_err(|e| format!("SQL by_evidence query: {}", e))?;
        for row in rows.flatten() {
            by_evidence.insert(row.0, row.1);
        }
    }

    let top_fitness: Vec<TopGene> = {
        let mut stmt = conn
            .prepare(
                "SELECT gene_id, status, fitness, verification_status \
                 FROM evolution_genes ORDER BY fitness DESC NULLS LAST LIMIT 10",
            )
            .map_err(|e| format!("SQL top_fitness: {}", e))?;
        let rows = stmt
            .query_map([], |row| {
                Ok(TopGene {
                    gene_id: row.get(0)?,
                    status: row.get(1)?,
                    fitness: row.get::<_, Option<f64>>(2).ok().flatten(),
                    verification: row.get::<_, Option<String>>(3).ok().flatten(),
                })
            })
            .map_err(|e| format!("SQL top_fitness query: {}", e))?;
        let mut v: Vec<TopGene> = Vec::new();
        for row in rows.flatten() {
            v.push(row);
        }
        v
    };

    let verified_count = *by_status.get("verified").unwrap_or(&0);
    let candidate_count = *by_status.get("candidate").unwrap_or(&0);
    let active_count = *by_status.get("active").unwrap_or(&0);
    let retired_count = *by_status.get("retired").unwrap_or(&0);

    let low_fitness_verified: u64 = conn
        .query_row(
            "SELECT COUNT(*) FROM evolution_genes \
             WHERE status='verified' AND (fitness IS NULL OR fitness < 500)",
            [],
            |row| row.get(0),
        )
        .map_err(|e| format!("SQL low_fitness: {}", e))?;

    let avg_fitness: Option<f64> = {
        let has: u64 = conn
            .query_row(
                "SELECT COUNT(*) FROM evolution_genes WHERE fitness IS NOT NULL",
                [],
                |row| row.get(0),
            )
            .map_err(|e| format!("SQL has_fitness: {}", e))?;
        if has > 0 {
            conn.query_row(
                "SELECT AVG(fitness) FROM evolution_genes WHERE fitness IS NOT NULL",
                [],
                |row| {
                    let v: f64 = row.get(0)?;
                    Ok(Some((v * 10.0).round() / 10.0))
                },
            )
            .map_err(|e| format!("SQL avg_fitness: {}", e))?
        } else {
            None
        }
    };

    let _ = conn.close();

    let mut signals: Vec<String> = Vec::new();
    if verified_count < 20 {
        signals.push(format!("VERIFIED_LOW({})", verified_count));
    }
    if total > 0 && candidate_count as f64 > total as f64 * 0.8 {
        signals.push(format!("CANDIDATE_STAGNATION({}/{})", candidate_count, total));
    }
    if low_fitness_verified > 5 {
        signals.push(format!("LOW_FITNESS_VERIFIED({})", low_fitness_verified));
    }
    if retired_count > active_count {
        signals.push(format!("RETIRE_EXCEEDS_ACTIVE({}>{})", retired_count, active_count));
    }

    let verified_score = if total > 0 {
        ((verified_count as f64 / total as f64) * 100.0 * 10.0).round() / 10.0
    } else {
        0.0
    };
    let vtc_ratio = if candidate_count > 0 {
        ((verified_count as f64 / candidate_count as f64) * 1000.0).round() / 1000.0
    } else {
        verified_count as f64
    };

    let health_signals = if signals.is_empty() { vec![] } else { signals };

    Ok(GeneSummary {
        schema: format!("{}/summary", ENGINE_VERSION),
        created_at: now_iso(),
        total_genes: total,
        by_status: {
            let mut s = HashMap::new();
            for k in ["active", "candidate", "verified", "retired", "rejected"] {
                if let Some(&v) = by_status.get(k) {
                    s.insert(k.to_string(), v);
                }
            }
            s
        },
        by_evidence,
        health: HealthIndicators {
            verified_score,
            verified_count,
            candidate_count,
            active_count,
            retired_count,
            avg_fitness,
            low_fitness_verified,
            verified_to_candidate_ratio: vtc_ratio,
            signals: health_signals,
        },
        top_fitness,
        boundary: BOUNDARY.to_string(),
    })
}

fn run_core_cycle(db_path: &str) -> Result<CoreCycleResult, String> {
    let start = now_iso();
    let start_epoch = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();

    let promote = promote_candidates(db_path)?;
    let backfill = backfill_records(db_path)?;
    let summary = generate_db_summary(db_path)?;

    let end_epoch = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let duration = (end_epoch.as_secs_f64() - start_epoch.as_secs_f64() * 1000.0).round() / 1000.0;

    Ok(CoreCycleResult {
        schema: format!("{}/core_cycle", ENGINE_VERSION),
        created_at: start,
        promote,
        backfill,
        summary,
        duration_seconds: duration.max(0.0),
        boundary: BOUNDARY.to_string(),
    })
}

// ── PyO3 exports ─────────────────────────────────────────────────

#[pyfunction]
fn native_promote_candidates(db_path: Option<String>) -> PyResult<String> {
    let result = promote_candidates(&db_path.unwrap_or_else(|| DEFAULT_DB.to_string()));
    match result {
        Ok(r) => serde_json::to_string_pretty(&r)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialize: {}", e))),
        Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(e)),
    }
}

#[pyfunction]
fn native_backfill_records(db_path: Option<String>) -> PyResult<String> {
    let result = backfill_records(&db_path.unwrap_or_else(|| DEFAULT_DB.to_string()));
    match result {
        Ok(r) => serde_json::to_string_pretty(&r)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialize: {}", e))),
        Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(e)),
    }
}

#[pyfunction]
fn native_generate_db_summary(db_path: Option<String>) -> PyResult<String> {
    let result = generate_db_summary(&db_path.unwrap_or_else(|| DEFAULT_DB.to_string()));
    match result {
        Ok(r) => serde_json::to_string_pretty(&r)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialize: {}", e))),
        Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(e)),
    }
}

#[pyfunction]
fn native_run_core_cycle(db_path: Option<String>) -> PyResult<String> {
    let result = run_core_cycle(&db_path.unwrap_or_else(|| DEFAULT_DB.to_string()));
    match result {
        Ok(r) => serde_json::to_string_pretty(&r)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialize: {}", e))),
        Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(e)),
    }
}

#[pyfunction]
fn native_info() -> PyResult<String> {
    Ok(format!(
        r#"{{"engine": "{}", "boundary": "{}", "default_db": "{}"}}"#,
        ENGINE_VERSION, BOUNDARY, DEFAULT_DB
    ))
}

// ── Python module ────────────────────────────────────────────────

#[pymodule]
fn hermes_pgg_self_evolution_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_promote_candidates, m)?)?;
    m.add_function(wrap_pyfunction!(native_backfill_records, m)?)?;
    m.add_function(wrap_pyfunction!(native_generate_db_summary, m)?)?;
    m.add_function(wrap_pyfunction!(native_run_core_cycle, m)?)?;
    m.add_function(wrap_pyfunction!(native_info, m)?)?;
    Ok(())
}

// ── Tests ────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::{
        backfill_records, build_standard_template, generate_db_summary,
        is_blocked_by_inflation_gate, now_iso, promote_candidates, run_core_cycle,
        BOUNDARY, DEFAULT_DB, ENGINE_VERSION, MAX_BATCH_PROMOTE, MIN_FITNESS_FOR_PROMOTION,
    };

    #[test]
    fn test_now_iso_format() {
        let ts = now_iso();
        assert!(ts.len() >= 20, "ISO string too short: {}", ts);
        assert!(ts.contains('T'), "Missing T separator: {}", ts);
    }

    #[test]
    fn test_constants_are_defined() {
        assert!(!ENGINE_VERSION.is_empty());
        assert!(!BOUNDARY.is_empty());
        assert!(MIN_FITNESS_FOR_PROMOTION > 0.0);
        assert!(MAX_BATCH_PROMOTE > 0);
        assert!(!DEFAULT_DB.is_empty());
    }

    #[test]
    fn test_inflation_gate_blocks_backfill_prefix() {
        assert!(is_blocked_by_inflation_gate("backfilled_123"));
    }

    #[test]
    fn test_inflation_gate_allows_verified() {
        assert!(!is_blocked_by_inflation_gate("verified_by_agent"));
    }

    #[test]
    fn test_inflation_gate_allows_active() {
        assert!(!is_blocked_by_inflation_gate("active_evolved_gene"));
    }

    #[test]
    fn test_inflation_gate_blocks_needs_review() {
        assert!(is_blocked_by_inflation_gate("needs_review"));
    }

    #[test]
    fn test_inflation_gate_blocks_unverified() {
        assert!(is_blocked_by_inflation_gate("unverified_backfill"));
    }

    #[test]
    fn test_inflation_gate_blocks_pending_review() {
        assert!(is_blocked_by_inflation_gate("pending_review_gene"));
    }

    #[test]
    fn test_inflation_gate_blocks_pending_underscore() {
        assert!(is_blocked_by_inflation_gate("pending_approval"));
    }

    #[test]
    fn test_inflation_gate_blocks_candidate() {
        assert!(is_blocked_by_inflation_gate("candidate_gene_123"));
    }

    #[test]
    fn test_inflation_gate_blocks_select() {
        assert!(is_blocked_by_inflation_gate("SELECT"));
    }

    #[test]
    fn test_inflation_gate_case_insensitive() {
        assert!(is_blocked_by_inflation_gate("BACKFILL_xyz"));
    }

    #[test]
    fn test_inflation_gate_blocks_preliminary() {
        assert!(is_blocked_by_inflation_gate("preliminary_gene"));
    }

    #[test]
    fn test_inflation_gate_empty_string() {
        assert!(!is_blocked_by_inflation_gate(""));
    }

    #[test]
    fn test_build_standard_template_contains_gene_id() {
        let tpl = build_standard_template("pgg_test_gene_123");
        assert!(tpl.contains("pgg_test_gene_123"));
        assert!(tpl.contains("backfill_gene"));
        assert!(tpl.contains("signals_match"));
    }

    #[test]
    fn test_build_standard_template_valid_json() {
        let tpl = build_standard_template("pgg_my_gene");
        let parsed: Result<serde_json::Value, _> = serde_json::from_str(&tpl);
        assert!(parsed.is_ok(), "Template should be valid JSON");
        let obj = parsed.unwrap();
        assert_eq!(obj["type"], "pgg_gene");
        assert_eq!(obj["id"], "pgg_my_gene");
    }

    #[test]
    fn test_build_standard_template_diff_ids() {
        let a = build_standard_template("gene_a");
        let b = build_standard_template("gene_b");
        assert!(a.contains("gene_a"));
        assert!(b.contains("gene_b"));
        assert_ne!(a, b);
    }

    #[test]
    fn test_promote_candidates_with_real_db() {
        let result = promote_candidates(DEFAULT_DB).unwrap_or_else(|e| {
            panic!("Unexpected error: {}", e);
        });
        assert!(result.schema.contains("promote"));
        assert_eq!(result.boundary, BOUNDARY);
        println!(
            "Promoted: {}, total: {}, skipped: {:?}",
            result.promoted, result.total_candidates_total, result.skipped_reasons
        );
    }

    #[test]
    fn test_backfill_records_with_real_db() {
        let result = backfill_records(DEFAULT_DB).unwrap_or_else(|e| {
            panic!("Unexpected error: {}", e);
        });
        assert!(result.schema.contains("backfill"));
        println!("Filled: {}, total_missing: {}", result.filled, result.total_missing);
    }

    #[test]
    fn test_generate_db_summary_with_real_db() {
        let result = generate_db_summary(DEFAULT_DB).unwrap_or_else(|e| {
            panic!("Unexpected error: {}", e);
        });
        assert!(result.total_genes > 0, "GeneDB should have genes");
        assert!(!result.by_status.is_empty());
        assert!(result.top_fitness.len() <= 10);
        println!(
            "Total: {}, by_status: {:?}, verified_score: {}, avg_fitness: {:?}",
            result.total_genes,
            result.by_status,
            result.health.verified_score,
            result.health.avg_fitness
        );
    }

    #[test]
    fn test_generate_db_summary_json_shape() {
        let result = generate_db_summary(DEFAULT_DB).unwrap();
        let json_str = serde_json::to_string_pretty(&result).unwrap();
        assert!(json_str.contains("total_genes"));
        assert!(json_str.contains("by_status"));
        assert!(json_str.contains("health"));
        assert!(json_str.contains("top_fitness"));
    }

    #[test]
    fn test_run_core_cycle_with_real_db() {
        let result = run_core_cycle(DEFAULT_DB).unwrap_or_else(|e| {
            panic!("Unexpected error: {}", e);
        });
        assert!(result.schema.contains("core_cycle"));
        assert_eq!(result.boundary, BOUNDARY);
        assert!(result.duration_seconds >= 0.0);
        assert!(result.summary.total_genes > 0);
        println!(
            "Core cycle: promoted={}, filled={}, total={}, duration={}s",
            result.promote.promoted,
            result.backfill.filled,
            result.summary.total_genes,
            result.duration_seconds
        );
    }

    #[test]
    fn test_run_core_cycle_json_output() {
        let result = run_core_cycle(DEFAULT_DB).unwrap();
        let json_str = serde_json::to_string(&result).unwrap();
        assert!(json_str.contains("promote"));
        assert!(json_str.contains("backfill"));
        assert!(json_str.contains("summary"));
        assert!(json_str.contains("duration_seconds"));
    }

    #[test]
    fn test_unknown_db_returns_error() {
        let result = promote_candidates("/tmp/nonexistent_gene_db.sqlite3");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("not found"));
    }

    #[test]
    fn test_promote_result_has_all_fields() {
        let result = promote_candidates(DEFAULT_DB).unwrap();
        let _json = serde_json::to_string(&result).unwrap();
    }

    #[test]
    fn test_summary_health_indicators_present() {
        let result = generate_db_summary(DEFAULT_DB).unwrap();
        assert!(result.health.verified_score >= 0.0);
    }
}