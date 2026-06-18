use chrono::{Datelike, Local, Timelike};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::env;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

#[derive(Clone, Debug)]
struct SubTask {
    name: &'static str,
    bin: &'static str,
    args: &'static [&'static str],
    cwd: &'static str,
    timeout_secs: u64,
}

fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}

fn hermes_home() -> PathBuf {
    home().join(".hermes")
}

fn data_dir(group: &str) -> PathBuf {
    hermes_home().join("data/pgg-launchd-omnibus").join(group)
}

fn log_dir() -> PathBuf {
    hermes_home().join("logs/pgg-launchd-omnibus")
}

fn sha256_short(s: &str) -> String {
    let digest = Sha256::digest(s.as_bytes());
    digest
        .iter()
        .take(8)
        .map(|b| format!("{:02x}", b))
        .collect::<String>()
}

fn safe_json_string(s: &[u8], limit: usize) -> String {
    let text = String::from_utf8_lossy(s);
    let mut out = String::new();
    for ch in text.chars().take(limit) {
        out.push(ch);
    }
    out
}

fn lock_path(group: &str) -> PathBuf {
    hermes_home()
        .join("run")
        .join(format!("pgg-launchd-omnibus-{}.lock", group))
}

fn acquire_lock(group: &str) -> Result<PathBuf, String> {
    let p = lock_path(group);
    if let Some(parent) = p.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    match fs::create_dir(&p) {
        Ok(_) => Ok(p),
        Err(e) => Err(format!("LOCK_EXISTS_OR_CREATE_FAILED:{}", e)),
    }
}

fn release_lock(p: &Path) {
    let _ = fs::remove_dir(p);
}

fn run_subtask(group: &str, task: &SubTask) -> serde_json::Value {
    let bin_path = PathBuf::from(task.bin);
    let started = Local::now();
    let mut status = "PASS".to_string();
    let mut exit_code: Option<i32> = None;
    let mut stdout = String::new();
    let mut stderr = String::new();
    let mut error = String::new();
    let began = Instant::now();

    if !bin_path.exists() {
        status = "BLOCKED_MISSING_BINARY".to_string();
        error = format!("missing binary {}", task.bin);
    } else {
        let child_res = Command::new(task.bin)
            .args(task.args)
            .current_dir(task.cwd)
            .env("HOME", home())
            .env("HERMES_HOME", hermes_home())
            .env("HERMES_AGENT_ROOT", hermes_home().join("hermes-agent"))
            .env("PYTHONPATH", hermes_home().join("hermes-agent"))
            .env("PATH", format!("{}/bin:{}/hermes-agent/.venv/bin:{}/hermes-agent/venv/bin:{}/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin", hermes_home().display(), hermes_home().display(), hermes_home().display(), home().display()))
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn();
        match child_res {
            Ok(mut child) => {
                let timeout = Duration::from_secs(task.timeout_secs);
                loop {
                    match child.try_wait() {
                        Ok(Some(_)) => break,
                        Ok(None) => {
                            if began.elapsed() > timeout {
                                let _ = child.kill();
                                status = "BLOCKED_TIMEOUT".to_string();
                                error = format!("timeout_after_{}s", task.timeout_secs);
                                break;
                            }
                            std::thread::sleep(Duration::from_millis(200));
                        }
                        Err(e) => {
                            status = "BLOCKED_WAIT_ERROR".to_string();
                            error = e.to_string();
                            break;
                        }
                    }
                }
                match child.wait_with_output() {
                    Ok(out) => {
                        exit_code = out.status.code();
                        stdout = safe_json_string(&out.stdout, 4000);
                        stderr = safe_json_string(&out.stderr, 4000);
                        if status == "PASS" && !out.status.success() {
                            status = "BLOCKED_EXIT_NONZERO".to_string();
                        }
                    }
                    Err(e) => {
                        status = "BLOCKED_OUTPUT_ERROR".to_string();
                        error = e.to_string();
                    }
                }
            }
            Err(e) => {
                status = "BLOCKED_SPAWN_ERROR".to_string();
                error = e.to_string();
            }
        }
    }

    let ended = Local::now();
    let record = json!({
        "schema": "PGGLaunchdOmnibusSubtask/v1",
        "group": group,
        "task": task.name,
        "status": status,
        "started_at": started.to_rfc3339(),
        "ended_at": ended.to_rfc3339(),
        "duration_ms": began.elapsed().as_millis(),
        "exit_code": exit_code,
        "bin": task.bin,
        "args": task.args,
        "cwd": task.cwd,
        "stdout_tail": stdout,
        "stderr_tail": stderr,
        "error": error,
        "stdout_ref": sha256_short(&stdout),
        "stderr_ref": sha256_short(&stderr),
    });

    let task_dir = data_dir(group).join("subtasks").join(task.name);
    let _ = fs::create_dir_all(&task_dir);
    let _ = fs::write(
        task_dir.join("latest.json"),
        serde_json::to_vec_pretty(&record).unwrap_or_default(),
    );
    if let Ok(mut f) = OpenOptions::new()
        .create(true)
        .append(true)
        .open(task_dir.join("ledger.jsonl"))
    {
        let _ = writeln!(
            f,
            "{}",
            serde_json::to_string(&record).unwrap_or_else(|_| "{}".to_string())
        );
    }
    record
}

