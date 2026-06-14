use std::env;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;
use std::process::{Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

const DEFAULT_ROOT: &str = "/Users/appleoppa/.hermes/hermes-agent";
const DEFAULT_HOME: &str = "/Users/appleoppa/.hermes";
const LOG_PATH: &str = "/Users/appleoppa/.hermes/logs/pgg_skillflow_p9_watchdog.log";
const DATA_DIR: &str = "/Users/appleoppa/.hermes/data/pgg-skillflow-p9-watchdog";

fn now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

fn json_escape(s: &str) -> String {
    s.replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', "\\n")
        .replace('\r', "\\r")
}

fn json_str(s: &str) -> String {
    format!("\"{}\"", json_escape(s))
}

fn first_existing_python(root: &str) -> String {
    let candidates = [
        format!("{}/.venv/bin/python", root),
        format!("{}/venv/bin/python", root),
        "/Users/appleoppa/.hermes/hermes-agent/.venv/bin/python".to_string(),
        "/Users/appleoppa/.hermes/hermes-agent/venv/bin/python".to_string(),
        "python3".to_string(),
    ];
    for c in candidates {
        if c == "python3" || Path::new(&c).exists() {
            return c;
        }
    }
    "python3".to_string()
}

fn append_log(s: &str) {
    if let Some(parent) = Path::new(LOG_PATH).parent() {
        let _ = fs::create_dir_all(parent);
    }
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(LOG_PATH) {
        let _ = writeln!(f, "{}", s);
    }
}

fn main() {
    let root = env::var("HERMES_AGENT_ROOT").unwrap_or_else(|_| DEFAULT_ROOT.to_string());
    let hermes_home = env::var("HERMES_HOME").unwrap_or_else(|_| DEFAULT_HOME.to_string());
    let py = first_existing_python(&root);
    let args: Vec<String> = env::args().skip(1).collect();
    let started = now_epoch();
    let _ = fs::create_dir_all(DATA_DIR);

    append_log(&format!(
        "[{}] START pgg_skillflow_p9_watchdog_runner python={} args={:?}",
        started, py, args
    ));

    let mut cmd = Command::new(&py);
    cmd.current_dir(&root)
        .env("HERMES_HOME", &hermes_home)
        .env(
            "PYTHONPATH",
            match env::var("PYTHONPATH") {
                Ok(existing) if !existing.is_empty() => format!("{}:{}", root, existing),
                _ => root.clone(),
            },
        )
        .arg("-m")
        .arg("agent.pgg_skillflow_live_window_gate")
        .arg("--summary")
        .args(&args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    let output = match cmd.output() {
        Ok(o) => o,
        Err(e) => {
            let msg = format!("spawn_error: {}", e);
            append_log(&msg);
            eprintln!("PGG_SKILLFLOW_P9_WATCHDOG_ERROR {}", msg);
            std::process::exit(127);
        }
    };
    let completed = now_epoch();
    let duration = completed.saturating_sub(started);
    let code = output.status.code().unwrap_or(-1);
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    let status = if output.status.success() {
        "PASS"
    } else {
        "ERROR"
    };

    append_log(&format!(
        "[{}] END status={} exit_code={} duration={}s",
        completed, status, code, duration
    ));
    if !stdout.trim().is_empty() {
        append_log(&format!("stdout: {}", stdout.trim()));
    }
    if !stderr.trim().is_empty() {
        append_log(&format!("stderr: {}", stderr.trim()));
    }

    let latest = format!(
        "{{\"schema\":\"PGGSkillflowP9WatchdogRustRunner/v1\",\"started_epoch\":{},\"completed_epoch\":{},\"status\":\"{}\",\"exit_code\":{},\"duration_s\":{},\"python\":{},\"root\":{},\"stdout\":{},\"stderr\":{},\"boundary\":\"Rust supervisor for existing Python module; no production route mutation; no AGI/T5 claim\"}}",
        started, completed, status, code, duration, json_str(&py), json_str(&root), json_str(&stdout), json_str(&stderr)
    );
    let latest_path = format!("{}/latest.json", DATA_DIR);
    let ledger_path = format!("{}/ledger.jsonl", DATA_DIR);
    let _ = fs::write(&latest_path, &latest);
    if let Ok(mut f) = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&ledger_path)
    {
        let _ = writeln!(f, "{}", latest);
    }

    print!("{}", stdout);
    eprint!("{}", stderr);
    println!(
        "PGG_SKILLFLOW_P9_WATCHDOG_{} exit_code={} latest={} duration={}s",
        status, code, latest_path, duration
    );
    if !output.status.success() {
        std::process::exit(2);
    }
}
