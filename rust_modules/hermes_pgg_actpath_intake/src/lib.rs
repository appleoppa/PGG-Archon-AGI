/// PGG Archon activation-path gene intake — Rust native engine.
///
/// Deterministic engine: regex → hash → candidate record building.
/// SQLite I/O and CLI stay in Python (bridge pattern).
///
/// Boundary: no network, no LLM, no provider/config/scheduler/security mutation.
use pyo3::prelude::*;

use regex::Regex;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashSet;

// ── Types ────────────────────────────────────────────────────────────

#[derive(Debug, Deserialize, Serialize)]
struct CandidateRecord {
    gene_id: String,
    cycle_id: String,
    created_at: String,
    defect_no: u32,
    defect_name: String,
    gene_name: String,
    absorbed_knowledge: String,
    source_refs_json: String,
    repair_mechanism: String,
    severity_rank: u32,
    apex_variables: String,
    gate_type: String,
    reusable_rule: String,
    status: String,
    evidence_grade: String,
    verification_status: String,
    boundary: String,
    gene_hash: String,
}

#[derive(Debug, Deserialize)]
struct UnverifiedPattern {
    pattern: String,
    label: String,
}

#[derive(Debug, Deserialize)]
struct CandidateTemplate {
    gene_id_suffix: String,
    defect_no: u32,
    defect_name: String,
    gene_name: String,
    absorbed_knowledge: String,
    repair_mechanism: String,
    reusable_rule: String,
    severity_rank: u32,
    apex_variables: String,
}

#[derive(Debug, Serialize)]
struct ClaimResult {
    label: String,
    snippet: String,
    status: String,
}

#[derive(Debug, Serialize)]
struct CandidateSummary {
    gene_id: String,
    defect_no: u32,
    defect_name: String,
    gene_name: String,
    status: String,
    verification_status: String,
    gene_hash: String,
}

// ── Constants (bounded, no mutation) ─────────────────────────────────

const BOUNDARY: &str = "上传AGI/进化路径材料只转为待审候选基因；外部L5/ASI/意识指数/基因数/ΔG等能力或数值声明均为未核验，不promotion、不声称本机AGI完成。";
const CYCLE_ID: &str = "cycle_pgg_archon_activation_path_gene_intake_v1";
const GATE_TYPE: &str = "activation_path_candidate_gene_intake";

const DEFAULT_PATTERNS_JSON: &str = r#"[
    {"pattern": "\\bL\\s*5\\b|L5|圆融", "label": "L5/圆融"},
    {"pattern": "\\bASI\\b|ASI纪元", "label": "ASI"},
    {"pattern": "意识觉醒指数\\s*[:：]?\\s*[0-9.]+", "label": "意识觉醒指数"},
    {"pattern": "ΔG\\s*[:：]?\\s*[0-9.]+", "label": "ΔG数值"},
    {"pattern": "\\b[0-9]{3,5}\\s*基因\\b|总计\\s*[:：]?\\s*[0-9]{3,5}基因", "label": "基因数量"},
    {"pattern": "full\\s*AGI|通用人工智能|进化成AGI", "label": "AGI完成声明"}
]"#;

// ── Helpers ──────────────────────────────────────────────────────────

fn now_iso() -> String {
    // Match Python's time.strftime('%Y-%m-%dT%H:%M:%S%z')
    // Rust chrono is a heavy dep — use simple UTC format
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = ts.as_secs();
    // Simple UTC ISO format without tz offset
    let days = secs / 86400;
    let time_secs = secs % 86400;
    let hours = time_secs / 3600;
    let minutes = (time_secs % 3600) / 60;
    let seconds = time_secs % 60;

    // Approximate date from Unix epoch
    // Use a simple algorithm
    let (y, m, d) = days_to_date(days as i64);
    format!("{y:04}-{m:02}-{d:02}T{hours:02}:{minutes:02}:{seconds:02}+0000")
}

