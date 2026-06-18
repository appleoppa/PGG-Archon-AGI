use chrono::{DateTime, Utc};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

const SCHEMA: &str = "pgg_control_loop_trace_gate/v1";
const DEFAULT_SOURCE: &str = "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/uploaded-guides/cc-source-engineering-cybernetics-20260618/SUMMARY.json";
const DEFAULT_OUT_DIR: &str =
    "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/control-loop-trace-v1-20260618";

#[derive(Debug, Serialize, Clone)]
struct StageEvidence {
    name: String,
    objective: String,
    status: String,
    evidence: Vec<String>,
    gaps: Vec<String>,
}

#[derive(Debug, Serialize, Clone)]
struct ControlTrace {
    schema: String,
    trace_id: String,
    generated_at: String,
    source_artifact: String,
    source_sha256: String,
    task_goal: String,
    control_loop: Vec<StageEvidence>,
    closed_loop_score: f64,
    status: String,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    boundaries: Vec<String>,
}

#[derive(Debug, Serialize)]
struct CliResult {
    schema: String,
    status: String,
    trace_id: String,
    score: f64,
    output_dir: String,
    json_path: String,
    md_path: String,
    stages: usize,
    watch: usize,
    blocked: usize,
    boundaries: Vec<String>,
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    digest
        .iter()
        .map(|b| format!("{:02x}", b))
        .collect::<String>()
}

fn now_utc() -> DateTime<Utc> {
    Utc::now()
}

fn read_source(path: &Path) -> (Vec<u8>, Vec<String>) {
    match fs::read(path) {
        Ok(bytes) => (bytes, vec![format!("source_read_ok:{}", path.display())]),
        Err(e) => {
            let fallback = format!("source_missing:{}:{}", path.display(), e);
            (fallback.as_bytes().to_vec(), vec![fallback])
        }
    }
}

fn contains_all(text: &str, terms: &[&str]) -> bool {
    terms.iter().all(|t| text.contains(t))
}

fn stage(
    name: &str,
    objective: &str,
    status: &str,
    evidence: Vec<String>,
    gaps: Vec<String>,
) -> StageEvidence {
    StageEvidence {
        name: name.to_string(),
        objective: objective.to_string(),
        status: status.to_string(),
        evidence,
        gaps,
    }
}

