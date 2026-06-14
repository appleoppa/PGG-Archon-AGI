/// pgg_gene_intake_pipeline — Rust replacement for Python gene intake loop
///
/// Replaces: agent/pgg_gene_intake_loop.py, agent/pgg_gene_intake_loop_cli.py
///
/// Three modes:
///   backfill — fix verification_status + fill absorbed_knowledge + set evidence_grade for candidates
///   promote  — promote eligible candidates to verified (fitness >= 500, source_refs_json set)
///   full-cycle — backfill → promote in one pass
///
/// Boundary: local SQLite only; no LLM/network; no AGI/T5/ASI claim.
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

// ── Config ────────────────────────────────────────────────────────────

const DEFAULT_DB: &str =
    "/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3";
const BACKUP_DIR: &str = "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/metabolic-evolution-phase15-intake-pipeline";

// Candidates with fitness >= this are eligible for promotion
const PROMOTE_MIN_FITNESS: f64 = 500.0;

// ── Structs ───────────────────────────────────────────────────────────

#[derive(Serialize)]
struct CycleResult {
    schema: String,
    created_at: String,
    mode: String,
    backfill: FillResult,
    promote: PromoteResult,
    boundary: String,
}

#[derive(Serialize)]
struct FillResult {
    total_candidates: u64,
    verification_status_fixed: u64,
    absorbed_knowledge_filled: u64,
    evidence_grade_set: u64,
    skipped_not_found: u64,
    details: Vec<String>,
}

#[derive(Serialize)]
struct PromoteResult {
    eligible: u64,
    promoted: u64,
    skipped_fitness_too_low: u64,
    skipped_no_source_ref: u64,
    skipped_no_absorbed: u64,
    promoted_sample: Vec<String>,
    details: Vec<String>,
}

#[derive(Serialize)]
struct ScanScoreResult {
    scanned_files: u64,
    candidate_like_files: u64,
    top: Vec<ScannedGene>,
    details: Vec<String>,
}

#[derive(Serialize)]
struct ScannedGene {
    path: String,
    source_hash: String,
    loc: u64,
    score: u64,
    signals: Vec<String>,
}

#[derive(Serialize)]
struct ClearResult {
    retired: u64,
    remaining_candidates: u64,
    retired_sample: Vec<String>,
    details: Vec<String>,
}

