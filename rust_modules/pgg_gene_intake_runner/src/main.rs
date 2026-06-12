use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

const PYTHON: &str = "/Users/appleoppa/.hermes/hermes-agent/venv/bin/python";
const WORKDIR: &str = "/Users/appleoppa/.hermes/hermes-agent";
const DATA_DIR: &str = "/Users/appleoppa/.hermes/data/gene-intake-loop";

fn now_epoch() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
}

fn json_escape(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"").replace('\n', "\\n").replace('\r', "\\r")
}

fn main() {
    fs::create_dir_all(DATA_DIR).expect("create data dir");
    let ts = now_epoch();
    let started = ts;
    let output = Command::new(PYTHON)
        .current_dir(WORKDIR)
        .env("PYTHONPATH", WORKDIR)
        .args(["-m", "agent.pgg_gene_intake_loop_cli", "--json-only"])
        .output()
        .expect("run pgg_gene_intake_loop_cli");

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    let status_code = output.status.code().unwrap_or(-1);
    let completed = now_epoch();
    let status = if output.status.success() { "PASS" } else { "ERROR" };

    let wrapper = format!(
        "{{\"schema\":\"PGGGeneIntakeLaunchdRunner/v1\",\"started_epoch\":{},\"completed_epoch\":{},\"status\":\"{}\",\"exit_code\":{},\"stdout\":{},\"stderr\":{},\"boundary\":\"Rust launchd runner; dry-run intake loop by default; no network/LLM; no promotion auto-merge\"}}",
        started,
        completed,
        status,
        status_code,
        serde_json_string(&stdout),
        serde_json_string(&stderr),
    );

    let latest = format!("{}/latest.json", DATA_DIR);
    fs::write(&latest, &wrapper).expect("write latest");

    let ledger = format!("{}/ledger.jsonl", DATA_DIR);
    let mut f = OpenOptions::new().create(true).append(true).open(&ledger).expect("open ledger");
    writeln!(f, "{}", wrapper).expect("append ledger");

    println!("GENE_INTAKE_RUNNER_{} exit_code={} latest={}", status, status_code, latest);
    if !output.status.success() { std::process::exit(2); }
}

fn serde_json_string(s: &str) -> String {
    format!("\"{}\"", json_escape(s))
}
