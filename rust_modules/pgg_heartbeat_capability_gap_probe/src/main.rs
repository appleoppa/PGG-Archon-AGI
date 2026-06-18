use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Gap {
    gap_id: String,
    title: String,
    severity: String,
    evidence: Vec<String>,
    recommendation: String,
    mutation_required: bool,
    candidate_next_gate: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct GapPacket {
    schema: String,
    generated_at_epoch: u64,
    status: String,
    score: f64,
    probes_run: usize,
    gaps: Vec<Gap>,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    boundaries: Vec<String>,
    output_dir: String,
    latest_gap_json: String,
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
fn sha256_hex(s: &str) -> String {
    hex::encode(Sha256::digest(s.as_bytes()))
}
fn exists(p: &Path) -> bool {
    p.exists()
}
fn json_status(p: &Path) -> String {
    fs::read_to_string(p)
        .ok()
        .and_then(|s| serde_json::from_str::<Value>(&s).ok())
        .and_then(|v| {
            v.get("status")
                .or_else(|| v.get("classification"))
                .and_then(|x| x.as_str())
                .map(|s| s.to_string())
        })
        .unwrap_or("MISSING".to_string())
}
fn cmd(program: &str, args: &[&str]) -> String {
    Command::new(program)
        .args(args)
        .output()
        .map(|o| {
            String::from_utf8_lossy(&o.stdout).to_string() + &String::from_utf8_lossy(&o.stderr)
        })
        .unwrap_or_default()
}

fn main() {
    let h = home();
    let out_dir = h
        .join(".hermes/workspace/pgg-archon-governance/heartbeat-capability-gap-probe-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");
    let mut gaps: Vec<Gap> = Vec::new();
    let blocked: Vec<String> = Vec::new();
    let mut probes = 0usize;

    let p14=h.join(".hermes/workspace/pgg-archon-governance/heartbeat-candidate-executor-preflight-v1-20260618/latest_executor_preflight.json");
    probes += 1;
    if json_status(&p14) != "PASS_EXECUTOR_PREFLIGHT_DRY_RUN_READY" {
        gaps.push(Gap {
            gap_id: "gap_preflight_not_ready".to_string(),
            title: "P14 preflight not ready".to_string(),
            severity: "HIGH".to_string(),
            evidence: vec![p14.display().to_string(), json_status(&p14)],
            recommendation: "Regenerate P14 preflight before capability probing.".to_string(),
            mutation_required: false,
            candidate_next_gate: "rerun-p14".to_string(),
        });
    }

    let p7_plist = h.join("Library/LaunchAgents/ai.hermes.pgg-heartbeat-light-runner.plist");
    probes += 1;
    let p11_plist =
        h.join("Library/LaunchAgents/ai.hermes.pgg-heartbeat-plan-rotation-runner.plist");
    probes += 1;
    if !exists(&p7_plist) {
        gaps.push(Gap {
            gap_id: "gap_heartbeat_light_runner_plist_missing".to_string(),
            title: "P7 heartbeat LIGHT runner plist missing".to_string(),
            severity: "HIGH".to_string(),
            evidence: vec![p7_plist.display().to_string()],
            recommendation:
                "Recreate scoped launchd plist only with explicit scheduler authorization."
                    .to_string(),
            mutation_required: true,
            candidate_next_gate: "p7-repair-preflight".to_string(),
        });
    }
    if !exists(&p11_plist) {
        gaps.push(Gap{gap_id:"gap_plan_rotation_plist_missing".to_string(),title:"P11 plan rotation plist missing".to_string(),severity:"HIGH".to_string(),evidence:vec![p11_plist.display().to_string()],recommendation:"Recreate scoped plan-rotation launchd plist only with explicit scheduler authorization.".to_string(),mutation_required:true,candidate_next_gate:"p11-repair-preflight".to_string()});
    }

    let health_plist = h.join("Library/LaunchAgents/ai.hermes.pgg-health-monitor.plist");
    probes += 1;
    if !exists(&health_plist) {
        gaps.push(Gap{gap_id:"gap_health_monitor_no_standalone_plist".to_string(),title:"health-monitor has no standalone launchd plist".to_string(),severity:"MEDIUM".to_string(),evidence:vec![health_plist.display().to_string()],recommendation:"Either accept as normalized WATCH or design a separate health-monitor launchd LIGHT job.".to_string(),mutation_required:true,candidate_next_gate:"health-monitor-launchd-design-gate".to_string()});
    }

    let p8=h.join(".hermes/workspace/pgg-archon-governance/heartbeat-alert-summarizer-v1-20260618/latest_heartbeat_alert_packet.json");
    probes += 1;
    let p8_status = json_status(&p8);
    if !p8_status.starts_with("PASS") {
        gaps.push(Gap {
            gap_id: "gap_alert_summarizer_not_pass".to_string(),
            title: "Alert summarizer is not PASS".to_string(),
            severity: "HIGH".to_string(),
            evidence: vec![p8.display().to_string(), p8_status],
            recommendation: "Regenerate P8 summarizer before delivery/plan execution.".to_string(),
            mutation_required: false,
            candidate_next_gate: "rerun-p8".to_string(),
        });
    }

    let p9_receipt=h.join(".hermes/workspace/pgg-archon-governance/heartbeat-alert-delivery-gate-v1-20260618/FEISHU_DELIVERY_RECEIPT.json");
    probes += 1;
    if !exists(&p9_receipt) {
        gaps.push(Gap {
            gap_id: "gap_delivery_receipt_missing".to_string(),
            title: "No Feishu delivery receipt".to_string(),
            severity: "LOW".to_string(),
            evidence: vec![p9_receipt.display().to_string()],
            recommendation: "Keep P9A candidate-only; send only when explicitly authorized."
                .to_string(),
            mutation_required: false,
            candidate_next_gate: "p9-delivery-candidate".to_string(),
        });
    }

    let git_out = cmd(
        "git",
        &[
            "-C",
            "/Users/appleoppa/.hermes/hermes-agent",
            "status",
            "--short",
            "rust_modules/Cargo.toml",
        ],
    );
    probes += 1;
    if !git_out.trim().is_empty() {
        gaps.push(Gap{gap_id:"gap_unsettled_rust_workspace_manifest".to_string(),title:"Rust workspace manifest has unsettled changes".to_string(),severity:"MEDIUM".to_string(),evidence:vec![git_out.trim().to_string()],recommendation:"Prepare scoped commit/PR settlement after the P-series stabilizes; do not auto-commit.".to_string(),mutation_required:true,candidate_next_gate:"scoped-git-settlement-preflight".to_string()});
    }

    let score = (100.0 - (gaps.len() as f64 * 8.0)).max(50.0);
    let status = if gaps.iter().any(|g| g.severity == "HIGH") {
        "PASS_CAPABILITY_GAP_PROBE_WITH_HIGH_WATCH"
    } else if gaps.is_empty() {
        "PASS_CAPABILITY_GAP_PROBE_GREEN"
    } else {
        "PASS_CAPABILITY_GAP_PROBE_WITH_WATCH"
    }
    .to_string();
    let latest = out_dir.join("latest_capability_gap_probe.json");
    let report = out_dir.join("CAPABILITY_GAP_PROBE.md");
    let acceptance = out_dir.join("ACCEPTANCE.json");
    let packet = GapPacket {
        schema: "pgg_heartbeat_capability_gap_probe/v1".to_string(),
        generated_at_epoch: now_epoch(),
        status: status.clone(),
        score,
        probes_run: probes,
        gaps: gaps.clone(),
        watch_items: gaps
            .iter()
            .map(|g| format!("{}: {}", g.severity, g.title))
            .collect(),
        blocked_items: blocked,
        boundaries: vec![
            "Probe is read-only and does not repair gaps.".to_string(),
            "Mutation-required gaps are candidates only.".to_string(),
            "No provider/LLM/network call.".to_string(),
            "No auto-commit/config/scheduler change.".to_string(),
        ],
        output_dir: out_dir.display().to_string(),
        latest_gap_json: latest.display().to_string(),
        report_md: report.display().to_string(),
        acceptance_json: acceptance.display().to_string(),
    };
    let json = serde_json::to_string_pretty(&packet).unwrap();
    fs::write(&latest, &json).expect("write latest");
    let mut md = String::from("# PGG Heartbeat Capability Gap Probe v1\n\n");
    md.push_str(&format!(
        "- status: `{}`\n- score: `{}`\n- probes_run: `{}`\n- gaps: `{}`\n\n",
        status,
        score,
        probes,
        gaps.len()
    ));
    for g in &gaps {
        md.push_str(&format!("## {} — {}\n- severity: {}\n- mutation_required: {}\n- recommendation: {}\n- next_gate: {}\n\n",g.gap_id,g.title,g.severity,g.mutation_required,g.recommendation,g.candidate_next_gate));
    }
    fs::write(&report, md).expect("write report");
    let acc = serde_json::json!({"schema":"pgg_heartbeat_capability_gap_probe_acceptance/v1","status":status,"score":score,"probes_run":probes,"gap_count":gaps.len(),"watch_count":packet.watch_items.len(),"blocked_count":packet.blocked_items.len(),"latest_gap_json":latest,"report_md":report,"acceptance_json":acceptance,"gap_digest":sha256_hex(&json),"next_action":"P16 gap-to-action router; still candidate-only unless authorized."});
    fs::write(&acceptance, serde_json::to_string_pretty(&acc).unwrap()).expect("write acceptance");
    println!("{}", serde_json::to_string_pretty(&packet).unwrap());
}
