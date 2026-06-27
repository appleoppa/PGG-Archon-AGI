use chrono::Utc;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

const SCHEMA: &str = "pgg_control_curriculum_eval_pack/v1";
const DEFAULT_REVIEW: &str = "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/actor-critic-review-gate-v1-20260618/actor_critic_review.json";
const DEFAULT_OUT_DIR: &str = "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/control-curriculum-eval-pack-v1-20260618";

#[derive(Debug, Deserialize)]
struct ActorPacket {
    task_id: String,
    source_score: f64,
    evidence_paths: Vec<String>,
    boundary_count: usize,
    quality_gate_count: usize,
}

#[derive(Debug, Deserialize)]
struct ReviewReport {
    schema: String,
    review_id: String,
    actor: ActorPacket,
    critic_score: f64,
    verdict: String,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    boundaries: Vec<String>,
}

#[derive(Debug, Serialize)]
struct Scenario {
    name: String,
    description: String,
    injected_condition: String,
    expected_control_response: String,
    checks: Vec<String>,
    score: f64,
    status: String,
    evidence: Vec<String>,
}

#[derive(Debug, Serialize)]
struct EvalPack {
    schema: String,
    eval_id: String,
    generated_at: String,
    source_review: String,
    source_review_schema: String,
    source_review_sha256: String,
    source_verdict: String,
    scenarios: Vec<Scenario>,
    total_score: f64,
    status: String,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    boundaries: Vec<String>,
}

