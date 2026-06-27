use anyhow::{anyhow, Context, Result};
use chrono::Local;
use rusqlite::{params, Connection, OptionalExtension};
use serde::Deserialize;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[derive(Debug, Deserialize)]
struct OffspringEntry {
    pid_a: i64,
    pid_b: i64,
    name_a: String,
    name_b: String,
    quality_avg: f64,
    code: String,
    #[serde(default)]
    review_channel: Option<String>,
}

#[derive(Debug, Deserialize)]
struct InputFile {
    #[serde(default)]
    entries: Vec<OffspringEntry>,
}

fn now() -> String {
    Local::now().format("%Y-%m-%dT%H:%M:%S%z").to_string()
}

fn default_db() -> PathBuf {
    let home = env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string());
    PathBuf::from(home).join(".hermes/data/pgg_archon.db")
}

fn parse_args() -> Result<(PathBuf, PathBuf, bool)> {
    let mut input: Option<PathBuf> = None;
    let mut db = default_db();
    let mut dry_run = false;
    let mut args = env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--input" => input = Some(PathBuf::from(args.next().ok_or_else(|| anyhow!("--input requires path"))?)),
            "--db" => db = PathBuf::from(args.next().ok_or_else(|| anyhow!("--db requires path"))?),
            "--dry-run" => dry_run = true,
            "--help" | "-h" => {
                println!("Usage: pgg-fusion-session-consumer --input offspring.json [--db pgg_archon.db] [--dry-run]");
                std::process::exit(0);
            }
            other => return Err(anyhow!("unknown arg: {}", other)),
        }
    }
    Ok((input.ok_or_else(|| anyhow!("missing --input"))?, db, dry_run))
}

fn ast_check(code: &str) -> Result<()> {
    let mut child = Command::new("python3")
        .arg("-c")
        .arg("import ast,sys; ast.parse(sys.stdin.read()); print('AST_OK')")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .context("spawn python3 ast checker")?;
    use std::io::Write;
    child.stdin.as_mut().ok_or_else(|| anyhow!("missing stdin"))?.write_all(code.as_bytes())?;
    let out = child.wait_with_output()?;
    if !out.status.success() {
        return Err(anyhow!("ast_check_failed: {}", String::from_utf8_lossy(&out.stderr)));
    }
    Ok(())
}

fn backup_db(db: &Path) -> Result<PathBuf> {
    let backup = db.with_extension(format!("db.bak.{}", Local::now().format("%Y%m%d%H%M%S-fusion-session-consumer")));
    fs::copy(db, &backup).with_context(|| format!("backup db {:?} -> {:?}", db, backup))?;
    Ok(backup)
}

fn load_entries(path: &Path) -> Result<Vec<OffspringEntry>> {
    let text = fs::read_to_string(path).with_context(|| format!("read input {:?}", path))?;
    if let Ok(wrapper) = serde_json::from_str::<InputFile>(&text) {
        if !wrapper.entries.is_empty() { return Ok(wrapper.entries); }
    }
    let entries: Vec<OffspringEntry> = serde_json::from_str(&text).context("parse offspring json as entries array or {entries}")?;
    Ok(entries)
}

fn main() -> Result<()> {
    let (input, db, dry_run) = parse_args()?;
    let entries = load_entries(&input)?;
    if entries.is_empty() { return Err(anyhow!("no entries")); }
    for e in &entries {
        if e.code.len() < 100 { return Err(anyhow!("offspring code too short for {} x {}", e.name_a, e.name_b)); }
        ast_check(&e.code).with_context(|| format!("ast check {} x {}", e.name_a, e.name_b))?;
    }
    let backup = if dry_run { None } else { Some(backup_db(&db)?) };
    let conn = Connection::open(&db).with_context(|| format!("open db {:?}", db))?;
    let before: i64 = conn.query_row("SELECT COUNT(*) FROM genes WHERE pattern_type='llm_fusion'", [], |r| r.get(0))?;
    let mut written = 0_i64;
    let mut results = Vec::<serde_json::Value>::new();
    if !dry_run {
        for e in &entries {
            let max_id: i64 = conn.query_row("SELECT COALESCE(MAX(id),0) FROM genes", [], |r| r.get(0))?;
            let offspring_id = max_id + 1;
            let quality = (e.quality_avg * 0.9 * 100.0).round() / 100.0;
            let name = format!("llm_fusion_{}_{}", e.name_a.chars().take(20).collect::<String>(), e.name_b.chars().take(20).collect::<String>()).replace(' ', "_").chars().take(60).collect::<String>();
            let ts = now();
            let inserted: usize = conn.execute(
                "INSERT OR IGNORE INTO genes (id,name,pattern_type,source_repo,code_snippet,quality_score,extracted_at) VALUES (?1,?2,'llm_fusion','fusion_session_consumer',?3,?4,?5)",
                params![offspring_id, name, e.code, quality, ts],
            )?;
            if inserted == 0 { continue; }
            conn.execute("INSERT OR IGNORE INTO gene_lifecycle (gene_id,state,candidate_at,quality_score) VALUES (?1,'candidate',?2,?3)", params![offspring_id, ts, quality])?;
            conn.execute(
                "INSERT OR IGNORE INTO evolution_genes (gene_id,parent_gene_id,state,generation,mutation_vector,fitness_before,fitness_after,created_at,review_status,review_channel) VALUES (?1,?2,'candidate',1,'llm_fusion',NULL,?3,?4,'pending',?5)",
                params![offspring_id, format!("{},{}", e.pid_a, e.pid_b), quality, ts, e.review_channel.clone().unwrap_or_else(|| "session_consumer".to_string())],
            )?;
            written += 1;
            results.push(serde_json::json!({"offspring_id": offspring_id, "parents": [e.pid_a, e.pid_b], "quality": quality, "code_len": e.code.len()}));
        }
    }
    let after: i64 = conn.query_row("SELECT COUNT(*) FROM genes WHERE pattern_type='llm_fusion'", [], |r| r.get(0))?;
    let latest: Option<serde_json::Value> = conn.query_row(
        "SELECT g.id,g.name,g.quality_score,LENGTH(g.code_snippet),eg.parent_gene_id,eg.review_status FROM genes g LEFT JOIN evolution_genes eg ON eg.gene_id=g.id WHERE g.pattern_type='llm_fusion' ORDER BY g.id DESC LIMIT 1",
        [],
        |r| Ok(serde_json::json!({"id": r.get::<_, i64>(0)?, "name": r.get::<_, String>(1)?, "quality": r.get::<_, f64>(2)?, "code_len": r.get::<_, i64>(3)?, "parent_gene_id": r.get::<_, Option<String>>(4)?, "review_status": r.get::<_, Option<String>>(5)?}))
    ).optional()?;
    println!("{}", serde_json::to_string_pretty(&serde_json::json!({
        "schema": "pgg_fusion_session_consumer/v1",
        "created_at": now(),
        "dry_run": dry_run,
        "input": input,
        "db": db,
        "backup": backup,
        "entries": entries.len(),
        "before_llm_fusion": before,
        "written": written,
        "after_llm_fusion": after,
        "results": results,
        "latest": latest,
        "boundary": "local DB writeback only; offspring remains pending candidate; no promotion/approval claim"
    }))?);
    Ok(())
}