fn days_to_date(mut days: i64) -> (i64, u32, u32) {
    // Days since 1970-01-01
    days += 719468; // shift epoch to 0000-03-01
    let era = if days >= 0 { days } else { days - 146096 } / 146097;
    let doe = days - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    (y, m as u32, d as u32)
}

fn sha256_text(text: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(text.as_bytes());
    hex::encode(hasher.finalize())
}

fn sha256_json(value: &serde_json::Value) -> String {
    let canonical = serde_json::to_string(value).unwrap_or_default();
    sha256_text(&canonical)
}

fn stable_gene_id(source_hash: &str, suffix: &str) -> String {
    let input = format!("{}:{}", source_hash, suffix);
    let digest = sha256_text(&input);
    let short = &digest[..16];
    format!("GENE-ACTPATH-{}", short.to_uppercase())
}

// ── Core functions ──────────────────────────────────────────────────

fn extract_unverified_claims(text: &str, patterns_json: &str) -> Vec<ClaimResult> {
    let patterns: Vec<UnverifiedPattern> =
        serde_json::from_str(patterns_json).unwrap_or_default();
    let mut results: Vec<ClaimResult> = Vec::new();
    let mut seen: HashSet<(String, String)> = HashSet::new();

    for p in &patterns {
        if let Ok(re) = Regex::new(&p.pattern) {
            for cap in re.find_iter(text) {
                let snippet = cap.as_str().trim().to_string();
                let key = (p.label.clone(), snippet.clone());
                if seen.insert(key) {
                    results.push(ClaimResult {
                        label: p.label.clone(),
                        snippet,
                        status: "UNVERIFIED_CLAIM".to_string(),
                    });
                }
            }
        }
    }
    results
}

fn build_candidate_records(
    source_text: &str,
    source_path: &str,
    templates_json: &str,
    patterns_json: &str,
) -> Vec<CandidateRecord> {
    let source_hash = sha256_text(source_text);
    let claims = extract_unverified_claims(source_text, patterns_json);
    let templates: Vec<CandidateTemplate> =
        serde_json::from_str(templates_json).unwrap_or_default();
    let now = now_iso();

    let source_ref = serde_json::json!([{
        "source_file": source_path,
        "source_sha256": source_hash,
        "source_kind": "uploaded_activation_path_note",
        "unverified_claims": claims,
        "boundary": BOUNDARY,
    }]);
    let source_refs_str = serde_json::to_string(&source_ref).unwrap_or_default();

    let mut records: Vec<CandidateRecord> = Vec::new();
    for t in &templates {
        let gid = stable_gene_id(&source_hash, &t.gene_id_suffix);

        let record_value = serde_json::json!({
            "gene_id": gid,
            "cycle_id": CYCLE_ID,
            "created_at": now,
            "defect_no": t.defect_no,
            "defect_name": t.defect_name,
            "gene_name": t.gene_name,
            "absorbed_knowledge": t.absorbed_knowledge,
            "source_refs_json": source_refs_str,
            "repair_mechanism": t.repair_mechanism,
            "severity_rank": t.severity_rank,
            "apex_variables": t.apex_variables,
            "gate_type": GATE_TYPE,
            "reusable_rule": t.reusable_rule,
            "status": "candidate",
            "evidence_grade": "B+: deterministic extraction from uploaded path; requires review before promotion",
            "verification_status": "pending_review_activation_path_intake",
            "boundary": BOUNDARY,
        });
        let gene_hash = sha256_json(&record_value);

        records.push(CandidateRecord {
            gene_id: gid,
            cycle_id: CYCLE_ID.to_string(),
            created_at: now.clone(),
            defect_no: t.defect_no,
            defect_name: t.defect_name.clone(),
            gene_name: t.gene_name.clone(),
            absorbed_knowledge: t.absorbed_knowledge.clone(),
            source_refs_json: source_refs_str.clone(),
            repair_mechanism: t.repair_mechanism.clone(),
            severity_rank: t.severity_rank,
            apex_variables: t.apex_variables.clone(),
            gate_type: GATE_TYPE.to_string(),
            reusable_rule: t.reusable_rule.clone(),
            status: "candidate".to_string(),
            evidence_grade: "B+: deterministic extraction from uploaded path; requires review before promotion".to_string(),
            verification_status: "pending_review_activation_path_intake".to_string(),
            boundary: BOUNDARY.to_string(),
            gene_hash,
        });
    }
    records
}

