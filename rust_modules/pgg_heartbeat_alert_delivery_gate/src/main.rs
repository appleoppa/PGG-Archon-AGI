use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize)]
struct DeliveryCandidate {
    schema: String,
    generated_at_epoch: u64,
    status: String,
    mode: String,
    should_send_if_authorized: bool,
    reason: String,
    alert_level: String,
    alert_status: String,
    fingerprint: String,
    previous_fingerprint: Option<String>,
    changed_since_last_candidate: bool,
    candidate_targets: Vec<String>,
    message_preview: String,
    source_alert_packet: String,
    source_alert_sha256: String,
    watch_clusters: usize,
    blocked_clusters: usize,
    boundaries: Vec<String>,
    output_dir: String,
    candidate_json: String,
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

fn read_json(path: &Path) -> Option<Value> {
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str::<Value>(&s).ok())
}

fn safe_str(v: &Value, key: &str) -> String {
    v.get(key)
        .and_then(|x| x.as_str())
        .unwrap_or("UNKNOWN")
        .to_string()
}

fn safe_usize(v: &Value, key: &str) -> usize {
    v.get(key).and_then(|x| x.as_u64()).unwrap_or(0) as usize
}

fn main() {
    let h = home();
    let out_dir =
        h.join(".hermes/workspace/pgg-archon-governance/heartbeat-alert-delivery-gate-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");

    let alert_path = h.join(".hermes/workspace/pgg-archon-governance/heartbeat-alert-summarizer-v1-20260618/latest_heartbeat_alert_packet.json");
    let alert_bytes = fs::read(&alert_path).unwrap_or_default();
    let alert_sha = sha256_hex(&alert_bytes);
    let alert = read_json(&alert_path).unwrap_or(Value::Null);

    let alert_status = safe_str(&alert, "status");
    let alert_level = safe_str(&alert, "alert_level");
    let watch_clusters = safe_usize(&alert, "unique_watch_clusters");
    let blocked_clusters = safe_usize(&alert, "unique_blocked_clusters");
    let runner_entries = safe_usize(&alert, "runner_entries_scanned");
    let replay_entries = safe_usize(&alert, "replay_entries_scanned");

    let clusters = alert
        .get("clusters")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let cluster_summary: Vec<String> = clusters
        .iter()
        .take(5)
        .map(|c| {
            let sev = c.get("severity").and_then(|v| v.as_str()).unwrap_or("?");
            let key = c.get("key").and_then(|v| v.as_str()).unwrap_or("unknown");
            let count = c.get("count").and_then(|v| v.as_u64()).unwrap_or(0);
            format!("[{sev}] {key}×{count}")
        })
        .collect();

    let fingerprint_material = serde_json::json!({
        "alert_level": alert_level,
        "blocked_clusters": blocked_clusters,
        "watch_clusters": watch_clusters,
        "clusters": cluster_summary,
    });
    let fingerprint = sha256_hex(
        serde_json::to_string(&fingerprint_material)
            .unwrap()
            .as_bytes(),
    );

    let state_path = out_dir.join("last_delivery_candidate_state.json");
    let previous_fingerprint = read_json(&state_path).and_then(|v| {
        v.get("fingerprint")
            .and_then(|x| x.as_str())
            .map(|s| s.to_string())
    });
    let changed = previous_fingerprint.as_deref() != Some(&fingerprint);

    let should_send = blocked_clusters > 0 || (changed && alert_level != "GREEN");
    let reason = if blocked_clusters > 0 {
        "BLOCKED cluster exists; delivery would be high priority if authorized."
    } else if changed && alert_level != "GREEN" {
        "Alert fingerprint changed and alert level is non-green; delivery would be useful if authorized."
    } else if alert_level == "GREEN" {
        "Alert is green; no delivery needed."
    } else {
        "No alert change since last candidate; suppress duplicate delivery."
    }.to_string();

    let message_preview = format!(
        "PGG Heartbeat Alert: {alert_level} / {alert_status}\nwatch_clusters={watch_clusters}, blocked_clusters={blocked_clusters}, runner_entries={runner_entries}, replay_entries={replay_entries}\n{}\nsource={}",
        cluster_summary.join("; "),
        alert_path.display()
    );

    let candidate_json = out_dir.join("latest_delivery_candidate.json");
    let report_md = out_dir.join("HEARTBEAT_ALERT_DELIVERY_GATE.md");
    let acceptance_json = out_dir.join("ACCEPTANCE.json");

    let candidate = DeliveryCandidate {
        schema: "pgg_heartbeat_alert_delivery_gate/v1".to_string(),
        generated_at_epoch: now_epoch(),
        status: if should_send {
            "PASS_DELIVERY_CANDIDATE_READY_WITH_AUTH_REQUIRED"
        } else {
            "PASS_DELIVERY_SUPPRESSED_NO_CHANGE"
        }
        .to_string(),
        mode: "dry_run_candidate_only_no_send".to_string(),
        should_send_if_authorized: should_send,
        reason,
        alert_level,
        alert_status,
        fingerprint: fingerprint.clone(),
        previous_fingerprint,
        changed_since_last_candidate: changed,
        candidate_targets: vec!["feishu:oc_d0b2662c68b45174d33bbd6ddf947f71".to_string()],
        message_preview,
        source_alert_packet: alert_path.display().to_string(),
        source_alert_sha256: alert_sha,
        watch_clusters,
        blocked_clusters,
        boundaries: vec![
            "P9A is dry-run only and does not send any message.".to_string(),
            "Actual delivery requires separate P9B authorization and send_message readback."
                .to_string(),
            "Duplicate non-blocking WATCH is suppressed unless fingerprint changes.".to_string(),
            "No provider/LLM/network call is performed by this Rust gate.".to_string(),
        ],
        output_dir: out_dir.display().to_string(),
        candidate_json: candidate_json.display().to_string(),
        report_md: report_md.display().to_string(),
        acceptance_json: acceptance_json.display().to_string(),
    };

    let json = serde_json::to_string_pretty(&candidate).expect("candidate json");
    fs::write(&candidate_json, &json).expect("write candidate");
    fs::write(
        &state_path,
        serde_json::json!({
            "fingerprint": fingerprint,
            "updated_at_epoch": now_epoch(),
            "candidate_json": candidate_json,
        })
        .to_string(),
    )
    .expect("write state");

    let mut md = String::new();
    md.push_str("# PGG Heartbeat Alert Delivery Gate v1\n\n");
    md.push_str(&format!(
        "- status: `{}`\n- mode: `{}`\n- should_send_if_authorized: `{}`\n- changed_since_last_candidate: `{}`\n- alert_level: `{}`\n- watch_clusters: `{}`\n- blocked_clusters: `{}`\n\n",
        candidate.status,
        candidate.mode,
        candidate.should_send_if_authorized,
        candidate.changed_since_last_candidate,
        candidate.alert_level,
        candidate.watch_clusters,
        candidate.blocked_clusters
    ));
    md.push_str("## Message preview\n\n```text\n");
    md.push_str(&candidate.message_preview);
    md.push_str("\n```\n\n## Boundaries\n\n");
    for b in &candidate.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(&report_md, md).expect("write report");

    let acceptance = serde_json::json!({
        "schema": "pgg_heartbeat_alert_delivery_gate_acceptance/v1",
        "status": candidate.status,
        "mode": candidate.mode,
        "should_send_if_authorized": candidate.should_send_if_authorized,
        "changed_since_last_candidate": candidate.changed_since_last_candidate,
        "alert_level": candidate.alert_level,
        "watch_clusters": candidate.watch_clusters,
        "blocked_clusters": candidate.blocked_clusters,
        "candidate_json": candidate.candidate_json,
        "report_md": candidate.report_md,
        "candidate_sha256": sha256_hex(json.as_bytes()),
        "next_action": "P9B may send the message preview to Feishu only with explicit delivery authorization."
    });
    fs::write(
        &acceptance_json,
        serde_json::to_string_pretty(&acceptance).unwrap(),
    )
    .expect("write acceptance");

    println!("{}", serde_json::to_string_pretty(&candidate).unwrap());
}
