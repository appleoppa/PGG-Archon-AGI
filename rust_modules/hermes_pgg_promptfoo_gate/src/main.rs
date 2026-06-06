use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

const BOUNDARY: &str = "Rust one-click promptfoo gate: orchestrates real promptfoo CLI, Python finalizer, legal boundary gate, MiMo audit gate, and Manifest readback; not an official benchmark score, not legal correctness proof, not L2/full AGI proof.";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct PromptfooCounts {
    pub passed: u32,
    pub failed: u32,
    pub errors: u32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GateVerdict {
    pub schema: String,
    pub status: String,
    pub manifest_key: String,
    pub promptfoo_counts: PromptfooCounts,
    pub legal_boundary_status: String,
    pub audit_gate: Value,
    pub artifact_path: String,
    pub artifact_sha256: String,
    pub audit_summary_path: String,
    pub audit_summary_sha256: String,
    pub closure_path: String,
    pub closure_sha256: String,
    pub boundary: String,
}

#[derive(Debug, Clone)]
struct Config {
    hermes_agent: PathBuf,
    promptfoo_dir: PathBuf,
    config: PathBuf,
    prompt: PathBuf,
    provider: PathBuf,
    raw_result: PathBuf,
    run_log: PathBuf,
    out_dir: PathBuf,
    manifest: PathBuf,
    manifest_key: String,
    suite_id: String,
    source_type: String,
    domains: String,
    title: String,
    timeout: String,
    skip_promptfoo: bool,
    allow_dirty: bool,
}

fn default_config() -> Config {
    let home = env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string());
    let hermes_agent = PathBuf::from(format!("{home}/.hermes/hermes-agent"));
    let promptfoo_dir = PathBuf::from(format!(
        "{home}/.hermes/workspace/pgg-archon-governance/eval-harness/promptfoo-smoke"
    ));
    let raw_result = promptfoo_dir.join("artifacts/promptfoo_results_50_adaptive.json");
    let run_log = promptfoo_dir.join("artifacts/promptfoo_run_50_adaptive.log");
    Config {
        hermes_agent: hermes_agent.clone(),
        promptfoo_dir: promptfoo_dir.clone(),
        config: promptfoo_dir.join("promptfooconfig_50_adaptive.yaml"),
        prompt: promptfoo_dir.join("prompt_adaptive_50.txt"),
        provider: promptfoo_dir.join("hermes_provider.py"),
        raw_result,
        run_log,
        out_dir: PathBuf::from(format!(
            "{home}/.hermes/workspace/audit/promptfoo_50_suite_adaptive_gate_{}",
            unix_ts()
        )),
        manifest: PathBuf::from(format!("{home}/.hermes/data/EVOLUTION_MANIFEST.json")),
        manifest_key: "latest_promptfoo_50_suite_adaptive_gate".to_string(),
        suite_id: "promptfoo_50_suite_adaptive".to_string(),
        source_type: "official_harness_smoke_50".to_string(),
        domains: "arithmetic_toy:10,gsm8k_public_sample:20,legal_case_0006_fact_boundary:20"
            .to_string(),
        title: "Promptfoo 50-suite adaptive one-click Rust gate".to_string(),
        timeout: "60".to_string(),
        skip_promptfoo: false,
        allow_dirty: false,
    }
}

fn unix_ts() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

