use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::HashSet;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

const SCHEMA: &str = "PGGSourceRefRepairAccelerator/v0.1";
const BOUNDARY: &str = "SOURCE_REF_REPAIR_PROPOSAL_FIRST_BACKUP_DB_HIGH_CONFIDENCE_LOW_ENGINEERING_ONLY_NO_LEGAL_SECURITY_CREDENTIAL_PROVIDER_SCHEDULER_AUTO_REPAIR";

#[derive(Debug, Clone, Serialize, Deserialize)]
struct DebtRow {
    gene_id: String,
    gene_name: String,
    status: String,
    verification_status: String,
    evidence_grade: String,
    risk_lane: String,
    old_ref: Option<String>,
    debt_class: String,
    source_refs_json: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct RepairProposal {
    gene_id: String,
    gene_name: String,
    old_ref: String,
    new_ref: String,
    confidence: f64,
    risk_lane: String,
    action: String,
    evidence: Vec<String>,
    debt_class: String,
}

fn now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

fn parse_arg(args: &[String], key: &str) -> Option<String> {
    args.windows(2).find(|w| w[0] == key).map(|w| w[1].clone())
}

fn has_flag(args: &[String], key: &str) -> bool {
    args.iter().any(|a| a == key)
}

fn source_file_from_json(raw: &str) -> Option<String> {
    let v: Value = serde_json::from_str(raw).ok()?;
    v.get("source_file")
        .and_then(|x| x.as_str())
        .map(|s| s.to_string())
}

fn classify_risk(text: &str) -> String {
    let t = text.to_lowercase();
    let high = [
        "legal",
        "law",
        "case",
        "案件",
        "法律",
        "credential",
        "token",
        "secret",
        "provider",
        "config",
        "scheduler",
        "security",
        "auth",
        "oauth",
        "生产",
        "办案",
    ];
    if high.iter().any(|w| t.contains(w)) {
        if ["legal", "law", "case", "案件", "法律", "办案"]
            .iter()
            .any(|w| t.contains(w))
        {
            return "legal".into();
        }
        if ["credential", "token", "secret", "auth", "oauth"]
            .iter()
            .any(|w| t.contains(w))
        {
            return "credential".into();
        }
        return "security_or_config".into();
    }
    "low_engineering".into()
}

fn classify_debt(old_ref: &Option<String>, source_refs_json: &str) -> String {
    match old_ref {
        None => {
            if source_refs_json.trim().is_empty()
                || source_refs_json.trim() == "{}"
                || source_refs_json.trim() == "[]"
            {
                "missing_source_ref".into()
            } else {
                "invalid_reference".into()
            }
        }
        Some(p) => {
            let path = Path::new(p);
            if path.exists() {
                "present_but_marked_missing".into()
            } else if p.contains("/var/") || p.contains("/tmp/") {
                "local_only_artifact".into()
            } else {
                "missing_file".into()
            }
        }
    }
}

fn read_debt_rows(db_path: &Path, limit: usize) -> Result<Vec<DebtRow>, String> {
    let con = Connection::open(db_path).map_err(|e| format!("open db: {e}"))?;
    let mut stmt = con
        .prepare(
            "SELECT CAST(eg.gene_id AS TEXT),
                COALESCE(g.name, 'gene_' || eg.gene_id),
                eg.state,
                eg.review_status,
                CAST(COALESCE(eg.review_confidence, '') AS TEXT),
                COALESCE(eg.evidence_ref, ''),
                COALESCE(eg.mutation_vector, ''),
                COALESCE(eg.review_reason, ''),
                COALESCE(eg.review_channel, ''),
                COALESCE(g.code_snippet, '')
         FROM evolution_genes eg
         LEFT JOIN genes g ON eg.gene_id = g.id
         WHERE lower(eg.state) LIKE '%blocked%'
            OR lower(COALESCE(eg.review_status, '')) LIKE '%source_missing%'
            OR lower(COALESCE(eg.review_status, '')) LIKE '%blocked_source%'
            OR lower(COALESCE(eg.review_reason, '')) LIKE '%source missing%'
            OR COALESCE(eg.evidence_ref, '') LIKE '%source_file%'
         ORDER BY eg.created_at DESC LIMIT ?1",
        )
        .map_err(|e| format!("prepare inventory: {e}"))?;
    let rows = stmt
        .query_map(params![limit as i64], |row| {
            let source_refs_json: String = row.get::<_, Option<String>>(5)?.unwrap_or_default();
            let old_ref = source_file_from_json(&source_refs_json);
            let status: String = row.get::<_, Option<String>>(2)?.unwrap_or_default();
            let verification_status: String = row.get::<_, Option<String>>(3)?.unwrap_or_default();
            let evidence_grade: String = row.get::<_, Option<String>>(4)?.unwrap_or_default();
            let text = format!(
                "{} {} {} {} {} {}",
                row.get::<_, Option<String>>(1)?.unwrap_or_default(),
                row.get::<_, Option<String>>(6)?.unwrap_or_default(),
                row.get::<_, Option<String>>(7)?.unwrap_or_default(),
                row.get::<_, Option<String>>(8)?.unwrap_or_default(),
                row.get::<_, Option<String>>(9)?.unwrap_or_default(),
                source_refs_json
            );
            Ok(DebtRow {
                gene_id: row.get::<_, String>(0)?,
                gene_name: row.get::<_, String>(1)?,
                status,
                verification_status,
                evidence_grade,
                risk_lane: classify_risk(&text),
                debt_class: classify_debt(&old_ref, &source_refs_json),
                old_ref,
                source_refs_json,
            })
        })
        .map_err(|e| format!("query inventory: {e}"))?;
    let mut out = Vec::new();
    for r in rows {
        out.push(r.map_err(|e| format!("row inventory: {e}"))?);
    }
    Ok(out
        .into_iter()
        .filter(|r| {
            r.debt_class != "present_but_marked_missing"
                || r.verification_status.contains("source_missing")
        })
        .collect())
}

fn write_json(path: &Path, value: &Value) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create parent: {e}"))?;
    }
    fs::write(path, serde_json::to_string_pretty(value).unwrap())
        .map_err(|e| format!("write json {path:?}: {e}"))
}