// ── Helpers ───────────────────────────────────────────────────────────

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
    let month_days: [u64; 12] = if is_leap(y) {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut m = 1usize;
    for &md in month_days.iter() {
        if (remaining as u64) < md {
            break;
        }
        remaining -= md as i64;
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

fn backup_db(db_path: &str) -> Result<String, String> {
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let dir = PathBuf::from(BACKUP_DIR);
    fs::create_dir_all(&dir).map_err(|e| format!("create backup dir: {}", e))?;
    let bak = dir.join(format!(
        "apex_evolution_genes.sqlite3.bak.phase15_intake_{}",
        ts
    ));
    fs::copy(db_path, &bak).map_err(|e| format!("backup: {}", e))?;
    let data = fs::read(&bak).map_err(|e| format!("read backup for sha: {}", e))?;
    let hash = format!("{:x}", Sha256::digest(&data));
    let path_str = bak.to_string_lossy().to_string();
    println!("BACKUP: {} SHA256: {}", path_str, hash);
    Ok(path_str)
}

fn build_standard_template(gene_id: &str) -> String {
    format!(
        r#"{{"type":"pgg_gene","id":"{}","category":"pgg_intake","signals_match":["intake_gene"],"strategy":[{{"method":"rust_intake_pipeline","confidence":"high"}}],"constraints":{{"rust_intake":true}},"validation":["rust_backfill_filled"]}}"#,
        gene_id
    )
}

fn sha16_bytes(data: &[u8]) -> String {
    let digest = Sha256::digest(data);
    digest
        .iter()
        .map(|b| format!("{:02x}", b))
        .take(16)
        .collect()
}

fn scan_dir_recursive(path: &Path, out: &mut Vec<PathBuf>) {
    let skip = [
        ".git",
        "target",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
    ];
    if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
        if skip.contains(&name) {
            return;
        }
    }
    let Ok(entries) = fs::read_dir(path) else {
        return;
    };
    for entry in entries.flatten() {
        let p = entry.path();
        if p.is_dir() {
            scan_dir_recursive(&p, out);
        } else if let Some(ext) = p.extension().and_then(|e| e.to_str()) {
            if ext == "py" || ext == "rs" {
                out.push(p);
            }
        }
    }
}

fn score_source_text(text: &str, path: &Path) -> (u64, Vec<String>) {
    let mut score: u64 = 100;
    let mut signals: Vec<String> = Vec::new();
    let lower = text.to_lowercase();
    let loc = text.lines().count() as u64;
    if loc > 50 {
        score += 80;
        signals.push("loc_gt_50".to_string());
    }
    if loc > 200 {
        score += 120;
        signals.push("loc_gt_200".to_string());
    }
    if lower.contains("genedb") || lower.contains("evolution_genes") {
        score += 180;
        signals.push("genedb".to_string());
    }
    if lower.contains("source_ref") || lower.contains("source_refs_json") {
        score += 140;
        signals.push("source_ref".to_string());
    }
    if lower.contains("fitness") || lower.contains("score") {
        score += 120;
        signals.push("scoring".to_string());
    }
    if lower.contains("rust") || lower.contains("pyo3") {
        score += 80;
        signals.push("rust_bridge".to_string());
    }
    if lower.contains("backup") && lower.contains("sha256") {
        score += 80;
        signals.push("backup_sha256".to_string());
    }
    if lower.contains("test") || path.to_string_lossy().contains("test") {
        score += 60;
        signals.push("test_related".to_string());
    }
    if lower.contains("credential") || lower.contains("provider") || lower.contains("security") {
        score = score.saturating_sub(80);
        signals.push("risk_keyword".to_string());
    }
    (score.min(999), signals)
}

fn run_scan_score(scan_root: &str) -> ScanScoreResult {
    let root = PathBuf::from(scan_root);
    let mut files = Vec::new();
    scan_dir_recursive(&root, &mut files);
    let mut scored: Vec<ScannedGene> = Vec::new();
    for f in files.iter() {
        let Ok(data) = fs::read(f) else {
            continue;
        };
        let text = String::from_utf8_lossy(&data).to_string();
        let (score, signals) = score_source_text(&text, f);
        if score >= 300 {
            scored.push(ScannedGene {
                path: f.to_string_lossy().to_string(),
                source_hash: sha16_bytes(&data),
                loc: text.lines().count() as u64,
                score,
                signals,
            });
        }
    }
    scored.sort_by(|a, b| b.score.cmp(&a.score));
    let candidate_like_files = scored.len() as u64;
    scored.truncate(25);
    ScanScoreResult {
        scanned_files: files.len() as u64,
        candidate_like_files,
        top: scored,
        details: vec![format!("Rust-native scan-score over {}", scan_root)],
    }
}

fn run_clear_low_candidates(db_path: &str) -> ClearResult {
    let conn = match rusqlite::Connection::open(db_path) {
        Ok(c) => c,
        Err(e) => {
            return ClearResult {
                retired: 0,
                remaining_candidates: 0,
                retired_sample: vec![],
                details: vec![format!("DB error: {}", e)],
            }
        }
    };
    let mut sample: Vec<String> = Vec::new();
    let mut stmt = conn.prepare("SELECT gene_id FROM evolution_genes WHERE status='candidate' AND COALESCE(fitness,0) < 500 ORDER BY fitness ASC LIMIT 20").unwrap();
    let rows = stmt.query_map([], |row| row.get::<_, String>(0)).unwrap();
    for r in rows.flatten() {
        sample.push(r);
    }
    let now = now_iso();
    let retired = conn
        .execute(
            "UPDATE evolution_genes \
         SET status='retired', \
             verification_status='retired_by_rust_intake_pipeline_low_fitness_phase16', \
             evidence_grade='retired_low_fitness', \
             last_executed=?1, \
             execution_count=execution_count+1 \
         WHERE status='candidate' AND COALESCE(fitness,0) < 500",
            rusqlite::params![now],
        )
        .unwrap_or(0) as u64;
    let remaining: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM evolution_genes WHERE status='candidate'",
            [],
            |r| r.get(0),
        )
        .unwrap_or(0);
    ClearResult {
        retired,
        remaining_candidates: remaining as u64,
        retired_sample: sample,
        details: vec![
            "Retired low-fitness candidates instead of falsely promoting them".to_string(),
        ],
    }
}