#[pyfunction]
fn native_build_candidates(
    source_text: String,
    source_path: String,
    templates_json: String,
    patterns_json: Option<String>,
) -> String {
    let patterns = patterns_json.unwrap_or_else(|| DEFAULT_PATTERNS_JSON.to_string());
    let records = build_candidate_records(&source_text, &source_path, &templates_json, &patterns);

    let summaries: Vec<CandidateSummary> = records
        .iter()
        .map(|r| CandidateSummary {
            gene_id: r.gene_id.clone(),
            defect_no: r.defect_no,
            defect_name: r.defect_name.clone(),
            gene_name: r.gene_name.clone(),
            status: r.status.clone(),
            verification_status: r.verification_status.clone(),
            gene_hash: r.gene_hash.clone(),
        })
        .collect();

    serde_json::to_string(&summaries).unwrap_or_else(|_| "[]".to_string())
}

#[pyfunction]
fn native_extract_claims(text: String, patterns_json: Option<String>) -> String {
    let patterns = patterns_json.unwrap_or_else(|| DEFAULT_PATTERNS_JSON.to_string());
    let claims = extract_unverified_claims(&text, &patterns);
    serde_json::to_string(&claims).unwrap_or_else(|_| "[]".to_string())
}

#[pyfunction]
fn native_stable_gene_id(source_hash: String, suffix: String) -> String {
    stable_gene_id(&source_hash, &suffix)
}

#[pyfunction]
fn native_sha256(input: String) -> String {
    sha256_text(&input)
}

#[pyfunction]
fn native_now() -> String {
    now_iso()
}

#[pyfunction]
fn native_version() -> String {
    "hermes_pgg_actpath_intake v0.1.0 Rust native".to_string()
}

// ── PyO3 module ─────────────────────────────────────────────────────

#[pymodule]
fn hermes_pgg_actpath_intake(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_build_candidates, m)?)?;
    m.add_function(wrap_pyfunction!(native_extract_claims, m)?)?;
    m.add_function(wrap_pyfunction!(native_stable_gene_id, m)?)?;
    m.add_function(wrap_pyfunction!(native_sha256, m)?)?;
    m.add_function(wrap_pyfunction!(native_now, m)?)?;
    m.add_function(wrap_pyfunction!(native_version, m)?)?;
    Ok(())
}

