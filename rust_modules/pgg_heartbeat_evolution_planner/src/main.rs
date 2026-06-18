use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct PlanStep {
    phase: String,
    objective: String,
    trigger: String,
    entry_points: Vec<String>,
    evidence_inputs: Vec<String>,
    runtime_mode: String,
    boundary: String,
    next_action_if_pass: String,
    next_action_if_watch: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct PlanPacket {
    schema: String,
    generated_at_epoch: u64,
    status: String,
    score: f64,
    source_digest: String,
    source_summary: String,
    current_state: Value,
    step_count: usize,
    steps: Vec<PlanStep>,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    boundaries: Vec<String>,
    output_dir: String,
    latest_plan_json: String,
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

fn read_json(path: &PathBuf) -> Value {
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or(Value::Null)
}

fn main() {
    let h = home();
    let out_dir =
        h.join(".hermes/workspace/pgg-archon-governance/heartbeat-evolution-planner-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");

    let manifest_path = h.join(".hermes/data/EVOLUTION_MANIFEST.json");
    let manifest = read_json(&manifest_path);
    let delivery = read_json(&h.join(".hermes/workspace/pgg-archon-governance/heartbeat-alert-delivery-gate-v1-20260618/latest_delivery_candidate.json"));
    let receipt = read_json(&h.join(".hermes/workspace/pgg-archon-governance/heartbeat-alert-delivery-gate-v1-20260618/FEISHU_DELIVERY_RECEIPT.json"));
    let alert = read_json(&h.join(".hermes/workspace/pgg-archon-governance/heartbeat-alert-summarizer-v1-20260618/latest_heartbeat_alert_packet.json"));
    let runner = read_json(&h.join(".hermes/workspace/pgg-archon-governance/heartbeat-light-runner-v1-20260618/latest_heartbeat_light_runner.json"));
    let replay = read_json(&h.join(".hermes/workspace/pgg-archon-governance/heartbeat-replay-ledger-gate-v1-20260618/latest_heartbeat_replay_entry.json"));

    let digest_material = serde_json::json!({
        "manifest_latest": manifest.get("latest_pgg_heartbeat_alert_delivery_sent_v1"),
        "delivery_status": delivery.get("status"),
        "receipt_status": receipt.get("status"),
        "alert_level": alert.get("alert_level"),
        "runner_classification": runner.get("classification"),
        "replay_classification": replay.get("classification"),
    });
    let source_digest = sha256_hex(serde_json::to_string(&digest_material).unwrap().as_bytes());

    let watch_items = vec![
        "health-monitor lacks a dedicated launchd plist; continue compact WATCH until a separate health job exists or a normalized sentinel is added.".to_string(),
        "Heartbeat chain still has non-blocking WATCH; keep summarizer/delivery suppression active to avoid alert fatigue.".to_string(),
    ];
    let blocked_items: Vec<String> = vec![];

    let steps = vec![
        PlanStep {
            phase: "P10.1".to_string(),
            objective: "Daily self-audit and state readback".to_string(),
            trigger: "Every launchd tick or manual review after any WATCH change".to_string(),
            entry_points: vec![
                "/Users/appleoppa/.hermes/bin/pgg-heartbeat-light-runner".to_string(),
                "/Users/appleoppa/.hermes/bin/pgg-heartbeat-alert-summarizer".to_string(),
                "/Users/appleoppa/.hermes/bin/pgg-heartbeat-alert-delivery-gate".to_string(),
            ],
            evidence_inputs: vec![
                "heartbeat_replay_ledger.jsonl".to_string(),
                "heartbeat_light_runner_ledger.jsonl".to_string(),
                "latest_heartbeat_alert_packet.json".to_string(),
                "FEISHU_DELIVERY_RECEIPT.json".to_string(),
            ],
            runtime_mode: "read_only_observe_and_summarize".to_string(),
            boundary: "No provider/config/credential/security/scheduler mutation.".to_string(),
            next_action_if_pass:
                "Proceed to capability-gap reasoning without changing runtime authority."
                    .to_string(),
            next_action_if_watch:
                "Keep WATCH compacted; do not send duplicates unless fingerprint changes."
                    .to_string(),
        },
        PlanStep {
            phase: "P10.2".to_string(),
            objective: "Capability gap analysis".to_string(),
            trigger: "If watch clusters persist or new domains are missing".to_string(),
            entry_points: vec![
                "pgg-heartbeat-alert-summarizer".to_string(),
                "pgg-heartbeat-evolution-planner".to_string(),
            ],
            evidence_inputs: vec![
                "latest_heartbeat_alert_packet.json".to_string(),
                "EVOLUTION_MANIFEST.json".to_string(),
            ],
            runtime_mode: "read_only_gap_analysis".to_string(),
            boundary: "Suggest only; no automatic fix or scheduler expansion.".to_string(),
            next_action_if_pass: "Add one bounded next-step candidate in the plan.".to_string(),
            next_action_if_watch:
                "Mark as pending design gap and keep it visible in the next plan.".to_string(),
        },
        PlanStep {
            phase: "P10.3".to_string(),
            objective: "Self-optimization recommendation".to_string(),
            trigger: "When gaps are stable and repeated across multiple cycles".to_string(),
            entry_points: vec!["pgg-heartbeat-evolution-planner".to_string()],
            evidence_inputs: vec![
                "launchctl list".to_string(),
                "health latest.json".to_string(),
            ],
            runtime_mode: "recommendation_only".to_string(),
            boundary: "Do not mutate launchd, config, providers, or memory automatically."
                .to_string(),
            next_action_if_pass: "Promote the recommendation into a separate candidate gate."
                .to_string(),
            next_action_if_watch: "Keep the recommendation as WATCH-backed planning context."
                .to_string(),
        },
    ];

    let score = if blocked_items.is_empty() {
        100.0
    } else {
        60.0
    };
    let status = if blocked_items.is_empty() {
        "PASS_EVOLUTION_PLAN_GENERATED_WITH_WATCH"
    } else {
        "BLOCKED_EVOLUTION_PLAN"
    }
    .to_string();

    let latest_plan_json = out_dir.join("latest_evolution_plan.json");
    let report_md = out_dir.join("HEARTBEAT_EVOLUTION_PLAN.md");
    let acceptance_json = out_dir.join("ACCEPTANCE.json");

    let packet = PlanPacket {
        schema: "pgg_heartbeat_evolution_planner/v1".to_string(),
        generated_at_epoch: now_epoch(),
        status: status.clone(),
        score,
        source_digest,
        source_summary: "Plan synthesized from P7/P8/P9 heartbeat chain plus delivery receipt; it remains read-only and is meant to turn recurring Heartbeat observations into a self-improvement loop.".to_string(),
        current_state: serde_json::json!({
            "delivery_sent": receipt.get("status"),
            "alert_status": alert.get("status"),
            "alert_level": alert.get("alert_level"),
            "runner_classification": runner.get("classification"),
            "replay_classification": replay.get("classification"),
        }),
        step_count: steps.len(),
        steps: steps.clone(),
        watch_items: watch_items.clone(),
        blocked_items: blocked_items.clone(),
        boundaries: vec![
            "Planner is read-only and emits strategy, not runtime mutation.".to_string(),
            "No provider/LLM/network call is performed by this Rust gate.".to_string(),
            "No automatic launchd/config/provider/security change.".to_string(),
            "OpenClaw Heartbeat is still mapped to Hermes/PGG local mechanisms only.".to_string(),
        ],
        output_dir: out_dir.display().to_string(),
        latest_plan_json: latest_plan_json.display().to_string(),
        report_md: report_md.display().to_string(),
        acceptance_json: acceptance_json.display().to_string(),
    };

    let json = serde_json::to_string_pretty(&packet).unwrap();
    fs::write(&latest_plan_json, &json).expect("write plan json");

    let mut md = String::new();
    md.push_str("# PGG Heartbeat Evolution Planner v1\n\n");
    md.push_str(&format!(
        "- status: `{}`\n- score: `{}`\n- step_count: `{}`\n- source_digest: `{}`\n\n",
        packet.status, packet.score, packet.step_count, packet.source_digest
    ));
    md.push_str("## Steps\n\n");
    for s in &steps {
        md.push_str(&format!(
            "### {}\n- objective: {}\n- trigger: {}\n- entry_points: {}\n- runtime_mode: {}\n- boundary: {}\n- pass: {}\n- watch: {}\n\n",
            s.phase,
            s.objective,
            s.trigger,
            s.entry_points.join(", "),
            s.runtime_mode,
            s.boundary,
            s.next_action_if_pass,
            s.next_action_if_watch
        ));
    }
    md.push_str("## WATCH\n\n");
    for w in &watch_items {
        md.push_str(&format!("- {}\n", w));
    }
    md.push_str("\n## Boundaries\n\n");
    for b in &packet.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(&report_md, md).expect("write md");

    let acceptance = serde_json::json!({
        "schema": "pgg_heartbeat_evolution_planner_acceptance/v1",
        "status": status,
        "score": score,
        "step_count": steps.len(),
        "watch_items": watch_items,
        "blocked_items": blocked_items,
        "latest_plan_json": latest_plan_json,
        "report_md": report_md,
        "acceptance_json": acceptance_json,
        "source_digest": packet.source_digest,
        "next_action": "P11 candidate: schedule only if a future plan-rotation launchd job is explicitly requested."
    });
    fs::write(
        &acceptance_json,
        serde_json::to_string_pretty(&acceptance).unwrap(),
    )
    .expect("write acceptance");

    println!("{}", serde_json::to_string_pretty(&packet).unwrap());
}
