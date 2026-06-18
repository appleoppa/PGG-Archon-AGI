use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Cluster {
    key: String,
    severity: String,
    count: usize,
    first_seen_epoch: Option<u64>,
    last_seen_epoch: Option<u64>,
    sample: String,
    action: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct AlertPacket {
    schema: String,
    generated_at_epoch: u64,
    status: String,
    alert_level: String,
    runner_entries_scanned: usize,
    replay_entries_scanned: usize,
    unique_watch_clusters: usize,
    unique_blocked_clusters: usize,
    repeated_watch_count: usize,
    clusters: Vec<Cluster>,
    latest_runner_classification: Option<String>,
    latest_replay_classification: Option<String>,
    latest_runner_run_id: Option<String>,
    latest_replay_pulse_id: Option<String>,
    boundaries: Vec<String>,
    output_dir: String,
    latest_alert_json: String,
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

fn read_jsonl(path: &Path) -> Vec<Value> {
    let text = fs::read_to_string(path).unwrap_or_default();
    text.lines()
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .collect()
}

fn norm_key(s: &str) -> String {
    let lower = s.to_lowercase();
    if lower.contains("health-monitor")
        || lower.contains("health monitor")
        || lower.contains("pgg-health")
    {
        "health_monitor_standalone_plist_watch".to_string()
    } else if lower.contains("production")
        || lower.contains("full agi")
        || lower.contains("t5")
        || lower.contains("runtime")
    {
        "bounded_runtime_non_production_boundary".to_string()
    } else if lower.contains("launchctl") || lower.contains("launchd") {
        "launchd_visibility_watch".to_string()
    } else if lower.contains("blocked") {
        "blocked_items_present".to_string()
    } else {
        let cleaned: String = lower
            .chars()
            .map(|c| if c.is_ascii_alphanumeric() { c } else { '_' })
            .collect();
        cleaned
            .split('_')
            .filter(|p| !p.is_empty())
            .take(8)
            .collect::<Vec<_>>()
            .join("_")
    }
}

fn add_cluster(
    map: &mut BTreeMap<String, Cluster>,
    key: String,
    severity: &str,
    msg: &str,
    epoch: Option<u64>,
) {
    map.entry(format!("{}::{}", severity, key.clone()))
        .and_modify(|c| {
            c.count += 1;
            c.last_seen_epoch = epoch.or(c.last_seen_epoch);
            if c.first_seen_epoch.is_none() {
                c.first_seen_epoch = epoch;
            }
        })
        .or_insert_with(|| Cluster {
            key,
            severity: severity.to_string(),
            count: 1,
            first_seen_epoch: epoch,
            last_seen_epoch: epoch,
            sample: msg.to_string(),
            action: if severity == "BLOCKED" {
                "Immediate human/LLM review before next runtime expansion.".to_string()
            } else {
                "Keep as compact WATCH; do not notify repeatedly unless count or severity changes."
                    .to_string()
            },
        });
}

fn collect_items(entries: &[Value], map: &mut BTreeMap<String, Cluster>) {
    for e in entries {
        let epoch = e.get("created_at_epoch").and_then(|v| v.as_u64());
        if let Some(arr) = e.get("watch_items").and_then(|v| v.as_array()) {
            for item in arr {
                if let Some(s) = item.as_str() {
                    add_cluster(map, norm_key(s), "WATCH", s, epoch);
                }
            }
        }
        if let Some(arr) = e.get("blocked_items").and_then(|v| v.as_array()) {
            for item in arr {
                if let Some(s) = item.as_str() {
                    add_cluster(map, norm_key(s), "BLOCKED", s, epoch);
                }
            }
        }
        // Runner stores replay_watch_count; convert it to a compact inherited cluster without exploding every run.
        if let Some(n) = e.get("replay_watch_count").and_then(|v| v.as_u64()) {
            if n > 0 {
                add_cluster(
                    map,
                    "inherited_replay_watch_count".to_string(),
                    "WATCH",
                    &format!("Runner inherited {n} replay WATCH items."),
                    epoch,
                );
            }
        }
        if let Some(n) = e.get("replay_blocked_count").and_then(|v| v.as_u64()) {
            if n > 0 {
                add_cluster(
                    map,
                    "inherited_replay_blocked_count".to_string(),
                    "BLOCKED",
                    &format!("Runner inherited {n} replay BLOCKED items."),
                    epoch,
                );
            }
        }
    }
}

fn main() {
    let h = home();
    let out_dir =
        h.join(".hermes/workspace/pgg-archon-governance/heartbeat-alert-summarizer-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");

    let runner_ledger = h.join(".hermes/workspace/pgg-archon-governance/heartbeat-light-runner-v1-20260618/heartbeat_light_runner_ledger.jsonl");
    let replay_ledger = h.join(".hermes/workspace/pgg-archon-governance/heartbeat-replay-ledger-gate-v1-20260618/heartbeat_replay_ledger.jsonl");
    let runner_entries = read_jsonl(&runner_ledger);
    let replay_entries = read_jsonl(&replay_ledger);

    let mut cluster_map: BTreeMap<String, Cluster> = BTreeMap::new();
    collect_items(&runner_entries, &mut cluster_map);
    collect_items(&replay_entries, &mut cluster_map);

    let mut clusters: Vec<Cluster> = cluster_map.into_values().collect();
    clusters.sort_by(|a, b| {
        b.severity
            .cmp(&a.severity)
            .then(b.count.cmp(&a.count))
            .then(a.key.cmp(&b.key))
    });

    let unique_watch: BTreeSet<String> = clusters
        .iter()
        .filter(|c| c.severity == "WATCH")
        .map(|c| c.key.clone())
        .collect();
    let unique_blocked: BTreeSet<String> = clusters
        .iter()
        .filter(|c| c.severity == "BLOCKED")
        .map(|c| c.key.clone())
        .collect();
    let repeated_watch_count = clusters
        .iter()
        .filter(|c| c.severity == "WATCH" && c.count > 1)
        .count();

    let latest_runner = runner_entries.last();
    let latest_replay = replay_entries.last();
    let latest_runner_classification = latest_runner
        .and_then(|v| v.get("classification"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let latest_replay_classification = latest_replay
        .and_then(|v| v.get("classification"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let latest_runner_run_id = latest_runner
        .and_then(|v| v.get("run_id"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let latest_replay_pulse_id = latest_replay
        .and_then(|v| v.get("pulse_id"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let alert_level = if !unique_blocked.is_empty() {
        "HIGH_BLOCKED"
    } else if !unique_watch.is_empty() {
        "LOW_WATCH_COMPACTED"
    } else {
        "GREEN"
    }
    .to_string();
    let status = if !unique_blocked.is_empty() {
        "BLOCKED_HEARTBEAT_ALERT_SUMMARY"
    } else if !unique_watch.is_empty() {
        "PASS_HEARTBEAT_ALERT_SUMMARY_WITH_COMPACTED_WATCH"
    } else {
        "PASS_HEARTBEAT_ALERT_SUMMARY_GREEN"
    }
    .to_string();

    let latest_alert_json = out_dir.join("latest_heartbeat_alert_packet.json");
    let report_md = out_dir.join("HEARTBEAT_ALERT_SUMMARY.md");
    let acceptance_json = out_dir.join("ACCEPTANCE.json");

    let packet = AlertPacket {
        schema: "pgg_heartbeat_alert_summarizer/v1".to_string(),
        generated_at_epoch: now_epoch(),
        status: status.clone(),
        alert_level: alert_level.clone(),
        runner_entries_scanned: runner_entries.len(),
        replay_entries_scanned: replay_entries.len(),
        unique_watch_clusters: unique_watch.len(),
        unique_blocked_clusters: unique_blocked.len(),
        repeated_watch_count,
        clusters: clusters.clone(),
        latest_runner_classification,
        latest_replay_classification,
        latest_runner_run_id,
        latest_replay_pulse_id,
        boundaries: vec![
            "Summarizer is read-only; it only reads heartbeat ledgers and writes compact alert artifacts.".to_string(),
            "No provider/LLM/network call.".to_string(),
            "No launchd mutation; scheduling remains owned by P7 LIGHT runner.".to_string(),
            "Compacted WATCH is not hidden; it is de-duplicated to prevent alert fatigue.".to_string(),
        ],
        output_dir: out_dir.display().to_string(),
        latest_alert_json: latest_alert_json.display().to_string(),
        report_md: report_md.display().to_string(),
        acceptance_json: acceptance_json.display().to_string(),
    };

    let json = serde_json::to_string_pretty(&packet).expect("packet json");
    fs::write(&latest_alert_json, &json).expect("write latest alert");

    let mut md = String::new();
    md.push_str("# PGG Heartbeat Alert Summary v1\n\n");
    md.push_str(&format!(
        "- status: `{}`\n- alert_level: `{}`\n- runner_entries: `{}`\n- replay_entries: `{}`\n- unique_watch_clusters: `{}`\n- unique_blocked_clusters: `{}`\n- repeated_watch_clusters: `{}`\n- packet_sha256: `{}`\n\n",
        status,
        alert_level,
        packet.runner_entries_scanned,
        packet.replay_entries_scanned,
        packet.unique_watch_clusters,
        packet.unique_blocked_clusters,
        packet.repeated_watch_count,
        sha256_hex(json.as_bytes())
    ));
    md.push_str("## Clusters\n\n");
    if clusters.is_empty() {
        md.push_str("- none\n");
    } else {
        for c in &clusters {
            md.push_str(&format!(
                "- [{}] {} count={} sample={}\n",
                c.severity, c.key, c.count, c.sample
            ));
        }
    }
    md.push_str("\n## Boundaries\n\n");
    for b in &packet.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(&report_md, md).expect("write report");

    let acceptance = serde_json::json!({
        "schema": "pgg_heartbeat_alert_summarizer_acceptance/v1",
        "status": status,
        "alert_level": alert_level,
        "runner_entries_scanned": packet.runner_entries_scanned,
        "replay_entries_scanned": packet.replay_entries_scanned,
        "unique_watch_clusters": packet.unique_watch_clusters,
        "unique_blocked_clusters": packet.unique_blocked_clusters,
        "latest_alert_json": latest_alert_json,
        "report_md": report_md,
        "packet_sha256": sha256_hex(json.as_bytes()),
        "next_action": "P9 candidate: optional alert delivery bridge only after explicit notification-channel authorization."
    });
    fs::write(
        &acceptance_json,
        serde_json::to_string_pretty(&acceptance).unwrap(),
    )
    .expect("write acceptance");

    println!("{}", serde_json::to_string_pretty(&packet).unwrap());
    if !unique_blocked.is_empty() {
        std::process::exit(2);
    }
}
