use chrono::{DateTime, Local, Utc};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::env;
use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

#[derive(Clone, Serialize)]
struct FileInfo {
    path: String,
    size_bytes: u64,
    modified: String,
    age_days: i64,
    kind: String,
    sha256: Option<String>,
}

#[derive(Serialize)]
struct Report {
    schema: &'static str,
    generated_at: String,
    status: &'static str,
    root: String,
    boundary: Vec<&'static str>,
    totals: Totals,
    large_files: Vec<FileInfo>,
    duplicate_candidates: Vec<DuplicateGroup>,
    stale_temp_candidates: Vec<FileInfo>,
    scattered_report_candidates: Vec<FileInfo>,
    next_actions: Vec<&'static str>,
}

#[derive(Serialize)]
struct Totals {
    scanned_files: usize,
    scanned_bytes: u64,
    skipped_dirs: usize,
    large_count: usize,
    duplicate_group_count: usize,
    stale_temp_count: usize,
    scattered_report_count: usize,
}

#[derive(Serialize)]
struct DuplicateGroup {
    sha256: String,
    size_bytes: u64,
    count: usize,
    paths: Vec<String>,
}

fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}
fn is_skip_dir(p: &Path) -> bool {
    let s = p.to_string_lossy();
    [
        "node_modules",
        ".git",
        "target",
        "__pycache__",
        ".venv",
        "venv",
        "Library/Caches",
    ]
    .iter()
    .any(|x| s.contains(x))
}
fn classify(path: &Path) -> String {
    let name = path
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("")
        .to_lowercase();
    if name.ends_with(".zip") || name.ends_with(".tar") || name.ends_with(".gz") {
        "archive".into()
    } else if name.ends_with(".log") {
        "log".into()
    } else if name.ends_with(".md") || name.ends_with(".txt") {
        "text_report".into()
    } else if name.ends_with(".json") || name.ends_with(".jsonl") {
        "json".into()
    } else if name.ends_with(".pyc") || name.contains("tmp") || name.ends_with(".bak") {
        "temp_or_backup".into()
    } else {
        "other".into()
    }
}
fn sha256_file(path: &Path, max_bytes: u64) -> Option<String> {
    let meta = fs::metadata(path).ok()?;
    if meta.len() > max_bytes {
        return None;
    }
    let mut f = File::open(path).ok()?;
    let mut h = Sha256::new();
    let mut buf = [0u8; 8192];
    loop {
        let n = f.read(&mut buf).ok()?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Some(hex::encode(h.finalize()))
}
fn walk(root: &Path, out: &mut Vec<PathBuf>, skipped: &mut usize) {
    let rd = match fs::read_dir(root) {
        Ok(r) => r,
        Err(_) => return,
    };
    for e in rd.flatten() {
        let p = e.path();
        if p.is_dir() {
            if is_skip_dir(&p) {
                *skipped += 1;
                continue;
            }
            walk(&p, out, skipped);
        } else if p.is_file() {
            out.push(p);
        }
    }
}
fn info(path: &Path, hash: bool) -> Option<FileInfo> {
    let meta = fs::metadata(path).ok()?;
    let modified = meta.modified().unwrap_or(SystemTime::UNIX_EPOCH);
    let age_days = SystemTime::now()
        .duration_since(modified)
        .unwrap_or(Duration::from_secs(0))
        .as_secs() as i64
        / 86400;
    let dt: DateTime<Utc> = modified.into();
    Some(FileInfo {
        path: path.to_string_lossy().to_string(),
        size_bytes: meta.len(),
        modified: dt.with_timezone(&Local).to_rfc3339(),
        age_days,
        kind: classify(path),
        sha256: if hash {
            sha256_file(path, 20 * 1024 * 1024)
        } else {
            None
        },
    })
}
fn main() {
    let h = home();
    let root = env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| h.join(".hermes/workspace"));
    let out_dir =
        h.join(".hermes/workspace/pgg-archon-governance/workspace-candidate-report-daily");
    let _ = fs::create_dir_all(&out_dir);
    let mut files = Vec::new();
    let mut skipped = 0usize;
    walk(&root, &mut files, &mut skipped);
    let mut total_bytes = 0u64;
    let mut large = Vec::new();
    let mut stale = Vec::new();
    let mut scattered = Vec::new();
    let mut hash_map: HashMap<String, Vec<FileInfo>> = HashMap::new();
    for p in &files {
        if let Some(meta) = fs::metadata(p).ok() {
            total_bytes += meta.len();
        }
        let kind = classify(p);
        let i = match info(
            p,
            matches!(
                kind.as_str(),
                "text_report" | "json" | "archive" | "temp_or_backup"
            ),
        ) {
            Some(v) => v,
            None => continue,
        };
        if i.size_bytes >= 25 * 1024 * 1024 {
            large.push(i.clone());
        }
        if i.age_days >= 30 && (i.kind == "temp_or_backup" || i.kind == "log") {
            stale.push(i.clone());
        }
        let ps = i.path.to_lowercase();
        if (ps.ends_with(".md") || ps.ends_with(".txt"))
            && (ps.contains("report")
                || ps.contains("audit")
                || ps.contains("报告")
                || ps.contains("审计"))
            && !ps.contains("references/")
        {
            scattered.push(i.clone());
        }
        if let Some(hs) = &i.sha256 {
            hash_map.entry(hs.clone()).or_default().push(i);
        }
    }
    large.sort_by_key(|x| std::cmp::Reverse(x.size_bytes));
    stale.sort_by_key(|x| std::cmp::Reverse(x.age_days));
    scattered.sort_by_key(|x| std::cmp::Reverse(x.size_bytes));
    large.truncate(50);
    stale.truncate(80);
    scattered.truncate(80);
    let mut dups: Vec<DuplicateGroup> = hash_map
        .into_iter()
        .filter_map(|(sha, v)| {
            if v.len() >= 2 {
                Some(DuplicateGroup {
                    sha256: sha,
                    size_bytes: v[0].size_bytes,
                    count: v.len(),
                    paths: v.into_iter().map(|x| x.path).collect(),
                })
            } else {
                None
            }
        })
        .collect();
    dups.sort_by_key(|g| std::cmp::Reverse(g.size_bytes * g.count as u64));
    dups.truncate(50);
    let report = Report {
        schema: "pgg_workspace_candidate_report/v1",
        generated_at: Local::now().to_rfc3339(),
        status: "PASS_READ_ONLY_CANDIDATES",
        root: root.to_string_lossy().to_string(),
        boundary: vec![
            "read-only",
            "no delete",
            "no move",
            "no archive mutation",
            "candidate list only",
            "daily launchd allowed by user adjudication C3",
        ],
        totals: Totals {
            scanned_files: files.len(),
            scanned_bytes: total_bytes,
            skipped_dirs: skipped,
            large_count: large.len(),
            duplicate_group_count: dups.len(),
            stale_temp_count: stale.len(),
            scattered_report_count: scattered.len(),
        },
        large_files: large,
        duplicate_candidates: dups,
        stale_temp_candidates: stale,
        scattered_report_candidates: scattered,
        next_actions: vec![
            "review candidates manually",
            "convert approved items into allowlist cleanup plan",
            "backup before any future move/delete",
            "do not treat candidates as deletion approval",
        ],
    };
    let json = serde_json::to_string_pretty(&report).unwrap();
    let latest = out_dir.join("latest.json");
    let dated = out_dir.join(format!(
        "candidate-report-{}.json",
        Local::now().format("%Y%m%d-%H%M%S")
    ));
    fs::write(&latest, &json).unwrap();
    fs::write(&dated, &json).unwrap();
    let mut md = String::new();
    md.push_str("# Workspace Candidate Report Daily\n\n");
    md.push_str(&format!(
        "- generated_at: `{}`\n- status: `{}`\n- root: `{}`\n\n",
        report.generated_at, report.status, report.root
    ));
    md.push_str(&format!("## Totals\n\n- scanned_files: {}\n- scanned_bytes: {}\n- skipped_dirs: {}\n- large: {}\n- duplicate_groups: {}\n- stale_temp: {}\n- scattered_reports: {}\n\n", report.totals.scanned_files, report.totals.scanned_bytes, report.totals.skipped_dirs, report.totals.large_count, report.totals.duplicate_group_count, report.totals.stale_temp_count, report.totals.scattered_report_count));
    md.push_str("## Boundary\n\n只读候选清单；不删除、不移动、不归档。后续清理必须 allowlist + backup + readback。\n");
    fs::write(out_dir.join("latest.md"), md).unwrap();
    println!("{}", json);
}
