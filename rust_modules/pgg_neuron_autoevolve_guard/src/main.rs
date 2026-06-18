use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;

const SCHEMA: &str = "PGGNeuronAutoEvolveGuard/v1";
const DEFAULT_THRESHOLD: u64 = 50;
const DEFAULT_TOP: u64 = 80;

#[derive(Debug, Serialize, Deserialize)]
struct GuardReport {
    schema: String,
    status: String,
    generated_at: String,
    threshold: u64,
    top: u64,
    live_defer_pool_count: u64,
    historical_defer_pool_count: u64,
    effective_defer_pool_count: u64,
    triggered: bool,
    actions: Vec<ActionResult>,
    candidate_pack_path: String,
    candidate_pack_sha256: Option<String>,
    skill_reference_path: String,
    skill_reference_sha256: Option<String>,
    manifest_key: String,
    boundary: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct ActionResult {
    name: String,
    status: String,
    exit_code: Option<i32>,
    stdout_sha256: Option<String>,
    stderr_sha256: Option<String>,
    summary: String,
}

fn home() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}
fn hermes() -> PathBuf {
    home().join(".hermes")
}
fn root() -> PathBuf {
    hermes().join("workspace/pgg-archon-governance/session-neural-consolidation")
}
fn data_dir() -> PathBuf {
    hermes().join("data/neuron-autoevolve-guard")
}
fn latest_path() -> PathBuf {
    data_dir().join("latest.json")
}
fn ledger_path() -> PathBuf {
    data_dir().join("ledger.jsonl")
}
fn manifest_path() -> PathBuf {
    hermes().join("data/EVOLUTION_MANIFEST.json")
}
fn candidate_pack_path() -> PathBuf {
    root().join("defer-pool-reference-candidates-20260618/DEFER_POOL_REFERENCE_SKILL_CANDIDATES_20260618.md")
}
fn skill_reference_path() -> PathBuf {
    hermes().join("skills/workflow/memory-retrieval-architecture/references/pgg-neuron-defer-pool-cluster-reference-candidates-20260618.md")
}

fn timestamp() -> String {
    Command::new("date")
        .arg("+%Y-%m-%dT%H:%M:%S%z")
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .unwrap_or_else(|| "unknown".to_string())
        .trim()
        .to_string()
}

fn sha256_bytes(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    digest.iter().map(|b| format!("{:02x}", b)).collect()
}
fn sha256_file(path: &Path) -> Option<String> {
    fs::read(path).ok().map(|b| sha256_bytes(&b))
}

fn read_json(path: &Path) -> Value {
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or(Value::Null)
}

fn nested_u64(v: &Value, keys: &[&str]) -> u64 {
    let mut cur = v;
    for k in keys {
        cur = match cur.get(*k) {
            Some(x) => x,
            None => return 0,
        };
    }
    cur.as_u64().unwrap_or(0)
}

fn manifest_historical_defer_count() -> u64 {
    let manifest = read_json(&manifest_path());
    let direct = nested_u64(
        &manifest,
        &[
            "latest_pgg_neuron_system_defer_cluster_route_20260610",
            "defer_pool_count",
        ],
    );
    if direct > 0 {
        return direct;
    }
    let pointer = manifest
        .get("latest_pgg_neuron_system_defer_cluster_route")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    if pointer.is_empty() {
        return 0;
    }
    nested_u64(&manifest, &[pointer, "defer_pool_count"])
}

fn live_defer_count() -> u64 {
    let latest = read_json(&root().join("defer_cluster_route_latest.json"));
    nested_u64(&latest, &["defer_pool_count"])
}

