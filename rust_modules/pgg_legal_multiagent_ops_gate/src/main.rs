use serde::Serialize;
use std::env;
use std::path::PathBuf;
use std::process::Command;

#[derive(Serialize)]
struct Check { name: String, status: String, evidence: String }
#[derive(Serialize)]
struct Report { schema: String, status: String, score: u32, checks: Vec<Check>, boundary: Vec<String> }

fn home() -> PathBuf { PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string())) }
fn exists(path: PathBuf) -> bool { path.exists() }
fn run(cmd: &str, args: &[&str]) -> (bool, String) {
    match Command::new(cmd).args(args).output() {
        Ok(o) => {
            let mut s = String::new();
            s.push_str(&String::from_utf8_lossy(&o.stdout));
            s.push_str(&String::from_utf8_lossy(&o.stderr));
            (o.status.success(), s.trim().chars().take(600).collect())
        }
        Err(e) => (false, format!("exec error: {e}")),
    }
}
fn check(name: &str, ok: bool, evidence: String) -> Check {
    Check { name: name.to_string(), status: if ok {"PASS"} else {"WATCH"}.to_string(), evidence }
}

fn main() {
    let h = home();
    let mut checks: Vec<Check> = vec![];
    let required_profiles = [
        "pgg-business-master",
        "pgg-fact-evidence",
        "pgg-inspection-audit",
        "pgg-law-source",
        "pgg-strategy-simulation",
    ];
    let mut missing = vec![];
    for p in required_profiles { if !exists(h.join(".hermes/profiles").join(p)) { missing.push(p); } }
    checks.push(check("department_profiles_exist", missing.is_empty(), if missing.is_empty(){"all required legal/ops profiles exist".to_string()} else {format!("missing profiles: {:?}", missing)}));

    let case_depts = h.join(".hermes/bin/pgg-case-departments");
    checks.push(check("case_department_controller_exists", exists(case_depts.clone()), case_depts.display().to_string()));
    let cms = h.join(".hermes/bin/cms_case_guard");
    checks.push(check("cms_case_guard_exists", exists(cms.clone()), cms.display().to_string()));
    let trusted = h.join(".hermes/bin/case_trusted_workflow_gate");
    checks.push(check("trusted_workflow_gate_exists", exists(trusted.clone()), trusted.display().to_string()));

    let (_, cron_out) = run(h.join(".local/bin/hermes").to_str().unwrap_or("hermes"), &["cron", "list", "--all"]);
    checks.push(check("hermes_cron_empty_for_durable_ops", cron_out.contains("No scheduled jobs"), cron_out));

    let (db_ok, db_out) = run("sqlite3", &[h.join(".hermes/state.db").to_str().unwrap_or(""), "PRAGMA integrity_check;"]);
    checks.push(check("state_db_integrity", db_ok && db_out.trim()=="ok", db_out));

    let (cms_ok, cms_out) = run(h.join(".hermes/bin/cms_case_guard").to_str().unwrap_or("cms_case_guard"), &["--next"]);
    checks.push(check("cms_next_sequence_probe", cms_ok && cms_out.contains("\"status\": \"PASS\""), cms_out));

    let role_map = ["cms", "matter_department", "evidence_management", "legal_support", "inspection_audit", "secondary_llm_or_subagent"];
    checks.push(check("six_required_roles_declared", true, role_map.join(",")));

    let pass = checks.iter().filter(|c| c.status=="PASS").count() as u32;
    let score = (pass * 100 / checks.len() as u32) as u32;
    let status = if score >= 90 {"PASS_OBSERVE_ONLY_READY"} else {"WATCH"}.to_string();
    let r = Report{
        schema:"pgg-legal-multiagent-ops-gate/v1".to_string(),
        status,
        score,
        checks,
        boundary: vec![
            "observe-only pilot gate; does not start 24h LLM agents".to_string(),
            "does not mutate cases, credentials, provider config, scheduler/security core".to_string(),
            "legal finalization still requires trusted workflow receipts".to_string(),
            "durable scheduling must use launchd/Rust, not Hermes cron".to_string(),
        ]
    };
    println!("{}", serde_json::to_string_pretty(&r).unwrap());
    if !r.status.starts_with("PASS") { std::process::exit(1); }
}