#[derive(Debug, Serialize)]
struct CliResult {
    schema: String,
    status: String,
    eval_id: String,
    score: f64,
    scenarios: usize,
    output_dir: String,
    eval_json: String,
    eval_md: String,
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

fn scenario(
    name: &str,
    description: &str,
    injected_condition: &str,
    expected: &str,
    checks: Vec<String>,
    pass: bool,
    evidence: Vec<String>,
) -> Scenario {
    Scenario {
        name: name.to_string(),
        description: description.to_string(),
        injected_condition: injected_condition.to_string(),
        expected_control_response: expected.to_string(),
        checks,
        score: if pass { 25.0 } else { 0.0 },
        status: if pass { "PASS" } else { "BLOCKED" }.to_string(),
        evidence,
    }
}

fn build_eval(review: &ReviewReport, review_path: &Path, review_sha: &str) -> EvalPack {
    let nominal_pass = review.critic_score >= 90.0 && review.blocked_items.is_empty();
    let noise_pass = review.actor.evidence_paths.len() >= 2 && review.actor.quality_gate_count >= 4;
    let disturbance_pass = !review.verdict.contains("BLOCK") && !review.watch_items.is_empty();
    let uncertainty_pass = review.actor.boundary_count >= 4
        && review.boundaries.iter().any(|b| b.contains("no provider"));

    let scenarios = vec![
        scenario(
            "nominal",
            "Normal DTO/review path should approve read-only evidence when critic checks pass.",
            "baseline actor-critic review with score and zero blocked items",
            "approve readonly or approve readonly with runtime watch",
            vec!["critic_score>=90".to_string(), "blocked_items=0".to_string()],
            nominal_pass,
            vec![
                format!("critic_score={}", review.critic_score),
                format!("actor_task_id={}", review.actor.task_id),
                format!("actor_source_score={}", review.actor.source_score),
                format!("blocked_items={}", review.blocked_items.len()),
            ],
        ),
        scenario(
            "noise",
            "Evidence noise / status-field hallucination should be controlled by evidence_paths and quality gates.",
            "status claim exists, but evaluator requires readback paths and quality gates",
            "do not treat status text alone as capability",
            vec!["evidence_paths>=2".to_string(), "quality_gate_count>=4".to_string()],
            noise_pass,
            vec![
                format!("evidence_paths={}", review.actor.evidence_paths.len()),
                format!("quality_gate_count={}", review.actor.quality_gate_count),
            ],
        ),
        scenario(
            "disturbance",
            "WATCH / mid-flight risk should avoid runtime auto-promotion.",
            "review has WATCH because runtime adoption is gated",
            "approve read-only but revise before runtime",
            vec!["verdict!=BLOCK".to_string(), "watch_items>=1".to_string()],
            disturbance_pass,
            vec![
                format!("verdict={}", review.verdict),
                format!("watch_items={}", review.watch_items.len()),
            ],
        ),
        scenario(
            "uncertainty",
            "Incomplete authority / boundary uncertainty should preserve provider/config/security/scheduler limits.",
            "runtime authority not granted; provider/config/security/scheduler boundary must remain explicit",
            "keep explicit boundary and require separate gate",
            vec!["boundary_count>=4".to_string(), "no_provider_boundary=true".to_string()],
            uncertainty_pass,
            vec![
                format!("actor_boundary_count={}", review.actor.boundary_count),
                format!("boundaries={:?}", review.boundaries),
            ],
        ),
    ];
    let total_score: f64 = scenarios.iter().map(|s| s.score).sum();
    let blocked_items: Vec<String> = scenarios
        .iter()
        .filter(|s| s.status == "BLOCKED")
        .map(|s| s.name.clone())
        .collect();
    let mut watch_items = review.watch_items.clone();
    watch_items.push("Eval pack is deterministic fixture generation; not yet a launchd/CI scheduled regression suite.".to_string());
    let status = if blocked_items.is_empty() {
        "PASS_CONTROL_CURRICULUM_EVAL_WITH_WATCH"
    } else {
        "BLOCKED_CONTROL_CURRICULUM_EVAL"
    };

    EvalPack {
        schema: SCHEMA.to_string(),
        eval_id: format!(
            "cce-{}",
            &sha256_hex(format!("{}:{}", review.review_id, review_sha).as_bytes())[..16]
        ),
        generated_at: Utc::now().to_rfc3339(),
        source_review: review_path.display().to_string(),
        source_review_schema: review.schema.clone(),
        source_review_sha256: review_sha.to_string(),
        source_verdict: review.verdict.clone(),
        scenarios,
        total_score,
        status: status.to_string(),
        watch_items,
        blocked_items,
        boundaries: vec![
            "deterministic curriculum pack only".to_string(),
            "no provider/LLM/network call".to_string(),
            "no provider/config/credential/security/scheduler mutation".to_string(),
            "not external benchmark/full AGI/T5/legal correctness proof".to_string(),
        ],
    }
}

fn write_md(pack: &EvalPack, path: &Path) -> std::io::Result<()> {
    let mut md = String::new();
    md.push_str("# Control Curriculum Eval Pack v1\n\n");
    md.push_str(&format!("- Eval ID: `{}`\n", pack.eval_id));
    md.push_str(&format!("- Status: `{}`\n", pack.status));
    md.push_str(&format!("- Score: `{}`\n", pack.total_score));
    md.push_str(&format!("- Source verdict: `{}`\n\n", pack.source_verdict));
    for s in &pack.scenarios {
        md.push_str(&format!("## {} — {} — {}\n\n", s.name, s.status, s.score));
        md.push_str(&format!("{}\n\n", s.description));
        md.push_str(&format!("Injected: `{}`\n\n", s.injected_condition));
        md.push_str(&format!("Expected: `{}`\n\n", s.expected_control_response));
        md.push_str("Evidence:\n");
        for e in &s.evidence {
            md.push_str(&format!("- `{}`\n", e));
        }
        md.push('\n');
    }
    md.push_str("## Boundaries\n\n");
    for b in &pack.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(path, md)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let review_path = PathBuf::from(arg_value(&args, "--review", DEFAULT_REVIEW));
    let out_dir = PathBuf::from(arg_value(&args, "--out-dir", DEFAULT_OUT_DIR));
    let bytes = match fs::read(&review_path) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("failed_to_read_review:{}:{}", review_path.display(), e);
            std::process::exit(2);
        }
    };
    let review_sha = sha256_hex(&bytes);
    let review: ReviewReport = match serde_json::from_slice(&bytes) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("failed_to_parse_review:{}:{}", review_path.display(), e);
            std::process::exit(3);
        }
    };
    let pack = build_eval(&review, &review_path, &review_sha);
    fs::create_dir_all(&out_dir).unwrap();
    let eval_json = out_dir.join("control_curriculum_eval_pack.json");
    let eval_md = out_dir.join("CONTROL_CURRICULUM_EVAL_PACK.md");
    let acceptance_json = out_dir.join("ACCEPTANCE.json");
    fs::write(&eval_json, serde_json::to_string_pretty(&pack).unwrap()).unwrap();
    write_md(&pack, &eval_md).unwrap();
    let result = CliResult {
        schema: pack.schema.clone(),
        status: pack.status.clone(),
        eval_id: pack.eval_id.clone(),
        score: pack.total_score,
        scenarios: pack.scenarios.len(),
        output_dir: out_dir.display().to_string(),
        eval_json: eval_json.display().to_string(),
        eval_md: eval_md.display().to_string(),
        acceptance_json: acceptance_json.display().to_string(),
        watch: pack.watch_items.len(),
        blocked: pack.blocked_items.len(),
    };
    fs::write(
        &acceptance_json,
        serde_json::to_string_pretty(&result).unwrap(),
    )
    .unwrap();
    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