fn run_action(name: &str, program: &str, args: &[&str]) -> ActionResult {
    match Command::new(program).args(args).output() {
        Ok(out) => {
            let code = out.status.code();
            let ok = out.status.success();
            let stdout = String::from_utf8_lossy(&out.stdout);
            let stderr = String::from_utf8_lossy(&out.stderr);
            ActionResult {
                name: name.to_string(),
                status: if ok { "PASS" } else { "BLOCKED_NON_ZERO_EXIT" }.to_string(),
                exit_code: code,
                stdout_sha256: Some(sha256_bytes(&out.stdout)),
                stderr_sha256: Some(sha256_bytes(&out.stderr)),
                summary: format!(
                    "{} {} | stdout={} bytes stderr={} bytes | stdout_head={} | stderr_head={}",
                    program,
                    args.join(" "),
                    out.stdout.len(),
                    out.stderr.len(),
                    stdout
                        .chars()
                        .take(160)
                        .collect::<String>()
                        .replace('\n', " "),
                    stderr
                        .chars()
                        .take(160)
                        .collect::<String>()
                        .replace('\n', " ")
                ),
            }
        }
        Err(e) => ActionResult {
            name: name.to_string(),
            status: "BLOCKED_EXEC_FAILED".to_string(),
            exit_code: None,
            stdout_sha256: None,
            stderr_sha256: None,
            summary: e.to_string(),
        },
    }
}

fn write_candidate_pack_from_manifest() -> ActionResult {
    let manifest = read_json(&manifest_path());
    let key = "latest_pgg_neuron_system_defer_cluster_route_20260610";
    let settlement = manifest.get(key).cloned().unwrap_or(Value::Null);
    if settlement.is_null() {
        return ActionResult {
            name: "candidate_pack".to_string(),
            status: "BLOCKED_MANIFEST_SETTLEMENT_MISSING".to_string(),
            exit_code: None,
            stdout_sha256: None,
            stderr_sha256: None,
            summary: key.to_string(),
        };
    }
    let pattern_counts = settlement
        .get("pattern_counts")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();
    let destination_counts = settlement
        .get("destination_counts")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();
    let mut pattern_lines = Vec::new();
    for (k, v) in pattern_counts.iter() {
        pattern_lines.push(format!("- `{}`: `{}`", k, v.as_u64().unwrap_or(0)));
    }
    let mut dest_lines = Vec::new();
    for (k, v) in destination_counts.iter() {
        dest_lines.push(format!("- `{}`: `{}`", k, v.as_u64().unwrap_or(0)));
    }
    let content = format!(
        "# PGG 神经元 DEFER 池自动阈值候选包\n\n\
status: `PASS_AUTOGENERATED_BY_NEURON_AUTOEVOLVE_GUARD`\n\n\
source: `{}`\n\n\
defer_pool_count: `{}`\n\n\
cluster_count: `{}`\n\n\
boundary: candidate/reference package only; no MEMORY/USER write; no Akashic bulk write; no skill auto-install.\n\n\
## Destination counts\n\n{}\n\n\
## Pattern counts\n\n{}\n\n\
## 自动吸收策略\n\n\
- current live queue 达到阈值时自动运行 `pgg_neuron_defer_cluster_route` / `pgg_neuron_pattern_frequency` / `pgg_neuron_review_first_pass`。\n\
- historical settlement 达到阈值但 live queue 为 0 时，自动生成本候选包与 skill reference 索引，避免把“已聚类历史池”误报成未开始。\n\
- 候选只进入 references/skills proposal；manual curated review 仍需人工批准；Akashic 只允许小批量 gate。\n",
        key,
        settlement.get("defer_pool_count").and_then(|v| v.as_u64()).unwrap_or(0),
        settlement.get("cluster_count").and_then(|v| v.as_u64()).unwrap_or(0),
        dest_lines.join("\n"),
        pattern_lines.join("\n")
    );
    let path = candidate_pack_path();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    match fs::write(&path, content.as_bytes()) {
        Ok(_) => ActionResult {
            name: "candidate_pack".to_string(),
            status: "PASS".to_string(),
            exit_code: Some(0),
            stdout_sha256: Some(sha256_bytes(content.as_bytes())),
            stderr_sha256: None,
            summary: path.to_string_lossy().to_string(),
        },
        Err(e) => ActionResult {
            name: "candidate_pack".to_string(),
            status: "BLOCKED_WRITE_FAILED".to_string(),
            exit_code: None,
            stdout_sha256: None,
            stderr_sha256: None,
            summary: e.to_string(),
        },
    }
}

