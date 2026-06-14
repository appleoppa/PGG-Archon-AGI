use std::env;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;
use std::process::{Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

const DEFAULT_ROOT: &str = "/Users/appleoppa/.hermes/hermes-agent";
const DEFAULT_HOME: &str = "/Users/appleoppa/.hermes";
const DATA_DIR: &str = "/Users/appleoppa/.hermes/data/pgg-python-module-runner";
const LOG_PATH: &str = "/Users/appleoppa/.hermes/logs/pgg_python_module_runner.log";

fn now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}
fn esc(s: &str) -> String {
    s.replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', "\\n")
        .replace('\r', "\\r")
}
fn js(s: &str) -> String {
    format!("\"{}\"", esc(s))
}
fn first_python(root: &str) -> String {
    for c in [
        format!("{}/.venv/bin/python", root),
        format!("{}/venv/bin/python", root),
        "python3".to_string(),
    ] {
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
    let home = env::var("HERMES_HOME").unwrap_or_else(|_| DEFAULT_HOME.to_string());
    let module = env::var("PGG_RUN_MODULE")
        .ok()
        .or_else(|| env::args().nth(1))
        .unwrap_or_else(|| {
            eprintln!("PGG_PYTHON_MODULE_RUNNER_ERROR missing PGG_RUN_MODULE or first arg");
            std::process::exit(64)
        });
    let mut user_args: Vec<String> = env::args().skip(1).collect();
    if env::var("PGG_RUN_MODULE").is_err() && !user_args.is_empty() {
        user_args.remove(0);
    }
    let py = env::var("HERMES_PYTHON").unwrap_or_else(|_| first_python(&root));
    let started = now_epoch();
    let _ = fs::create_dir_all(DATA_DIR);
    append_log(&format!(
        "[{}] START module={} python={} args={:?}",
        started, module, py, user_args
    ));
    let mut cmd = Command::new(&py);
    cmd.current_dir(&root)
        .env("HERMES_HOME", &home)
        .env(
            "PYTHONPATH",
            match env::var("PYTHONPATH") {
                Ok(e) if !e.is_empty() => format!("{}:{}", root, e),
                _ => root.clone(),
            },
        )
        .arg("-m")
        .arg(&module)
        .args(&user_args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let output = match cmd.output() {
        Ok(o) => o,
        Err(e) => {
            eprintln!("PGG_PYTHON_MODULE_RUNNER_SPAWN_ERROR {}", e);
            std::process::exit(127)
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
        "[{}] END module={} status={} exit_code={} duration={}s",
        completed, module, status, code, duration
    ));
    let rec=format!("{{\"schema\":\"PGGPythonModuleRunner/v1\",\"module\":{},\"started_epoch\":{},\"completed_epoch\":{},\"status\":\"{}\",\"exit_code\":{},\"duration_s\":{},\"python\":{},\"root\":{},\"stdout_hash_len\":{},\"stderr_hash_len\":{},\"boundary\":\"Rust supervisor only; Python module business logic unchanged; no credential/config/security mutation\"}}",
        js(&module),started,completed,status,code,duration,js(&py),js(&root),stdout.len(),stderr.len());
    let safe_module = module.replace(
        |c: char| !c.is_ascii_alphanumeric() && c != '_' && c != '-',
        "_",
    );
    let latest = format!("{}/{}.latest.json", DATA_DIR, safe_module);
    let ledger = format!("{}/ledger.jsonl", DATA_DIR);
    let _ = fs::write(&latest, &rec);
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(&ledger) {
        let _ = writeln!(f, "{}", rec);
    }
    print!("{}", stdout);
    eprint!("{}", stderr);
    eprintln!(
        "PGG_PYTHON_MODULE_RUNNER_{} module={} exit_code={} latest={} duration={}s",
        status, module, code, latest, duration
    );
    if !output.status.success() {
        std::process::exit(if code >= 0 { code } else { 1 });
    }
}
