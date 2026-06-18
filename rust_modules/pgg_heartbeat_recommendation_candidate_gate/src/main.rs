use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct CandidateTask {
    candidate_id: String,
    source_phase: String,
    title: String,
    trigger: String,
    risk: String,
    apply_allowed: bool,
    required_evidence: Vec<String>,
    suggested_gate: String,
    boundary: String,
    status: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct CandidatePacket {
    schema: String,
    generated_at_epoch: u64,
    status: String,
    score: f64,
    source_plan: String,
    source_plan_sha256: String,
    source_rotation_ledger: String,
    rotation_entries_scanned: usize,
    candidates: Vec<CandidateTask>,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    boundaries: Vec<String>,
    output_dir: String,
    latest_candidates_json: String,
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
fn read_jsonl_count(path: &Path) -> usize {
    fs::read_to_string(path)
        .map(|s| s.lines().filter(|l| !l.trim().is_empty()).count())
        .unwrap_or(0)
}

fn main() {
    let h = home();
    let out_dir = h.join(".hermes/workspace/pgg-archon-governance/heartbeat-recommendation-candidate-gate-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");

    let plan_path = h.join(".hermes/workspace/pgg-archon-governance/heartbeat-evolution-planner-v1-20260618/latest_evolution_plan.json");
    let rotation_ledger = h.join(".hermes/workspace/pgg-archon-governance/heartbeat-plan-rotation-runner-v1-20260618/plan_rotation_runner_ledger.jsonl");
    let plan_bytes = fs::read(&plan_path).unwrap_or_default();
    let plan = read_json(&plan_path);
    let rotation_count = read_jsonl_count(&rotation_ledger);

    let mut watch_items: Vec<String> = Vec::new();
    let blocked_items: Vec<String> = Vec::new();
    if plan == Value::Null {
        watch_items.push("Source P10 plan missing or unreadable.".to_string());
    }
    if rotation_count < 1 {
        watch_items.push(
            "P11 rotation ledger has no entries; candidates are based on static plan only."
                .to_string(),
        );
    }

    let mut candidates: Vec<CandidateTask> = Vec::new();
    if let Some(steps) = plan.get("steps").and_then(|v| v.as_array()) {
        for step in steps {
            let phase = step
                .get("phase")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown");
            let objective = step
                .get("objective")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown objective");
            let trigger = step
                .get("trigger")
                .and_then(|v| v.as_str())
                .unwrap_or("manual review");
            let boundary = step
                .get("boundary")
                .and_then(|v| v.as_str())
                .unwrap_or("no auto apply");
            let risk = if objective.to_lowercase().contains("audit") {
                "LOW_READONLY"
            } else if objective.to_lowercase().contains("gap") {
                "LOW_READONLY_ANALYSIS"
            } else {
                "MEDIUM_REQUIRES_SEPARATE_GATE"
            };
            let gate = if objective.to_lowercase().contains("audit") {
                "pgg-heartbeat-alert-summarizer"
            } else if objective.to_lowercase().contains("gap") {
                "pgg-heartbeat-recommendation-candidate-gate"
            } else {
                "future-specific-candidate-gate-required"
            };
            let id_material = format!("{}:{}:{}", phase, objective, trigger);
            candidates.push(CandidateTask {
                candidate_id: format!("rec-{}", &sha256_hex(id_material.as_bytes())[..12]),
                source_phase: phase.to_string(),
                title: objective.to_string(),
                trigger: trigger.to_string(),
                risk: risk.to_string(),
                apply_allowed: false,
                required_evidence: vec![
                    plan_path.display().to_string(),
                    rotation_ledger.display().to_string(),
                    "EVOLUTION_MANIFEST.json readback before any promotion".to_string(),
                ],
                suggested_gate: gate.to_string(),
                boundary: boundary.to_string(),
                status: "CANDIDATE_ONLY_NOT_EXECUTED".to_string(),
            });
        }
    }

    if candidates.is_empty() {
        watch_items.push("No candidate tasks generated from P10 plan.".to_string());
    }
    let status = if blocked_items.is_empty() && !candidates.is_empty() {
        "PASS_RECOMMENDATION_CANDIDATES_GENERATED_WITH_WATCH"
    } else {
        "PARTIAL_RECOMMENDATION_CANDIDATES_WITH_WATCH"
    }
    .to_string();
    let score = if !candidates.is_empty() { 100.0 } else { 50.0 };

    let latest_candidates_json = out_dir.join("latest_recommendation_candidates.json");
    let report_md = out_dir.join("RECOMMENDATION_CANDIDATES.md");
    let acceptance_json = out_dir.join("ACCEPTANCE.json");

    let packet = CandidatePacket {
        schema: "pgg_heartbeat_recommendation_candidate_gate/v1".to_string(),
        generated_at_epoch: now_epoch(),
        status: status.clone(),
        score,
        source_plan: plan_path.display().to_string(),
        source_plan_sha256: sha256_hex(&plan_bytes),
        source_rotation_ledger: rotation_ledger.display().to_string(),
        rotation_entries_scanned: rotation_count,
        candidates: candidates.clone(),
        watch_items: watch_items.clone(),
        blocked_items: blocked_items.clone(),
        boundaries: vec![
            "Candidate gate is read-only and does not execute, fix, commit, or mutate config.".to_string(),
            "All candidates have apply_allowed=false.".to_string(),
            "Promotion requires a separate scoped gate and explicit authorization for any mutation.".to_string(),
            "No provider/LLM/network call.".to_string(),
        ],
        output_dir: out_dir.display().to_string(),
        latest_candidates_json: latest_candidates_json.display().to_string(),
        report_md: report_md.display().to_string(),
        acceptance_json: acceptance_json.display().to_string(),
    };
    let json = serde_json::to_string_pretty(&packet).unwrap();
    fs::write(&latest_candidates_json, &json).expect("write candidates");

    let mut md = String::new();
    md.push_str("# PGG Heartbeat Recommendation Candidates v1\n\n");
    md.push_str(&format!(
        "- status: `{}`\n- score: `{}`\n- candidates: `{}`\n- rotation_entries_scanned: `{}`\n\n",
        status,
        score,
        candidates.len(),
        rotation_count
    ));
    md.push_str("## Candidates\n\n");
    for c in &candidates {
        md.push_str(&format!("### {}\n- title: {}\n- risk: {}\n- apply_allowed: {}\n- suggested_gate: {}\n- boundary: {}\n\n", c.candidate_id, c.title, c.risk, c.apply_allowed, c.suggested_gate, c.boundary));
    }
    md.push_str("## Boundaries\n\n");
    for b in &packet.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(&report_md, md).expect("write report");

    let acceptance = serde_json::json!({
        "schema":"pgg_heartbeat_recommendation_candidate_acceptance/v1",
        "status":status,
        "score":score,
        "candidate_count":candidates.len(),
        "rotation_entries_scanned":rotation_count,
        "watch_count":watch_items.len(),
        "blocked_count":blocked_items.len(),
        "latest_candidates_json":latest_candidates_json,
        "report_md":report_md,
        "acceptance_json":acceptance_json,
        "next_action":"P13 candidate: candidate prioritizer/scoring gate; still no auto-apply."
    });
    fs::write(
        &acceptance_json,
        serde_json::to_string_pretty(&acceptance).unwrap(),
    )
    .expect("write acceptance");

    println!("{}", serde_json::to_string_pretty(&packet).unwrap());
}