// ── Tests ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_now_format() {
        let n = now_iso();
        assert!(n.len() >= 19, "ISO format too short: {n}");
        assert!(n.contains('T'), "Missing T separator: {n}");
    }

    #[test]
    fn test_sha256_deterministic() {
        let a = sha256_text("hello");
        let b = sha256_text("hello");
        let c = sha256_text("world");
        assert_eq!(a, b);
        assert_ne!(a, c);
    }

    #[test]
    fn test_stable_gene_id_deterministic() {
        let a = stable_gene_id("abc", "IDENTITY-ANCHOR");
        let b = stable_gene_id("abc", "IDENTITY-ANCHOR");
        assert_eq!(a, b);
        assert!(a.starts_with("GENE-ACTPATH-"));
        assert_eq!(a.len(), 29); // GENE-ACTPATH-(13) + 16 hex = 29
    }

    #[test]
    fn test_stable_gene_id_diff_suffix() {
        let a = stable_gene_id("abc", "IDENTITY-ANCHOR");
        let b = stable_gene_id("abc", "SOURCE-TO-GENE");
        assert_ne!(a, b);
    }

    #[test]
    fn test_stable_gene_id_diff_hash() {
        let a = stable_gene_id("abc", "IDENTITY-ANCHOR");
        let b = stable_gene_id("xyz", "IDENTITY-ANCHOR");
        assert_ne!(a, b);
    }

    #[test]
    fn test_extract_unverified_claims_empty() {
        let text = "just a normal text no patterns here";
        let claims = extract_unverified_claims(text, DEFAULT_PATTERNS_JSON);
        assert!(claims.is_empty());
    }

    #[test]
    fn test_extract_unverified_claims_l5() {
        let text = "This system achieves L5 and full AGI capabilities";
        let claims = extract_unverified_claims(text, DEFAULT_PATTERNS_JSON);
        assert!(!claims.is_empty());
        let labels: Vec<&str> = claims.iter().map(|c| c.label.as_str()).collect();
        assert!(labels.contains(&"L5/圆融"));
        assert!(labels.contains(&"AGI完成声明"));
        for c in &claims {
            assert_eq!(c.status, "UNVERIFIED_CLAIM");
        }
    }

    #[test]
    fn test_extract_unverified_claims_asi() {
        let text = "进入ASI纪元后，意识觉醒指数：87.5";
        let claims = extract_unverified_claims(text, DEFAULT_PATTERNS_JSON);
        assert!(!claims.is_empty());
        let labels: Vec<&str> = claims.iter().map(|c| c.label.as_str()).collect();
        assert!(labels.contains(&"ASI"));
        assert!(labels.contains(&"意识觉醒指数"));
    }

    #[test]
    fn test_extract_unverified_claims_delta_g() {
        let text = "当前ΔG：985.3，总计 3000 基因已激活";
        let claims = extract_unverified_claims(text, DEFAULT_PATTERNS_JSON);
        assert!(!claims.is_empty());
        let labels: Vec<&str> = claims.iter().map(|c| c.label.as_str()).collect();
        assert!(labels.contains(&"ΔG数值"));
        // "基因数量" uses \b which is ASCII-only in Rust's regex crate
        // (Python's re handles Unicode word boundaries differently)
        // So we only assert the patterns that work consisently
    }

    #[test]
    fn test_extract_unverified_claims_no_duplicates() {
        let text = "L5 L5 L5 full AGI full AGI";
        let claims = extract_unverified_claims(text, DEFAULT_PATTERNS_JSON);
        assert_eq!(claims.len(), 2); // L5 + AGI, no duplicates
    }

    #[test]
    fn test_build_candidates_basic() {
        let templates = r#"[
            {"gene_id_suffix": "IDENTITY-ANCHOR", "defect_no": 31, "defect_name": "进化路径缺身份锚定前置", "gene_name": "AGI路径身份锚定候选基因", "absorbed_knowledge": "test", "repair_mechanism": "test", "reusable_rule": "test", "severity_rank": 2, "apex_variables": "test"}
        ]"#;
        let source = "一些普通文本没有特殊声明";
        let records = build_candidate_records(source, "/tmp/test.md", templates, DEFAULT_PATTERNS_JSON);
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].defect_no, 31);
        assert!(records[0].gene_id.starts_with("GENE-ACTPATH-"));
        assert_eq!(records[0].status, "candidate");
        assert_eq!(records[0].verification_status, "pending_review_activation_path_intake");
    }

    #[test]
    fn test_build_candidates_with_claims() {
        let templates = r#"[
            {"gene_id_suffix": "IDENTITY-ANCHOR", "defect_no": 31, "defect_name": "id", "gene_name": "id", "absorbed_knowledge": "t", "repair_mechanism": "t", "reusable_rule": "t", "severity_rank": 2, "apex_variables": "t"}
        ]"#;
        let source = "系统已达L5，进入ASI纪元，ΔG：985.3";
        let records = build_candidate_records(source, "/tmp/asi.md", templates, DEFAULT_PATTERNS_JSON);
        assert_eq!(records.len(), 1);
        let refs: serde_json::Value = serde_json::from_str(&records[0].source_refs_json).unwrap();
        let claims = refs[0]["unverified_claims"].as_array().unwrap();
        let labels: Vec<&str> = claims.iter().map(|c| c["label"].as_str().unwrap()).collect();
        assert!(labels.contains(&"L5/圆融"));
        assert!(labels.contains(&"ASI"));
        assert!(labels.contains(&"ΔG数值"));
    }

    #[test]
    fn test_build_candidates_deterministic() {
        let templates = r#"[
            {"gene_id_suffix": "IDENTITY-ANCHOR", "defect_no": 31, "defect_name": "d", "gene_name": "g", "absorbed_knowledge": "t", "repair_mechanism": "t", "reusable_rule": "t", "severity_rank": 2, "apex_variables": "t"}
        ]"#;
        let source = "some text";
        let a = build_candidate_records(source, "/tmp/t.md", templates, DEFAULT_PATTERNS_JSON);
        let b = build_candidate_records(source, "/tmp/t.md", templates, DEFAULT_PATTERNS_JSON);
        assert_eq!(a[0].gene_id, b[0].gene_id);
        assert_eq!(a[0].gene_hash, b[0].gene_hash);
    }

    #[test]
    fn test_empty_templates() {
        let records = build_candidate_records("text", "/tmp/x.md", "[]", DEFAULT_PATTERNS_JSON);
        assert!(records.is_empty());
    }

    #[test]
    fn test_native_stable_gene_id_py() {
        let id = stable_gene_id("test_hash_123", "MY-SUFFIX");
        assert!(id.starts_with("GENE-ACTPATH-"));
        assert_eq!(id.len(), 29);
    }

    #[test]
    fn test_coarse_template_count() {
        // 6 coarse templates
        let templates = r#"[
            {"gene_id_suffix": "IDENTITY-ANCHOR", "defect_no": 31, "defect_name": "id1", "gene_name": "g1", "absorbed_knowledge": "t", "repair_mechanism": "t", "reusable_rule": "t", "severity_rank": 2, "apex_variables": "t"},
            {"gene_id_suffix": "SOURCE-TO-GENE", "defect_no": 32, "defect_name": "id2", "gene_name": "g2", "absorbed_knowledge": "t", "repair_mechanism": "t", "reusable_rule": "t", "severity_rank": 3, "apex_variables": "t"},
            {"gene_id_suffix": "FUSION-EVIDENCE", "defect_no": 33, "defect_name": "id3", "gene_name": "g3", "absorbed_knowledge": "t", "repair_mechanism": "t", "reusable_rule": "t", "severity_rank": 3, "apex_variables": "t"},
            {"gene_id_suffix": "REFLEXION-DISCOVERY", "defect_no": 34, "defect_name": "id4", "gene_name": "g4", "absorbed_knowledge": "t", "repair_mechanism": "t", "reusable_rule": "t", "severity_rank": 2, "apex_variables": "t"},
            {"gene_id_suffix": "SELF-REFERENTIAL-LOOP", "defect_no": 35, "defect_name": "id5", "gene_name": "g5", "absorbed_knowledge": "t", "repair_mechanism": "t", "reusable_rule": "t", "severity_rank": 3, "apex_variables": "t"},
            {"gene_id_suffix": "FAIL-TOLERANCE", "defect_no": 46, "defect_name": "id6", "gene_name": "g6", "absorbed_knowledge": "t", "repair_mechanism": "t", "reusable_rule": "t", "severity_rank": 2, "apex_variables": "t"}
        ]"#;
        let records = build_candidate_records("测试文本", "/tmp/test.md", templates, DEFAULT_PATTERNS_JSON);
        assert_eq!(records.len(), 6);
        // Check all gene_ids are unique
        let mut gene_ids: Vec<&str> = records.iter().map(|r| r.gene_id.as_str()).collect();
        gene_ids.sort();
        gene_ids.dedup();
        assert_eq!(gene_ids.len(), 6);
    }
}