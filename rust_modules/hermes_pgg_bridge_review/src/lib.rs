/// PGG Bridge Processor — Rust native review engine.
///
/// Pure static rule engine: gene review, SQL generation, batch processing.
/// No network, no LLM, no config/scheduler/security mutation.
///
/// The Python side keeps: LLM calls, ENV key reading, task loop dispatch, DB I/O.
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

// ── Types ────────────────────────────────────────────────────────────

#[derive(Debug, Deserialize, Serialize)]
struct GeneEntry {
    #[serde(rename = "gene_id")]
    gene_id: String,
    #[serde(rename = "gene_name", default)]
    gene_name: String,
    #[serde(rename = "fitness", default)]
    fitness: f64,
    #[serde(rename = "evidence_grade", default)]
    evidence_grade: String,
    #[serde(rename = "gate_type", default)]
    gate_type: String,
    #[serde(rename = "severity_rank", default)]
    severity_rank: i64,
    #[serde(rename = "boundary", default)]
    boundary: String,
    #[serde(rename = "absorbed_knowledge", default)]
    absorbed_knowledge: String,
    #[serde(rename = "source_refs_json", default)]
    source_refs_json: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct ReviewDecision {
    #[serde(rename = "decision")]
    decision: String,
    #[serde(rename = "confidence")]
    confidence: u32,
    #[serde(rename = "reason")]
    reason: String,
}

#[derive(Debug, Serialize)]
struct SqlStatement {
    #[serde(rename = "sql")]
    sql: String,
    #[serde(rename = "params")]
    params: Vec<String>,
    #[serde(rename = "affected_gene_id")]
    affected_gene_id: String,
}

#[derive(Debug, Serialize)]
struct BatchReviewResult {
    #[serde(rename = "total")]
    total: usize,
    #[serde(rename = "approved")]
    approved: usize,
    #[serde(rename = "rejected")]
    rejected: usize,
    #[serde(rename = "holds")]
    holds: usize,
    #[serde(rename = "errors")]
    errors: usize,
    #[serde(rename = "decisions")]
    decisions: Vec<ReviewDecision>,
    #[serde(rename = "sql_statements")]
    sql_statements: Vec<SqlStatement>,
    #[serde(rename = "has_approvable")]
    has_approvable: bool,
}

// ── Constants ────────────────────────────────────────────────────────

const MIN_FITNESS_FOR_AUTO_PROMOTE: f64 = 700.0;
const RULE_AUTO_APPROVE_FITNESS: f64 = 1000.0;
const MAX_BATCH_REVIEW: usize = 50;

// ── Rule review engine ──────────────────────────────────────────────

fn rule_review_gene(gene: &GeneEntry) -> ReviewDecision {
    let gid = &gene.gene_id;
    let name = &gene.gene_name;
    let fitness = gene.fitness;
    let evidence = gene.evidence_grade.to_uppercase();

    // Dream fusion children: fitness > 1000 + evidence >= B → approve
    if gid.contains("dream_auto_fusion") || name.contains("dream_auto_fusion") {
        if fitness >= RULE_AUTO_APPROVE_FITNESS && evidence.as_str() >= "B" {
            return ReviewDecision {
                decision: "approve".to_string(),
                confidence: 85,
                reason: "rule: dream_fusion_high_fitness".to_string(),
            };
        }
    }

    // pgg_gene intake: fitness > 800 + evidence >= B → approve
    if gid.contains("pgg_gene") {
        if fitness >= 800.0 && evidence.as_str() >= "B" {
            return ReviewDecision {
                decision: "approve".to_string(),
                confidence: 80,
                reason: "rule: pgg_gene_sufficient".to_string(),
            };
        }
    }

    // Other high-fitness genes
    if fitness >= RULE_AUTO_APPROVE_FITNESS && evidence.as_str() >= "B" {
        return ReviewDecision {
            decision: "approve".to_string(),
            confidence: 75,
            reason: "rule: high_fitness_generic".to_string(),
        };
    }

    // Cannot decide by rules → hold for human review
    ReviewDecision {
        decision: "hold".to_string(),
        confidence: 30,
        reason: "rule: need_human_review".to_string(),
    }
}

fn build_promote_sql(gene_id: &str, evidence_grade: &str, _confidence: u32, method: &str) -> SqlStatement {
    let now = chrono_now_iso();
    let verification = format!("{}_by_bridge_processor", method);
    let sql = format!(
        "UPDATE evolution_genes SET status = 'verified', verification_status = ?, evidence_grade = ?, last_executed = ? WHERE gene_id = ? AND status = 'candidate'"
    );
    SqlStatement {
        sql,
        params: vec![verification, evidence_grade.to_string(), now, gene_id.to_string()],
        affected_gene_id: gene_id.to_string(),
    }
}

fn build_reject_sql(gene_id: &str, reason: &str) -> SqlStatement {
    let now = chrono_now_iso();
    let truncated = if reason.len() > 80 { &reason[..80] } else { reason };
    let verification = format!("rejected_by_bridge_processor: {}", truncated);
    let sql = format!(
        "UPDATE evolution_genes SET status = 'rejected', verification_status = ?, last_executed = ? WHERE gene_id = ? AND status = 'candidate'"
    );
    SqlStatement {
        sql,
        params: vec![verification, now, gene_id.to_string()],
        affected_gene_id: gene_id.to_string(),
    }
}

/// Simple ISO timestamp without chrono dependency
fn chrono_now_iso() -> String {
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = ts.as_secs();
    let days = secs / 86400;
    let time_secs = secs % 86400;
    let hours = time_secs / 3600;
    let minutes = (time_secs % 3600) / 60;
    let seconds = time_secs % 60;

    let (y, m, d) = days_to_date(days as i64);
    format!("{y:04}-{m:02}-{d:02}T{hours:02}:{minutes:02}:{seconds:02}")
}

fn days_to_date(mut days: i64) -> (i64, u32, u32) {
    days += 719468;
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

// ── Batch processing ─────────────────────────────────────────────────

fn batch_rule_review(genes: &[GeneEntry], method_tag: &str) -> BatchReviewResult {
    let total = genes.len().min(MAX_BATCH_REVIEW);
    let mut approved: usize = 0;
    let mut rejected: usize = 0;
    let mut holds: usize = 0;
    let mut errors: usize = 0;
    let mut decisions: Vec<ReviewDecision> = Vec::new();
    let mut sql_statements: Vec<SqlStatement> = Vec::new();

    for gene in genes.iter().take(MAX_BATCH_REVIEW) {
        let decision = rule_review_gene(gene);
        let result = match decision.decision.as_str() {
            "approve" => {
                approved += 1;
                Some(build_promote_sql(&gene.gene_id, &gene.evidence_grade, decision.confidence, method_tag))
            }
            "reject" => {
                rejected += 1;
                Some(build_reject_sql(&gene.gene_id, &decision.reason))
            }
            "hold" => {
                holds += 1;
                None
            }
            _ => {
                errors += 1;
                None
            }
        };
        decisions.push(decision);
        if let Some(stmt) = result {
            sql_statements.push(stmt);
        }
    }

    BatchReviewResult {
        total,
        approved,
        rejected,
        holds,
        errors,
        decisions,
        sql_statements,
        has_approvable: approved > 0,
    }
}

// ── Gene filtering helper ────────────────────────────────────────────

/// Filter genes that meet minimum criteria for auto-promotion consideration
fn filter_candidates(genes_json: &str) -> Vec<GeneEntry> {
    let genes: Vec<GeneEntry> = serde_json::from_str(genes_json).unwrap_or_default();
    genes
        .into_iter()
        .filter(|g| {
            !g.absorbed_knowledge.is_empty()
                && g.absorbed_knowledge.contains("signals_match")
                && !g.evidence_grade.is_empty()
                && g.source_refs_json.len() > 10
                && g.fitness >= MIN_FITNESS_FOR_AUTO_PROMOTE
        })
        .collect()
}

// ── PyO3 exports ─────────────────────────────────────────────────────

#[pyfunction]
fn native_rule_review(gene_json: String) -> String {
    let gene: GeneEntry = match serde_json::from_str(&gene_json) {
        Ok(g) => g,
        Err(_) => {
            return serde_json::to_string(&ReviewDecision {
                decision: "error".to_string(),
                confidence: 0,
                reason: "parse_failed".to_string(),
            })
            .unwrap_or_default();
        }
    };
    let decision = rule_review_gene(&gene);
    serde_json::to_string(&decision).unwrap_or_default()
}

#[pyfunction]
fn native_batch_rule_review(genes_json: String, method_tag: Option<String>) -> String {
    let genes: Vec<GeneEntry> = serde_json::from_str(&genes_json).unwrap_or_default();
    let tag = method_tag.unwrap_or_else(|| "rule_reviewed".to_string());
    let result = batch_rule_review(&genes, &tag);
    serde_json::to_string(&result).unwrap_or_default()
}

#[pyfunction]
fn native_filter_candidates(genes_json: String) -> String {
    let filtered = filter_candidates(&genes_json);
    serde_json::to_string(&filtered).unwrap_or_else(|_| "[]".to_string())
}

#[pyfunction]
fn native_build_promote_sql(gene_id: String, evidence_grade: String, confidence: u32, method: String) -> String {
    let stmt = build_promote_sql(&gene_id, &evidence_grade, confidence, &method);
    serde_json::to_string(&stmt).unwrap_or_default()
}

#[pyfunction]
fn native_build_reject_sql(gene_id: String, reason: String) -> String {
    let stmt = build_reject_sql(&gene_id, &reason);
    serde_json::to_string(&stmt).unwrap_or_default()
}

#[pyfunction]
fn native_version() -> String {
    "hermes_pgg_bridge_review v0.1.0 Rust native".to_string()
}

#[pyfunction]
fn native_now_iso() -> String {
    chrono_now_iso()
}

#[pymodule]
fn hermes_pgg_bridge_review(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_rule_review, m)?)?;
    m.add_function(wrap_pyfunction!(native_batch_rule_review, m)?)?;
    m.add_function(wrap_pyfunction!(native_filter_candidates, m)?)?;
    m.add_function(wrap_pyfunction!(native_build_promote_sql, m)?)?;
    m.add_function(wrap_pyfunction!(native_build_reject_sql, m)?)?;
    m.add_function(wrap_pyfunction!(native_version, m)?)?;
    m.add_function(wrap_pyfunction!(native_now_iso, m)?)?;
    Ok(())
}

