use serde_json::{json, Value};
use std::env;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

const CLI: &str = "/Users/appleoppa/.hermes/bin/pgg-batch-proof-metabolism-loop";
const DATA_DIR: &str = "/Users/appleoppa/.hermes/data/batch-proof-metabolism-loop";
const WORKSPACE_ROOT: &str = "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/metabolic-evolution-phase6-rust-runner";
const BOUNDARY: &str = "Rust runner orchestrates bounded batch proof metabolism; Python CLI is legacy payload; max10; backup/diff/rollback; no legal/security/credential auto-promotion";

fn now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system time before epoch")
        .as_secs()
}

fn now_tag() -> String {
    let secs = now_epoch();
    format!("epoch{}", secs)
}

fn parse_args(args: &[String]) -> (usize, bool, Option<PathBuf>, Option<PathBuf>) {
    let mut limit = 10usize;
    let mut execute = env::var("PGG_BATCH_METABOLISM_EXECUTE").ok().as_deref() == Some("1");
    let mut outdir: Option<PathBuf> = None;
    let mut rust_core_audit_queue: Option<PathBuf> = None;
    let mut i = 1usize;
    while i < args.len() {
        match args[i].as_str() {
            "--limit" => {
                if i + 1 < args.len() {
                    limit = args[i + 1].parse().unwrap_or(10);
                    i += 1;
                }
            }
            "--execute" => execute = true,
            "--outdir" => {
                if i + 1 < args.len() {
                    outdir = Some(PathBuf::from(&args[i + 1]));
                    i += 1;
                }
            }
            "--rust-core-audit" => {
                if i + 1 < args.len() {
                    rust_core_audit_queue = Some(PathBuf::from(&args[i + 1]));
                    i += 1;
                }
            }
            _ => {}
        }
        i += 1;
    }
    if limit > 10 {
        limit = 10;
    }
    (limit, execute, outdir, rust_core_audit_queue)
}

fn extract_net_gain(payload: &Value) -> Value {
    payload.get("net_gain").cloned().unwrap_or_else(
        || json!({"promoted":0,"blocked_source_missing":0,"queue_reduced_estimate":0}),
    )
}

fn parse_source_file(packet: &Value) -> Option<String> {
    let raw = packet.get("source_refs_json")?.as_str()?;
    let parsed: Value = serde_json::from_str(raw).ok()?;
    parsed
        .get("source_file")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
}

fn evaluate_source_ref(packet: &Value) -> Value {
    let capability_id = packet
        .get("capability_id")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");
    match parse_source_file(packet) {
        Some(source_file) => {
            let exists = Path::new(&source_file).exists();
            json!({
                "capability_id": capability_id,
                "source_file": source_file,
                "verdict": if exists { "SOURCE_PRESENT" } else { "SOURCE_MISSING" },
                "exists": exists,
            })
        }
        None => json!({
            "capability_id": capability_id,
            "source_file": null,
            "verdict": "SOURCE_REF_PARSE_ERROR",
            "exists": false,
        }),
    }
}

fn build_rust_mutation_diff(packets: &[Value]) -> Value {
    let mut promote = Vec::new();
    let mut block = Vec::new();
    let mut human_or_forbidden = Vec::new();

    for packet in packets {
        let capability_id = packet
            .get("capability_id")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown")
            .to_string();
        let risk_lane = packet
            .get("risk_lane")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");
        let verdict = packet
            .get("completion_verdict")
            .or_else(|| packet.get("verdict"))
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");

        if verdict == "PASS_CONTROLLED_PROMOTION_PROPOSAL" && risk_lane == "low_engineering" {
            promote.push(json!({"capability_id": capability_id, "risk_lane": risk_lane, "action":"promote_verified"}));
        } else if verdict == "BLOCKED_SOURCE_MISSING" || verdict == "SOURCE_MISSING" {
            block.push(json!({"capability_id": capability_id, "risk_lane": risk_lane, "action":"mark_blocked_source_missing"}));
        } else if verdict == "PASS_CONTROLLED_PROMOTION_PROPOSAL" {
            human_or_forbidden.push(json!({"capability_id": capability_id, "risk_lane": risk_lane, "reason":"forbidden_auto_promotion_lane"}));
        } else {
            human_or_forbidden.push(json!({"capability_id": capability_id, "risk_lane": risk_lane, "reason":"not_promotable"}));
        }
    }

    json!({
        "schema":"PGGBatchProofMetabolismRustCoreDiff/v0.1",
        "promote_count": promote.len(),
        "block_count": block.len(),
        "human_or_forbidden_count": human_or_forbidden.len(),
        "promote": promote,
        "block": block,
        "human_or_forbidden": human_or_forbidden,
        "boundary":"Rust core diff is deterministic proposal only; DB mutation still requires controlled backup/execute gate",
    })
}