fn collect_matching_files(root: &Path, basename: &str, max: usize) -> Vec<String> {
    let mut found = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    let ignored: HashSet<&str> = [
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "target",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
    ]
    .into_iter()
    .collect();
    while let Some(dir) = stack.pop() {
        if found.len() >= max {
            break;
        }
        let entries = match fs::read_dir(&dir) {
            Ok(e) => e,
            Err(_) => continue,
        };
        for entry in entries.flatten() {
            let p = entry.path();
            let name = p.file_name().and_then(|s| s.to_str()).unwrap_or("");
            if p.is_dir() {
                if !ignored.contains(name) {
                    stack.push(p);
                }
            } else if name == basename {
                found.push(p.to_string_lossy().to_string());
                if found.len() >= max {
                    break;
                }
            }
        }
    }
    found
}

fn git_history_hits(repo_root: &Path, basename: &str, max: usize) -> Vec<String> {
    let output = Command::new("git")
        .arg("log")
        .arg("--all")
        .arg("--name-only")
        .arg("--pretty=format:")
        .current_dir(repo_root)
        .output();
    let Ok(out) = output else {
        return vec![];
    };
    let text = String::from_utf8_lossy(&out.stdout);
    let mut seen = HashSet::new();
    let mut hits = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if line.ends_with(basename) && seen.insert(line.to_string()) {
            hits.push(line.to_string());
            if hits.len() >= max {
                break;
            }
        }
    }
    hits
}

fn git_last_commit_for_path(repo_root: &Path, rel_path: &str) -> Option<String> {
    let out = Command::new("git")
        .arg("log")
        .arg("--all")
        .arg("-n")
        .arg("1")
        .arg("--format=%H")
        .arg("--")
        .arg(rel_path)
        .current_dir(repo_root)
        .output()
        .ok()?;
    let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
    if s.is_empty() {
        None
    } else {
        Some(s)
    }
}

