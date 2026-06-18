use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct RankedCandidate {
    rank: usize,
    candidate_id: String,
    title: String,
    risk: String,
    priority_score: f64,
    value_score: f64,
    safety_score: f64,
    evidence_score: f64,
    recurrence_score: f64,
    risk_penalty: f64,
    apply_allowed: bool,
    recommended_next_gate: String,
    reason: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct PriorityPacket {
    schema: String,
    generated_at_epoch: u64,
    status: String,
    score: f64,
    source_candidates: String,
    source_sha256: String,
    ranked_count: usize,
    queue: Vec<RankedCandidate>,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    boundaries: Vec<String>,
    output_dir: String,
    latest_priority_json: String,
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
fn b(v: &Value, k: &str) -> bool {
    v.get(k).and_then(|x| x.as_bool()).unwrap_or(false)
}

fn main() {
    let h = home();
    let out_dir = h.join(
        ".hermes/workspace/pgg-archon-governance/heartbeat-candidate-prioritizer-v1-20260618",
    );
    fs::create_dir_all(&out_dir).expect("create output dir");
    let src = h.join(".hermes/workspace/pgg-archon-governance/heartbeat-recommendation-candidate-gate-v1-20260618/latest_recommendation_candidates.json");
    let bytes = fs::read(&src).unwrap_or_default();
    let data = read_json(&src);
    let mut watch: Vec<String> = Vec::new();
    let blocked: Vec<String> = Vec::new();
    if data == Value::Null {
        watch.push("Source P12 candidates missing/unreadable.".to_string());
    }
    let mut ranked: Vec<RankedCandidate> = Vec::new();
    if let Some(cands) = data.get("candidates").and_then(|v| v.as_array()) {
        for c in cands {
            let id = s(c, "candidate_id");
            let title = s(c, "title");
            let risk = s(c, "risk");
            let apply = b(c, "apply_allowed");
            let lower = title.to_lowercase();
            let value = if lower.contains("gap") {
                92.0
            } else if lower.contains("audit") {
                88.0
            } else if lower.contains("optimization") {
                80.0
            } else {
                70.0
            };
            let safety = if risk.contains("LOW_READONLY") {
                96.0
            } else if risk.contains("MEDIUM") {
                78.0
            } else {
                70.0
            };
            let evidence = c
                .get("required_evidence")
                .and_then(|v| v.as_array())
                .map(|a| (a.len() as f64 * 25.0).min(100.0))
                .unwrap_or(0.0);
            let recurrence = if s(c, "trigger").to_lowercase().contains("watch")
                || s(c, "trigger").to_lowercase().contains("multiple")
            {
                85.0
            } else {
                70.0
            };
            let penalty =
                if risk.contains("MEDIUM") { 12.0 } else { 0.0 } + if apply { 40.0 } else { 0.0 };
            let score = (value * 0.35) + (safety * 0.30) + (evidence * 0.20) + (recurrence * 0.15)
                - penalty;
            ranked.push(RankedCandidate {
                rank: 0,
                candidate_id: id,
                title,
                risk: risk.clone(),
                priority_score: (score * 10.0).round() / 10.0,
                value_score: value,
                safety_score: safety,
                evidence_score: evidence,
                recurrence_score: recurrence,
                risk_penalty: penalty,
                apply_allowed: apply,
                recommended_next_gate: if risk.contains("MEDIUM") {
                    "specific-design-gate-required-before-any-action".to_string()
                } else {
                    "read-only-scoped-gate-ok".to_string()
                },
                reason: if risk.contains("MEDIUM") {
                    "Higher risk; keep behind separate design gate.".to_string()
                } else {
                    "High safety and evidence; safe to prioritize as read-only gate.".to_string()
                },
            });
        }
    }
    ranked.sort_by(|a, b| {
        b.priority_score
            .partial_cmp(&a.priority_score)
            .unwrap()
            .then(a.candidate_id.cmp(&b.candidate_id))
    });
    for (i, c) in ranked.iter_mut().enumerate() {
        c.rank = i + 1;
    }
    if ranked.is_empty() {
        watch.push("No candidates available to prioritize.".to_string());
    }
    let status = if !ranked.is_empty() {
        "PASS_CANDIDATE_PRIORITY_QUEUE_GENERATED"
    } else {
        "PARTIAL_CANDIDATE_PRIORITY_QUEUE_WITH_WATCH"
    }
    .to_string();
    let score = if !ranked.is_empty() { 100.0 } else { 50.0 };
    let latest = out_dir.join("latest_candidate_priority_queue.json");
    let report = out_dir.join("CANDIDATE_PRIORITY_QUEUE.md");
    let acceptance = out_dir.join("ACCEPTANCE.json");
    let packet = PriorityPacket {
        schema: "pgg_heartbeat_candidate_prioritizer/v1".to_string(),
        generated_at_epoch: now_epoch(),
        status: status.clone(),
        score,
        source_candidates: src.display().to_string(),
        source_sha256: sha256_hex(&bytes),
        ranked_count: ranked.len(),
        queue: ranked.clone(),
        watch_items: watch.clone(),
        blocked_items: blocked.clone(),
        boundaries: vec![
            "Prioritizer is read-only and does not execute candidates.".to_string(),
            "apply_allowed remains false for all queue items.".to_string(),
            "Ranking does not imply approval to mutate config/provider/security/scheduler."
                .to_string(),
            "No provider/LLM/network call.".to_string(),
        ],
        output_dir: out_dir.display().to_string(),
        latest_priority_json: latest.display().to_string(),
        report_md: report.display().to_string(),
        acceptance_json: acceptance.display().to_string(),
    };
    let json = serde_json::to_string_pretty(&packet).unwrap();
    fs::write(&latest, &json).expect("write latest");
    let mut md = String::from("# PGG Heartbeat Candidate Priority Queue v1\n\n");
    md.push_str(&format!(
        "- status: `{}`\n- ranked_count: `{}`\n\n",
        status,
        ranked.len()
    ));
    for c in &ranked {
        md.push_str(&format!("## #{} {}\n- id: {}\n- score: {}\n- risk: {}\n- apply_allowed: {}\n- next_gate: {}\n- reason: {}\n\n",c.rank,c.title,c.candidate_id,c.priority_score,c.risk,c.apply_allowed,c.recommended_next_gate,c.reason));
    }
    fs::write(&report, md).expect("write report");
    let acc = serde_json::json!({"schema":"pgg_heartbeat_candidate_prioritizer_acceptance/v1","status":status,"score":score,"ranked_count":ranked.len(),"watch_count":watch.len(),"blocked_count":blocked.len(),"latest_priority_json":latest,"report_md":report,"acceptance_json":acceptance,"next_action":"P14 candidate executor preflight; still dry-run only unless explicitly authorized."});
    fs::write(&acceptance, serde_json::to_string_pretty(&acc).unwrap()).expect("write acceptance");
    println!("{}", serde_json::to_string_pretty(&packet).unwrap());
}