fn write_skill_reference_index() -> ActionResult {
    let pack = candidate_pack_path();
    let content = format!(
        "# PGG 神经元自动阈值触发规则\n\n\
status: `PASS_AUTOGENERATED_REFERENCE_INDEX`\n\n\
当神经元 DEFER live queue 或 historical settlement 达到阈值时，系统必须自动运行低风险候选生成链，而不是等待用户说“神经元系统”。\n\n\
## 当前默认阈值\n\n\
- live defer queue threshold: `50`\n\
- historical settlement threshold: `50`\n\n\
## 自动动作\n\n\
1. `pgg_neuron_defer_cluster_route --json --top 80`\n\
2. `pgg_neuron_pattern_frequency --min-count 3 --json`\n\
3. `pgg_neuron_review_first_pass --limit 500 --json`\n\
4. 生成候选包：`{}`\n\
5. 写入 guard ledger：`~/.hermes/data/neuron-autoevolve-guard/ledger.jsonl`\n\n\
## 安全边界\n\n\
不写 MEMORY/USER；不 bulk 写 Akashic；不自动安装 skill；不修改 provider/config/GitHub/production route。\n",
        pack.to_string_lossy()
    );
    let path = skill_reference_path();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    match fs::write(&path, content.as_bytes()) {
        Ok(_) => ActionResult {
            name: "skill_reference_index".to_string(),
            status: "PASS".to_string(),
            exit_code: Some(0),
            stdout_sha256: Some(sha256_bytes(content.as_bytes())),
            stderr_sha256: None,
            summary: path.to_string_lossy().to_string(),
        },
        Err(e) => ActionResult {
            name: "skill_reference_index".to_string(),
            status: "BLOCKED_WRITE_FAILED".to_string(),
            exit_code: None,
            stdout_sha256: None,
            stderr_sha256: None,
            summary: e.to_string(),
        },
    }
}

fn update_manifest_entry() -> ActionResult {
    let path = manifest_path();
    let mut manifest = read_json(&path);
    if !manifest.is_object() {
        return ActionResult {
            name: "manifest_entry".to_string(),
            status: "BLOCKED_MANIFEST_INVALID".to_string(),
            exit_code: None,
            stdout_sha256: None,
            stderr_sha256: None,
            summary: path.to_string_lossy().to_string(),
        };
    }
    let key = "latest_pgg_neuron_autoevolve_guard_20260618";
    let mut entry = BTreeMap::new();
    entry.insert(
        "schema".to_string(),
        json!("PGGNeuronAutoEvolveGuardSettlement/v1"),
    );
    entry.insert(
        "status".to_string(),
        json!("PASS_LAUNCHD_AUTO_THRESHOLD_GUARD_INSTALLED"),
    );
    entry.insert("created_at".to_string(), json!(timestamp()));
    entry.insert(
        "binary".to_string(),
        json!("/Users/appleoppa/.hermes/bin/pgg_neuron_autoevolve_guard"),
    );
    entry.insert(
        "launchd_label".to_string(),
        json!("ai.hermes.pgg-neuron-autoevolve-guard"),
    );
    entry.insert("threshold".to_string(), json!(DEFAULT_THRESHOLD));
    entry.insert(
        "candidate_pack".to_string(),
        json!(candidate_pack_path().to_string_lossy().to_string()),
    );
    entry.insert(
        "skill_reference".to_string(),
        json!(skill_reference_path().to_string_lossy().to_string()),
    );
    entry.insert("boundary".to_string(), json!("read-only/low-risk candidate generation; no MEMORY/USER write; no Akashic bulk write; no skill auto-install"));
    manifest["latest_pgg_neuron_autoevolve_guard"] = json!(key);
    manifest[key] = json!(entry);
    let backup = path.with_extension("json.bak_neuron_autoevolve_guard_20260618");
    let _ = fs::copy(&path, backup);
    match fs::write(
        &path,
        serde_json::to_vec_pretty(&manifest).unwrap_or_default(),
    ) {
        Ok(_) => ActionResult {
            name: "manifest_entry".to_string(),
            status: "PASS".to_string(),
            exit_code: Some(0),
            stdout_sha256: sha256_file(&path),
            stderr_sha256: None,
            summary: key.to_string(),
        },
        Err(e) => ActionResult {
            name: "manifest_entry".to_string(),
            status: "BLOCKED_WRITE_FAILED".to_string(),
            exit_code: None,
            stdout_sha256: None,
            stderr_sha256: None,
            summary: e.to_string(),
        },
    }
}

