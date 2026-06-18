use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct SnapshotRef {
    name: String,
    path: String,
    exists: bool,
    sha256: Option<String>,
    status: Option<String>,
    score: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct LedgerEntry {
    pulse_id: String,
    created_at_epoch: u64,
    source_control_chain: Vec<SnapshotRef>,
    heartbeat_mapping: SnapshotRef,
    health_snapshot: SnapshotRef,
    launchd_snapshot: Value,
    verification_snapshot: Value,
    classification: String,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    next_action: String,
    boundaries: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct GatePacket {
    schema: String,
    status: String,
    score: f64,
    ledger_entry: LedgerEntry,
    output_dir: String,
    ledger_jsonl: String,
    latest_json: String,
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

fn sha256_bytes(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn read_json(path: &Path) -> Option<Value> {
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
}

fn snapshot(name: &str, path: &Path, score_key: Option<&str>) -> SnapshotRef {
    let exists = path.exists();
    let bytes = if exists {
        fs::read(path).unwrap_or_default()
    } else {
        Vec::new()
    };
    let value = if exists {
        serde_json::from_slice::<Value>(&bytes).ok()
    } else {
        None
    };
    let status = value
        .as_ref()
        .and_then(|v| {
            v.get("status")
                .or_else(|| v.get("verdict"))
                .or_else(|| v.get("level"))
        })
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let score = value.as_ref().and_then(|v| {
        score_key
            .and_then(|k| v.get(k))
            .and_then(|x| x.as_f64())
            .or_else(|| v.get("score").and_then(|x| x.as_f64()))
            .or_else(|| v.get("total_score").and_then(|x| x.as_f64()))
            .or_else(|| v.get("closed_loop_score").and_then(|x| x.as_f64()))
            .or_else(|| v.get("critic_score").and_then(|x| x.as_f64()))
    });
    SnapshotRef {
        name: name.to_string(),
        path: path.display().to_string(),
        exists,
        sha256: if exists {
            Some(sha256_bytes(&bytes))
        } else {
            None
        },
        status,
        score,
    }
}

fn command(program: &str, args: &[&str]) -> (bool, String) {
    match Command::new(program).args(args).output() {
        Ok(o) => {
            let mut s = String::new();
            s.push_str(&String::from_utf8_lossy(&o.stdout));
            s.push_str(&String::from_utf8_lossy(&o.stderr));
            (o.status.success(), s)
        }
        Err(e) => (false, e.to_string()),
    }
}

fn main() {
    let h = home();
    let out_dir =
        h.join(".hermes/workspace/pgg-archon-governance/heartbeat-replay-ledger-gate-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");

    let p1 = h.join(".hermes/workspace/pgg-archon-governance/control-loop-trace-v1-20260618/control_loop_trace.json");
    let p2 = h.join(".hermes/workspace/pgg-archon-governance/durable-task-object-v1-20260618/durable_task_object.json");
    let p3 = h.join(".hermes/workspace/pgg-archon-governance/actor-critic-review-gate-v1-20260618/actor_critic_review.json");
    let p4 = h.join(".hermes/workspace/pgg-archon-governance/control-curriculum-eval-pack-v1-20260618/control_curriculum_eval_pack.json");
    let p5 = h.join(".hermes/workspace/pgg-archon-governance/heartbeat-mapping-gate-v1-20260618/heartbeat_mapping_gate.json");
    let health = h.join(".hermes/data/health-monitor/latest.json");

    let mut watch: Vec<String> = Vec::new();
    let blocked: Vec<String> = Vec::new();

    let chain = vec![
        snapshot("P1_CONTROL_LOOP_TRACE", &p1, Some("closed_loop_score")),
        snapshot("P2_DURABLE_TASK_OBJECT", &p2, Some("source_score")),
        snapshot("P3_ACTOR_CRITIC_REVIEW", &p3, Some("critic_score")),
        snapshot("P4_CONTROL_CURRICULUM_EVAL", &p4, Some("total_score")),
    ];
    if chain.iter().any(|s| !s.exists) {
        watch.push("One or more P1-P4 control-chain artifacts are missing.".to_string());
    }

    let heartbeat_mapping = snapshot("P5_HEARTBEAT_MAPPING", &p5, Some("score"));
    if !heartbeat_mapping.exists {
        watch.push("P5 heartbeat mapping evidence missing.".to_string());
    }

    let health_snapshot = snapshot("PGG_HEALTH_MONITOR_LATEST", &health, None);
    if !health_snapshot.exists || health_snapshot.status.as_deref() != Some("PASS") {
        watch.push("Health latest snapshot is missing or not PASS.".to_string());
    }

    let (launch_ok, launch_out) = command("launchctl", &["list"]);
    let launchd_snapshot = serde_json::json!({
        "collector": "launchctl list",
        "ok": launch_ok,
        "has_autonomy_default_loop": launch_out.contains("ai.hermes.pgg-autonomy-default-loop"),
        "has_batch_evolution_scheduler": launch_out.contains("ai.hermes.pgg-batch-evolution-scheduler"),
        "pgg_line_count": launch_out.lines().filter(|l| l.contains("ai.hermes.pgg")).count(),
        "sha256": sha256_bytes(launch_out.as_bytes()),
    });
    if !launchd_snapshot
        .get("has_autonomy_default_loop")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
    {
        watch.push("launchctl snapshot does not show autonomy default-loop.".to_string());
    }

    let verification_snapshot = serde_json::json!({
        "hermes_goal_exists": h.join(".hermes/bin/hermes-goal").exists(),
        "p4_status": chain.get(3).and_then(|s| s.status.clone()),
        "p4_score": chain.get(3).and_then(|s| s.score),
        "p5_status": heartbeat_mapping.status,
        "p5_score": heartbeat_mapping.score,
    });
    if !verification_snapshot
        .get("hermes_goal_exists")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
    {
        watch.push("hermes-goal binary missing.".to_string());
    }

    // Preserve inherited WATCH from P5 instead of hiding it.
    if let Some(v) = read_json(&p5) {
        if let Some(arr) = v.get("watch_items").and_then(|x| x.as_array()) {
            for item in arr {
                if let Some(s) = item.as_str() {
                    watch.push(format!("P5 inherited WATCH: {s}"));
                }
            }
        }
    }

    watch.sort();
    watch.dedup();

    let chain_score: f64 = chain
        .iter()
        .map(|s| if s.exists { 15.0 } else { 5.0 })
        .sum();
    let map_score = if heartbeat_mapping.exists { 15.0 } else { 5.0 };
    let health_score = if health_snapshot.status.as_deref() == Some("PASS") {
        10.0
    } else {
        4.0
    };
    let launch_score = if launchd_snapshot
        .get("has_autonomy_default_loop")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
    {
        10.0
    } else {
        4.0
    };
    let verify_score = if verification_snapshot
        .get("hermes_goal_exists")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
    {
        5.0
    } else {
        2.0
    };
    let score = chain_score + map_score + health_score + launch_score + verify_score;

    let status = if blocked.is_empty() && score >= 90.0 {
        if watch.is_empty() {
            "PASS_HEARTBEAT_REPLAY_LEDGER"
        } else {
            "PASS_HEARTBEAT_REPLAY_LEDGER_WITH_WATCH"
        }
    } else if blocked.is_empty() {
        "PARTIAL_HEARTBEAT_REPLAY_LEDGER_WITH_WATCH"
    } else {
        "BLOCKED_HEARTBEAT_REPLAY_LEDGER"
    }
    .to_string();

    let pulse_id = format!(
        "hbr-{}",
        &sha256_bytes(format!("{}{:?}", now_epoch(), chain).as_bytes())[..16]
    );
    let entry = LedgerEntry {
        pulse_id,
        created_at_epoch: now_epoch(),
        source_control_chain: chain,
        heartbeat_mapping,
        health_snapshot,
        launchd_snapshot,
        verification_snapshot,
        classification: status.clone(),
        watch_items: watch.clone(),
        blocked_items: blocked.clone(),
        next_action: "P7 candidate: launchd LIGHT heartbeat runner only after explicit runtime/scheduler authorization.".to_string(),
        boundaries: vec![
            "Replay ledger is read-only evidence capture; it does not schedule or execute runtime actions.".to_string(),
            "No provider/config/credential/security/scheduler mutation.".to_string(),
            "OpenClaw Heartbeat remains mapped to local Hermes/PGG mechanisms; no external runtime copied.".to_string(),
            "PASS proves bounded local ledger generation, not full autonomy/full AGI/T5/external benchmark.".to_string(),
        ],
    };

    let latest_json = out_dir.join("latest_heartbeat_replay_entry.json");
    let ledger_jsonl = out_dir.join("heartbeat_replay_ledger.jsonl");
    let report_md = out_dir.join("HEARTBEAT_REPLAY_LEDGER_GATE.md");
    let acceptance_json = out_dir.join("ACCEPTANCE.json");

    let entry_line = serde_json::to_string(&entry).expect("entry json");
    fs::write(&latest_json, serde_json::to_string_pretty(&entry).unwrap()).expect("write latest");
    let mut previous = String::new();
    if ledger_jsonl.exists() {
        previous = fs::read_to_string(&ledger_jsonl).unwrap_or_default();
        if !previous.ends_with('\n') && !previous.is_empty() {
            previous.push('\n');
        }
    }
    previous.push_str(&entry_line);
    previous.push('\n');
    fs::write(&ledger_jsonl, previous).expect("write ledger jsonl");

    let packet = GatePacket {
        schema: "pgg_heartbeat_replay_ledger_gate/v1".to_string(),
        status: status.clone(),
        score,
        ledger_entry: entry.clone(),
        output_dir: out_dir.display().to_string(),
        ledger_jsonl: ledger_jsonl.display().to_string(),
        latest_json: latest_json.display().to_string(),
        report_md: report_md.display().to_string(),
        acceptance_json: acceptance_json.display().to_string(),
    };

    let mut md = String::new();
    md.push_str("# PGG Heartbeat Replay Ledger Gate v1\n\n");
    md.push_str(&format!(
        "- status: `{}`\n- score: `{:.1}`\n- pulse_id: `{}`\n- watch: `{}`\n- blocked: `{}`\n\n",
        status,
        score,
        entry.pulse_id,
        watch.len(),
        blocked.len()
    ));
    md.push_str("## Snapshots\n\n");
    for s in &entry.source_control_chain {
        md.push_str(&format!(
            "- {}: exists={} status={:?} score={:?}\n",
            s.name, s.exists, s.status, s.score
        ));
    }
    md.push_str(&format!(
        "- P5: exists={} status={:?} score={:?}\n",
        entry.heartbeat_mapping.exists,
        entry.heartbeat_mapping.status,
        entry.heartbeat_mapping.score
    ));
    md.push_str(&format!(
        "- Health: exists={} status={:?}\n",
        entry.health_snapshot.exists, entry.health_snapshot.status
    ));
    md.push_str("\n## WATCH\n\n");
    if watch.is_empty() {
        md.push_str("- none\n");
    } else {
        for w in &watch {
            md.push_str(&format!("- {}\n", w));
        }
    }
    md.push_str("\n## Boundary\n\n");
    for b in &entry.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(&report_md, md).expect("write report");

    let acceptance = serde_json::json!({
        "schema": "pgg_heartbeat_replay_ledger_acceptance/v1",
        "status": status,
        "score": score,
        "pulse_id": entry.pulse_id,
        "watch_count": watch.len(),
        "blocked_count": blocked.len(),
        "ledger_jsonl": ledger_jsonl,
        "latest_json": latest_json,
        "report_md": report_md,
        "latest_sha256": sha256_bytes(&serde_json::to_vec_pretty(&entry).unwrap()),
        "next_action": entry.next_action,
    });
    fs::write(
        &acceptance_json,
        serde_json::to_string_pretty(&acceptance).unwrap(),
    )
    .expect("write acceptance");

    println!("{}", serde_json::to_string_pretty(&packet).unwrap());
}