fn archive_git_blob(repo_root: &Path, rel_path: &str, outdir: &Path) -> Option<(String, String)> {
    let commit = git_last_commit_for_path(repo_root, rel_path)?;
    let spec = format!("{}:{}", commit, rel_path);
    let out = Command::new("git")
        .arg("show")
        .arg(&spec)
        .current_dir(repo_root)
        .output()
        .ok()?;
    if !out.status.success() || out.stdout.is_empty() {
        return None;
    }
    let archive_dir = outdir.join("historical_sources");
    fs::create_dir_all(&archive_dir).ok()?;
    let safe = rel_path.replace('/', "__");
    let target = archive_dir.join(format!("{}__{}", &commit[..12.min(commit.len())], safe));
    fs::write(&target, out.stdout).ok()?;
    Some((target.to_string_lossy().to_string(), commit))
}

fn text_reference_hits(root: &Path, needles: &[String], max: usize) -> Vec<String> {
    let mut hits = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    let ignored: HashSet<&str> = [
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "target",
        "__pycache__",
    ]
    .into_iter()
    .collect();
    while let Some(dir) = stack.pop() {
        if hits.len() >= max {
            break;
        }
        let entries = match fs::read_dir(&dir) {
            Ok(e) => e,
            Err(_) => continue,
        };
        for entry in entries.flatten() {
            let p = entry.path();
            let name = p.file_name().and_then(|s| s.to_str()).unwrap_or("");
            if p.is_dir() {
                if !ignored.contains(name) {
                    stack.push(p);
                }
            } else if matches!(
                p.extension().and_then(|s| s.to_str()),
                Some("md" | "json" | "jsonl" | "txt" | "py")
            ) {
                if let Ok(meta) = fs::metadata(&p) {
                    if meta.len() > 2_000_000 {
                        continue;
                    }
                }
                if let Ok(text) = fs::read_to_string(&p) {
                    if needles.iter().any(|n| !n.is_empty() && text.contains(n)) {
                        hits.push(p.to_string_lossy().to_string());
                        if hits.len() >= max {
                            break;
                        }
                    }
                }
            }
        }
    }
    hits
}

fn choose_candidate(
    row: &DebtRow,
    repo_root: &Path,
    workspace_root: &Path,
    skills_root: &Path,
    outdir: &Path,
) -> RepairProposal {
    let old = row.old_ref.clone().unwrap_or_default();
    let basename = Path::new(&old)
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("")
        .to_string();
    let mut evidence = Vec::new();
    let mut new_ref = String::new();
    let mut confidence = 0.0;
    if !basename.is_empty() {
        let current_repo = collect_matching_files(repo_root, &basename, 5);
        if let Some(first) = current_repo.first() {
            new_ref = first.clone();
            confidence = if current_repo.len() == 1 { 0.92 } else { 0.78 };
            evidence.push(format!("repo_current_path_match:{}", first));
        }
        if new_ref.is_empty() {
            let current_ws = collect_matching_files(workspace_root, &basename, 5);
            if let Some(first) = current_ws.first() {
                new_ref = first.clone();
                confidence = if current_ws.len() == 1 { 0.86 } else { 0.70 };
                evidence.push(format!("workspace_current_path_match:{}", first));
            }
        }
        let history = git_history_hits(repo_root, &basename, 5);
        if new_ref.is_empty() && history.len() == 1 {
            if let Some((archived, commit)) = archive_git_blob(repo_root, &history[0], outdir) {
                new_ref = archived.clone();
                confidence = 0.88;
                evidence.push(format!("git_history_archive:{}:{}", commit, history[0]));
                evidence.push(format!("archived_source_file:{}", archived));
            }
        }
        for h in history {
            evidence.push(format!("git_history_path:{}", h));
        }
        let refs = text_reference_hits(skills_root, &[row.gene_id.clone(), basename.clone()], 5);
        for h in refs {
            evidence.push(format!("skill_or_manifest_reference:{}", h));
        }
    }
    if new_ref.is_empty() {
        new_ref = old.clone();
        evidence.push("no_current_path_candidate_found".into());
    }
    let action =
        if confidence >= 0.85 && row.risk_lane == "low_engineering" && Path::new(&new_ref).exists()
        {
            "REPAIR_EXECUTE_ALLOWED"
        } else {
            "REPAIR_PROPOSAL_ONLY"
        }
        .to_string();
    RepairProposal {
        gene_id: row.gene_id.clone(),
        gene_name: row.gene_name.clone(),
        old_ref: old,
        new_ref,
        confidence,
        risk_lane: row.risk_lane.clone(),
        action,
        evidence,
        debt_class: row.debt_class.clone(),
    }
}

