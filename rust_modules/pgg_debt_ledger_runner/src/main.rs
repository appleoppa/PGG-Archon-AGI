use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct DebtEntry {
    schema: String,
    id: String,
    created_at_epoch: u64,
    updated_at_epoch: u64,
    source: String,
    debt_type: String,
    severity: String,
    summary: String,
    evidence_path: String,
    status: String,
    next_action: String,
    requires_user: bool,
    boundary: String,
}

#[derive(Debug, Serialize)]
struct DailyReport {
    schema: String,
    generated_at_epoch: u64,
    report_date_local: String,
    yesterday_local: String,
    classification: String,
    ledger_path: String,
    latest_path: String,
    open_total: usize,
    opened_yesterday: usize,
    resolved_yesterday: usize,
    pending_user_decision: usize,
    open_items: Vec<DebtEntry>,
    yesterday_items: Vec<DebtEntry>,
    boundaries: Vec<String>,
}

fn home() -> PathBuf {
    env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/Users/appleoppa"))
}
fn now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}
fn sha16(s: &str) -> String {
    let h = Sha256::digest(s.as_bytes());
    hex::encode(h)[..16].to_string()
}
fn date_cmd(args: &[&str]) -> String {
    Command::new("/bin/date")
        .args(args)
        .output()
        .ok()
        .and_then(|o| {
            if o.status.success() {
                Some(String::from_utf8_lossy(&o.stdout).trim().to_string())
            } else {
                None
            }
        })
        .unwrap_or_else(|| "unknown-date".to_string())
}
fn local_ymd(epoch: u64) -> String {
    date_cmd(&["-r", &epoch.to_string(), "+%Y-%m-%d"])
}
fn append_entry(ledger: &Path, e: &DebtEntry) {
    let mut content = if ledger.exists() {
        fs::read_to_string(ledger).unwrap_or_default()
    } else {
        String::new()
    };
    if !content.is_empty() && !content.ends_with('\n') {
        content.push('\n');
    }
    content.push_str(&serde_json::to_string(e).unwrap());
    content.push('\n');
    fs::write(ledger, content).expect("write ledger");
}
fn read_entries(ledger: &Path) -> Vec<DebtEntry> {
    if !ledger.exists() {
        return vec![];
    }
    let f = match fs::File::open(ledger) {
        Ok(f) => f,
        Err(_) => return vec![],
    };
    BufReader::new(f)
        .lines()
        .filter_map(|line| {
            let line = line.ok()?;
            if line.trim().is_empty() {
                return None;
            }
            serde_json::from_str::<DebtEntry>(&line).ok()
        })
        .collect()
}
fn latest_by_id(entries: Vec<DebtEntry>) -> Vec<DebtEntry> {
    let mut map = std::collections::BTreeMap::<String, DebtEntry>::new();
    for e in entries {
        match map.get(&e.id) {
            Some(old) if old.updated_at_epoch > e.updated_at_epoch => {}
            _ => {
                map.insert(e.id.clone(), e);
            }
        }
    }
    map.into_values().collect()
}
fn make_entry(
    source: &str,
    debt_type: &str,
    severity: &str,
    summary: &str,
    evidence_path: &str,
    status: &str,
    next_action: &str,
    requires_user: bool,
) -> DebtEntry {
    let t = now_epoch();
    let id = format!(
        "DEBT-{}",
        sha16(&format!("{}:{}:{}", source, debt_type, summary)).to_uppercase()
    );
    DebtEntry {
        schema: "pgg_debt_ledger/v1".to_string(),
        id,
        created_at_epoch: t,
        updated_at_epoch: t,
        source: source.to_string(),
        debt_type: debt_type.to_string(),
        severity: severity.to_string(),
        summary: summary.to_string(),
        evidence_path: evidence_path.to_string(),
        status: status.to_string(),
        next_action: next_action.to_string(),
        requires_user,
        boundary: "Debt ledger records pending/blocked/watch items only; it does not write MEMORY/USER or mutate core runtime.".to_string(),
    }
}
fn print_usage() {
    eprintln!("Usage: pgg-debt-ledger-runner [daily|seed-adjudication|add <type> <severity> <status> <requires_user:true|false> <summary> <next_action> <evidence_path>]");
}
fn main() {
    let h = home();
    let base = h.join(".hermes/workspace/pgg-archon-governance/debt-ledger");
    fs::create_dir_all(&base).expect("create debt-ledger dir");
    let ledger = base.join("debt_ledger.jsonl");
    let latest = base.join("latest_daily_report.json");
    let md = base.join("DAILY_DEBT_REPORT.md");
    let args: Vec<String> = env::args().collect();
    let mode = args.get(1).map(|s| s.as_str()).unwrap_or("daily");
    match mode {
        "seed-adjudication" => {
            let evidence = h.join(".hermes/workspace/feishu-doc-local-comparison/TAPjwl7PeiFeAkkm67mcBqdFnlc-20260618-210339/CONFLICT_DECISION_PACKET.md");
            let e = make_entry(
                "feishu_yifei_adjudication_20260618",
                "SYSTEM_WATCH",
                "P1",
                "D8 heartbeat launchd runner exists as plist but must be proven loaded/runs/readback after repair.",
                &evidence.display().to_string(),
                "open",
                "Run launchd bootstrap/kickstart/readback for heartbeat light and plan rotation runners, then append resolved entry.",
                false,
            );
            append_entry(&ledger, &e);
            println!("{}", serde_json::to_string_pretty(&e).unwrap());
        }
        "add" => {
            if args.len() < 9 {
                print_usage();
                std::process::exit(2);
            }
            let requires_user = args[5].parse::<bool>().unwrap_or(false);
            let e = make_entry(
                "manual_or_runner",
                &args[2],
                &args[3],
                &args[6],
                &args[8],
                &args[4],
                &args[7],
                requires_user,
            );
            append_entry(&ledger, &e);
            println!("{}", serde_json::to_string_pretty(&e).unwrap());
        }
        "daily" => {
            let entries = latest_by_id(read_entries(&ledger));
            let today = date_cmd(&["+%Y-%m-%d"]);
            let yesterday = date_cmd(&["-v-1d", "+%Y-%m-%d"]);
            let mut open: Vec<DebtEntry> = entries
                .iter()
                .filter(|e| e.status == "open" || e.status == "blocked" || e.status == "watch")
                .cloned()
                .collect();
            open.sort_by(|a, b| {
                a.severity
                    .cmp(&b.severity)
                    .then(a.created_at_epoch.cmp(&b.created_at_epoch))
            });
            let yesterday_items: Vec<DebtEntry> = entries
                .iter()
                .filter(|e| {
                    local_ymd(e.updated_at_epoch) == yesterday
                        || local_ymd(e.created_at_epoch) == yesterday
                })
                .cloned()
                .collect();
            let opened_yesterday = yesterday_items
                .iter()
                .filter(|e| e.status == "open" || e.status == "blocked" || e.status == "watch")
                .count();
            let resolved_yesterday = yesterday_items
                .iter()
                .filter(|e| e.status == "resolved")
                .count();
            let pending_user_decision = open.iter().filter(|e| e.requires_user).count();
            let classification = if open.is_empty() {
                "PASS_DEBT_LEDGER_NO_OPEN_ITEMS"
            } else {
                "WATCH_DEBT_LEDGER_OPEN_ITEMS"
            }
            .to_string();
            let report = DailyReport {
                schema: "pgg_debt_ledger_daily_report/v1".to_string(),
                generated_at_epoch: now_epoch(),
                report_date_local: today,
                yesterday_local: yesterday,
                classification,
                ledger_path: ledger.display().to_string(),
                latest_path: latest.display().to_string(),
                open_total: open.len(),
                opened_yesterday,
                resolved_yesterday,
                pending_user_decision,
                open_items: open.clone(),
                yesterday_items,
                boundaries: vec![
                    "Local ledger/report only; no Feishu/external delivery unless separately authorized.".to_string(),
                    "Does not write MEMORY/USER or modify provider/config/scheduler/security.".to_string(),
                    "Daily 07:00 launchd report includes yesterday plus previously open pending items.".to_string(),
                ],
            };
            fs::write(&latest, serde_json::to_string_pretty(&report).unwrap())
                .expect("write latest report");
            let mut m = String::from("# PGG Debt Ledger Daily Report\n\n");
            m.push_str(&format!("- classification: `{}`\n- report_date: `{}`\n- yesterday: `{}`\n- open_total: `{}`\n- opened_yesterday: `{}`\n- resolved_yesterday: `{}`\n- pending_user_decision: `{}`\n\n", report.classification, report.report_date_local, report.yesterday_local, report.open_total, report.opened_yesterday, report.resolved_yesterday, report.pending_user_decision));
            m.push_str("## Open / Pending Items\n\n");
            if open.is_empty() {
                m.push_str("- None\n");
            } else {
                for e in &open {
                    m.push_str(&format!(
                        "- `{}` `{}` `{}` — {} | next: {}\n",
                        e.id, e.severity, e.status, e.summary, e.next_action
                    ));
                }
            }
            m.push_str("\n## Boundaries\n\n");
            for b in &report.boundaries {
                m.push_str(&format!("- {}\n", b));
            }
            fs::write(&md, m).expect("write md");
            println!("{}", serde_json::to_string_pretty(&report).unwrap());
        }
        _ => {
            print_usage();
            std::process::exit(2);
        }
    }
}