fn hourly_tasks() -> Vec<SubTask> {
    vec![
        SubTask {
            name: "case_departments_idle_reaper",
            bin: "/Users/appleoppa/.hermes/bin/pgg-case-departments",
            args: &["reap", "--idle-seconds", "3600", "--json"],
            cwd: "/Users/appleoppa",
            timeout_secs: 120,
        },
        SubTask {
            name: "health_monitor",
            bin: "/Users/appleoppa/.hermes/bin/pgg-health-monitor-light-runner",
            args: &[],
            cwd: "/Users/appleoppa/.hermes/hermes-agent",
            timeout_secs: 180,
        },
        SubTask {
            name: "heartbeat_light",
            bin: "/Users/appleoppa/.hermes/bin/pgg-heartbeat-light-runner",
            args: &[],
            cwd: "/Users/appleoppa",
            timeout_secs: 180,
        },
        SubTask {
            name: "skillflow_watchdog",
            bin: "/Users/appleoppa/.hermes/bin/pgg_skillflow_p9_watchdog",
            args: &[],
            cwd: "/Users/appleoppa/.hermes/hermes-agent",
            timeout_secs: 240,
        },
        SubTask {
            name: "neuron_autoevolve_guard",
            bin: "/Users/appleoppa/.hermes/bin/pgg_neuron_autoevolve_guard",
            args: &["--threshold", "50", "--top", "80"],
            cwd: "/Users/appleoppa/.hermes/hermes-agent",
            timeout_secs: 300,
        },
        SubTask {
            name: "omniroute_sidecar_gateway",
            bin: "/Users/appleoppa/.hermes/bin/pgg-omniroute-sidecar",
            args: &[],
            cwd: "/Users/appleoppa/.hermes/hermes-agent",
            timeout_secs: 120,
        },
    ]
}

fn twice_daily_tasks() -> Vec<SubTask> {
    vec![
        SubTask {
            name: "autonomy_default_loop",
            bin: "/Users/appleoppa/.hermes/bin/pgg-autonomy-default-loop-locked",
            args: &[],
            cwd: "/Users/appleoppa/.hermes/hermes-agent",
            timeout_secs: 600,
        },
        SubTask {
            name: "self_evolution_loop",
            bin: "/Users/appleoppa/.hermes/bin/pgg_self_evolution_runner",
            args: &[],
            cwd: "/Users/appleoppa/.hermes/hermes-agent",
            timeout_secs: 600,
        },
        SubTask {
            name: "github_cli_mcp_self_evolution",
            bin: "/Users/appleoppa/.hermes/bin/pgg-github-cli-mcp-self-evolution-runner",
            args: &[],
            cwd: "/Users/appleoppa/.hermes/hermes-agent",
            timeout_secs: 600,
        },
        SubTask {
            name: "autonomy_observe_light",
            bin: "/Users/appleoppa/.hermes/bin/pgg-autonomy-observe-light-runner",
            args: &[],
            cwd: "/Users/appleoppa/.hermes/hermes-agent",
            timeout_secs: 600,
        },
        SubTask {
            name: "heartbeat_plan_rotation",
            bin: "/Users/appleoppa/.hermes/bin/pgg-heartbeat-plan-rotation-runner",
            args: &[],
            cwd: "/Users/appleoppa",
            timeout_secs: 300,
        },
    ]
}