fn parse_arg_u64(name: &str, default_value: u64) -> u64 {
    let args: Vec<String> = std::env::args().collect();
    args.windows(2)
        .find(|w| w[0] == name)
        .and_then(|w| w[1].parse::<u64>().ok())
        .unwrap_or(default_value)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let threshold = parse_arg_u64("--threshold", DEFAULT_THRESHOLD);
    let top = parse_arg_u64("--top", DEFAULT_TOP);
    let live = live_defer_count();
    let historical = manifest_historical_defer_count();
    let effective = live.max(historical);
    let triggered = effective >= threshold;
    let mut actions = Vec::new();
    if triggered {
        actions.push(run_action(
            "defer_cluster_route",
            "/Users/appleoppa/.hermes/bin/pgg_neuron_defer_cluster_route",
            &["--json", "--top", &top.to_string()],
        ));
        actions.push(run_action(
            "pattern_frequency",
            "/Users/appleoppa/.hermes/bin/pgg_neuron_pattern_frequency",
            &["--min-count", "3", "--json"],
        ));
        actions.push(run_action(
            "first_pass_review",
            "/Users/appleoppa/.hermes/bin/pgg_neuron_review_first_pass",
            &["--limit", "500", "--json"],
        ));
        actions.push(write_candidate_pack_from_manifest());
        actions.push(write_skill_reference_index());
        actions.push(update_manifest_entry());
    }
    let blocked = actions.iter().any(|a| a.status.starts_with("BLOCKED"));
    let status = if blocked {
        "BLOCKED"
    } else if triggered {
        "PASS_TRIGGERED_ACTIONS_COMPLETE"
    } else {
        "PASS_BELOW_THRESHOLD_NOOP"
    };
    let report = GuardReport {
        schema: SCHEMA.to_string(),
        status: status.to_string(),
        generated_at: timestamp(),
        threshold,
        top,
        live_defer_pool_count: live,
        historical_defer_pool_count: historical,
        effective_defer_pool_count: effective,
        triggered,
        actions,
        candidate_pack_path: candidate_pack_path().to_string_lossy().to_string(),
        candidate_pack_sha256: sha256_file(&candidate_pack_path()),
        skill_reference_path: skill_reference_path().to_string_lossy().to_string(),
        skill_reference_sha256: sha256_file(&skill_reference_path()),
        manifest_key: "latest_pgg_neuron_autoevolve_guard_20260618".to_string(),
        boundary: "read-only/low-risk candidate generation; no MEMORY/USER write; no Akashic bulk write; no skill auto-install; no provider/config/GitHub/production route mutation".to_string(),
    };
    fs::create_dir_all(data_dir())?;
    let pretty = serde_json::to_string_pretty(&report)?;
    fs::write(latest_path(), &pretty)?;
    let mut ledger = OpenOptions::new()
        .create(true)
        .append(true)
        .open(ledger_path())?;
    writeln!(ledger, "{}", serde_json::to_string(&report)?)?;
    println!("{}", pretty);
    if blocked {
        std::process::exit(2);
    }
    Ok(())
}