fn parse_args() -> Result<Config, String> {
    let mut cfg = default_config();
    let args: Vec<String> = env::args().collect();
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--hermes-agent" => {
                i += 1;
                cfg.hermes_agent = PathBuf::from(args.get(i).ok_or("missing --hermes-agent")?);
            }
            "--promptfoo-dir" => {
                i += 1;
                cfg.promptfoo_dir = PathBuf::from(args.get(i).ok_or("missing --promptfoo-dir")?);
            }
            "--config" => {
                i += 1;
                cfg.config = PathBuf::from(args.get(i).ok_or("missing --config")?);
            }
            "--prompt" => {
                i += 1;
                cfg.prompt = PathBuf::from(args.get(i).ok_or("missing --prompt")?);
            }
            "--provider" => {
                i += 1;
                cfg.provider = PathBuf::from(args.get(i).ok_or("missing --provider")?);
            }
            "--raw-result" => {
                i += 1;
                cfg.raw_result = PathBuf::from(args.get(i).ok_or("missing --raw-result")?);
            }
            "--run-log" => {
                i += 1;
                cfg.run_log = PathBuf::from(args.get(i).ok_or("missing --run-log")?);
            }
            "--out-dir" => {
                i += 1;
                cfg.out_dir = PathBuf::from(args.get(i).ok_or("missing --out-dir")?);
            }
            "--manifest" => {
                i += 1;
                cfg.manifest = PathBuf::from(args.get(i).ok_or("missing --manifest")?);
            }
            "--manifest-key" => {
                i += 1;
                cfg.manifest_key = args.get(i).ok_or("missing --manifest-key")?.clone();
            }
            "--suite-id" => {
                i += 1;
                cfg.suite_id = args.get(i).ok_or("missing --suite-id")?.clone();
            }
            "--source-type" => {
                i += 1;
                cfg.source_type = args.get(i).ok_or("missing --source-type")?.clone();
            }
            "--domains" => {
                i += 1;
                cfg.domains = args.get(i).ok_or("missing --domains")?.clone();
            }
            "--title" => {
                i += 1;
                cfg.title = args.get(i).ok_or("missing --title")?.clone();
            }
            "--timeout" => {
                i += 1;
                cfg.timeout = args.get(i).ok_or("missing --timeout")?.clone();
            }
            "--skip-promptfoo" => cfg.skip_promptfoo = true,
            "--allow-dirty" => cfg.allow_dirty = true,
            "--help" | "-h" => {
                print_help();
                std::process::exit(0);
            }
            other => return Err(format!("unknown argument: {other}")),
        }
        i += 1;
    }
    Ok(cfg)
}