fn rust_core_audit(queue_path: &Path, limit: usize) -> Result<Value, String> {
    let raw = fs::read_to_string(queue_path).map_err(|e| format!("read queue: {e}"))?;
    let parsed: Value = serde_json::from_str(&raw).map_err(|e| format!("parse queue: {e}"))?;
    let arr = parsed.as_array().ok_or("queue json must be an array")?;
    let take_n = std::cmp::min(limit, arr.len());
    let source_evaluations: Vec<Value> = arr.iter().take(take_n).map(evaluate_source_ref).collect();
    let source_present = source_evaluations
        .iter()
        .filter(|v| v.get("verdict").and_then(|x| x.as_str()) == Some("SOURCE_PRESENT"))
        .count();
    let source_missing = source_evaluations
        .iter()
        .filter(|v| v.get("verdict").and_then(|x| x.as_str()) == Some("SOURCE_MISSING"))
        .count();
    let diff_inputs: Vec<Value> = arr
        .iter()
        .take(take_n)
        .zip(source_evaluations.iter())
        .map(|(packet, eval)| {
            let completion_verdict = match eval.get("verdict").and_then(|v| v.as_str()) {
                Some("SOURCE_MISSING") => "BLOCKED_SOURCE_MISSING",
                _ => packet
                    .get("completion_verdict")
                    .or_else(|| packet.get("verdict"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("WATCH_PROOF_PACKET_INCOMPLETE"),
            };
            json!({
                "capability_id": packet.get("capability_id").cloned().unwrap_or_else(|| json!("unknown")),
                "risk_lane": packet.get("risk_lane").cloned().unwrap_or_else(|| json!("unknown")),
                "completion_verdict": completion_verdict,
            })
        })
        .collect();
    let rust_mutation_diff = build_rust_mutation_diff(&diff_inputs);
    Ok(json!({
        "schema":"PGGBatchProofMetabolismRustCoreAudit/v0.1",
        "queue_path": queue_path,
        "limit": take_n,
        "source_present": source_present,
        "source_missing": source_missing,
        "source_parse_error": take_n - source_present - source_missing,
        "source_evaluations": source_evaluations,
        "rust_mutation_diff": rust_mutation_diff,
        "boundary":"Rust core audit performs source_ref parse/existence gate and deterministic diff proposal only; no DB mutation",
    }))
}

fn run_cli(limit: usize, execute: bool, outdir: &Path) -> (i32, String, String) {
    let mut cmd = Command::new(CLI);
    cmd.arg("--outdir")
        .arg(outdir)
        .arg("--limit")
        .arg(limit.to_string());
    if execute {
        cmd.arg("--execute");
    }
    let output = cmd.output().expect("run pgg-batch-proof-metabolism-loop");
    let code = output.status.code().unwrap_or(-1);
    (
        code,
        String::from_utf8_lossy(&output.stdout).to_string(),
        String::from_utf8_lossy(&output.stderr).to_string(),
    )
}

fn write_latest_and_ledger(wrapper: &Value) -> std::io::Result<()> {
    fs::create_dir_all(DATA_DIR)?;
    let latest = Path::new(DATA_DIR).join("latest.json");
    fs::write(&latest, serde_json::to_string_pretty(wrapper).unwrap())?;
    let ledger = Path::new(DATA_DIR).join("ledger.jsonl");
    let mut f = OpenOptions::new().create(true).append(true).open(&ledger)?;
    writeln!(f, "{}", serde_json::to_string(wrapper).unwrap())?;
    Ok(())
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let (limit, execute, outdir_arg, rust_core_audit_queue) = parse_args(&args);
    fs::create_dir_all(WORKSPACE_ROOT).expect("create workspace root");
    let outdir = outdir_arg.unwrap_or_else(|| Path::new(WORKSPACE_ROOT).join(now_tag()));

    if let Some(queue_path) = rust_core_audit_queue {
        fs::create_dir_all(&outdir).expect("create rust core audit outdir");
        let started = now_epoch();
        match rust_core_audit(&queue_path, limit) {
            Ok(mut audit) => {
                audit["started_epoch"] = json!(started);
                audit["completed_epoch"] = json!(now_epoch());
                audit["status"] = json!("PASS_RUST_CORE_AUDIT");
                let audit_path = outdir.join("rust_core_audit.json");
                fs::write(&audit_path, serde_json::to_string_pretty(&audit).unwrap())
                    .expect("write rust core audit");
                println!("{}", serde_json::to_string_pretty(&audit).unwrap());
                return;
            }
            Err(err) => {
                let failure = json!({
                    "schema":"PGGBatchProofMetabolismRustCoreAudit/v0.1",
                    "status":"ERROR_RUST_CORE_AUDIT",
                    "error":err,
                    "queue_path":queue_path,
                    "boundary":"Rust core audit failed before any DB mutation",
                });
                println!("{}", serde_json::to_string_pretty(&failure).unwrap());
                std::process::exit(2);
            }
        }
    }

    let started = now_epoch();
    let (exit_code, stdout, stderr) = run_cli(limit, execute, &outdir);
    let completed = now_epoch();
    let parsed: Option<Value> = serde_json::from_str(stdout.trim()).ok();
    let net_gain = parsed
        .as_ref()
        .map(extract_net_gain)
        .unwrap_or_else(|| json!({}));
    let status = if exit_code == 0 { "PASS" } else { "ERROR" };
    let wrapper = json!({
        "schema": "PGGBatchProofMetabolismRustRunner/v0.1",
        "started_epoch": started,
        "completed_epoch": completed,
        "status": status,
        "exit_code": exit_code,
        "limit": limit,
        "execute": execute,
        "outdir": outdir,
        "net_gain": net_gain,
        "payload": parsed,
        "stdout_tail": stdout.chars().rev().take(4000).collect::<String>().chars().rev().collect::<String>(),
        "stderr_tail": stderr.chars().rev().take(4000).collect::<String>().chars().rev().collect::<String>(),
        "boundary": BOUNDARY,
    });
    write_latest_and_ledger(&wrapper).expect("write runner latest/ledger");
    println!("{}", serde_json::to_string_pretty(&wrapper).unwrap());
    if exit_code != 0 {
        std::process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn limit_is_clamped_to_ten() {
        let args = vec![
            "runner".to_string(),
            "--limit".to_string(),
            "99".to_string(),
        ];
        let (limit, _, _, _) = parse_args(&args);
        assert_eq!(limit, 10);
    }

    #[test]
    fn extract_net_gain_defaults_when_missing() {
        let payload = json!({"schema":"x"});
        let gain = extract_net_gain(&payload);
        assert_eq!(gain["promoted"], 0);
        assert_eq!(gain["queue_reduced_estimate"], 0);
    }

    #[test]
    fn source_ref_gate_detects_present_and_missing_files() {
        let temp_file =
            std::env::temp_dir().join(format!("pgg_source_ref_gate_{}.txt", now_epoch()));
        fs::write(&temp_file, "ok").unwrap();
        let present = json!({
            "capability_id":"gene-present",
            "risk_lane":"low_engineering",
            "source_refs_json": serde_json::to_string(&json!({"source_file": temp_file})).unwrap()
        });
        let missing = json!({
            "capability_id":"gene-missing",
            "risk_lane":"low_engineering",
            "source_refs_json": "{\"source_file\":\"/definitely/not/here.py\"}"
        });
        assert_eq!(evaluate_source_ref(&present)["verdict"], "SOURCE_PRESENT");
        assert_eq!(evaluate_source_ref(&missing)["verdict"], "SOURCE_MISSING");
        let _ = fs::remove_file(temp_file);
    }

    #[test]
    fn mutation_diff_blocks_non_low_engineering_auto_promotion() {
        let packets = vec![
            json!({"capability_id":"g1","risk_lane":"low_engineering","completion_verdict":"PASS_CONTROLLED_PROMOTION_PROPOSAL"}),
            json!({"capability_id":"g2","risk_lane":"legal","completion_verdict":"PASS_CONTROLLED_PROMOTION_PROPOSAL"}),
            json!({"capability_id":"g3","risk_lane":"low_engineering","completion_verdict":"BLOCKED_SOURCE_MISSING"}),
        ];
        let diff = build_rust_mutation_diff(&packets);
        assert_eq!(diff["promote_count"], 1);
        assert_eq!(diff["block_count"], 1);
        assert_eq!(diff["human_or_forbidden_count"], 1);
    }
}
