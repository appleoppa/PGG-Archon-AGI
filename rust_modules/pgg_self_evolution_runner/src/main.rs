use std::fs::{self, OpenOptions};
use std::io::Write;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

const PYTHON: &str = "/Users/appleoppa/.hermes/hermes-agent/venv/bin/python";
const WORKDIR: &str = "/Users/appleoppa/.hermes/hermes-agent";
const DATA_DIR: &str = "/Users/appleoppa/.hermes/data/self-evolution-loop";
const PLIST_LABEL: &str = "ai.hermes.pgg-self-evolution-loop";

fn now_epoch() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
}

fn json_escape(s: &str) -> String {
    s.replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', "\\n")
        .replace('\r', "\\r")
}

fn serde_json_string(s: &str) -> String {
    format!("\"{}\"", json_escape(s))
}

fn main() {
    fs::create_dir_all(DATA_DIR).expect("create data dir");
    let ts = now_epoch();
    let started = ts;

    let output = Command::new(PYTHON)
        .current_dir(WORKDIR)
        .env("PYTHONPATH", WORKDIR)
        .env("HERMES_HOME", "/Users/appleoppa/.hermes")
        .args(["agent/pgg_self_evolution_loop.py", "--no-intake"])
        .output()
        .expect("run pgg_self_evolution_loop");

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    let status_code = output.status.code().unwrap_or(-1);
    let completed = now_epoch();
    let status = if output.status.success() { "PASS" } else { "ERROR" };

    let wrapper = format!(
        "{{\"schema\":\"PGGSelfEvolutionRunner/v1\",\"label\":\"{}\",\"started_epoch\":{},\"completed_epoch\":{},\"status\":\"{}\",\"exit_code\":{},\"stdout\":{},\"stderr\":{},\"boundary\":\"Rust launchd runner; local DB writes; no LLM/network; no AGI/T5/ASI claim\"}}",
        PLIST_LABEL,
        started,
        completed,
        status,
        status_code,
        serde_json_string(&stdout),
        serde_json_string(&stderr),
    );

    // Write latest.json
    let latest = format!("{}/latest.json", DATA_DIR);
    fs::write(&latest, &wrapper).expect("write latest");

    // Append to ledger
    let ledger = format!("{}/ledger.jsonl", DATA_DIR);
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&ledger)
        .expect("open ledger");
    writeln!(f, "{}", wrapper).expect("append ledger");

    println!("SELF_EVOLUTION_LOOP_{} exit_code={} latest={} duration={}s", status, status_code, latest, completed - started);

    if !output.status.success() {
        std::process::exit(2);
    }
}