fn inventory(db: &Path, outdir: &Path, limit: usize) -> Result<Value, String> {
    let rows = read_debt_rows(db, limit)?;
    let mut classes = serde_json::Map::new();
    for r in &rows {
        let n = classes
            .get(&r.debt_class)
            .and_then(|v| v.as_u64())
            .unwrap_or(0)
            + 1;
        classes.insert(r.debt_class.clone(), json!(n));
    }
    let payload = json!({"schema": SCHEMA, "mode":"inventory", "db_path": db, "debt_count": rows.len(), "debt_classes": classes, "rows": rows, "db_mutation": false, "boundary": BOUNDARY});
    write_json(&outdir.join("source_ref_debt_inventory.json"), &payload)?;
    Ok(payload)
}

fn proposal(
    db: &Path,
    outdir: &Path,
    repo_root: &Path,
    workspace_root: &Path,
    skills_root: &Path,
    limit: usize,
) -> Result<Value, String> {
    let rows = read_debt_rows(db, limit)?;
    let proposals: Vec<RepairProposal> = rows
        .iter()
        .map(|r| choose_candidate(r, repo_root, workspace_root, skills_root, outdir))
        .collect();
    let allowed = proposals
        .iter()
        .filter(|p| p.action == "REPAIR_EXECUTE_ALLOWED")
        .count();
    let payload = json!({"schema": SCHEMA, "mode":"proposal", "proposal_count": proposals.len(), "execute_allowed_count": allowed, "proposals": proposals, "db_mutation": false, "boundary": BOUNDARY});
    write_json(&outdir.join("source_ref_repair_proposal.json"), &payload)?;
    Ok(payload)
}

fn sha256_path(path: &Path) -> Result<String, String> {
    let bytes = fs::read(path).map_err(|e| format!("read for sha256: {e}"))?;
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    Ok(format!("{:x}", hasher.finalize()))
}

