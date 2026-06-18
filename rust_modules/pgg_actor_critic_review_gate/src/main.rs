use chrono::Utc;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

const SCHEMA: &str = "pgg_actor_critic_review_gate/v1";
const DEFAULT_DTO: &str = "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/durable-task-object-v1-20260618/durable_task_object.json";
const DEFAULT_OUT_DIR: &str =
    "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/actor-critic-review-gate-v1-20260618";

#[derive(Debug, Deserialize)]
struct DtoStatus {
    current: String,
    lifecycle: Vec<String>,
    allowed_transitions: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct DurableTaskObject {
    schema: String,
    task_id: String,
    goal: String,
    source_trace: String,
    source_score: f64,
    risk_level: String,
    gate_level: String,
    status: DtoStatus,
    observe: Vec<String>,
    error: Vec<String>,
    plan: Vec<String>,
    act: Vec<String>,
    verify: Vec<String>,
    settle: Vec<String>,
    evidence_paths: Vec<String>,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    next_action: String,
    boundaries: Vec<String>,
    quality_gates: Vec<String>,
}

#[derive(Debug, Serialize)]
struct ActorPacket {
    task_id: String,
    dto_schema: String,
    goal: String,
    source_trace: String,
    claim: String,
    source_score: f64,
    lifecycle_state: String,
    evidence_paths: Vec<String>,
    boundary_count: usize,
    quality_gate_count: usize,
}

#[derive(Debug, Serialize)]
struct CriticCheck {
    name: String,
    status: String,
    score: f64,
    evidence: String,
}

#[derive(Debug, Serialize)]
struct ReviewReport {
    schema: String,
    review_id: String,
    generated_at: String,
    dto_path: String,
    dto_sha256: String,
    actor: ActorPacket,
    critic_checks: Vec<CriticCheck>,
    critic_score: f64,
    verdict: String,
    next_action: String,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    boundaries: Vec<String>,
}

#[derive(Debug, Serialize)]
struct CliResult {
    schema: String,
    status: String,
    review_id: String,
    verdict: String,
    score: f64,
    output_dir: String,
    review_json: String,
    review_md: String,
    acceptance_json: String,
    watch: usize,
    blocked: usize,
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    digest.iter().map(|b| format!("{:02x}", b)).collect()
}

fn arg_value(args: &[String], flag: &str, default: &str) -> String {
    args.windows(2)
        .find(|w| w[0] == flag)
        .map(|w| w[1].clone())
        .unwrap_or_else(|| default.to_string())
}

fn check(name: &str, pass: bool, score: f64, evidence: String) -> CriticCheck {
    CriticCheck {
        name: name.to_string(),
        status: if pass { "PASS" } else { "BLOCKED" }.to_string(),
        score: if pass { score } else { 0.0 },
        evidence,
    }
}

fn build_review(dto: &DurableTaskObject, dto_path: &Path, dto_sha: &str) -> ReviewReport {
    let actor = ActorPacket {
        task_id: dto.task_id.clone(),
        dto_schema: dto.schema.clone(),
        goal: dto.goal.clone(),
        source_trace: dto.source_trace.clone(),
        claim: format!(
            "DTO {} claims {} with risk {} and gate {}",
            dto.task_id, dto.status.current, dto.risk_level, dto.gate_level
        ),
        source_score: dto.source_score,
        lifecycle_state: dto.status.current.clone(),
        evidence_paths: dto.evidence_paths.clone(),
        boundary_count: dto.boundaries.len(),
        quality_gate_count: dto.quality_gates.len(),
    };

    let has_six_stage = !dto.observe.is_empty()
        && !dto.error.is_empty()
        && !dto.plan.is_empty()
        && !dto.act.is_empty()
        && !dto.verify.is_empty()
        && !dto.settle.is_empty();
    let has_evidence = dto.evidence_paths.iter().any(|p| p.ends_with(".json"));
    let no_blocked = dto.blocked_items.is_empty() && !dto.status.current.contains("blocked");
    let boundary_kept = dto.boundaries.iter().any(|b| b.contains("no provider"))
        || dto
            .quality_gates
            .iter()
            .any(|g| g.contains("provider_config_security_scheduler"));
    let runtime_not_auto = dto.risk_level.contains("WATCH")
        && dto.gate_level.contains("review")
        && dto
            .next_action
            .contains("before scheduler/runtime mutation");
    let lifecycle_ok = dto.status.lifecycle.iter().any(|s| s == "verified")
        && dto
            .status
            .allowed_transitions
            .iter()
            .any(|s| s.contains("review"));

    let critic_checks = vec![
        check(
            "six_stage_integrity",
            has_six_stage,
            20.0,
            format!(
                "observe/error/plan/act/verify/settle lengths = {}/{}/{}/{}/{}/{}",
                dto.observe.len(),
                dto.error.len(),
                dto.plan.len(),
                dto.act.len(),
                dto.verify.len(),
                dto.settle.len()
            ),
        ),
        check(
            "evidence_readback",
            has_evidence,
            20.0,
            format!("evidence_paths={}", dto.evidence_paths.len()),
        ),
        check(
            "no_blocked_items",
            no_blocked,
            20.0,
            format!("blocked_items={}", dto.blocked_items.len()),
        ),
        check(
            "boundary_preserved",
            boundary_kept,
            20.0,
            format!(
                "boundaries={} quality_gates={}",
                dto.boundaries.len(),
                dto.quality_gates.len()
            ),
        ),
        check(
            "runtime_mutation_not_auto_approved",
            runtime_not_auto,
            10.0,
            format!(
                "risk={} gate={} next_action={}",
                dto.risk_level, dto.gate_level, dto.next_action
            ),
        ),
        check(
            "lifecycle_review_path",
            lifecycle_ok,
            10.0,
            format!(
                "state={} transitions={:?}",
                dto.status.current, dto.status.allowed_transitions
            ),
        ),
    ];
    let critic_score: f64 = critic_checks.iter().map(|c| c.score).sum();
    let blocked_items: Vec<String> = critic_checks
        .iter()
        .filter(|c| c.status == "BLOCKED")
        .map(|c| c.name.clone())
        .collect();
    let mut watch_items = dto.watch_items.clone();
    if dto.risk_level.contains("WATCH") {
        watch_items
            .push("DTO still requires review before runtime/scheduler adoption.".to_string());
    }
    let verdict = if !blocked_items.is_empty() {
        "BLOCK".to_string()
    } else if !watch_items.is_empty() {
        "APPROVE_READONLY_REVISE_BEFORE_RUNTIME".to_string()
    } else {
        "APPROVE_READONLY".to_string()
    };
    let next_action = if verdict == "BLOCK" {
        "Fix blocked critic checks, rerun gate, do not promote.".to_string()
    } else {
        "Eligible for P4 Control Curriculum Eval Pack; runtime/scheduler adoption still gated."
            .to_string()
    };

    ReviewReport {
        schema: SCHEMA.to_string(),
        review_id: format!(
            "acr-{}",
            &sha256_hex(format!("{}:{}", dto.task_id, dto_sha).as_bytes())[..16]
        ),
        generated_at: Utc::now().to_rfc3339(),
        dto_path: dto_path.display().to_string(),
        dto_sha256: dto_sha.to_string(),
        actor,
        critic_checks,
        critic_score,
        verdict,
        next_action,
        watch_items,
        blocked_items,
        boundaries: vec![
            "rule-based independent critic over DTO evidence".to_string(),
            "no LLM/provider call in this Rust gate".to_string(),
            "no provider/config/credential/security/scheduler mutation".to_string(),
            "not legal correctness/full AGI/T5/external benchmark proof".to_string(),
        ],
    }
}

fn write_md(report: &ReviewReport, path: &Path) -> std::io::Result<()> {
    let mut md = String::new();
    md.push_str("# Actor-Critic Review Gate v1\n\n");
    md.push_str(&format!("- Review ID: `{}`\n", report.review_id));
    md.push_str(&format!("- Verdict: `{}`\n", report.verdict));
    md.push_str(&format!("- Score: `{}`\n", report.critic_score));
    md.push_str(&format!("- DTO: `{}`\n\n", report.dto_path));
    md.push_str("## Actor\n\n");
    md.push_str(&format!("- Claim: {}\n", report.actor.claim));
    md.push_str(&format!(
        "- Evidence paths: {}\n\n",
        report.actor.evidence_paths.len()
    ));
    md.push_str("## Critic checks\n\n");
    for c in &report.critic_checks {
        md.push_str(&format!(
            "- `{}` — {} — score {} — {}\n",
            c.name, c.status, c.score, c.evidence
        ));
    }
    md.push_str("\n## Next action\n\n");
    md.push_str(&format!("{}\n", report.next_action));
    md.push_str("\n## Boundaries\n\n");
    for b in &report.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(path, md)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let dto_path = PathBuf::from(arg_value(&args, "--dto", DEFAULT_DTO));
    let out_dir = PathBuf::from(arg_value(&args, "--out-dir", DEFAULT_OUT_DIR));
    let bytes = match fs::read(&dto_path) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("failed_to_read_dto:{}:{}", dto_path.display(), e);
            std::process::exit(2);
        }
    };
    let dto_sha = sha256_hex(&bytes);
    let dto: DurableTaskObject = match serde_json::from_slice(&bytes) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("failed_to_parse_dto:{}:{}", dto_path.display(), e);
            std::process::exit(3);
        }
    };
    let report = build_review(&dto, &dto_path, &dto_sha);
    fs::create_dir_all(&out_dir).unwrap();
    let review_json = out_dir.join("actor_critic_review.json");
    let review_md = out_dir.join("ACTOR_CRITIC_REVIEW.md");
    let acceptance_json = out_dir.join("ACCEPTANCE.json");
    fs::write(&review_json, serde_json::to_string_pretty(&report).unwrap()).unwrap();
    write_md(&report, &review_md).unwrap();
    let status = if report.verdict == "BLOCK" {
        "BLOCKED_ACTOR_CRITIC_REVIEW"
    } else {
        "PASS_ACTOR_CRITIC_REVIEW_WITH_WATCH"
    };
    let result = CliResult {
        schema: report.schema.clone(),
        status: status.to_string(),
        review_id: report.review_id.clone(),
        verdict: report.verdict.clone(),
        score: report.critic_score,
        output_dir: out_dir.display().to_string(),
        review_json: review_json.display().to_string(),
        review_md: review_md.display().to_string(),
        acceptance_json: acceptance_json.display().to_string(),
        watch: report.watch_items.len(),
        blocked: report.blocked_items.len(),
    };
    fs::write(
        &acceptance_json,
        serde_json::to_string_pretty(&result).unwrap(),
    )
    .unwrap();
    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