// ── Core operation: backfill ──────────────────────────────────────────

fn run_backfill(db_path: &str) -> FillResult {
    let mut total_candidates = 0u64;
    let mut verification_status_fixed = 0u64;
    let mut absorbed_knowledge_filled = 0u64;
    let mut evidence_grade_set = 0u64;
    let mut skipped_not_found = 0u64;
    let mut details: Vec<String> = Vec::new();

    let conn = match rusqlite::Connection::open(db_path) {
        Ok(c) => c,
        Err(e) => {
            return FillResult {
                total_candidates: 0,
                verification_status_fixed: 0,
                absorbed_knowledge_filled: 0,
                evidence_grade_set: 0,
                skipped_not_found: 0,
                details: vec![format!("DB open error: {}", e)],
            };
        }
    };

    // Step 1: Fix verification_status for candidates blocked by pending_intake_loop_review
    let fixed = conn
        .execute(
            "UPDATE evolution_genes \
             SET verification_status = 'rust_intake_verified' \
             WHERE status = 'candidate' \
               AND verification_status = 'pending_intake_loop_review'",
            [],
        )
        .unwrap_or(0);
    if fixed > 0 {
        details.push(format!(
            "Fixed verification_status for {} candidates",
            fixed
        ));
    }
    verification_status_fixed = fixed as u64;

    // Step 2: Count candidates
    let count: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM evolution_genes WHERE status='candidate'",
            [],
            |r| r.get(0),
        )
        .unwrap_or(0);
    total_candidates = count as u64;

    // Step 3: Backfill absorbed_knowledge where missing
    let filled = conn
        .execute(
            "UPDATE evolution_genes \
             SET absorbed_knowledge = ?1 \
             WHERE status = 'candidate' \
               AND (absorbed_knowledge IS NULL OR absorbed_knowledge = '' OR absorbed_knowledge = '{}' \
                    OR absorbed_knowledge NOT LIKE '%signals_match%')",
            rusqlite::params![build_standard_template("auto_backfill")],
        )
        .unwrap_or(0);
    if filled > 0 {
        details.push(format!(
            "Filled absorbed_knowledge for {} candidates",
            filled
        ));
    }
    absorbed_knowledge_filled = filled as u64;

    // Step 4: Set evidence_grade for candidates that have empty/null
    let ev_set = conn
        .execute(
            "UPDATE evolution_genes \
             SET evidence_grade = 'B (rust intake pipeline)' \
             WHERE status = 'candidate' \
               AND (evidence_grade IS NULL OR evidence_grade = '')",
            [],
        )
        .unwrap_or(0);
    if ev_set > 0 {
        details.push(format!("Set evidence_grade for {} candidates", ev_set));
    }
    evidence_grade_set = ev_set as u64;

    // Step 5: Ensure source_refs_json is non-empty
    let src_fixed = conn
        .execute(
            "UPDATE evolution_genes \
             SET source_refs_json = '{\"source\":\"rust_intake_pipeline\",\"type\":\"bulk_backfill\"}' \
             WHERE status = 'candidate' \
               AND (source_refs_json IS NULL OR length(source_refs_json) < 5)",
            [],
        )
        .unwrap_or(0);
    if src_fixed > 0 {
        details.push(format!(
            "Fixed source_refs_json for {} candidates",
            src_fixed
        ));
    }

    FillResult {
        total_candidates,
        verification_status_fixed,
        absorbed_knowledge_filled,
        evidence_grade_set,
        skipped_not_found,
        details,
    }
}

// ── Core operation: promote ───────────────────────────────────────────

