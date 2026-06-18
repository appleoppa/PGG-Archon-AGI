use chrono::Utc;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

const SCHEMA: &str = "pgg_durable_task_object/v1";
const DEFAULT_TRACE: &str = "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/control-loop-trace-v1-20260618/control_loop_trace.json";
const DEFAULT_OUT_DIR: &str =
    "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/durable-task-object-v1-20260618";

#[derive(Debug, Deserialize)]
struct ControlStage {
    name: String,
    objective: String,
    status: String,
    evidence: Vec<String>,
    gaps: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct ControlTrace {
    schema: String,
    trace_id: String,
    source_artifact: String,
    task_goal: String,
    control_loop: Vec<ControlStage>,
    closed_loop_score: f64,
    status: String,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    boundaries: Vec<String>,
}

#[derive(Debug, Serialize)]
struct TaskStatus {
    current: String,
    lifecycle: Vec<String>,
    allowed_transitions: Vec<String>,
}

#[derive(Debug, Serialize)]
struct DurableTaskObject {
    schema: String,
    task_id: String,
    created_at: String,
    goal: String,
    source_trace: String,
    source_trace_schema: String,
    source_artifact: String,
    source_score: f64,
    risk_level: String,
    gate_level: String,
    status: TaskStatus,
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
struct CliResult {
    schema: String,
    status: String,
    task_id: String,
    score: f64,
    output_dir: String,
    task_json: String,
    task_md: String,
    acceptance_json: String,
    risk_level: String,
    gate_level: String,
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

fn stage(trace: &ControlTrace, name: &str) -> Vec<String> {
    trace
        .control_loop
        .iter()
        .filter(|s| s.name == name)
        .flat_map(|s| {
            let mut lines = vec![format!("{}: {}", s.status, s.objective)];
            lines.extend(s.evidence.iter().map(|e| format!("evidence: {}", e)));
            lines.extend(s.gaps.iter().map(|g| format!("gap: {}", g)));
            lines
        })
        .collect()
}

fn evidence_paths(trace: &ControlTrace, trace_path: &Path) -> Vec<String> {
    let mut paths = vec![
        trace_path.display().to_string(),
        trace.source_artifact.clone(),
    ];
    for st in &trace.control_loop {
        for e in &st.evidence {
            for token in e.split_whitespace() {
                if token.starts_with("/Users/appleoppa/") {
                    paths.push(token.trim_matches(',').trim_matches('`').to_string());
                }
                if let Some(rest) = token.strip_prefix("source=") {
                    paths.push(rest.trim_matches(',').to_string());
                }
            }
        }
    }
    paths.sort();
    paths.dedup();
    paths
}

fn build_object(trace: &ControlTrace, trace_path: &Path, trace_sha: &str) -> DurableTaskObject {
    let blocked = !trace.blocked_items.is_empty() || trace.status.contains("BLOCKED");
    let watch = !trace.watch_items.is_empty() || trace.status.contains("WATCH");
    let risk_level = if blocked {
        "HIGH"
    } else if watch {
        "LOW_WITH_WATCH"
    } else {
        "LOW"
    };
    let gate_level = if blocked {
        "human_gate"
    } else if watch {
        "llm_or_human_review_before_runtime"
    } else {
        "auto_readonly"
    };
    let current = if blocked {
        "blocked"
    } else if watch {
        "verified_with_watch"
    } else {
        "verified"
    };
    let next_action = if blocked {
        "Resolve blocked items before any execution.".to_string()
    } else if watch {
        "Promote to Actor-Critic Review Gate or Heartbeat Mapping Gate before scheduler/runtime mutation.".to_string()
    } else {
        "Eligible for read-only aggregation into PGG task ledger.".to_string()
    };

    DurableTaskObject {
        schema: SCHEMA.to_string(),
        task_id: format!(
            "dto-{}",
            &sha256_hex(format!("{}:{}", trace.trace_id, trace_sha).as_bytes())[..16]
        ),
        created_at: Utc::now().to_rfc3339(),
        goal: trace.task_goal.clone(),
        source_trace: trace.trace_id.clone(),
        source_trace_schema: trace.schema.clone(),
        source_artifact: trace_path.display().to_string(),
        source_score: trace.closed_loop_score,
        risk_level: risk_level.to_string(),
        gate_level: gate_level.to_string(),
        status: TaskStatus {
            current: current.to_string(),
            lifecycle: vec![
                "created".to_string(),
                "observed".to_string(),
                "planned".to_string(),
                "acted".to_string(),
                "verified".to_string(),
                "settled".to_string(),
                "archived".to_string(),
            ],
            allowed_transitions: vec![
                "verified_with_watch -> review".to_string(),
                "verified -> archive".to_string(),
                "blocked -> human_gate".to_string(),
            ],
        },
        observe: stage(trace, "observe"),
        error: stage(trace, "compare_error"),
        plan: stage(trace, "plan_route"),
        act: stage(trace, "act"),
        verify: stage(trace, "verify"),
        settle: stage(trace, "settle"),
        evidence_paths: evidence_paths(trace, trace_path),
        watch_items: trace.watch_items.clone(),
        blocked_items: trace.blocked_items.clone(),
        next_action,
        boundaries: trace.boundaries.clone(),
        quality_gates: vec![
            "file_existence_is_not_completion".to_string(),
            "status_field_is_not_capability".to_string(),
            "readback_required_before_done".to_string(),
            "provider_config_security_scheduler_mutation_requires_separate_authorization"
                .to_string(),
        ],
    }
}

fn write_md(task: &DurableTaskObject, path: &Path) -> std::io::Result<()> {
    let mut md = String::new();
    md.push_str("# Durable Task Object v1\n\n");
    md.push_str(&format!("- Task ID: `{}`\n", task.task_id));
    md.push_str(&format!("- Schema: `{}`\n", task.schema));
    md.push_str(&format!("- Status: `{}`\n", task.status.current));
    md.push_str(&format!("- Risk: `{}`\n", task.risk_level));
    md.push_str(&format!("- Gate: `{}`\n", task.gate_level));
    md.push_str(&format!("- Next action: {}\n\n", task.next_action));
    for (title, lines) in [
        ("Observe", &task.observe),
        ("Error", &task.error),
        ("Plan", &task.plan),
        ("Act", &task.act),
        ("Verify", &task.verify),
        ("Settle", &task.settle),
    ] {
        md.push_str(&format!("## {}\n\n", title));
        for line in lines {
            md.push_str(&format!("- {}\n", line));
        }
        md.push('\n');
    }
    md.push_str("## Evidence paths\n\n");
    for p in &task.evidence_paths {
        md.push_str(&format!("- `{}`\n", p));
    }
    md.push_str("\n## Boundaries\n\n");
    for b in &task.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(path, md)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let trace_path = PathBuf::from(arg_value(&args, "--trace", DEFAULT_TRACE));
    let out_dir = PathBuf::from(arg_value(&args, "--out-dir", DEFAULT_OUT_DIR));

    let trace_bytes = match fs::read(&trace_path) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("failed_to_read_trace:{}:{}", trace_path.display(), e);
            std::process::exit(2);
        }
    };
    let trace_sha = sha256_hex(&trace_bytes);
    let trace: ControlTrace = match serde_json::from_slice(&trace_bytes) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("failed_to_parse_trace:{}:{}", trace_path.display(), e);
            std::process::exit(3);
        }
    };
    let task = build_object(&trace, &trace_path, &trace_sha);
    if let Err(e) = fs::create_dir_all(&out_dir) {
        eprintln!("failed_to_create_out_dir:{}:{}", out_dir.display(), e);
        std::process::exit(4);
    }
    let task_json = out_dir.join("durable_task_object.json");
    let task_md = out_dir.join("DURABLE_TASK_OBJECT.md");
    let acceptance_json = out_dir.join("ACCEPTANCE.json");
    fs::write(&task_json, serde_json::to_string_pretty(&task).unwrap()).unwrap();
    write_md(&task, &task_md).unwrap();
    let status = if task.blocked_items.is_empty() {
        "PASS_DURABLE_TASK_OBJECT_WITH_WATCH"
    } else {
        "BLOCKED_DURABLE_TASK_OBJECT"
    };
    let score = if task.blocked_items.is_empty() {
        100.0
    } else {
        60.0
    };
    let result = CliResult {
        schema: task.schema.clone(),
        status: status.to_string(),
        task_id: task.task_id.clone(),
        score,
        output_dir: out_dir.display().to_string(),
        task_json: task_json.display().to_string(),
        task_md: task_md.display().to_string(),
        acceptance_json: acceptance_json.display().to_string(),
        risk_level: task.risk_level.clone(),
        gate_level: task.gate_level.clone(),
        watch: task.watch_items.len() + usize::from(task.risk_level.contains("WATCH")),
        blocked: task.blocked_items.len(),
    };
    fs::write(
        &acceptance_json,
        serde_json::to_string_pretty(&result).unwrap(),
    )
    .unwrap();
    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