fn print_help() {
    println!("pgg-promptfoo-gate -- Rust one-click promptfoo adaptive 50-suite gate");
    println!("  --skip-promptfoo        reuse existing raw/log artifacts; still runs finalizer+MiMo+Manifest readback");
    println!("  --allow-dirty          allow unrelated git dirty files; default blocks them");
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let data = fs::read(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    let mut hasher = Sha256::new();
    hasher.update(data);
    Ok(format!("{:x}", hasher.finalize()))
}

fn ensure_exists(path: &Path, name: &str) -> Result<(), String> {
    if path.exists() {
        Ok(())
    } else {
        Err(format!("missing {name}: {}", path.display()))
    }
}

fn check_dirty(cfg: &Config) -> Result<Value, String> {
    let out = Command::new("git")
        .arg("status")
        .arg("--short")
        .current_dir(&cfg.hermes_agent)
        .output()
        .map_err(|e| format!("git status failed: {e}"))?;
    if !out.status.success() {
        return Err(format!("git status exit={}", out.status));
    }
    let text = String::from_utf8_lossy(&out.stdout).to_string();
    let dirty: Vec<String> = text
        .lines()
        .map(|s| s.to_string())
        .filter(|s| !s.trim().is_empty())
        .collect();
    let unrelated: Vec<String> = dirty
        .iter()
        .filter(|line| {
            !(line.contains("rust_modules/hermes_pgg_promptfoo_gate/")
                || line.contains("agent/pgg_archon_promptfoo_finalize.py")
                || line.contains("agent/pgg_archon_audited_manifest_gate.py")
                || line.contains("tests/test_pgg_archon_promptfoo_finalize.py"))
        })
        .cloned()
        .collect();
    if !cfg.allow_dirty && !unrelated.is_empty() {
        return Err(format!("unrelated dirty files blocked: {unrelated:?}; pass --allow-dirty only for running gate, never for scoped commit"));
    }
    let dirty_count = dirty.len();
    let unrelated_count = unrelated.len();
    let dirty_sample: Vec<String> = dirty.into_iter().take(50).collect();
    let unrelated_sample: Vec<String> = unrelated.into_iter().take(50).collect();
    Ok(json!({
        "dirty_count": dirty_count,
        "unrelated_dirty_count": unrelated_count,
        "dirty_sample": dirty_sample,
        "unrelated_dirty_sample": unrelated_sample,
        "truncated": dirty_count > 50 || unrelated_count > 50,
        "allow_dirty": cfg.allow_dirty
    }))
}

pub fn parse_promptfoo_counts(log_text: &str) -> Result<PromptfooCounts, String> {
    let mut passed = None;
    let mut failed = None;
    let mut errors = None;
    let mut in_results = false;
    for line in log_text.lines() {
        if line.trim() == "Results:" {
            in_results = true;
            continue;
        }
        if !in_results {
            continue;
        }
        let clean: String = line
            .chars()
            .filter(|c| c.is_ascii_digit() || c.is_ascii_whitespace() || c.is_ascii_alphabetic())
            .collect();
        let mut parts = clean.split_whitespace();
        if let Some(n) = parts.next().and_then(|s| s.parse::<u32>().ok()) {
            let rest = parts.collect::<Vec<_>>().join(" ").to_lowercase();
            if rest.contains("passed") {
                passed = Some(n);
            }
            if rest.contains("failed") {
                failed = Some(n);
            }
            if rest.contains("errors") {
                errors = Some(n);
            }
        }
    }
    match (passed, failed, errors) {
        (Some(p), Some(f), Some(e)) => Ok(PromptfooCounts {
            passed: p,
            failed: f,
            errors: e,
        }),
        _ => Err("could not parse promptfoo Results counts".to_string()),
    }
}

pub fn parse_promptfoo_counts_from_raw(raw_text: &str) -> Result<PromptfooCounts, String> {
    let obj: Value =
        serde_json::from_str(raw_text).map_err(|e| format!("raw JSON parse failed: {e}"))?;
    let rows = obj
        .get("results")
        .and_then(|v| v.get("results"))
        .and_then(Value::as_array)
        .ok_or_else(|| "raw JSON missing results.results".to_string())?;
    let mut passed = 0u32;
    let mut failed = 0u32;
    let mut errors = 0u32;
    for row in rows {
        if row.get("success").and_then(Value::as_bool) == Some(true)
            || row.get("score").and_then(Value::as_i64) == Some(1)
        {
            passed += 1;
        } else if row.get("error").is_some() || row.get("failureReason").is_some() {
            errors += 1;
        } else {
            failed += 1;
        }
    }
    Ok(PromptfooCounts {
        passed,
        failed,
        errors,
    })
}

fn run_promptfoo(cfg: &Config) -> Result<(), String> {
    fs::create_dir_all(cfg.raw_result.parent().unwrap()).map_err(|e| e.to_string())?;
    let shell = format!(
        "set -o pipefail && PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_PYTHON={}/venv/bin/python3 npm exec --yes --package promptfoo@0.121.15 -- promptfoo eval --config {} --output {} 2>&1 | tee {}",
        cfg.hermes_agent.display(),
        shell_quote(&cfg.config),
        shell_quote(&cfg.raw_result),
        shell_quote(&cfg.run_log),
    );
    let status = Command::new("bash")
        .arg("-lc")
        .arg(shell)
        .current_dir(&cfg.promptfoo_dir)
        .status()
        .map_err(|e| format!("promptfoo spawn failed: {e}"))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("promptfoo exit={status}"))
    }
}

