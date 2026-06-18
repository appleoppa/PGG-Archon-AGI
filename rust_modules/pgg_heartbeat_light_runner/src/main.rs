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
    replay_gate_binary: String,
    replay_exit_success: bool,
    replay_status: String,
    replay_score: Option<f64>,
    replay_pulse_id: Option<String>,
    replay_watch_count: usize,
    replay_blocked_count: usize,
    classification: String,
    stdout_sha256: String,
    latest_replay_json: Option<String>,
    replay_ledger_jsonl: Option<String>,
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
    let out_dir =
        h.join(".hermes/workspace/pgg-archon-governance/heartbeat-light-runner-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");
    fs::create_dir_all(h.join(".hermes/logs")).ok();

    let replay_bin = h.join(".hermes/bin/pgg-heartbeat-replay-ledger-gate");
    let mut watch: Vec<String> = Vec::new();
    let mut blocked: Vec<String> = Vec::new();

    let output = if replay_bin.exists() {
        Command::new(&replay_bin).output()
    } else {
        blocked.push(
            "Replay gate binary missing; LIGHT runner cannot capture heartbeat pulse.".to_string(),
        );
        Command::new("/usr/bin/false").output()
    };

    let (success, stdout, stderr) = match output {
        Ok(o) => (
            o.status.success(),
            String::from_utf8_lossy(&o.stdout).to_string(),
            String::from_utf8_lossy(&o.stderr).to_string(),
        ),
        Err(e) => {
            blocked.push(format!("Failed to execute replay gate: {e}"));
            (false, String::new(), String::new())
        }
    };

    let parsed: Option<Value> = serde_json::from_str(&stdout).ok();
    if parsed.is_none() {
        watch.push("Replay gate stdout was not parseable JSON.".to_string());
    }
    if !stderr.trim().is_empty() {
        watch.push("Replay gate emitted stderr; inspect runner stderr log.".to_string());
    }

    let replay_status = parsed
        .as_ref()
        .and_then(|v| v.get("status"))
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN")
        .to_string();
    let replay_score = parsed
        .as_ref()
        .and_then(|v| v.get("score"))
        .and_then(|v| v.as_f64());
    let ledger_entry = parsed.as_ref().and_then(|v| v.get("ledger_entry"));
    let replay_pulse_id = ledger_entry
        .and_then(|v| v.get("pulse_id"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let replay_watch_count = ledger_entry
        .and_then(|v| v.get("watch_items"))
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    let replay_blocked_count = ledger_entry
        .and_then(|v| v.get("blocked_items"))
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    if replay_blocked_count > 0 {
        blocked.push("Replay ledger contains blocked items.".to_string());
    }

    let latest_replay_json = parsed
        .as_ref()
        .and_then(|v| v.get("latest_json"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let replay_ledger_jsonl = parsed
        .as_ref()
        .and_then(|v| v.get("ledger_jsonl"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let classification = if blocked.is_empty() && success && replay_status.starts_with("PASS") {
        if replay_watch_count == 0 && watch.is_empty() {
            "PASS_HEARTBEAT_LIGHT_RUNNER".to_string()
        } else {
            "PASS_HEARTBEAT_LIGHT_RUNNER_WITH_WATCH".to_string()
        }
    } else if blocked.is_empty() {
        "PARTIAL_HEARTBEAT_LIGHT_RUNNER_WITH_WATCH".to_string()
    } else {
        "BLOCKED_HEARTBEAT_LIGHT_RUNNER".to_string()
    };

    let run_id = format!(
        "hbl-{}",
        &sha256_hex(
            format!(
                "{}{}",
                now_epoch(),
                replay_pulse_id.clone().unwrap_or_default()
            )
            .as_bytes()
        )[..16]
    );
    let entry = RunnerEntry {
        schema: "pgg_heartbeat_light_runner/v1".to_string(),
        run_id,
        created_at_epoch: now_epoch(),
        mode: "launchd_light_readonly".to_string(),
        replay_gate_binary: replay_bin.display().to_string(),
        replay_exit_success: success,
        replay_status,
        replay_score,
        replay_pulse_id,
        replay_watch_count,
        replay_blocked_count,
        classification: classification.clone(),
        stdout_sha256: sha256_hex(stdout.as_bytes()),
        latest_replay_json,
        replay_ledger_jsonl,
        watch_items: watch.clone(),
        blocked_items: blocked.clone(),
        boundaries: vec![
            "LIGHT runner only invokes the local read-only replay ledger gate.".to_string(),
            "No provider/LLM/network call is performed by this runner.".to_string(),
            "No provider/config/credential/security mutation.".to_string(),
            "launchd only schedules this bounded runner; it does not grant autonomous production control.".to_string(),
        ],
    };

    let latest = out_dir.join("latest_heartbeat_light_runner.json");
    let ledger = out_dir.join("heartbeat_light_runner_ledger.jsonl");
    let report = out_dir.join("HEARTBEAT_LIGHT_RUNNER.md");
    let acceptance = out_dir.join("ACCEPTANCE.json");

    let entry_line = serde_json::to_string(&entry).expect("entry json");
    fs::write(&latest, serde_json::to_string_pretty(&entry).unwrap()).expect("write latest");
    let mut previous = String::new();
    if ledger.exists() {
        previous = fs::read_to_string(&ledger).unwrap_or_default();
        if !previous.is_empty() && !previous.ends_with('\n') {
            previous.push('\n');
        }
    }
    previous.push_str(&entry_line);
    previous.push('\n');
    fs::write(&ledger, previous).expect("write ledger");

    let mut md = String::new();
    md.push_str("# PGG Heartbeat LIGHT Runner v1\n\n");
    md.push_str(&format!(
        "- classification: `{}`\n- run_id: `{}`\n- replay_status: `{}`\n- replay_score: `{:?}`\n- replay_watch: `{}`\n- replay_blocked: `{}`\n\n",
        entry.classification,
        entry.run_id,
        entry.replay_status,
        entry.replay_score,
        entry.replay_watch_count,
        entry.replay_blocked_count
    ));
    md.push_str("## Boundaries\n\n");
    for b in &entry.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(&report, md).expect("write report");

    let accept = serde_json::json!({
        "schema": "pgg_heartbeat_light_runner_acceptance/v1",
        "classification": classification,
        "run_id": entry.run_id,
        "replay_status": entry.replay_status,
        "replay_score": entry.replay_score,
        "replay_watch_count": entry.replay_watch_count,
        "replay_blocked_count": entry.replay_blocked_count,
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