fn execute_proposals(
    db: &Path,
    proposal_path: &Path,
    outdir: &Path,
    execute: bool,
) -> Result<Value, String> {
    fs::create_dir_all(outdir).map_err(|e| format!("create outdir: {e}"))?;
    let raw = fs::read_to_string(proposal_path).map_err(|e| format!("read proposal: {e}"))?;
    let v: Value = serde_json::from_str(&raw).map_err(|e| format!("parse proposal: {e}"))?;
    let proposals: Vec<RepairProposal> =
        serde_json::from_value(v.get("proposals").cloned().unwrap_or_else(|| json!([])))
            .map_err(|e| format!("proposal array: {e}"))?;
    let selected: Vec<RepairProposal> = proposals
        .into_iter()
        .filter(|p| {
            p.action == "REPAIR_EXECUTE_ALLOWED"
                && p.risk_lane == "low_engineering"
                && Path::new(&p.new_ref).exists()
        })
        .collect();
    let backup = outdir.join(format!(
        "{}.bak.phase14_sourceref_{}",
        db.file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("genedb.sqlite3"),
        now_epoch()
    ));
    let mut changed = 0usize;
    if execute && !selected.is_empty() {
        fs::copy(db, &backup).map_err(|e| format!("backup db: {e}"))?;
        let con = Connection::open(db).map_err(|e| format!("open db execute: {e}"))?;
        for p in &selected {
            let old_raw: String = con
                .query_row(
                    "SELECT COALESCE(evidence_ref, '') FROM evolution_genes WHERE gene_id=?1",
                    params![p.gene_id],
                    |r| r.get::<_, Option<String>>(0),
                )
                .map_err(|e| format!("fetch evidence_ref {}: {e}", p.gene_id))?
                .unwrap_or_else(|| "{}".into());
            let mut refs: Value = serde_json::from_str(&old_raw).unwrap_or_else(|_| json!({}));
            if !refs.is_object() {
                refs = json!({"legacy_source_refs_json": old_raw});
            }
            refs["source_file"] = json!(p.new_ref);
            refs["source_ref_repair"] = json!({"phase":"Phase14","old_ref":p.old_ref,"confidence":p.confidence,"evidence":p.evidence,"repaired_at_epoch":now_epoch(),"boundary":BOUNDARY});
            let marker = format!(
                "phase14_source_ref_repaired:{}",
                proposal_path.to_string_lossy()
            );
            con.execute("UPDATE evolution_genes SET evidence_ref=?1, review_status=CASE WHEN COALESCE(review_status, '') LIKE '%' || ?2 || '%' THEN review_status ELSE COALESCE(review_status, '') || ';' || ?2 END WHERE gene_id=?3", params![serde_json::to_string(&refs).unwrap(), marker, p.gene_id]).map_err(|e| format!("update {}: {e}", p.gene_id))?;
            changed += 1;
        }
    }
    let result = json!({"schema": SCHEMA, "mode":"execute", "execute_requested": execute, "db_mutation": execute && changed>0, "selected_count": selected.len(), "repaired_count": changed, "backup_path": if execute && changed>0 { Some(backup.to_string_lossy().to_string()) } else { None }, "backup_sha256": if execute && changed>0 { Some(sha256_path(&backup)?) } else { None }, "selected": selected, "boundary": BOUNDARY});
    write_json(
        &outdir.join("source_ref_repair_execute_result.json"),
        &result,
    )?;
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(name: &str) -> PathBuf {
        let p = env::temp_dir().join(format!(
            "pgg_sourceref_repair_test_{}_{}",
            name,
            now_epoch()
        ));
        fs::create_dir_all(&p).unwrap();
        p
    }

    fn fixture_db(dir: &Path, missing_ref: &str) -> PathBuf {
        let db = dir.join("genes.sqlite3");
        let con = Connection::open(&db).unwrap();
        con.execute_batch("CREATE TABLE genes(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,pattern_type TEXT,source_repo TEXT,code_snippet TEXT,quality_score REAL DEFAULT 0.0,extracted_at TEXT NOT NULL);CREATE TABLE evolution_genes(id INTEGER PRIMARY KEY AUTOINCREMENT,gene_id INTEGER NOT NULL,parent_gene_id INTEGER,state TEXT NOT NULL,generation INTEGER DEFAULT 0,mutation_vector TEXT,fitness_before REAL,fitness_after REAL,promoted_at TEXT,retired_at TEXT,evidence_ref TEXT,created_at TEXT NOT NULL,review_status TEXT DEFAULT 'pending',review_channel TEXT,review_confidence INTEGER,review_reason TEXT,reviewed_at TEXT,FOREIGN KEY (gene_id) REFERENCES genes(id));").unwrap();
        con.execute(
            "INSERT INTO genes(id,name,extracted_at) VALUES (1,'Sample Gate','2026-06-14')",
            [],
        )
        .unwrap();
        con.execute("INSERT INTO evolution_genes(gene_id,state,evidence_ref,created_at,review_status,review_confidence,review_reason,mutation_vector) VALUES (1,'blocked',?1,'2026-06-14','blocked_source_missing_phase13',0,'source missing','')", params![json!({"source_file": missing_ref}).to_string()]).unwrap();
        db
    }

    #[test]
    fn inventory_classifies_missing_source_debt() {
        let dir = temp_dir("inventory");
        let db = fixture_db(&dir, "/old/path/sample_gate.py");
        let out = dir.join("out");
        let result = inventory(&db, &out, 10).unwrap();
        assert_eq!(result["mode"], "inventory");
        assert_eq!(result["debt_count"], 1);
        assert_eq!(result["debt_classes"]["missing_file"], 1);
        assert!(out.join("source_ref_debt_inventory.json").exists());
    }

    #[test]
    fn proposal_and_execute_repairs_high_confidence_low_risk_source_ref() {
        let dir = temp_dir("execute");
        let repo = dir.join("repo");
        let agent = repo.join("agent");
        fs::create_dir_all(&agent).unwrap();
        let new_file = agent.join("sample_gate.py");
        fs::write(&new_file, "print('ok')\n").unwrap();
        Command::new("git")
            .arg("init")
            .current_dir(&repo)
            .output()
            .unwrap();
        let db = fixture_db(&dir, "/old/path/sample_gate.py");
        let out = dir.join("out");
        let p = proposal(&db, &out, &repo, &dir, &dir, 10).unwrap();
        assert_eq!(p["execute_allowed_count"], 1);
        let pp = out.join("source_ref_repair_proposal.json");
        let executed = execute_proposals(&db, &pp, &out.join("exec"), true).unwrap();
        assert_eq!(executed["db_mutation"], true);
        assert_eq!(executed["repaired_count"], 1);
        let con = Connection::open(&db).unwrap();
        let raw: String = con
            .query_row(
                "SELECT evidence_ref FROM evolution_genes WHERE gene_id=1",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert!(raw.contains("sample_gate.py"));
        assert!(raw.contains("source_ref_repair"));
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mode = parse_arg(&args, "--mode").unwrap_or_else(|| "inventory".into());
    let db = PathBuf::from(parse_arg(&args, "--db").unwrap_or_else(|| {
        format!(
            "{}/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3",
            env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".into())
        )
    }));
    let outdir = PathBuf::from(parse_arg(&args, "--outdir").unwrap_or_else(|| format!("{}/.hermes/workspace/pgg-archon-governance/metabolic-evolution-phase14-sourceref-repair/{}", env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".into()), now_epoch())));
    let limit: usize = parse_arg(&args, "--limit")
        .and_then(|s| s.parse().ok())
        .unwrap_or(50)
        .min(200);
    let repo_root = PathBuf::from(parse_arg(&args, "--repo-root").unwrap_or_else(|| {
        format!(
            "{}/.hermes/hermes-agent",
            env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".into())
        )
    }));
    let workspace_root = PathBuf::from(parse_arg(&args, "--workspace-root").unwrap_or_else(|| {
        format!(
            "{}/.hermes/workspace",
            env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".into())
        )
    }));
    let skills_root = PathBuf::from(parse_arg(&args, "--skills-root").unwrap_or_else(|| {
        format!(
            "{}/.hermes/skills",
            env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".into())
        )
    }));
    let result = match mode.as_str() {
        "inventory" => inventory(&db, &outdir, limit),
        "proposal" => proposal(
            &db,
            &outdir,
            &repo_root,
            &workspace_root,
            &skills_root,
            limit,
        ),
        "execute" => {
            let pp = parse_arg(&args, "--proposal")
                .map(PathBuf::from)
                .unwrap_or_else(|| outdir.join("source_ref_repair_proposal.json"));
            execute_proposals(&db, &pp, &outdir, has_flag(&args, "--execute"))
        }
        _ => Err(format!("unknown mode: {mode}")),
    };
    match result {
        Ok(v) => println!("{}", serde_json::to_string_pretty(&v).unwrap()),
        Err(e) => {
            eprintln!("ERROR: {e}");
            std::process::exit(1);
        }
    }
}
