use chrono::{Local, SecondsFormat};
use serde::Serialize;
use std::{env, fs, path::{Path, PathBuf}, process::Command};

#[derive(Serialize, Clone)]
struct CmdResult { ok: bool, output: String }
#[derive(Serialize, Clone)]
struct CaseScan { name: String, path: String, trusted_status: String, trusted_summary: String }
#[derive(Serialize)]
struct Report {
    schema: String,
    generated_at: String,
    status: String,
    score: u32,
    case_root: String,
    case_count: usize,
    cases: Vec<CaseScan>,
    state_db_integrity: CmdResult,
    sessions_stats: CmdResult,
    cms_next: CmdResult,
    profile_status: CmdResult,
    ops_gate: CmdResult,
    boundary: Vec<String>,
}
fn home() -> PathBuf { PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string())) }
fn run(cmd: &str, args: &[&str]) -> CmdResult {
    match Command::new(cmd).args(args).output() {
        Ok(o) => {
            let mut s=String::new();
            s.push_str(&String::from_utf8_lossy(&o.stdout));
            s.push_str(&String::from_utf8_lossy(&o.stderr));
            CmdResult{ok:o.status.success(), output:s.trim().chars().take(2000).collect()}
        },
        Err(e)=>CmdResult{ok:false, output:format!("exec error: {e}")}
    }
}
fn parse_trusted_status(out: &str, ok: bool) -> (String, String) {
    if ok && out.contains("\"status\": \"PASS\"") { return ("PASS".into(), "trusted workflow gate PASS".into()); }
    if out.contains("\"status\": \"WATCH\"") { return ("WATCH".into(), out.lines().take(6).collect::<Vec<_>>().join(" ")); }
    if out.contains("\"status\": \"BLOCKED\"") { return ("BLOCKED".into(), out.lines().take(6).collect::<Vec<_>>().join(" ")); }
    if ok { ("UNKNOWN_OK".into(), out.lines().take(6).collect::<Vec<_>>().join(" ")) } else { ("WATCH".into(), out.lines().take(6).collect::<Vec<_>>().join(" ")) }
}
fn write_markdown(report: &Report, path: &Path) -> std::io::Result<()> {
    let mut md=String::new();
    md.push_str("# PGG Legal Multi-Agent Ops Observe-Only Daily Report\n\n");
    md.push_str(&format!("- Generated: `{}`\n- Status: `{}`\n- Score: `{}`\n- Case root: `{}`\n- Case count: `{}`\n\n", report.generated_at, report.status, report.score, report.case_root, report.case_count));
    md.push_str("## Gates\n\n");
    md.push_str(&format!("- state_db_integrity: `{}` — `{}`\n", report.state_db_integrity.ok, report.state_db_integrity.output.lines().next().unwrap_or("")));
    md.push_str(&format!("- sessions_stats: `{}` — `{}`\n", report.sessions_stats.ok, report.sessions_stats.output.lines().next().unwrap_or("")));
    md.push_str(&format!("- cms_next: `{}`\n", report.cms_next.ok));
    md.push_str(&format!("- profile_status: `{}`\n", report.profile_status.ok));
    md.push_str(&format!("- ops_gate: `{}` — `{}`\n\n", report.ops_gate.ok, report.ops_gate.output.lines().next().unwrap_or("")));
    md.push_str("## Cases\n\n");
    for c in &report.cases { md.push_str(&format!("- `{}` — `{}` — {}\n", c.name, c.trusted_status, c.trusted_summary.replace('\n'," "))); }
    md.push_str("\n## Boundary\n\n");
    for b in &report.boundary { md.push_str(&format!("- {}\n", b)); }
    fs::write(path, md)
}
fn main() {
    let h=home();
    let case_root=h.join(".hermes/workspace/苹果中枢办案库");
    let out_dir=h.join(".hermes/workspace/pgg-archon-governance/legal-multiagent-ops");
    fs::create_dir_all(&out_dir).unwrap();
    let generated=Local::now().to_rfc3339_opts(SecondsFormat::Secs, true);
    let date=Local::now().format("%Y%m%d").to_string();
    let mut cases=Vec::new();
    if let Ok(entries)=fs::read_dir(&case_root) {
        for e in entries.flatten() {
            let p=e.path();
            if !p.is_dir() { continue; }
            let name=e.file_name().to_string_lossy().to_string();
            if name.starts_with('_') || name=="台账" { continue; }
            let gate=run(h.join(".hermes/bin/case_trusted_workflow_gate").to_str().unwrap_or("case_trusted_workflow_gate"), &[p.to_str().unwrap_or("")]);
            let (status, summary)=parse_trusted_status(&gate.output, gate.ok);
            cases.push(CaseScan{name, path:p.display().to_string(), trusted_status:status, trusted_summary:summary});
        }
    }
    cases.sort_by(|a,b| a.name.cmp(&b.name));
    let state_db=run("sqlite3", &[h.join(".hermes/state.db").to_str().unwrap_or(""), "PRAGMA integrity_check;"]);
    let sessions=run(h.join(".local/bin/hermes").to_str().unwrap_or("hermes"), &["sessions", "stats"]);
    let cms=run(h.join(".hermes/bin/cms_case_guard").to_str().unwrap_or("cms_case_guard"), &["--next"]);
    let profiles=run(h.join(".hermes/bin/pgg-case-departments").to_str().unwrap_or("pgg-case-departments"), &["status", "--json"]);
    let ops=run(h.join(".hermes/bin/pgg-legal-multiagent-ops-gate").to_str().unwrap_or("pgg-legal-multiagent-ops-gate"), &[]);
    let pass_cases=cases.iter().filter(|c| c.trusted_status=="PASS").count();
    let base_checks=[state_db.ok && state_db.output.trim()=="ok", sessions.ok, cms.ok, profiles.ok, ops.ok].iter().filter(|x| **x).count();
    let denom=5 + cases.len().max(1);
    let numer=base_checks + pass_cases;
    let score=((numer as f64 / denom as f64)*100.0).round() as u32;
    let status= if base_checks==5 { "PASS_OBSERVE_ONLY_REPORT_WRITTEN" } else { "WATCH_OBSERVE_ONLY_REPORT_WRITTEN" }.to_string();
    let report=Report{
        schema:"pgg-legal-multiagent-ops-observer/v1".into(), generated_at:generated, status, score,
        case_root:case_root.display().to_string(), case_count:cases.len(), cases,
        state_db_integrity:state_db, sessions_stats:sessions, cms_next:cms, profile_status:profiles, ops_gate:ops,
        boundary:vec![
            "observe-only reporter; no LLM/provider calls".into(),
            "does not mutate case files or generate final legal documents".into(),
            "trusted role participation requires receipts, not merely running profiles".into(),
            "durable scheduling is launchd/Rust; Hermes cron remains unused".into(),
        ]
    };
    let json_path=out_dir.join(format!("legal-multiagent-ops-report-{date}.json"));
    let md_path=out_dir.join(format!("legal-multiagent-ops-report-{date}.md"));
    fs::write(&json_path, serde_json::to_string_pretty(&report).unwrap()).unwrap();
    write_markdown(&report, &md_path).unwrap();
    fs::write(out_dir.join("latest.json"), serde_json::to_string_pretty(&report).unwrap()).unwrap();
    fs::write(out_dir.join("latest.md"), fs::read_to_string(&md_path).unwrap()).unwrap();
    println!("{}", serde_json::json!({"ok":true,"status":report.status,"score":report.score,"json":json_path,"md":md_path}));
}
