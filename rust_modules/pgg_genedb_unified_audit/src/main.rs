use chrono::Utc;
use rusqlite::Connection;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::Path;

const RUNTIME_DB: &str = "/Users/appleoppa/.hermes/data/pgg_archon.db";
const INTAKE_DB: &str =
    "/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3";
const OUT_DIR: &str =
    "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/genedb-unified-audit-20260615";

#[derive(Serialize)]
struct Audit {
    schema: String,
    generated_at: String,
    status: String,
    dbs: Vec<DbAudit>,
    issues: Vec<Issue>,
    canonical_model: String,
    boundary: String,
}

#[derive(Serialize)]
struct DbAudit {
    path: String,
    exists: bool,
    size_bytes: u64,
    sha256: String,
    tables: Vec<String>,
    counts: BTreeMap<String, i64>,
    columns: BTreeMap<String, Vec<String>>,
    schema_role: String,
}

#[derive(Serialize)]
struct Issue {
    path: String,
    severity: String,
    issue: String,
    recommendation: String,
}

fn sha256_file(path: &Path) -> String {
    match fs::read(path) {
        Ok(data) => format!("{:x}", Sha256::digest(&data)),
        Err(_) => String::new(),
    }
}

fn query_tables(conn: &Connection) -> Vec<String> {
    let mut stmt =
        match conn.prepare("select name from sqlite_master where type='table' order by name") {
            Ok(s) => s,
            Err(_) => return vec![],
        };
    let tables = match stmt.query_map([], |r| r.get::<_, String>(0)) {
        Ok(rows) => rows.filter_map(|r| r.ok()).collect(),
        Err(_) => vec![],
    };
    tables
}

fn audit_db(path: &str) -> DbAudit {
    let p = Path::new(path);
    let mut out = DbAudit {
        path: path.to_string(),
        exists: p.exists(),
        size_bytes: 0,
        sha256: String::new(),
        tables: vec![],
        counts: BTreeMap::new(),
        columns: BTreeMap::new(),
        schema_role: "missing".to_string(),
    };
    if !p.exists() {
        return out;
    }
    if let Ok(meta) = fs::metadata(p) {
        out.size_bytes = meta.len();
    }
    out.sha256 = sha256_file(p);
    let conn = match Connection::open(p) {
        Ok(c) => c,
        Err(_) => {
            out.schema_role = "open_error".to_string();
            return out;
        }
    };
    out.tables = query_tables(&conn);
    for table in out.tables.clone() {
        let safe_table = table.replace('"', "");
        let sql = format!("select count(*) from \"{}\"", safe_table);
        let count: i64 = conn.query_row(&sql, [], |r| r.get(0)).unwrap_or(-1);
        out.counts.insert(table.clone(), count);
        let pragma = format!("pragma table_info(\"{}\")", safe_table);
        let mut cols: Vec<String> = vec![];
        if let Ok(mut stmt) = conn.prepare(&pragma) {
            if let Ok(rows) = stmt.query_map([], |r| r.get::<_, String>(1)) {
                cols = rows.filter_map(|r| r.ok()).collect();
            }
        }
        out.columns.insert(table, cols);
    }
    if out.tables.contains(&"evolution_genes".to_string())
        && out.tables.contains(&"gene_lifecycle".to_string())
    {
        out.schema_role = "runtime_lifecycle_db".to_string();
    }
    if out.tables.contains(&"evolution_genes".to_string()) {
        if let Some(cols) = out.columns.get("evolution_genes") {
            if cols.contains(&"verification_status".to_string())
                && cols.contains(&"source_refs_json".to_string())
                && cols.contains(&"fitness".to_string())
            {
                out.schema_role = "intake_knowledge_db".to_string();
            }
        }
    }
    out
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let runtime = args
        .get(1)
        .cloned()
        .unwrap_or_else(|| RUNTIME_DB.to_string());
    let intake = args
        .get(2)
        .cloned()
        .unwrap_or_else(|| INTAKE_DB.to_string());
    let dbs = vec![audit_db(&runtime), audit_db(&intake)];
    let mut issues: Vec<Issue> = vec![];
    for d in &dbs {
        if !d.exists {
            issues.push(Issue {
                path: d.path.clone(),
                severity: "WATCH".to_string(),
                issue: "db_missing".to_string(),
                recommendation: "restore or update canonical DB path".to_string(),
            });
            continue;
        }
        if d.schema_role == "runtime_lifecycle_db" {
            let cols = d
                .columns
                .get("evolution_genes")
                .cloned()
                .unwrap_or_default();
            if !cols.contains(&"verification_status".to_string()) {
                issues.push(Issue {
                    path: d.path.clone(),
                    severity: "INFO_EXPECTED_SCHEMA_SPLIT".to_string(),
                    issue: "runtime evolution_genes has no verification_status".to_string(),
                    recommendation: "do not query verification_status on runtime lifecycle DB; use state/gene_lifecycle or intake DB".to_string(),
                });
            }
        }
    }
    let has_runtime = dbs.iter().any(|d| d.schema_role == "runtime_lifecycle_db");
    let has_intake = dbs.iter().any(|d| d.schema_role == "intake_knowledge_db");
    let status = if has_runtime && has_intake {
        "PASS_DUAL_CANONICAL_SCHEMA_MAPPED"
    } else {
        "WATCH_CANONICAL_SCHEMA_INCOMPLETE"
    };
    let audit = Audit {
        schema: "PGGGeneDBUnifiedAuditRust/v1".to_string(),
        generated_at: Utc::now().to_rfc3339(),
        status: status.to_string(),
        dbs,
        issues,
        canonical_model: "dual-canonical: runtime_lifecycle_db for activation/promotion chain; intake_knowledge_db for source_ref/fitness/verification_status/high-throughput metabolism".to_string(),
        boundary: "read-only Rust audit; no DB mutation, no promotion/retire, no AGI/external benchmark claim".to_string(),
    };
    let json = serde_json::to_string_pretty(&audit).unwrap();
    let _ = fs::create_dir_all(OUT_DIR);
    let _ = fs::write(format!("{}/genedb_unified_audit_rust.json", OUT_DIR), &json);
    println!("{}", json);
}