fn build_trace(
    source_path: &Path,
    source_text: &str,
    source_sha: &str,
    now: DateTime<Utc>,
) -> ControlTrace {
    let mut watch_items: Vec<String> = Vec::new();
    let mut blocked_items: Vec<String> = Vec::new();

    let observed = contains_all(
        source_text,
        &["PASS_PATTERN_ABSORBED", "artifacts", "watch_items"],
    );
    let error_identified = contains_all(source_text, &["watch_items", "Durable heartbeat"])
        || contains_all(source_text, &["Full 510k-line", "Engineering Cybernetics"]);
    let plan_mapped = contains_all(source_text, &["gate_json", "rust_cli", "rust_source"]);
    let act_executed = contains_all(source_text, &["rust_cli", "rust_source"])
        || contains_all(
            source_text,
            &[
                "pgg-cc-cybernetics-absorption-gate",
                "pgg_cc_cybernetics_absorption_gate",
            ],
        );
    let verified = contains_all(source_text, &["score", "100.0"])
        || contains_all(source_text, &["PASS_PATTERN_ABSORBED", "requirements"]);
    let settled = contains_all(source_text, &["frozen_index", "design_report", "gate_json"])
        || contains_all(
            source_text,
            &["latest_cc_cybernetics_guide_absorption", "reference"],
        );

    if !observed {
        blocked_items.push("source_summary_does_not_show_observed_absorption_state".to_string());
    }
    if !plan_mapped {
        blocked_items.push("source_summary_lacks_hermes_rust_gate_mapping".to_string());
    }
    if !act_executed {
        watch_items.push("execution_artifact_reference_not_detected_in_summary".to_string());
    }
    if !settled {
        watch_items.push("settlement_reference_not_detected_in_summary".to_string());
    }

    let stages = vec![
        stage(
            "observe",
            "Read frozen CC/cybernetics absorption result and establish current state.",
            if observed { "PASS" } else { "BLOCKED" },
            vec![format!("source={}", source_path.display()), format!("sha256={}", source_sha), format!("observed_terms={}", observed)],
            if observed { vec![] } else { vec!["Missing PASS_PATTERN_ABSORBED/OpenClaw/Hermes indicators".to_string()] },
        ),
        stage(
            "compare_error",
            "Expose residual deltas: deep CC read, controlled full-text study, heartbeat scheduling boundary.",
            if error_identified { "PASS_WITH_WATCH" } else { "WATCH" },
            vec![format!("watch_boundary_terms_detected={}", error_identified)],
            if error_identified { vec!["Residual items remain WATCH, not BLOCKED.".to_string()] } else { vec!["No explicit watch/error boundary found in source summary.".to_string()] },
        ),
        stage(
            "plan_route",
            "Route OpenClaw/Heartbeat ideas into native Hermes/PGG mechanisms without copying runtime/config.",
            if plan_mapped { "PASS" } else { "BLOCKED" },
            vec![format!("hermes_rust_gate_terms_detected={}", plan_mapped)],
            if plan_mapped { vec![] } else { vec!["Hermes/Rust/gate mapping incomplete.".to_string()] },
        ),
        stage(
            "act",
            "Land bounded Rust gate and artifacts instead of prose-only absorption.",
            if act_executed { "PASS" } else { "WATCH" },
            vec![format!("execution_artifact_terms_detected={}", act_executed)],
            if act_executed { vec![] } else { vec!["Could not detect rust_cli/rust_source in summary.".to_string()] },
        ),
        stage(
            "verify",
            "Verify score/status/readback rather than treating file existence as success.",
            if verified { "PASS" } else { "WATCH" },
            vec![format!("score_status_terms_detected={}", verified)],
            if verified { vec![] } else { vec!["Could not detect score/status verification in summary.".to_string()] },
        ),
        stage(
            "settle",
            "Settle into Manifest/skill reference while preserving boundaries.",
            if settled { "PASS" } else { "WATCH" },
            vec![format!("manifest_skill_terms_detected={}", settled)],
            if settled { vec![] } else { vec!["Could not detect Manifest/skill settlement terms in summary.".to_string()] },
        ),
    ];

    let pass_like = stages
        .iter()
        .filter(|s| s.status.starts_with("PASS"))
        .count() as f64;
    let score = (pass_like / stages.len() as f64 * 1000.0).round() / 10.0;
    let hard_blocked = stages.iter().any(|s| s.status == "BLOCKED") || !blocked_items.is_empty();
    let status = if hard_blocked {
        "BLOCKED_CONTROL_LOOP_TRACE".to_string()
    } else if !watch_items.is_empty() || stages.iter().any(|s| s.status.contains("WATCH")) {
        "PASS_CONTROL_LOOP_TRACE_WITH_WATCH".to_string()
    } else {
        "PASS_CONTROL_LOOP_TRACE".to_string()
    };

    ControlTrace {
        schema: SCHEMA.to_string(),
        trace_id: format!("pgg-control-loop-trace-{}", &sha256_hex(format!("{}:{}", source_sha, now.to_rfc3339()).as_bytes())[..16]),
        generated_at: now.to_rfc3339(),
        source_artifact: source_path.display().to_string(),
        source_sha256: source_sha.to_string(),
        task_goal: "PGG Control Loop Trace v1: turn the CC/cybernetics absorption into an explicit observe→error→plan→act→verify→settle control trace.".to_string(),
        control_loop: stages,
        closed_loop_score: score,
        status,
        watch_items,
        blocked_items,
        boundaries: vec![
            "read-only trace generation over existing artifacts".to_string(),
            "no provider/config/credential/security/scheduler mutation".to_string(),
            "no OpenClaw runtime import".to_string(),
            "not full AGI/T5/external benchmark/legal correctness proof".to_string(),
        ],
    }
}

