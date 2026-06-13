/// PGG Archon gene fusion core — Rust PyO3 native.
use pyo3::prelude::*;
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct GeneRecord {
    gene_id: String,
    cycle_id: Option<String>,
    defect_no: String,  // stored as string since SQLite may have mixed types
    defect_name: String,
    gene_name: Option<String>,
    absorbed_knowledge: Option<String>,
    source_refs_json: Option<String>,
    repair_mechanism: Option<String>,
    severity_rank: Option<String>,
    apex_variables: Option<String>,
    gate_type: Option<String>,
    reusable_rule: Option<String>,
    status: Option<String>,
    evidence_grade: Option<String>,
    verification_status: Option<String>,
    boundary: Option<String>,
    gene_hash: Option<String>,
    created_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct FusionGroup {
    defect_no: String,
    defect_name: String,
    members: Vec<GeneRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct FusionCand {
    fusion_gene_id: String,
    defect_no: String,
    defect_name: String,
    member_ids: Vec<String>,
    member_count: usize,
    evidence_grade: String,
    severity_rank: String,
    gene_hash: String,
    written: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct FusionResult {
    schema: String,
    created_at: String,
    db_path: String,
    enabled: bool,
    write: bool,
    min_member_count: i64,
    boundary: String,
    agi_completion_claim: bool,
    status: String,
    fusion_candidates: Vec<FusionCand>,
    fusion_records_written: i64,
    error: Option<String>,
}

const FUSION_GATE_TYPE: &str = "auto_gene_fusion";
const SUPERSEDED_STATUS: &str = "superseded_by_fusion";
const FUSION_STATUS: &str = "active";
const FUSION_VERIFICATION: &str = "verified_by_gene_fusion";

fn evidence_rank(grade: &str) -> i64 {
    let head = grade.split(':').next().unwrap_or("").trim();
    match head {
        "S" => 5, "A+" => 4, "A" => 3, "A-" => 2, "B+" => 1, "B" => 0,
        _ => -1,
    }
}

fn timestamp() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let dur = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default();
    let secs = dur.as_secs();
    let days = secs / 86400;
    let rem = secs % 86400;
    let h = rem / 3600;
    let m = (rem % 3600) / 60;
    let s = rem % 60;
    let mut y = 1970i64;
    let mut d = days as i64;
    loop {
        let days_in_year = if is_leap(y) { 366 } else { 365 };
        if d < days_in_year { break; }
        d -= days_in_year;
        y += 1;
    }
    let month_days = if is_leap(y) {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut mo = 1usize;
    for &md in month_days.iter() {
        if d < md { break; }
        d -= md;
        mo += 1;
    }
    let day = d + 1;
    format!("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}+0000", y, mo, day, h, m, s)
}

fn is_leap(y: i64) -> bool {
    (y % 4 == 0 && y % 100 != 0) || y % 400 == 0
}

fn sha256_hex(value: &serde_json::Value) -> String {
    let json_str = serde_json::to_string(value).unwrap_or_default();
    let mut hasher = Sha256::new();
    hasher.update(json_str.as_bytes());
    hex::encode(hasher.finalize())
}

fn stable_fusion_id(defect_no: &str, defect_name: &str, member_ids: &[String]) -> String {
    let mut sorted = member_ids.to_vec();
    sorted.sort();
    let payload = serde_json::json!({
        "defect_no": defect_no,
        "defect_name": defect_name,
        "members": sorted,
    });
    let digest = sha256_hex(&payload);
    format!("GENE-FUSION-{}", &digest[..16].to_uppercase())
}

fn parse_json_field(value: &str) -> Vec<serde_json::Value> {
    let trimmed = value.trim();
    if trimmed.is_empty() || trimmed == "null" || trimmed == "None" {
        return vec![];
    }
    if trimmed.starts_with('[') || trimmed.starts_with('{') {
        match serde_json::from_str::<serde_json::Value>(trimmed) {
            Ok(v) => match v {
                serde_json::Value::Array(arr) => return arr,
                _ => return vec![v],
            },
            Err(_) => {}
        }
    }
    vec![serde_json::Value::String(trimmed.to_string())]
}

fn merge_text_lines(values: &[Option<String>]) -> String {
    let mut seen: Vec<String> = Vec::new();
    for val in values {
        let text = match val {
            Some(s) => s.trim().to_string(),
            None => continue,
        };
        if text.is_empty() { continue; }
        for line in text.lines() {
            let l = line.trim().to_string();
            if !l.is_empty() && !seen.contains(&l) {
                seen.push(l);
            }
        }
    }
    seen.join("\n")
}

fn merge_source_refs(values: &[Option<String>]) -> Vec<serde_json::Value> {
    let mut merged: Vec<serde_json::Value> = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();
    for val in values {
        let text = match val {
            Some(s) => s,
            None => continue,
        };
        for item in parse_json_field(text) {
            let key = serde_json::to_string(&item).unwrap_or_default();
            if seen.insert(key) {
                merged.push(item);
            }
        }
    }
    merged
}

fn strongest_evidence(values: &[Option<String>]) -> String {
    let mut best_text = String::new();
    let mut best_score: i64 = -1_000_000_000;
    for val in values {
        let text = match val {
            Some(s) => s.trim().to_string(),
            None => continue,
        };
        if text.is_empty() { continue; }
        let score = evidence_rank(&text);
        if score > best_score {
            best_score = score;
            best_text = text;
        }
    }
    if best_text.is_empty() {
        "A-: gene_fusion default".to_string()
    } else {
        best_text
    }
}

fn max_severity(values: &[Option<String>], default: &str) -> String {
    let mut best = default.to_string();
    let mut best_val: i64 = -1;
    for val in values {
        let v = match val {
            Some(s) => s.trim().to_string(),
            None => continue,
        };
        if v.is_empty() { continue; }
        let n: i64 = v.parse().unwrap_or(-1);
        if n > best_val {
            best_val = n;
            best = v;
        }
    }
    best
}

// ── SQLite ──────────────────────────────────

fn open_db(db_path: &str) -> Result<Connection, String> {
    Connection::open(db_path).map_err(|e| format!("db_open_failed: {}", e))
}

fn ensure_fusion_cycle(conn: &Connection) -> Result<String, String> {
    let cycle_id = "cycle_pgg_archon_gene_fusion_v1";
    let created = timestamp();
    conn.execute(
        "INSERT OR IGNORE INTO evolution_cycles \
         (cycle_id, created_at, theme, sequence_logic, status, evidence_grade, boundary) \
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        params![cycle_id, created, "PGG Archon 同缺陷候选基因受控融合",
                "12534：融合→纠错→固化→降熵→规划", "active",
                "A-: gene_fusion union of verified candidates",
                "受控融合：合并同一缺陷下的多条候选基因，不调用模型、不修改核心代码、不声称 AGI 完成"],
    ).map_err(|e| format!("ensure_cycle_failed: {}", e))?;
    Ok(cycle_id.to_string())
}

/// Read a column that may be TEXT or INTEGER from SQLite.
macro_rules! row_text {
    ($row:expr, $col:expr) => {{
        let val: String = match $row.get::<_, String>($col) {
            Ok(s) => s,
            Err(_) => {
                match $row.get::<_, i64>($col) {
                    Ok(n) => n.to_string(),
                    Err(_) => String::new(),
                }
            }
        };
        val
    }};
}

fn select_fusion_groups(conn: &Connection, min_count: i64) -> Result<Vec<FusionGroup>, String> {
    let mut stmt = conn.prepare(
        "SELECT gene_id, cycle_id, defect_no, defect_name, gene_name, \
         absorbed_knowledge, source_refs_json, repair_mechanism, severity_rank, \
         apex_variables, gate_type, reusable_rule, status, evidence_grade, \
         verification_status, boundary, gene_hash, created_at \
         FROM evolution_genes \
         WHERE status IN ('active', 'verified') \
         ORDER BY created_at ASC"
    ).map_err(|e| format!("select_prepare_failed: {}", e))?;

    // Collect into GeneRecords using row_text! for safety
    let mut records: Vec<GeneRecord> = Vec::new();
    let rows = stmt.query_map([], |row| {
        Ok((
            row_text!(row, 0), row_text!(row, 1),
            row_text!(row, 2), row_text!(row, 3),
            row_text!(row, 4), row_text!(row, 5),
            row_text!(row, 6), row_text!(row, 7),
            row_text!(row, 8), row_text!(row, 9),
            row_text!(row, 10), row_text!(row, 11),
            row_text!(row, 12), row_text!(row, 13),
            row_text!(row, 14), row_text!(row, 15),
            row_text!(row, 16), row_text!(row, 17),
        ))
    }).map_err(|e| format!("select_query_failed: {}", e))?;

    for row in rows {
        let (gene_id, cycle_id, defect_no, defect_name, gene_name,
             absorbed_knowledge, source_refs_json, repair_mechanism,
             severity_rank, apex_variables, gate_type, reusable_rule,
             status, evidence_grade, verification_status,
             boundary, gene_hash, created_at) = row.map_err(|e| format!("row: {}", e))?;

        let gt = gate_type.as_str();
        let st = status.as_str();
        if gt == FUSION_GATE_TYPE || st == SUPERSEDED_STATUS {
            continue;
        }

        fn opt(s: String) -> Option<String> {
            if s.is_empty() { None } else { Some(s) }
        }

        records.push(GeneRecord {
            gene_id, cycle_id: opt(cycle_id),
            defect_no, defect_name, gene_name: opt(gene_name),
            absorbed_knowledge: opt(absorbed_knowledge),
            source_refs_json: opt(source_refs_json),
            repair_mechanism: opt(repair_mechanism),
            severity_rank: opt(severity_rank),
            apex_variables: opt(apex_variables),
            gate_type: opt(gate_type),
            reusable_rule: opt(reusable_rule),
            status: opt(status),
            evidence_grade: opt(evidence_grade),
            verification_status: opt(verification_status),
            boundary: opt(boundary),
            gene_hash: opt(gene_hash),
            created_at: opt(created_at),
        });
    }

    // Group by defect_no + defect_name
    let mut groups: HashMap<(String, String), Vec<GeneRecord>> = HashMap::new();
    for rec in records {
        groups.entry((rec.defect_no.clone(), rec.defect_name.clone()))
            .or_default().push(rec);
    }

    let mut result: Vec<FusionGroup> = groups.into_iter()
        .filter(|(_, members)| members.len() as i64 >= min_count)
        .map(|((defect_no, defect_name), members)| FusionGroup { defect_no, defect_name, members })
        .collect();

    result.sort_by(|a, b| b.members.len().cmp(&a.members.len())
        .then_with(|| a.defect_no.cmp(&b.defect_no)));
    Ok(result)
}

fn build_fusion_record(cycle_id: &str, group: &FusionGroup) -> (FusionCand, serde_json::Value) {
    let member_ids: Vec<String> = group.members.iter().map(|m| m.gene_id.clone()).collect();
    let fusion_id = stable_fusion_id(&group.defect_no, &group.defect_name, &member_ids);

    let absorbed = merge_text_lines(&group.members.iter()
        .map(|m| m.absorbed_knowledge.clone()).collect::<Vec<_>>());
    let repair = merge_text_lines(&group.members.iter()
        .map(|m| m.repair_mechanism.clone()).collect::<Vec<_>>());
    let rule = merge_text_lines(&group.members.iter()
        .map(|m| m.reusable_rule.clone()).collect::<Vec<_>>());
    let apex_vars = merge_text_lines(&group.members.iter()
        .map(|m| m.apex_variables.clone()).collect::<Vec<_>>());

    let mut refs = merge_source_refs(&group.members.iter()
        .map(|m| m.source_refs_json.clone()).collect::<Vec<_>>());
    refs.push(serde_json::json!({
        "fusion_member_gene_ids": member_ids,
        "fusion_member_count": member_ids.len(),
    }));

    let evidence = strongest_evidence(&group.members.iter()
        .map(|m| m.evidence_grade.clone()).collect::<Vec<_>>());
    let severity = max_severity(&group.members.iter()
        .map(|m| m.severity_rank.clone()).collect::<Vec<_>>(), "1");

    let mut record = serde_json::json!({
        "gene_id": fusion_id,
        "cycle_id": cycle_id,
        "created_at": timestamp(),
        "defect_no": group.defect_no,
        "defect_name": group.defect_name,
        "gene_name": format!("FUSION:{}", group.defect_name),
        "absorbed_knowledge": absorbed,
        "source_refs_json": serde_json::to_string(&refs).unwrap_or_default(),
        "repair_mechanism": repair,
        "severity_rank": severity,
        "apex_variables": apex_vars,
        "gate_type": FUSION_GATE_TYPE,
        "reusable_rule": rule,
        "status": FUSION_STATUS,
        "evidence_grade": evidence,
        "verification_status": FUSION_VERIFICATION,
        "boundary": "受控融合：合并同一缺陷下的多条候选基因",
        "member_ids": member_ids,
    });

    // Compute gene_hash (exclude gene_hash from input)
    let mut hash_input = record.clone();
    hash_input.as_object_mut().and_then(|m| m.remove("member_ids"));
    hash_input.as_object_mut().and_then(|m| m.remove("gene_hash"));
    let gene_hash = sha256_hex(&hash_input);

    record.as_object_mut().and_then(|m| m.insert("gene_hash".into(), serde_json::json!(gene_hash)));

    let cand = FusionCand {
        fusion_gene_id: fusion_id,
        defect_no: group.defect_no.clone(),
        defect_name: group.defect_name.clone(),
        member_ids: member_ids.clone(),
        member_count: member_ids.len(),
        evidence_grade: evidence,
        severity_rank: severity,
        gene_hash,
        written: false,
    };
    (cand, record)
}

fn insert_fusion_gene(conn: &Connection, record: &serde_json::Value) -> Result<bool, String> {
    let gene_id = record["gene_id"].as_str().ok_or("missing_gene_id")?;
    let exists: bool = conn.query_row(
        "SELECT 1 FROM evolution_genes WHERE gene_id = ?1", params![gene_id],
        |_| Ok(true)
    ).unwrap_or(false);
    if exists { return Ok(false); }

    let member_ids: Vec<String> = record["member_ids"].as_array()
        .map(|a| a.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .unwrap_or_default();

    let s = |key: &str| -> String {
        record[key].as_str().unwrap_or("").to_string()
    };

    conn.execute(
        "INSERT INTO evolution_genes \
         (gene_id, cycle_id, created_at, defect_no, defect_name, gene_name, \
          absorbed_knowledge, source_refs_json, repair_mechanism, severity_rank, \
          apex_variables, gate_type, reusable_rule, status, evidence_grade, \
          verification_status, boundary, gene_hash) \
         VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18)",
        params![s("gene_id"), s("cycle_id"), s("created_at"),
                s("defect_no"), s("defect_name"), s("gene_name"),
                s("absorbed_knowledge"), s("source_refs_json"), s("repair_mechanism"),
                s("severity_rank"), s("apex_variables"), s("gate_type"),
                s("reusable_rule"), s("status"), s("evidence_grade"),
                s("verification_status"), s("boundary"), s("gene_hash")],
    ).map_err(|e| format!("insert_fusion_failed: {}", e))?;

    for mid in &member_ids {
        let _ = conn.execute(
            "INSERT OR IGNORE INTO gene_source_map(gene_id, source_id) VALUES (?1, ?2)",
            params![gene_id, mid],
        );
        conn.execute(
            "UPDATE evolution_genes SET status = ?1 WHERE gene_id = ?2 AND status != ?1",
            params![SUPERSEDED_STATUS, mid],
        ).map_err(|e| format!("update_member_failed: {}", e))?;
    }
    Ok(true)
}

// ── Main pipeline ───────────────────────────

fn run_fusion(db_path: &str, write: bool, min_count: i64, enabled: bool) -> FusionResult {
    let mut result = FusionResult {
        schema: "PGGArchonGeneFusionSurface/v1".into(),
        created_at: timestamp(),
        db_path: db_path.into(),
        enabled, write,
        min_member_count: min_count,
        boundary: "受控融合：合并同一缺陷下的多条候选基因".into(),
        agi_completion_claim: false,
        ..Default::default()
    };
    if !enabled { result.status = "DISABLED".into(); return result; }
    if !std::path::Path::new(db_path).exists() {
        result.status = "BLOCK".into(); result.error = Some("gene_db_missing".into()); return result;
    }
    let conn = match open_db(db_path) { Ok(c) => c, Err(e) => {
        result.status = "BLOCK".into(); result.error = Some(e); return result; }};
    let cycle_id = match ensure_fusion_cycle(&conn) { Ok(id) => id, Err(e) => {
        result.status = "BLOCK".into(); result.error = Some(e); return result; }};
    let groups = match select_fusion_groups(&conn, min_count) { Ok(g) => g, Err(e) => {
        result.status = "BLOCK".into(); result.error = Some(e); return result; }};
    let mut candidates = Vec::new();
    let mut written = 0i64;
    for group in &groups {
        let (mut cand, record) = build_fusion_record(&cycle_id, group);
        if write {
            if let Ok(true) = insert_fusion_gene(&conn, &record) {
                cand.written = true;
                written += 1;
            }
        }
        candidates.push(cand);
    }
    if write { let _ = conn.execute_batch("COMMIT"); }
    result.status = if candidates.is_empty() { "WATCH".into() } else { "PASS".into() };
    result.fusion_candidates = candidates;
    result.fusion_records_written = written;
    result
}

// ── PyO3 exports ────────────────────────────

#[pyfunction]
fn native_run_fusion(db_path: &str, write: bool, min_member_count: i64, enabled: bool) -> PyResult<String> {
    let result = run_fusion(db_path, write, min_member_count, enabled);
    serde_json::to_string(&result).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

#[pyfunction]
fn native_merge_text_lines(values: Vec<String>) -> String {
    let opts: Vec<Option<String>> = values.into_iter().map(Some).collect();
    merge_text_lines(&opts)
}

#[pyfunction]
fn native_strongest_evidence(values: Vec<String>) -> String {
    let opts: Vec<Option<String>> = values.into_iter().map(Some).collect();
    strongest_evidence(&opts)
}

#[pyfunction]
fn native_info() -> String {
    format!("hermes_pgg_gene_fusion v{} — Fusion core", env!("CARGO_PKG_VERSION"))
}

#[pymodule]
fn hermes_pgg_gene_fusion(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_run_fusion, m)?)?;
    m.add_function(wrap_pyfunction!(native_merge_text_lines, m)?)?;
    m.add_function(wrap_pyfunction!(native_strongest_evidence, m)?)?;
    m.add_function(wrap_pyfunction!(native_info, m)?)?;
    Ok(())
}

// ── Tests ───────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sha256_deterministic() {
        let v = serde_json::json!({"a": 1, "b": "hello"});
        assert_eq!(sha256_hex(&v), sha256_hex(&v));
    }

    #[test]
    fn test_stable_fusion_id_deterministic() {
        let id1 = stable_fusion_id("1", "test_defect", &["g1".into(), "g2".into()]);
        let id2 = stable_fusion_id("1", "test_defect", &["g1".into(), "g2".into()]);
        assert_eq!(id1, id2);
        assert!(id1.starts_with("GENE-FUSION-"));
        assert_eq!(id1.len(), 28);
    }

    #[test]
    fn test_stable_fusion_id_order_independent() {
        let id1 = stable_fusion_id("1", "test", &["g1".into(), "g2".into()]);
        let id2 = stable_fusion_id("1", "test", &["g2".into(), "g1".into()]);
        assert_eq!(id1, id2);
    }

    #[test]
    fn test_parse_json_field_empty() {
        assert!(parse_json_field("").is_empty());
        assert!(parse_json_field("null").is_empty());
    }

    #[test]
    fn test_parse_json_field_array() {
        assert_eq!(parse_json_field("[1,2,3]").len(), 3);
    }

    #[test]
    fn test_merge_text_lines_dedup() {
        let r = merge_text_lines(&[Some("hello\nworld".into()), Some("hello\nrust".into())]);
        assert_eq!(r, "hello\nworld\nrust");
    }

    #[test]
    fn test_merge_text_lines_none() {
        assert_eq!(merge_text_lines(&[None, Some("only".into())]), "only");
    }

    #[test]
    fn test_merge_source_refs_dedup() {
        let r = merge_source_refs(&[
            Some(r#"[{"a":1},{"b":2}]"#.into()),
            Some(r#"[{"a":1}]"#.into()),
        ]);
        assert_eq!(r.len(), 2);
    }

    #[test]
    fn test_evidence_rank() {
        assert_eq!(evidence_rank("S"), 5);
        assert_eq!(evidence_rank("A+: good"), 4);
        assert_eq!(evidence_rank("unknown"), -1);
    }

    #[test]
    fn test_strongest_evidence() {
        assert_eq!(
            strongest_evidence(&[Some("B+: weak".into()), Some("S: best".into()), Some("A: ok".into())]),
            "S: best"
        );
    }

    #[test]
    fn test_strongest_evidence_empty() {
        assert_eq!(strongest_evidence(&[None, None]), "A-: gene_fusion default");
    }

    #[test]
    fn test_run_fusion_disabled() {
        let r = run_fusion("/tmp/nx.db", false, 2, false);
        assert_eq!(r.status, "DISABLED");
    }

    #[test]
    fn test_run_fusion_missing_db() {
        let r = run_fusion("/tmp/nonexistent_pgg_test.db", false, 2, true);
        assert_eq!(r.status, "BLOCK");
        assert_eq!(r.error.as_deref(), Some("gene_db_missing"));
    }

    #[test]
    fn test_is_leap() {
        assert!(is_leap(2000));
        assert!(!is_leap(1900));
        assert!(is_leap(2024));
    }

    #[test]
    fn test_timestamp_format() {
        let ts = timestamp();
        assert_eq!(ts.len(), 24);
        assert!(ts.contains('T'));
    }

    #[test]
    fn test_max_severity() {
        assert_eq!(max_severity(&[Some("3".into()), Some("7".into())], "1"), "7");
        assert_eq!(max_severity(&[None, None], "1"), "1");
    }

    #[test]
    fn test_fusion_boundary() {
        let r = run_fusion("/tmp/nx.db", false, 2, false);
        assert!(!r.agi_completion_claim);
    }
}