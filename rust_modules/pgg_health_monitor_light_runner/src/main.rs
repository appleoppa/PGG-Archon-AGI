use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize)]
struct RunnerEntry {
    schema: String,
    run_id: String,
    created_at_epoch: u64,
    mode: String,
    health_binary: String,
    health_exit_success: bool,
    health_status: String,
    health_level: String,
    alert_count: usize,
    classification: String,
    stdout_sha256: String,
    latest_health_json: String,
    ledger_jsonl: String,
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
fn val_str(v: &Value, key: &str, default: &str) -> String {
    v.get(key)
        .and_then(|x| x.as_str())
        .unwrap_or(default)
        .to_string()
}

fn main() {
    let h = home();
    let out_dir =
        h.join(".hermes/workspace/pgg-archon-governance/health-monitor-light-runner-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");
    fs::create_dir_all(h.join(".hermes/logs")).ok();
    fs::create_dir_all(h.join(".hermes/data/health-monitor-light-runner")).ok();

    let health_bin = h.join(".hermes/bin/pgg-health-monitor");
    let mut watch: Vec<String> = Vec::new();
    let mut blocked: Vec<String> = Vec::new();

    let output = if health_bin.exists() {
        Command::new(&health_bin).arg("--json").output()
    } else {
        blocked.push("pgg-health-monitor binary missing.".to_string());
        Command::new("/usr/bin/false").output()
    };

    let (success, stdout, stderr) = match output {
        Ok(o) => (
            o.status.success(),
            String::from_utf8_lossy(&o.stdout).to_string(),
            String::from_utf8_lossy(&o.stderr).to_string(),
        ),
        Err(e) => {
            blocked.push(format!("Failed to execute health monitor: {e}"));
            (false, String::new(), String::new())
        }
    };
    if !stderr.trim().is_empty() {
        watch.push("health-monitor emitted stderr; inspect launchd stderr log.".to_string());
    }
    let parsed: Option<Value> = serde_json::from_str(&stdout).ok();
    if parsed.is_none() {
        blocked.push("health-monitor stdout was not parseable JSON.".to_string());
    }

    let health_status = parsed
        .as_ref()
        .map(|v| val_str(v, "status", "UNKNOWN"))
        .unwrap_or_else(|| "UNKNOWN".to_string());
    let health_level = parsed
        .as_ref()
        .map(|v| val_str(v, "level", "unknown"))
        .unwrap_or_else(|| "unknown".to_string());
    let alert_count = parsed
        .as_ref()
        .and_then(|v| v.get("alerts"))
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    if alert_count > 0 {
        watch.push(format!("health-monitor reported {alert_count} alert(s)."));
    }
    if !success || health_status != "PASS" {
        blocked.push(format!(
            "health-monitor did not return PASS: success={success}, status={health_status}"
        ));
    }

    let classification = if blocked.is_empty() {
        if alert_count == 0 && watch.is_empty() && health_level == "green" {
            "PASS_HEALTH_MONITOR_LIGHT_RUNNER".to_string()
        } else {
            "PASS_HEALTH_MONITOR_LIGHT_RUNNER_WITH_WATCH".to_string()
        }
    } else {
        "BLOCKED_HEALTH_MONITOR_LIGHT_RUNNER".to_string()
    };
    let run_id = format!(
        "hml-{}",
        &sha256_hex(format!("{}{}{}", now_epoch(), health_status, alert_count).as_bytes())[..16]
    );
    let latest = out_dir.join("latest_health_monitor_light_runner.json");
    let ledger = out_dir.join("health_monitor_light_runner_ledger.jsonl");
    let report = out_dir.join("HEALTH_MONITOR_LIGHT_RUNNER.md");
    let acceptance = out_dir.join("ACCEPTANCE.json");
    let latest_data = h.join(".hermes/data/health-monitor-light-runner/latest.json");

    let entry = RunnerEntry {
        schema: "pgg_health_monitor_light_runner/v1".to_string(),
        run_id,
        created_at_epoch: now_epoch(),
        mode: "launchd_light_readonly".to_string(),
        health_binary: health_bin.display().to_string(),
        health_exit_success: success,
        health_status,
        health_level,
        alert_count,
        classification: classification.clone(),
        stdout_sha256: sha256_hex(stdout.as_bytes()),
        latest_health_json: h.join(".hermes/data/health-monitor/latest.json").display().to_string(),
        ledger_jsonl: ledger.display().to_string(),
        watch_items: watch.clone(),
        blocked_items: blocked.clone(),
        boundaries: vec![
            "LIGHT runner only invokes the local pgg-health-monitor --json CLI.".to_string(),
            "No provider/LLM/network call is performed by this runner.".to_string(),
            "No provider/config/credential/security mutation.".to_string(),
            "launchd only schedules bounded health observation; it does not grant autonomous production control.".to_string(),
        ],
    };

    let entry_line = serde_json::to_string(&entry).expect("entry json");
    let pretty = serde_json::to_string_pretty(&entry).unwrap();
    fs::write(&latest, &pretty).expect("write latest");
    fs::write(&latest_data, &pretty).expect("write latest data");
    let mut previous = if ledger.exists() {
        fs::read_to_string(&ledger).unwrap_or_default()
    } else {
        String::new()
    };
    if !previous.is_empty() && !previous.ends_with('\n') {
        previous.push('\n');
    }
    previous.push_str(&entry_line);
    previous.push('\n');
    fs::write(&ledger, previous).expect("write ledger");

    let mut md = String::from("# PGG Health Monitor LIGHT Runner v1\n\n");
    md.push_str(&format!("- classification: `{}`\n- run_id: `{}`\n- health_status: `{}`\n- health_level: `{}`\n- alert_count: `{}`\n\n", entry.classification, entry.run_id, entry.health_status, entry.health_level, entry.alert_count));
    md.push_str("## Boundaries\n\n");
    for b in &entry.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(&report, md).expect("write report");

    let accept = serde_json::json!({
        "schema":"pgg_health_monitor_light_runner_acceptance/v1",
        "classification":classification,
        "run_id":entry.run_id,
        "health_status":entry.health_status,
        "health_level":entry.health_level,
        "alert_count":entry.alert_count,
        "latest":latest,
        "latest_data":latest_data,
        "ledger":ledger,
        "report":report,
        "runner_sha256":sha256_hex(&serde_json::to_vec_pretty(&entry).unwrap()),
    });
    fs::write(&acceptance, serde_json::to_string_pretty(&accept).unwrap())
        .expect("write acceptance");
    println!("{}", serde_json::to_string_pretty(&entry).unwrap());
    if !blocked.is_empty() {
        std::process::exit(2);
    }
}