fn run_finalizer(cfg: &Config) -> Result<Value, String> {
    fs::create_dir_all(&cfg.out_dir).map_err(|e| e.to_string())?;
    let output = Command::new("python3")
        .arg("-m")
        .arg("agent.pgg_archon_promptfoo_finalize")
        .arg("--raw-result")
        .arg(&cfg.raw_result)
        .arg("--run-log")
        .arg(&cfg.run_log)
        .arg("--config")
        .arg(&cfg.config)
        .arg("--prompt")
        .arg(&cfg.prompt)
        .arg("--provider")
        .arg(&cfg.provider)
        .arg("--out-dir")
        .arg(&cfg.out_dir)
        .arg("--suite-id")
        .arg(&cfg.suite_id)
        .arg("--source-type")
        .arg(&cfg.source_type)
        .arg("--domains")
        .arg(&cfg.domains)
        .arg("--manifest-key")
        .arg(&cfg.manifest_key)
        .arg("--title")
        .arg(&cfg.title)
        .arg("--requested-status")
        .arg("PASS")
        .arg("--timeout")
        .arg(&cfg.timeout)
        .arg("--legal-boundary-precheck")
        .current_dir(&cfg.hermes_agent)
        .env("PYTHONPATH", &cfg.hermes_agent)
        .output()
        .map_err(|e| format!("finalizer spawn failed: {e}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
    fs::write(cfg.out_dir.join("finalizer.stdout.txt"), &stdout).map_err(|e| e.to_string())?;
    fs::write(cfg.out_dir.join("finalizer.stderr.txt"), &stderr).map_err(|e| e.to_string())?;
    if !output.status.success() {
        return Err(format!("finalizer exit={} stderr={stderr}", output.status));
    }
    let last_json = stdout
        .lines()
        .rev()
        .find(|l| l.trim_start().starts_with('{'))
        .ok_or("finalizer stdout missing JSON")?;
    serde_json::from_str(last_json)
        .map_err(|e| format!("finalizer JSON parse failed: {e}; stdout={stdout}"))
}

fn shell_quote(p: &Path) -> String {
    let s = p.to_string_lossy().replace('\'', "'\\''");
    format!("'{s}'")
}

fn read_json(path: &Path) -> Result<Value, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    serde_json::from_str(&text).map_err(|e| format!("json parse {}: {e}", path.display()))
}

fn verify_gate(cfg: &Config) -> Result<GateVerdict, String> {
    ensure_exists(&cfg.raw_result, "raw_result")?;
    ensure_exists(&cfg.run_log, "run_log")?;
    ensure_exists(&cfg.config, "config")?;
    ensure_exists(&cfg.prompt, "prompt")?;
    let counts =
        parse_promptfoo_counts(&fs::read_to_string(&cfg.run_log).map_err(|e| e.to_string())?)
            .or_else(|_| {
                parse_promptfoo_counts_from_raw(
                    &fs::read_to_string(&cfg.raw_result).map_err(|e| e.to_string())?,
                )
            })?;
    if counts
        != (PromptfooCounts {
            passed: 50,
            failed: 0,
            errors: 0,
        })
    {
        return Err(format!("promptfoo counts are not 50/0/0: {counts:?}"));
    }
    let manifest = read_json(&cfg.manifest)?;
    let entry = manifest
        .get(&cfg.manifest_key)
        .ok_or_else(|| format!("manifest key missing: {}", cfg.manifest_key))?;
    if entry.get("status").and_then(Value::as_str) != Some("PASS") {
        return Err(format!(
            "manifest status not PASS: {:?}",
            entry.get("status")
        ));
    }
    let audit_gate = entry
        .get("audit_gate")
        .ok_or("manifest audit_gate missing")?
        .clone();
    let judge_called = audit_gate
        .get("judge_called")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let pass_count = audit_gate
        .get("pass_count")
        .and_then(Value::as_u64)
        .unwrap_or(0);
    let audit_count = audit_gate
        .get("audit_count")
        .and_then(Value::as_u64)
        .unwrap_or(0);
    let timeout_count = audit_gate
        .get("timeout_count")
        .and_then(Value::as_u64)
        .unwrap_or(999);
    let reasons_empty = audit_gate
        .get("downgrade_reasons")
        .and_then(Value::as_array)
        .map(|a| a.is_empty())
        .unwrap_or(false);
    if !(judge_called && pass_count == 3 && audit_count == 3 && timeout_count == 0 && reasons_empty)
    {
        return Err(format!("audit_gate not strict PASS: {audit_gate}"));
    }
    let legal = entry
        .get("legal_boundary_gate")
        .ok_or("legal_boundary_gate missing")?;
    let legal_status = legal
        .get("status")
        .and_then(Value::as_str)
        .unwrap_or("UNKNOWN")
        .to_string();
    if legal_status != "PASS" {
        return Err(format!("legal boundary not PASS: {legal_status}"));
    }
    let artifact_path = PathBuf::from(
        entry
            .get("artifact_path")
            .and_then(Value::as_str)
            .ok_or("artifact_path missing")?,
    );
    let audit_summary_path = PathBuf::from(
        entry
            .get("audit_summary_path")
            .and_then(Value::as_str)
            .ok_or("audit_summary_path missing")?,
    );
    let closure_path = PathBuf::from(
        entry
            .get("closure_path")
            .and_then(Value::as_str)
            .unwrap_or(""),
    );
    ensure_exists(&artifact_path, "artifact")?;
    ensure_exists(&audit_summary_path, "audit_summary")?;
    if !closure_path.as_os_str().is_empty() {
        ensure_exists(&closure_path, "closure")?;
    }
    let artifact_sha = sha256_file(&artifact_path)?;
    let summary_sha = sha256_file(&audit_summary_path)?;
    let closure_sha = if closure_path.as_os_str().is_empty() {
        "".to_string()
    } else {
        sha256_file(&closure_path)?
    };
    if entry.get("artifact_sha256").and_then(Value::as_str) != Some(artifact_sha.as_str()) {
        return Err("artifact sha mismatch with manifest".to_string());
    }
    if entry.get("audit_summary_sha256").and_then(Value::as_str) != Some(summary_sha.as_str()) {
        return Err("audit summary sha mismatch with manifest".to_string());
    }
    Ok(GateVerdict {
        schema: "PGGArchonRustPromptfooGateVerdict/v1".to_string(),
        status: "PASS".to_string(),
        manifest_key: cfg.manifest_key.clone(),
        promptfoo_counts: counts,
        legal_boundary_status: legal_status,
        audit_gate,
        artifact_path: artifact_path.display().to_string(),
        artifact_sha256: artifact_sha,
        audit_summary_path: audit_summary_path.display().to_string(),
        audit_summary_sha256: summary_sha,
        closure_path: closure_path.display().to_string(),
        closure_sha256: closure_sha,
        boundary: BOUNDARY.to_string(),
    })
}

fn main() {
    let cfg = match parse_args() {
        Ok(c) => c,
        Err(e) => fail(&e),
    };
    for (p, name) in [
        (&cfg.hermes_agent, "hermes_agent"),
        (&cfg.promptfoo_dir, "promptfoo_dir"),
        (&cfg.config, "config"),
        (&cfg.prompt, "prompt"),
        (&cfg.provider, "provider"),
    ] {
        if let Err(e) = ensure_exists(p, name) {
            fail(&e);
        }
    }
    let dirty = match check_dirty(&cfg) {
        Ok(v) => v,
        Err(e) => fail(&e),
    };
    if !cfg.skip_promptfoo {
        if let Err(e) = run_promptfoo(&cfg) {
            fail(&e);
        }
    }
    if let Err(e) = run_finalizer(&cfg) {
        fail(&e);
    }
    match verify_gate(&cfg) {
        Ok(verdict) => {
            let out_path = cfg.out_dir.join("rust_gate_verdict.json");
            let mut value = serde_json::to_value(&verdict).unwrap();
            value["dirty_guard"] = dirty;
            fs::write(&out_path, serde_json::to_string_pretty(&value).unwrap()).unwrap();
            println!("{}", serde_json::to_string(&value).unwrap());
        }
        Err(e) => fail(&e),
    }
}

fn fail(reason: &str) -> ! {
    println!(
        "{}",
        json!({"schema":"PGGArchonRustPromptfooGateVerdict/v1","status":"WATCH","reason":reason,"boundary":BOUNDARY})
    );
    std::process::exit(2);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_promptfoo_counts() {
        let log = "Results:\n  ✓ 50 passed (100%)\n  0 failed (0%)\n  0 errors (0%)\n";
        assert_eq!(
            parse_promptfoo_counts(log).unwrap(),
            PromptfooCounts {
                passed: 50,
                failed: 0,
                errors: 0
            }
        );
    }

    #[test]
    fn fails_when_counts_missing() {
        assert!(parse_promptfoo_counts("no results").is_err());
    }

    #[test]
    fn parses_failed_counts() {
        let log = "Results:\n  ✓ 45 passed (90%)\n  ✗ 5 failed (10%)\n  0 errors (0%)\n";
        assert_eq!(
            parse_promptfoo_counts(log).unwrap(),
            PromptfooCounts {
                passed: 45,
                failed: 5,
                errors: 0
            }
        );
    }

    #[test]
    fn parses_counts_from_raw() {
        let raw = r#"{"results":{"results":[{"success":true},{"score":1},{"success":false},{"error":"x"}]}}"#;
        assert_eq!(
            parse_promptfoo_counts_from_raw(raw).unwrap(),
            PromptfooCounts {
                passed: 2,
                failed: 1,
                errors: 1
            }
        );
    }
}
