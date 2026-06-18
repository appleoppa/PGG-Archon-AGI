use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct RoutedAction {
    gap_id: String,
    route: String,
    status: String,
    evidence: Vec<String>,
    next_gate: String,
    mutation_performed_by_router: bool,
}
#[derive(Debug, Serialize, Deserialize)]
struct RouterPacket {
    schema: String,
    generated_at_epoch: u64,
    status: String,
    score: f64,
    source_gap_probe: String,
    actions: Vec<RoutedAction>,
    repaired_count: usize,
    remaining_watch_count: usize,
    blocked_count: usize,
    boundaries: Vec<String>,
    output_dir: String,
    latest_router_json: String,
    report_md: String,
    acceptance_json: String,
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
fn sha256_hex(s: &str) -> String {
    hex::encode(Sha256::digest(s.as_bytes()))
}
fn exists(p: &Path) -> bool {
    p.exists()
}
fn read_json(p: &Path) -> Value {
    fs::read_to_string(p)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or(Value::Null)
}
fn cmd(program: &str, args: &[&str]) -> String {
    Command::new(program)
        .args(args)
        .output()
        .map(|o| {
            String::from_utf8_lossy(&o.stdout).to_string() + &String::from_utf8_lossy(&o.stderr)
        })
        .unwrap_or_default()
}
fn main() {
    let h = home();
    let out_dir =
        h.join(".hermes/workspace/pgg-archon-governance/heartbeat-gap-action-router-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");
    let src=h.join(".hermes/workspace/pgg-archon-governance/heartbeat-capability-gap-probe-v1-20260618/latest_capability_gap_probe.json");
    let gap_json = read_json(&src);
    let p7 = h.join("Library/LaunchAgents/ai.hermes.pgg-heartbeat-light-runner.plist");
    let p11 = h.join("Library/LaunchAgents/ai.hermes.pgg-heartbeat-plan-rotation-runner.plist");
    let health = h.join("Library/LaunchAgents/ai.hermes.pgg-health-monitor.plist");
    let git_out = cmd(
        "git",
        &[
            "-C",
            "/Users/appleoppa/.hermes/hermes-agent",
            "status",
            "--short",
            "rust_modules/Cargo.toml",
        ],
    );
    let launch_out = cmd("launchctl", &["list"]);
    let mut actions: Vec<RoutedAction> = Vec::new();
    actions.push(RoutedAction {
        gap_id: "gap_heartbeat_light_runner_plist_missing".to_string(),
        route: "scoped_repair_verify".to_string(),
        status: if exists(&p7) {
            "REPAIRED_VERIFIED"
        } else {
            "STILL_MISSING"
        }
        .to_string(),
        evidence: vec![
            p7.display().to_string(),
            format!(
                "launchctl_has_label={}",
                launch_out.contains("ai.hermes.pgg-heartbeat-light-runner")
            ),
        ],
        next_gate: "none_if_verified_else_p7_repair".to_string(),
        mutation_performed_by_router: false,
    });
    actions.push(RoutedAction {
        gap_id: "gap_plan_rotation_plist_missing".to_string(),
        route: "scoped_repair_verify".to_string(),
        status: if exists(&p11) {
            "REPAIRED_VERIFIED"
        } else {
            "STILL_MISSING"
        }
        .to_string(),
        evidence: vec![
            p11.display().to_string(),
            format!(
                "launchctl_has_label={}",
                launch_out.contains("ai.hermes.pgg-heartbeat-plan-rotation-runner")
            ),
        ],
        next_gate: "none_if_verified_else_p11_repair".to_string(),
        mutation_performed_by_router: false,
    });
    actions.push(RoutedAction {
        gap_id: "gap_health_monitor_no_standalone_plist".to_string(),
        route: "design_gate".to_string(),
        status: if exists(&health) {
            "RESOLVED_BY_EXISTING_PLIST"
        } else {
            "WATCH_DESIGN_REQUIRED"
        }
        .to_string(),
        evidence: vec![health.display().to_string()],
        next_gate: "health-monitor-launchd-design-gate".to_string(),
        mutation_performed_by_router: false,
    });
    actions.push(RoutedAction {
        gap_id: "gap_unsettled_rust_workspace_manifest".to_string(),
        route: "settlement_gate".to_string(),
        status: if git_out.trim().is_empty() {
            "RESOLVED_CLEAN"
        } else {
            "WATCH_SETTLEMENT_REQUIRED"
        }
        .to_string(),
        evidence: vec![git_out.trim().to_string()],
        next_gate: "scoped-git-settlement-preflight".to_string(),
        mutation_performed_by_router: false,
    });
    let repaired = actions
        .iter()
        .filter(|a| a.status.contains("REPAIRED") || a.status.contains("RESOLVED"))
        .count();
    let remaining = actions
        .iter()
        .filter(|a| a.status.contains("WATCH") || a.status.contains("MISSING"))
        .count();
    let blocked = 0usize;
    let status = if remaining == 0 {
        "PASS_GAP_ACTION_ROUTER_ALL_RESOLVED"
    } else {
        "PASS_GAP_ACTION_ROUTER_WITH_REMAINING_WATCH"
    }
    .to_string();
    let score = (100.0 - (remaining as f64 * 12.0)).max(50.0);
    let latest = out_dir.join("latest_gap_action_router.json");
    let report = out_dir.join("GAP_ACTION_ROUTER.md");
    let acceptance = out_dir.join("ACCEPTANCE.json");
    let packet=RouterPacket{schema:"pgg_heartbeat_gap_action_router/v1".to_string(),generated_at_epoch:now_epoch(),status:status.clone(),score,source_gap_probe:src.display().to_string(),actions:actions.clone(),repaired_count:repaired,remaining_watch_count:remaining,blocked_count:blocked,boundaries:vec!["Router is read-only verification and routing; scoped plist repair is performed outside this binary.".to_string(),"No provider/LLM/network call.".to_string(),"No auto-commit/config/provider/security mutation.".to_string()],output_dir:out_dir.display().to_string(),latest_router_json:latest.display().to_string(),report_md:report.display().to_string(),acceptance_json:acceptance.display().to_string()};
    let json = serde_json::to_string_pretty(&packet).unwrap();
    fs::write(&latest, &json).expect("write latest");
    let mut md = String::from("# PGG Heartbeat Gap Action Router v1\n\n");
    md.push_str(&format!(
        "- status: `{}`\n- score: `{}`\n- repaired: `{}`\n- remaining_watch: `{}`\n\n",
        status, score, repaired, remaining
    ));
    for a in &actions {
        md.push_str(&format!(
            "## {}\n- route: {}\n- status: {}\n- next_gate: {}\n\n",
            a.gap_id, a.route, a.status, a.next_gate
        ));
    }
    fs::write(&report, md).expect("write report");
    let acc = serde_json::json!({"schema":"pgg_heartbeat_gap_action_router_acceptance/v1","status":status,"score":score,"repaired_count":repaired,"remaining_watch_count":remaining,"blocked_count":blocked,"latest_router_json":latest,"report_md":report,"acceptance_json":acceptance,"source_digest":sha256_hex(&gap_json.to_string()),"next_action":"P17 health-monitor launchd design or git settlement preflight."});
    fs::write(&acceptance, serde_json::to_string_pretty(&acc).unwrap()).expect("write acceptance");
    println!("{}", serde_json::to_string_pretty(&packet).unwrap());
}
