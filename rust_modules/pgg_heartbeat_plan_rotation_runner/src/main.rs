use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize)]
struct RotationEntry {
    schema: String,
    rotation_id: String,
    created_at_epoch: u64,
    mode: String,
    planner_binary: String,
    planner_exit_success: bool,
    planner_status: String,
    planner_score: Option<f64>,
    planner_step_count: Option<u64>,
    planner_watch_count: usize,
    planner_blocked_count: usize,
    classification: String,
    stdout_sha256: String,
    latest_plan_json: Option<String>,
    report_md: Option<String>,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
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

fn sha256_hex(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn main() {
    let h = home();
    let out_dir = h
        .join(".hermes/workspace/pgg-archon-governance/heartbeat-plan-rotation-runner-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");
    fs::create_dir_all(h.join(".hermes/logs")).ok();

    let planner_bin = h.join(".hermes/bin/pgg-heartbeat-evolution-planner");
    let mut watch: Vec<String> = Vec::new();
    let mut blocked: Vec<String> = Vec::new();

    let output = if planner_bin.exists() {
        Command::new(&planner_bin).output()
    } else {
        blocked.push("P10 planner binary missing; cannot rotate evolution plan.".to_string());
        Command::new("/usr/bin/false").output()
    };

    let (success, stdout, stderr) = match output {
        Ok(o) => (
            o.status.success(),
            String::from_utf8_lossy(&o.stdout).to_string(),
            String::from_utf8_lossy(&o.stderr).to_string(),
        ),
        Err(e) => {
            blocked.push(format!("Failed to execute planner: {e}"));
            (false, String::new(), String::new())
        }
    };

    let parsed: Option<Value> = serde_json::from_str(&stdout).ok();
    if parsed.is_none() {
        watch.push("Planner stdout was not parseable JSON.".to_string());
    }
    if !stderr.trim().is_empty() {
        watch.push("Planner emitted stderr; inspect rotation stderr log.".to_string());
    }

    let planner_status = parsed
        .as_ref()
        .and_then(|v| v.get("status"))
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN")
        .to_string();
    let planner_score = parsed
        .as_ref()
        .and_then(|v| v.get("score"))
        .and_then(|v| v.as_f64());
    let planner_step_count = parsed
        .as_ref()
        .and_then(|v| v.get("step_count"))
        .and_then(|v| v.as_u64());
    let planner_watch_count = parsed
        .as_ref()
        .and_then(|v| v.get("watch_items"))
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    let planner_blocked_count = parsed
        .as_ref()
        .and_then(|v| v.get("blocked_items"))
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    if planner_blocked_count > 0 {
        blocked.push("P10 planner returned blocked items.".to_string());
    }

    let latest_plan_json = parsed
        .as_ref()
        .and_then(|v| v.get("latest_plan_json"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let report_md = parsed
        .as_ref()
        .and_then(|v| v.get("report_md"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let classification = if blocked.is_empty() && success && planner_status.starts_with("PASS") {
        if planner_watch_count == 0 && watch.is_empty() {
            "PASS_PLAN_ROTATION_RUNNER".to_string()
        } else {
            "PASS_PLAN_ROTATION_RUNNER_WITH_WATCH".to_string()
        }
    } else if blocked.is_empty() {
        "PARTIAL_PLAN_ROTATION_RUNNER_WITH_WATCH".to_string()
    } else {
        "BLOCKED_PLAN_ROTATION_RUNNER".to_string()
    };

    let rotation_id = format!(
        "hpr-{}",
        &sha256_hex(format!("{}{}", now_epoch(), planner_status).as_bytes())[..16]
    );
    let entry = RotationEntry {
        schema: "pgg_heartbeat_plan_rotation_runner/v1".to_string(),
        rotation_id,
        created_at_epoch: now_epoch(),
        mode: "launchd_light_readonly_plan_rotation".to_string(),
        planner_binary: planner_bin.display().to_string(),
        planner_exit_success: success,
        planner_status,
        planner_score,
        planner_step_count,
        planner_watch_count,
        planner_blocked_count,
        classification: classification.clone(),
        stdout_sha256: sha256_hex(stdout.as_bytes()),
        latest_plan_json,
        report_md,
        watch_items: watch.clone(),
        blocked_items: blocked.clone(),
        boundaries: vec![
            "Plan rotation runner only invokes the local read-only P10 planner.".to_string(),
            "No provider/LLM/network call.".to_string(),
            "No automatic optimization apply, commit, config change, or provider mutation."
                .to_string(),
            "launchd schedules planning only; execution remains separately gated.".to_string(),
        ],
    };

    let latest = out_dir.join("latest_plan_rotation_runner.json");
    let ledger = out_dir.join("plan_rotation_runner_ledger.jsonl");
    let report = out_dir.join("PLAN_ROTATION_RUNNER.md");
    let acceptance = out_dir.join("ACCEPTANCE.json");

    let line = serde_json::to_string(&entry).unwrap();
    fs::write(&latest, serde_json::to_string_pretty(&entry).unwrap()).expect("write latest");
    let mut previous = String::new();
    if ledger.exists() {
        previous = fs::read_to_string(&ledger).unwrap_or_default();
        if !previous.is_empty() && !previous.ends_with('\n') {
            previous.push('\n');
        }
    }
    previous.push_str(&line);
    previous.push('\n');
    fs::write(&ledger, previous).expect("write ledger");

    let mut md = String::new();
    md.push_str("# PGG Heartbeat Plan Rotation Runner v1\n\n");
    md.push_str(&format!(
        "- classification: `{}`\n- rotation_id: `{}`\n- planner_status: `{}`\n- planner_score: `{:?}`\n- planner_steps: `{:?}`\n- planner_watch: `{}`\n- planner_blocked: `{}`\n\n",
        entry.classification,
        entry.rotation_id,
        entry.planner_status,
        entry.planner_score,
        entry.planner_step_count,
        entry.planner_watch_count,
        entry.planner_blocked_count
    ));
    md.push_str("## Boundaries\n\n");
    for b in &entry.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(&report, md).expect("write report");

    let accept = serde_json::json!({
        "schema": "pgg_heartbeat_plan_rotation_runner_acceptance/v1",
        "classification": classification,
        "rotation_id": entry.rotation_id,
        "planner_status": entry.planner_status,
        "planner_score": entry.planner_score,
        "planner_step_count": entry.planner_step_count,
        "planner_watch_count": entry.planner_watch_count,
        "planner_blocked_count": entry.planner_blocked_count,
        "latest": latest,
        "ledger": ledger,
        "report": report,
        "runner_sha256": sha256_hex(&serde_json::to_vec_pretty(&entry).unwrap()),
    });
    fs::write(&acceptance, serde_json::to_string_pretty(&accept).unwrap())
        .expect("write acceptance");

    println!("{}", serde_json::to_string_pretty(&entry).unwrap());
    if !blocked.is_empty() {
        std::process::exit(2);
    }
}