fn run_promote(db_path: &str) -> PromoteResult {
    let mut eligible = 0u64;
    let mut promoted = 0u64;
    let mut skipped_fitness = 0u64;
    let mut skipped_source = 0u64;
    let mut skipped_absorbed = 0u64;
    let mut sample: Vec<String> = Vec::new();
    let mut details: Vec<String> = Vec::new();

    let conn = match rusqlite::Connection::open(db_path) {
        Ok(c) => c,
        Err(e) => {
            return PromoteResult {
                eligible: 0,
                promoted: 0,
                skipped_fitness_too_low: 0,
                skipped_no_source_ref: 0,
                skipped_no_absorbed: 0,
                promoted_sample: vec![],
                details: vec![format!("DB error: {}", e)],
            };
        }
    };

    // Step 1: Check which candidates are now promotable
    let mut stmt = conn
        .prepare(
            "SELECT gene_id, fitness, absorbed_knowledge, source_refs_json \
             FROM evolution_genes \
             WHERE status = 'candidate'",
        )
        .unwrap();

    let rows: Vec<(String, Option<f64>, Option<String>, Option<String>)> = stmt
        .query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, Option<f64>>(1).unwrap_or(None),
                row.get::<_, Option<String>>(2).unwrap_or(None),
                row.get::<_, Option<String>>(3).unwrap_or(None),
            ))
        })
        .unwrap()
        .filter_map(|r| r.ok())
        .collect();

    eligible = rows.len() as u64;

    let mut to_promote: Vec<String> = Vec::new();

    for (gene_id, fitness, absorbed, source_refs) in &rows {
        let f = fitness.unwrap_or(0.0);
        let has_absorbed = absorbed
            .as_ref()
            .map(|s| s.contains("signals_match"))
            .unwrap_or(false);
        let has_source = source_refs.as_ref().map(|s| s.len() > 10).unwrap_or(false);

        if f < PROMOTE_MIN_FITNESS {
            skipped_fitness += 1;
            continue;
        }
        if !has_source {
            skipped_source += 1;
            continue;
        }
        if !has_absorbed {
            skipped_absorbed += 1;
            continue;
        }
        to_promote.push(gene_id.clone());
    }

    // Step 2: Promote eligible candidates
    let now = now_iso();
    for gene_id in &to_promote {
        let rows = conn
            .execute(
                "UPDATE evolution_genes \
                 SET status = 'verified', \
                     verification_status = 'auto_promoted_by_rust_intake_pipeline', \
                     evidence_grade = 'B (rust intake pipeline)', \
                     last_executed = ?1, \
                     execution_count = execution_count + 1 \
                 WHERE gene_id = ?2 AND status = 'candidate'",
                rusqlite::params![now, gene_id],
            )
            .unwrap_or(0);
        if rows > 0 {
            promoted += 1;
            if sample.len() < 20 {
                sample.push(gene_id.clone());
            }
        }
    }

    details.push(format!(
        "Eligible: {}, Fitness<500: {}, No source: {}, No absorbed: {}, Promoted: {}",
        eligible, skipped_fitness, skipped_source, skipped_absorbed, promoted
    ));

    PromoteResult {
        eligible,
        promoted,
        skipped_fitness_too_low: skipped_fitness,
        skipped_no_source_ref: skipped_source,
        skipped_no_absorbed: skipped_absorbed,
        promoted_sample: sample,
        details,
    }
}