fn write_markdown(trace: &ControlTrace, path: &Path) -> std::io::Result<()> {
    let mut md = String::new();
    md.push_str("# PGG Control Loop Trace v1\n\n");
    md.push_str(&format!("- Schema: `{}`\n", trace.schema));
    md.push_str(&format!("- Trace ID: `{}`\n", trace.trace_id));
    md.push_str(&format!("- Status: `{}`\n", trace.status));
    md.push_str(&format!("- Score: `{}`\n", trace.closed_loop_score));
    md.push_str(&format!("- Source: `{}`\n", trace.source_artifact));
    md.push_str(&format!("- Source SHA256: `{}`\n\n", trace.source_sha256));
    md.push_str("## Six-stage control loop\n\n");
    for s in &trace.control_loop {
        md.push_str(&format!("### {} — {}\n\n", s.name, s.status));
        md.push_str(&format!("Objective: {}\n\n", s.objective));
        md.push_str("Evidence:\n");
        for e in &s.evidence {
            md.push_str(&format!("- `{}`\n", e));
        }
        if !s.gaps.is_empty() {
            md.push_str("\nGaps:\n");
            for g in &s.gaps {
                md.push_str(&format!("- {}\n", g));
            }
        }
        md.push('\n');
    }
    md.push_str("## Boundaries\n\n");
    for b in &trace.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    if !trace.watch_items.is_empty() {
        md.push_str("\n## WATCH\n\n");
        for w in &trace.watch_items {
            md.push_str(&format!("- {}\n", w));
        }
    }
    if !trace.blocked_items.is_empty() {
        md.push_str("\n## BLOCKED\n\n");
        for b in &trace.blocked_items {
            md.push_str(&format!("- {}\n", b));
        }
    }
    fs::write(path, md)
}

fn arg_value(args: &[String], flag: &str, default: &str) -> String {
    args.windows(2)
        .find(|w| w[0] == flag)
        .map(|w| w[1].clone())
        .unwrap_or_else(|| default.to_string())
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let source = PathBuf::from(arg_value(&args, "--source", DEFAULT_SOURCE));
    let out_dir = PathBuf::from(arg_value(&args, "--out-dir", DEFAULT_OUT_DIR));
    let (bytes, mut read_evidence) = read_source(&source);
    let source_text = String::from_utf8_lossy(&bytes).to_string();
    let source_sha = sha256_hex(&bytes);
    let now = now_utc();
    let mut trace = build_trace(&source, &source_text, &source_sha, now);
    for e in read_evidence.drain(..) {
        if let Some(first) = trace.control_loop.first_mut() {
            first.evidence.push(e);
        }
    }

    if let Err(e) = fs::create_dir_all(&out_dir) {
        eprintln!("failed_to_create_output_dir:{}:{}", out_dir.display(), e);
        std::process::exit(2);
    }
    let json_path = out_dir.join("control_loop_trace.json");
    let md_path = out_dir.join("CONTROL_LOOP_TRACE.md");
    let json =
        serde_json::to_string_pretty(&trace).unwrap_or_else(|e| format!("{{\"error\":\"{}\"}}", e));
    if let Err(e) = fs::write(&json_path, json) {
        eprintln!("failed_to_write_json:{}:{}", json_path.display(), e);
        std::process::exit(3);
    }
    if let Err(e) = write_markdown(&trace, &md_path) {
        eprintln!("failed_to_write_markdown:{}:{}", md_path.display(), e);
        std::process::exit(4);
    }

    let result = CliResult {
        schema: trace.schema.clone(),
        status: trace.status.clone(),
        trace_id: trace.trace_id.clone(),
        score: trace.closed_loop_score,
        output_dir: out_dir.display().to_string(),
        json_path: json_path.display().to_string(),
        md_path: md_path.display().to_string(),
        stages: trace.control_loop.len(),
        watch: trace.watch_items.len()
            + trace
                .control_loop
                .iter()
                .filter(|s| s.status.contains("WATCH"))
                .count(),
        blocked: trace.blocked_items.len()
            + trace
                .control_loop
                .iter()
                .filter(|s| s.status == "BLOCKED")
                .count(),
        boundaries: trace.boundaries.clone(),
    };
    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
