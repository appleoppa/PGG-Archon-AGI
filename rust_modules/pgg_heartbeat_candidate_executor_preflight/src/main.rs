use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize)]
struct PreflightPacket {
    schema: String,
    generated_at_epoch: u64,
    status: String,
    score: f64,
    selected_candidate_id: String,
    selected_title: String,
    selected_rank: usize,
    selected_priority_score: f64,
    execution_allowed: bool,
    dry_run_only: bool,
    required_checks: Vec<String>,
    allowed_commands: Vec<String>,
    denied_actions: Vec<String>,
    evidence_inputs: Vec<String>,
    promotion_gate: String,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    boundaries: Vec<String>,
    output_dir: String,
    latest_preflight_json: String,
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
fn sha256_hex(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
fn read_json(path: &Path) -> Value {
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or(Value::Null)
}
fn s(v: &Value, k: &str) -> String {
    v.get(k).and_then(|x| x.as_str()).unwrap_or("").to_string()
}
fn f(v: &Value, k: &str) -> f64 {
    v.get(k).and_then(|x| x.as_f64()).unwrap_or(0.0)
}
fn u(v: &Value, k: &str) -> usize {
    v.get(k).and_then(|x| x.as_u64()).unwrap_or(0) as usize
}

fn main() {
    let h = home();
    let out_dir=h.join(".hermes/workspace/pgg-archon-governance/heartbeat-candidate-executor-preflight-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");
    let queue_path=h.join(".hermes/workspace/pgg-archon-governance/heartbeat-candidate-prioritizer-v1-20260618/latest_candidate_priority_queue.json");
    let q = read_json(&queue_path);
    let mut watch: Vec<String> = Vec::new();
    let blocked: Vec<String> = Vec::new();
    let top = q
        .get("queue")
        .and_then(|v| v.as_array())
        .and_then(|a| a.first())
        .cloned()
        .unwrap_or(Value::Null);
    if top == Value::Null {
        watch.push("No Top1 candidate found in P13 priority queue.".to_string());
    }
    let id = s(&top, "candidate_id");
    let title = s(&top, "title");
    let rank = u(&top, "rank");
    let pscore = f(&top, "priority_score");
    let apply_allowed = top
        .get("apply_allowed")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let execution_allowed = false;
    let mut required_checks = vec![
        "Read P13 latest_candidate_priority_queue.json and verify Top1 unchanged.".to_string(),
        "Read P12 latest_recommendation_candidates.json and verify candidate apply_allowed=false."
            .to_string(),
        "Read EVOLUTION_MANIFEST.json latest P10-P13 keys before any promotion.".to_string(),
        "Run only read-only capability-gap probes; no mutation.".to_string(),
    ];
    if apply_allowed {
        watch.push(
            "Top1 unexpectedly has apply_allowed=true; force dry-run preflight only.".to_string(),
        );
        required_checks
            .push("Require human override because apply_allowed true is unexpected.".to_string());
    }
    let allowed_commands = vec![
        "/Users/appleoppa/.hermes/bin/pgg-heartbeat-alert-summarizer".to_string(),
        "/Users/appleoppa/.hermes/bin/pgg-heartbeat-recommendation-candidate-gate".to_string(),
        "/Users/appleoppa/.hermes/bin/pgg-heartbeat-candidate-prioritizer".to_string(),
        "read-only manifest/session evidence inspection".to_string(),
    ];
    let denied_actions = vec![
        "auto-apply fixes".to_string(),
        "auto-commit or git push".to_string(),
        "provider/config/credential/security/scheduler mutation".to_string(),
        "production route/answer-chain changes".to_string(),
        "legal finalization".to_string(),
    ];
    let status = if top != Value::Null {
        "PASS_EXECUTOR_PREFLIGHT_DRY_RUN_READY"
    } else {
        "PARTIAL_EXECUTOR_PREFLIGHT_WITH_WATCH"
    }
    .to_string();
    let score = if top != Value::Null { 100.0 } else { 50.0 };
    let latest = out_dir.join("latest_executor_preflight.json");
    let report = out_dir.join("EXECUTOR_PREFLIGHT.md");
    let acceptance = out_dir.join("ACCEPTANCE.json");
    let packet=PreflightPacket{schema:"pgg_heartbeat_candidate_executor_preflight/v1".to_string(),generated_at_epoch:now_epoch(),status:status.clone(),score,selected_candidate_id:id.clone(),selected_title:title.clone(),selected_rank:rank,selected_priority_score:pscore,execution_allowed,dry_run_only:true,required_checks:required_checks.clone(),allowed_commands:allowed_commands.clone(),denied_actions:denied_actions.clone(),evidence_inputs:vec![queue_path.display().to_string(),"/Users/appleoppa/.hermes/workspace/pgg-archon-governance/heartbeat-recommendation-candidate-gate-v1-20260618/latest_recommendation_candidates.json".to_string(),"/Users/appleoppa/.hermes/data/EVOLUTION_MANIFEST.json".to_string()],promotion_gate:"P15 required before any execution: capability-gap scoped read-only probe gate".to_string(),watch_items:watch.clone(),blocked_items:blocked.clone(),boundaries:vec!["Preflight is dry-run only.".to_string(),"execution_allowed=false by design.".to_string(),"No provider/LLM/network call.".to_string(),"No mutation/commit/config/scheduler change.".to_string()],output_dir:out_dir.display().to_string(),latest_preflight_json:latest.display().to_string(),report_md:report.display().to_string(),acceptance_json:acceptance.display().to_string()};
    let json = serde_json::to_string_pretty(&packet).unwrap();
    fs::write(&latest, &json).expect("write latest");
    let mut md = String::from("# PGG Heartbeat Candidate Executor Preflight v1\n\n");
    md.push_str(&format!("- status: `{}`\n- candidate: `{}` {}\n- priority_score: `{}`\n- execution_allowed: `{}`\n- dry_run_only: `{}`\n\n",status,id,title,pscore,execution_allowed,true));
    md.push_str("## Required checks\n\n");
    for c in &required_checks {
        md.push_str(&format!("- {}\n", c));
    }
    md.push_str("\n## Denied actions\n\n");
    for d in &denied_actions {
        md.push_str(&format!("- {}\n", d));
    }
    fs::write(&report, md).expect("write report");
    let acc = serde_json::json!({"schema":"pgg_heartbeat_candidate_executor_preflight_acceptance/v1","status":status,"score":score,"selected_candidate_id":id,"execution_allowed":execution_allowed,"dry_run_only":true,"watch_count":watch.len(),"blocked_count":blocked.len(),"latest_preflight_json":latest,"report_md":report,"acceptance_json":acceptance,"queue_sha256":sha256_hex(&fs::read(&queue_path).unwrap_or_default()),"next_action":"P15 capability-gap scoped read-only probe gate; still no mutation."});
    fs::write(&acceptance, serde_json::to_string_pretty(&acc).unwrap()).expect("write acceptance");
    println!("{}", serde_json::to_string_pretty(&packet).unwrap());
}