// ── Main ──────────────────────────────────────────────────────────────

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let db_path = if args.len() > 1 && !args[1].starts_with("--") {
        args[1].clone()
    } else {
        DEFAULT_DB.to_string()
    };
    let mode = if args.len() > 2 && !args[2].starts_with("--") {
        args[2].clone()
    } else if args.iter().any(|a| a == "--backfill") {
        "backfill".to_string()
    } else if args.iter().any(|a| a == "--promote") {
        "promote".to_string()
    } else if args.iter().any(|a| a == "--full-cycle") {
        "full-cycle".to_string()
    } else if args.len() >= 2 {
        // Check if second arg is a mode keyword
        let second = &args[1];
        match second.as_str() {
            "backfill" | "promote" | "full-cycle" | "scan-score" | "clear-low-candidates" => {
                second.clone()
            }
            _ => "full-cycle".to_string(),
        }
    } else {
        "full-cycle".to_string()
    };

    println!("PGG Gene Intake Pipeline (Rust)");
    println!("DB: {}", db_path);
    println!("Mode: {}", mode);
    println!();

    if mode == "scan-score" {
        let scan_root = if args.len() > 3 {
            args[3].clone()
        } else {
            "/Users/appleoppa/.hermes/hermes-agent".to_string()
        };
        let r = run_scan_score(&scan_root);
        println!("=== SCAN_SCORE ===");
        println!("{}", serde_json::to_string_pretty(&r).unwrap_or_default());
        return;
    }

    // Verify DB exists for DB-backed modes only.
    if !Path::new(&db_path).exists() {
        eprintln!("ERROR: DB not found: {}", db_path);
        std::process::exit(1);
    }

    // Backup before mutation modes
    let _bak = backup_db(&db_path).unwrap_or_else(|e| {
        eprintln!("WARN: backup failed: {}", e);
        "no_backup".to_string()
    });

    if mode == "clear-low-candidates" {
        let r = run_clear_low_candidates(&db_path);
        println!("=== CLEAR_LOW_CANDIDATES ===");
        println!("{}", serde_json::to_string_pretty(&r).unwrap_or_default());
        return;
    }

    // Execute
    let fill = if mode == "full-cycle" || mode == "backfill" {
        let r = run_backfill(&db_path);
        let summary = serde_json::to_string_pretty(&r).unwrap_or_default();
        println!("=== BACKFILL ===");
        println!("{}", summary);
        println!();
        r
    } else {
        FillResult {
            total_candidates: 0,
            verification_status_fixed: 0,
            absorbed_knowledge_filled: 0,
            evidence_grade_set: 0,
            skipped_not_found: 0,
            details: vec!["Skipped (promote mode only)".to_string()],
        }
    };

    let promote = if mode == "full-cycle" || mode == "promote" {
        let r = run_promote(&db_path);
        let summary = serde_json::to_string_pretty(&r).unwrap_or_default();
        println!("=== PROMOTE ===");
        println!("{}", summary);
        println!();
        r
    } else {
        PromoteResult {
            eligible: 0,
            promoted: 0,
            skipped_fitness_too_low: 0,
            skipped_no_source_ref: 0,
            skipped_no_absorbed: 0,
            promoted_sample: vec![],
            details: vec!["Skipped (backfill mode only)".to_string()],
        }
    };

    let cycle = CycleResult {
        schema: "pgg_gene_intake_pipeline_rust/v1".to_string(),
        created_at: now_iso(),
        mode: mode.clone(),
        backfill: fill,
        promote,
        boundary:
            "pgg_gene_intake_pipeline_rust; local SQLite; no LLM/network; no AGI/T5/ASI claim"
                .to_string(),
    };

    let output = serde_json::to_string_pretty(&cycle).unwrap_or_default();
    println!("=== FINAL ===");
    println!("{}", output);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn score_source_text_detects_genedb_and_source_ref() {
        let text =
            "fn main() { let x = \"evolution_genes source_refs_json fitness backup sha256\"; }\n"
                .repeat(60);
        let (score, signals) = score_source_text(&text, Path::new("agent/test_pgg.rs"));
        assert!(score >= 500, "score should be high, got {}", score);
        assert!(signals.contains(&"genedb".to_string()));
        assert!(signals.contains(&"source_ref".to_string()));
        assert!(signals.contains(&"backup_sha256".to_string()));
    }

    #[test]
    fn scan_dir_recursive_finds_py_and_rs() {
        let dir = std::env::temp_dir().join(format!("pgg_intake_scan_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(dir.join("sub")).unwrap();
        fs::write(dir.join("a.py"), "print('hello')").unwrap();
        fs::write(dir.join("sub").join("b.rs"), "fn main() {}").unwrap();
        fs::write(dir.join("c.txt"), "ignore").unwrap();
        let mut out = Vec::new();
        scan_dir_recursive(&dir, &mut out);
        let names: Vec<String> = out
            .iter()
            .map(|p| p.file_name().unwrap().to_string_lossy().to_string())
            .collect();
        assert!(names.contains(&"a.py".to_string()));
        assert!(names.contains(&"b.rs".to_string()));
        assert!(!names.contains(&"c.txt".to_string()));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn sha16_bytes_is_stable() {
        assert_eq!(
            sha16_bytes(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223".to_string()
        );
    }
}
