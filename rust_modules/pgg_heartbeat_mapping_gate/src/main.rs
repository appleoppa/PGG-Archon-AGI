use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Probe {
    name: String,
    mapped_to: String,
    status: String,
    score: f64,
    evidence: Vec<String>,
    rationale: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct ResultPacket {
    schema: String,
    generated_at_epoch: u64,
    status: String,
    score: f64,
    probes: Vec<Probe>,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
    output_dir: String,
    evidence_json: String,
    evidence_md: String,
    acceptance_json: String,
    boundaries: Vec<String>,
}

fn home() -> PathBuf {
    env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/Users/appleoppa"))
}

fn exists(path: &Path) -> bool {
    path.exists()
}

fn read_to_string(path: &Path) -> String {
    fs::read_to_string(path).unwrap_or_default()
}

fn command_output(program: &str, args: &[&str], timeout_hint: &str) -> (bool, String) {
    let out = Command::new(program).args(args).output();
    match out {
        Ok(o) => {
            let mut s = String::new();
            s.push_str(&String::from_utf8_lossy(&o.stdout));
            s.push_str(&String::from_utf8_lossy(&o.stderr));
            (o.status.success(), truncate(&s, 4000))
        }
        Err(e) => (false, format!("{} failed: {}", timeout_hint, e)),
    }
}

fn truncate(s: &str, max_chars: usize) -> String {
    if s.chars().count() <= max_chars {
        return s.to_string();
    }
    s.chars().take(max_chars).collect::<String>() + "...<truncated>"
}

fn sha256_hex(s: &str) -> String {
    let digest = Sha256::digest(s.as_bytes());
    hex::encode(digest)
}

fn status_line(ok: bool) -> String {
    if ok {
        "PASS".to_string()
    } else {
        "WATCH".to_string()
    }
}

fn main() {
    let h = home();
    let out_dir =
        h.join(".hermes/workspace/pgg-archon-governance/heartbeat-mapping-gate-v1-20260618");
    fs::create_dir_all(&out_dir).expect("create output dir");

    let autonomy_bin = h.join(".hermes/bin/pgg-autonomy-default-loop");
    let health_bin = h.join(".hermes/bin/pgg-health-monitor");
    let goal_bin = h.join(".hermes/bin/hermes-goal");
    let autonomy_plist = h.join("Library/LaunchAgents/ai.hermes.pgg-autonomy-default-loop.plist");
    let scheduler_plist =
        h.join("Library/LaunchAgents/ai.hermes.pgg-batch-evolution-scheduler.plist");
    let health_latest = h.join(".hermes/data/health-monitor/latest.json");
    let p1 = h.join(".hermes/workspace/pgg-archon-governance/control-loop-trace-v1-20260618/control_loop_trace.json");
    let p2 = h.join(".hermes/workspace/pgg-archon-governance/durable-task-object-v1-20260618/durable_task_object.json");
    let p3 = h.join(".hermes/workspace/pgg-archon-governance/actor-critic-review-gate-v1-20260618/actor_critic_review.json");
    let p4 = h.join(".hermes/workspace/pgg-archon-governance/control-curriculum-eval-pack-v1-20260618/control_curriculum_eval_pack.json");

    let mut probes: Vec<Probe> = Vec::new();
    let mut watch: Vec<String> = Vec::new();
    let blocked: Vec<String> = Vec::new();

    let p1p4_ok = [&p1, &p2, &p3, &p4].iter().all(|p| exists(p));
    if !p1p4_ok {
        watch.push(
            "P1-P4 control evidence chain incomplete; heartbeat mapping remains partial"
                .to_string(),
        );
    }
    probes.push(Probe {
        name: "control_chain_source".to_string(),
        mapped_to: "P1 trace + P2 DTO + P3 actor-critic + P4 curriculum eval".to_string(),
        status: status_line(p1p4_ok),
        score: if p1p4_ok { 20.0 } else { 8.0 },
        evidence: vec![
            p1.display().to_string(),
            p2.display().to_string(),
            p3.display().to_string(),
            p4.display().to_string(),
        ],
        rationale: "Heartbeat must supervise a real control chain, not a standalone status field."
            .to_string(),
    });

    let autonomy_ok = exists(&autonomy_bin) && exists(&autonomy_plist);
    if !autonomy_ok {
        watch.push("autonomy default-loop binary or launchd plist missing".to_string());
    }
    probes.push(Probe {
        name: "periodic_pulse".to_string(),
        mapped_to: "pgg-autonomy-default-loop + launchd ai.hermes.pgg-autonomy-default-loop".to_string(),
        status: status_line(autonomy_ok),
        score: if autonomy_ok { 20.0 } else { 7.0 },
        evidence: vec![autonomy_bin.display().to_string(), autonomy_plist.display().to_string()],
        rationale: "OpenClaw Heartbeat periodic pulse maps to existing daily autonomy loop managed by launchd.".to_string(),
    });

    let (launch_ok, launch_out) = command_output("launchctl", &["list"], "launchctl list");
    let launch_has_autonomy =
        launch_ok && launch_out.contains("ai.hermes.pgg-autonomy-default-loop");
    let launch_has_scheduler =
        launch_ok && launch_out.contains("ai.hermes.pgg-batch-evolution-scheduler");
    if !launch_has_autonomy {
        watch.push("launchctl does not currently list autonomy default-loop".to_string());
    }
    if !launch_has_scheduler {
        watch.push("launchctl does not currently list batch evolution scheduler".to_string());
    }
    probes.push(Probe {
        name: "runtime_supervisor_visibility".to_string(),
        mapped_to: "launchctl list ai.hermes.pgg-*".to_string(),
        status: status_line(launch_has_autonomy && launch_has_scheduler),
        score: if launch_has_autonomy && launch_has_scheduler { 15.0 } else { 8.0 },
        evidence: vec![format!("launchctl list contains autonomy={launch_has_autonomy}, scheduler={launch_has_scheduler}"), scheduler_plist.display().to_string()],
        rationale: "Heartbeat equivalent requires machine supervisor visibility, not only files on disk.".to_string(),
    });

    let (health_ok, health_out) = if exists(&health_bin) {
        command_output(
            health_bin.to_string_lossy().as_ref(),
            &["--json"],
            "pgg-health-monitor",
        )
    } else {
        (false, "health binary missing".to_string())
    };
    let health_pass = health_ok
        && (health_out.contains("\"status\": \"PASS\"")
            || health_out.contains("\"status\":\"PASS\""));
    if !health_pass {
        watch.push("health-monitor live JSON did not return PASS".to_string());
    }
    probes.push(Probe {
        name: "health_signal".to_string(),
        mapped_to: "pgg-health-monitor --json + ~/.hermes/data/health-monitor/latest.json".to_string(),
        status: status_line(health_pass && exists(&health_latest)),
        score: if health_pass && exists(&health_latest) { 20.0 } else { 9.0 },
        evidence: vec![health_bin.display().to_string(), health_latest.display().to_string(), truncate(&health_out, 1200)],
        rationale: "Heartbeat health signal maps to the existing bounded health-monitor status and launchd/service inventory.".to_string(),
    });

    let goal_ok = exists(&goal_bin);
    let p4_text = read_to_string(&p4);
    let eval_ok = p4_text.contains("PASS") && p4_text.contains("scenarios");
    if !goal_ok {
        watch.push("hermes-goal command missing, one-click audit linkage not proven".to_string());
    }
    if !eval_ok {
        watch.push("P4 eval pack is not readable as PASS scenarios".to_string());
    }
    probes.push(Probe {
        name: "post_pulse_verification".to_string(),
        mapped_to: "hermes-goal + P4 replayable eval pack".to_string(),
        status: status_line(goal_ok && eval_ok),
        score: if goal_ok && eval_ok { 15.0 } else { 7.0 },
        evidence: vec![goal_bin.display().to_string(), p4.display().to_string()],
        rationale: "Heartbeat must close with verification/replay rather than a start-only signal."
            .to_string(),
    });

    let no_mutation = true;
    probes.push(Probe {
        name: "boundary_preservation".to_string(),
        mapped_to: "read-only mapping; no provider/config/credential/security/scheduler mutation"
            .to_string(),
        status: "PASS".to_string(),
        score: if no_mutation { 10.0 } else { 0.0 },
        evidence: vec![
            "This gate performs file/read-only command probes and writes only its evidence packet."
                .to_string(),
        ],
        rationale: "P5 is a mapping gate, not Heartbeat runtime installation or launchd mutation."
            .to_string(),
    });

    // Explicit WATCH: health-monitor itself appears to exist as CLI/latest, but no dedicated plist was observed in prior live audit.
    let dedicated_health_plist = h.join("Library/LaunchAgents/ai.hermes.pgg-health-monitor.plist");
    if !exists(&dedicated_health_plist) {
        watch.push("No dedicated ai.hermes.pgg-health-monitor.plist found; health is covered by CLI/latest and broader pgg launchd inventory, not a standalone health launchd job.".to_string());
    }

    let total_score: f64 = probes.iter().map(|p| p.score).sum();
    let status = if blocked.is_empty() && total_score >= 90.0 {
        if watch.is_empty() {
            "PASS_HEARTBEAT_MAPPING"
        } else {
            "PASS_HEARTBEAT_MAPPING_WITH_WATCH"
        }
    } else if blocked.is_empty() {
        "PARTIAL_HEARTBEAT_MAPPING_WITH_WATCH"
    } else {
        "BLOCKED_HEARTBEAT_MAPPING"
    }
    .to_string();

    let generated = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    let evidence_json = out_dir.join("heartbeat_mapping_gate.json");
    let evidence_md = out_dir.join("HEARTBEAT_MAPPING_GATE.md");
    let acceptance_json = out_dir.join("ACCEPTANCE.json");

    let packet = ResultPacket {
        schema: "pgg_heartbeat_mapping_gate/v1".to_string(),
        generated_at_epoch: generated,
        status: status.clone(),
        score: total_score,
        probes: probes.clone(),
        watch_items: watch.clone(),
        blocked_items: blocked.clone(),
        output_dir: out_dir.display().to_string(),
        evidence_json: evidence_json.display().to_string(),
        evidence_md: evidence_md.display().to_string(),
        acceptance_json: acceptance_json.display().to_string(),
        boundaries: vec![
            "OpenClaw/Heartbeat concepts are mapped to existing Hermes/PGG mechanisms only.".to_string(),
            "No external runtime/config/directory/scheduler is copied.".to_string(),
            "No provider/config/credential/security/scheduler mutation is performed.".to_string(),
            "PASS proves local bounded mapping evidence, not production autonomy/full AGI/T5/external benchmark.".to_string(),
        ],
    };

    let json = serde_json::to_string_pretty(&packet).expect("serialize packet");
    fs::write(&evidence_json, &json).expect("write evidence json");

    let mut md = String::new();
    md.push_str("# PGG Heartbeat Mapping Gate v1\n\n");
    md.push_str(&format!("- status: `{}`\n- score: `{:.1}`\n- watch: `{}`\n- blocked: `{}`\n- evidence_hash: `{}`\n\n", status, total_score, watch.len(), blocked.len(), &sha256_hex(&json)[..16]));
    md.push_str("## Mapping probes\n\n");
    for p in &probes {
        md.push_str(&format!(
            "### {}\n- mapped_to: {}\n- status: {}\n- score: {:.1}\n- rationale: {}\n\n",
            p.name, p.mapped_to, p.status, p.score, p.rationale
        ));
    }
    md.push_str("## WATCH\n\n");
    if watch.is_empty() {
        md.push_str("- none\n");
    } else {
        for w in &watch {
            md.push_str(&format!("- {}\n", w));
        }
    }
    md.push_str("\n## Boundaries\n\n");
    for b in &packet.boundaries {
        md.push_str(&format!("- {}\n", b));
    }
    fs::write(&evidence_md, md).expect("write md");

    let acceptance = serde_json::json!({
        "schema": "pgg_heartbeat_mapping_acceptance/v1",
        "status": status,
        "score": total_score,
        "probe_count": probes.len(),
        "watch_count": watch.len(),
        "blocked_count": blocked.len(),
        "evidence_json": evidence_json,
        "evidence_md": evidence_md,
        "gate_sha256": sha256_hex(&json),
        "next_action": "P6 candidate: heartbeat replay ledger or launchd LIGHT only after explicit runtime authorization"
    });
    fs::write(
        &acceptance_json,
        serde_json::to_string_pretty(&acceptance).unwrap(),
    )
    .expect("write acceptance");

    println!("{}", serde_json::to_string_pretty(&packet).unwrap());
}