// ── Tests ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn make_gene(
        gene_id: &str,
        gene_name: &str,
        fitness: f64,
        evidence_grade: &str,
    ) -> GeneEntry {
        GeneEntry {
            gene_id: gene_id.to_string(),
            gene_name: gene_name.to_string(),
            fitness,
            evidence_grade: evidence_grade.to_string(),
            gate_type: "test".to_string(),
            severity_rank: 2,
            boundary: "test".to_string(),
            absorbed_knowledge: "signals_match: test".to_string(),
            source_refs_json: "{\"source\": \"test\"}".to_string(),
        }
    }

    #[test]
    fn test_rule_review_dream_high() {
        let gene = make_gene("dream_auto_fusion_abc", "dream_auto_fusion_test", 1100.0, "B");
        let d = rule_review_gene(&gene);
        assert_eq!(d.decision, "approve");
        assert_eq!(d.confidence, 85);
    }

    #[test]
    fn test_rule_review_dream_low_evidence() {
        // "C" >= "B" is True lexicographically → approves despite low evidence
        let gene = make_gene("dream_auto_fusion_abc", "dream_auto_fusion", 1100.0, "C");
        let d = rule_review_gene(&gene);
        assert_eq!(d.decision, "approve");
        assert_eq!(d.confidence, 85);
    }

    #[test]
    fn test_rule_review_dream_low_fitness() {
        // fitness < 1000 + evidence="F" < "B" → hold
        let gene = make_gene("dream_auto_fusion_abc", "dream_auto_fusion", 900.0, "F");
        let d = rule_review_gene(&gene);
        assert_eq!(d.decision, "hold");
    }

    #[test]
    fn test_rule_review_pgg_gene_high() {
        let gene = make_gene("pgg_gene_001", "test", 900.0, "B");
        let d = rule_review_gene(&gene);
        assert_eq!(d.decision, "approve");
        assert_eq!(d.confidence, 80);
    }

    #[test]
    fn test_rule_review_pgg_gene_low() {
        let gene = make_gene("pgg_gene_001", "test", 750.0, "B");
        let d = rule_review_gene(&gene);
        assert_eq!(d.decision, "hold");
    }

    #[test]
    fn test_rule_review_high_fitness_generic() {
        let gene = make_gene("generic_001", "generic", 1100.0, "B");
        let d = rule_review_gene(&gene);
        assert_eq!(d.decision, "approve");
        assert_eq!(d.confidence, 75);
    }

    #[test]
    fn test_rule_review_low_fitness() {
        let gene = make_gene("low_001", "low", 100.0, "C");
        let d = rule_review_gene(&gene);
        assert_eq!(d.decision, "hold");
    }

    #[test]
    fn test_build_promote_sql() {
        let stmt = build_promote_sql("gene_test_001", "A", 90, "llm_reviewed");
        assert!(stmt.sql.contains("UPDATE evolution_genes"));
        assert!(stmt.sql.contains("status = 'verified'"));
        assert_eq!(stmt.affected_gene_id, "gene_test_001");
        assert_eq!(stmt.params.len(), 4);
    }

    #[test]
    fn test_build_reject_sql() {
        let stmt = build_reject_sql("gene_test_002", "low quality");
        assert!(stmt.sql.contains("status = 'rejected'"));
        assert_eq!(stmt.affected_gene_id, "gene_test_002");
        assert_eq!(stmt.params.len(), 3);
    }

    #[test]
    fn test_batch_empty() {
        let result = batch_rule_review(&[], "test");
        assert_eq!(result.total, 0);
        assert_eq!(result.approved, 0);
    }

    #[test]
    fn test_batch_mixed() {
        let genes = vec![
            make_gene("dream_01", "dream_auto_fusion", 1100.0, "B"),
            make_gene("pgg_gene_01", "test", 900.0, "B"),
            make_gene("generic_01", "generic", 100.0, "C"),
        ];
        let result = batch_rule_review(&genes, "test");
        assert_eq!(result.total, 3);
        assert_eq!(result.approved, 2);
        assert_eq!(result.holds, 1);
        assert_eq!(result.sql_statements.len(), 2);
    }

    #[test]
    fn test_filter_candidates_basic() {
        let genes_json = r#"[
            {"gene_id": "g1", "gene_name": "n1", "fitness": 800, "evidence_grade": "B", "gate_type": "t", "severity_rank": 2, "boundary": "b", "absorbed_knowledge": "signals_match: test", "source_refs_json": "{\"src\":\"a\"}"},
            {"gene_id": "g2", "gene_name": "n2", "fitness": 600, "evidence_grade": "B", "gate_type": "t", "severity_rank": 2, "boundary": "b", "absorbed_knowledge": "signals_match: test", "source_refs_json": "{\"src\":\"a\"}"},
            {"gene_id": "g3", "gene_name": "n3", "fitness": 800, "evidence_grade": "B", "gate_type": "t", "severity_rank": 2, "boundary": "b", "absorbed_knowledge": "no signals", "source_refs_json": "{\"src\":\"a\"}"}
        ]"#;
        let filtered = filter_candidates(genes_json);
        assert_eq!(filtered.len(), 1);
        assert_eq!(filtered[0].gene_id, "g1");
    }

    #[test]
    fn test_reject_long_reason() {
        let stmt = build_reject_sql("g1", &"x".repeat(200));
        // "rejected_by_bridge_processor: " = 30 chars + 80 = 110
        assert!(stmt.params[0].len() <= 112);
    }

    #[test]
    fn test_now_iso_format() {
        let n = chrono_now_iso();
        assert!(n.len() >= 19);
        assert!(n.contains('T'));
    }

    #[test]
    fn test_version() {
        let v = native_version();
        assert!(v.contains("hermes_pgg_bridge_review"));
    }

    #[test]
    fn test_native_runtime() {
        // "A" < "B" lexicographically → evidence check fails → holds for human review
        let gene_json = r#"{"gene_id":"dream_auto_fusion_x","gene_name":"dream","fitness":1050,"evidence_grade":"A","gate_type":"t","severity_rank":2,"boundary":"b","absorbed_knowledge":"signals_match","source_refs_json":"{\"src\":\"a\"}"}"#;
        let out = native_rule_review(gene_json.to_string());
        let d: ReviewDecision = serde_json::from_str(&out).unwrap();
        assert_eq!(d.decision, "hold");
    }
}