fn weekly_tasks() -> Vec<SubTask> {
    vec![
        SubTask {
            name: "legal_ops_observer",
            bin: "/Users/appleoppa/.hermes/bin/pgg-legal-ops-daily",
            args: &[],
            cwd: "/Users/appleoppa",
            timeout_secs: 600,
        },
        SubTask {
            name: "rustization_acceptance_light",
            bin: "/Users/appleoppa/.hermes/bin/pgg-hermes-rustization-acceptance-runner",
            args: &[],
            cwd: "/Users/appleoppa/.hermes/hermes-agent",
            timeout_secs: 1200,
        },
        SubTask {
            name: "launchd_consolidation_audit",
            bin: "/Users/appleoppa/.hermes/bin/pgg_launchd_omnibus",
            args: &["--audit-consolidation"],
            cwd: "/Users/appleoppa/.hermes/hermes-agent",
            timeout_secs: 120,
        },
    ]
}

fn usage() {
    eprintln!("Usage: pgg_launchd_omnibus --group hourly|twice-daily|weekly [--force] | --audit-consolidation");
}

fn audit_consolidation() -> i32 {
    let allowed_independent = [
        "ai.hermes.gateway-pgg-business-master",
        "ai.hermes.gateway-pgg-fact-evidence",
        "ai.hermes.gateway-pgg-inspection-audit",
        "ai.hermes.gateway-pgg-law-source",
        "ai.hermes.gateway-pgg-strategy-simulation",
        "ai.hermes.omniroute-dashboard-api",
        "ai.hermes.pgg-batch-evolution-scheduler",
        "ai.hermes.pgg-exec-dashboard",
        "ai.hermes.pgg-feishu-guardian",
        "ai.hermes.webui",
        "ai.hermes.pgg-hourly-omnibus",
        "ai.hermes.pgg-twice-daily-omnibus",
        "ai.hermes.pgg-weekly-omnibus",
    ];
    let absorbed = [
        "ai.hermes.pgg-autonomy-default-loop",
        "ai.hermes.pgg-self-evolution-loop",
        "ai.hermes.pgg-github-cli-mcp-self-evolution",
        "ai.hermes.pgg-heartbeat-light-runner",
        "ai.hermes.pgg-skillflow-p9-watchdog",
        "ai.hermes.pgg-health-monitor",
        "ai.hermes.pgg-case-departments-idle-reaper",
        "ai.hermes.pgg-neuron-autoevolve-guard",
        "ai.hermes.pgg-autonomy-observe-light",
        "ai.hermes.pgg-heartbeat-plan-rotation-runner",
        "ai.hermes.pgg-legal-ops-observer",
        "ai.hermes.rustization-acceptance-light",
        "ai.hermes.pgg-omniroute-sidecar-gateway",
    ];
    let la_dir = home().join("Library/LaunchAgents");
    let mut unknown = Vec::new();
    let mut absorbed_present = Vec::new();
    if let Ok(entries) = fs::read_dir(&la_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            let Some(name) = path.file_stem().and_then(|s| s.to_str()) else {
                continue;
            };
            if !name.starts_with("ai.hermes") {
                continue;
            }
            let label = name.to_string();
            if absorbed.contains(&label.as_str()) {
                absorbed_present.push(label);
            } else if !allowed_independent.contains(&label.as_str()) {
                unknown.push(label);
            }
        }
    }
    let status = if unknown.is_empty() {
        "PASS"
    } else {
        "WATCH_UNKNOWN_LAUNCHD_LABELS"
    };
    let record = json!({
        "schema": "PGGLaunchdConsolidationAudit/v1",
        "status": status,
        "unknown_labels": unknown,
        "absorbed_plists_still_on_disk": absorbed_present,
        "allowed_independent": allowed_independent,
        "rule": "New launchd jobs must be classified into hourly/twice-daily/weekly omnibus or explicitly justified as independent long-lived/high-risk/high-frequency service before bootstrap.",
        "boundary": "Read-only audit. Does not bootout/delete/mutate launchd jobs."
    });
    let dir = hermes_home().join("data/pgg-launchd-omnibus/audit");
    let _ = fs::create_dir_all(&dir);
    let _ = fs::write(
        dir.join("latest.json"),
        serde_json::to_vec_pretty(&record).unwrap_or_default(),
    );
    println!("{}", serde_json::to_string_pretty(&record).unwrap());
    if status == "PASS" {
        0
    } else {
        1
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.iter().any(|a| a == "--audit-consolidation") {
        std::process::exit(audit_consolidation());
    }
    let mut group = "hourly".to_string();
    let mut force = false;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--group" => {
                if i + 1 >= args.len() {
                    usage();
                    std::process::exit(2);
                }
                group = args[i + 1].clone();
                i += 1;
            }
            "--force" => force = true,
            "--help" | "-h" => {
                usage();
                return;
            }
            _ => {}
        }
        i += 1;
    }

    let now = Local::now();
    let tasks = match group.as_str() {
        "hourly" => hourly_tasks(),
        "twice-daily" => twice_daily_tasks(),
        "weekly" => weekly_tasks(),
        _ => {
            usage();
            std::process::exit(2);
        }
    };

    if group == "twice-daily" && !force && !(now.hour() == 7 || now.hour() == 19) {
        eprintln!(
            "WATCH_UNEXPECTED_CALENDAR_HOUR: twice-daily launched at hour {}",
            now.hour()
        );
    }
    if group == "weekly" && !force && !(now.weekday().number_from_monday() == 1 && now.hour() == 10)
    {
        eprintln!(
            "WATCH_UNEXPECTED_CALENDAR_SLOT: weekly launched at weekday {:?} hour {}",
            now.weekday(),
            now.hour()
        );
    }

    let dir = data_dir(&group);
    let _ = fs::create_dir_all(&dir);
    let _ = fs::create_dir_all(log_dir());

    let lock = match acquire_lock(&group) {
        Ok(p) => p,
        Err(e) => {
            let rec = json!({"schema":"PGGLaunchdOmnibusRun/v1","group":group,"status":"SKIP_ALREADY_RUNNING","error":e,"timestamp":now.to_rfc3339()});
            println!("{}", serde_json::to_string_pretty(&rec).unwrap());
            std::process::exit(0);
        }
    };

    let started = Instant::now();
    let mut results = Vec::new();
    for task in &tasks {
        results.push(run_subtask(&group, task));
        std::thread::sleep(Duration::from_millis(500));
    }
    release_lock(&lock);

    let pass = results
        .iter()
        .filter(|r| r.get("status").and_then(|v| v.as_str()) == Some("PASS"))
        .count();
    let blocked = results.len().saturating_sub(pass);
    let status = if blocked == 0 {
        "PASS"
    } else {
        "PASS_WITH_SUBTASK_BLOCKED"
    };
    let record = json!({
        "schema": "PGGLaunchdOmnibusRun/v1",
        "group": group,
        "status": status,
        "started_at": now.to_rfc3339(),
        "ended_at": Local::now().to_rfc3339(),
        "duration_ms": started.elapsed().as_millis(),
        "subtask_count": results.len(),
        "pass_count": pass,
        "blocked_count": blocked,
        "results": results,
        "boundary": "Rust launchd omnibus runner; preserves per-subtask ledger; no provider/config/credential/security mutation; legacy plists should be quarantined not deleted."
    });
    let _ = fs::write(
        dir.join("latest.json"),
        serde_json::to_vec_pretty(&record).unwrap_or_default(),
    );
    if let Ok(mut f) = OpenOptions::new()
        .create(true)
        .append(true)
        .open(dir.join("ledger.jsonl"))
    {
        let _ = writeln!(
            f,
            "{}",
            serde_json::to_string(&record).unwrap_or_else(|_| "{}".to_string())
        );
    }
    println!("{}", serde_json::to_string_pretty(&record).unwrap());
    if blocked > 0 {
        std::process::exit(1);
    }
}
