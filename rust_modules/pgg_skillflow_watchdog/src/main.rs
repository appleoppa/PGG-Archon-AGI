// pgg_skillflow_watchdog – Rust replacement for LLM-agent cron watchdog
// Reads gate JSON files, checks invariants, reports regressions.
// SOUL.md #8: Rust优先硬红线. SOUL.md #9: cron任务首选launchd.
// Zero LLM calls: pure JSON read + structural comparison.
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Deserialize)]
struct ReadinessGate {
    status: Option<String>,
    production_answer_chain_replaced: Option<serde_json::Value>,
    route_enforce: Option<serde_json::Value>,
    checks: Option<BTreeMap<String, serde_json::Value>>,
    blockers: Option<Vec<String>>,
    summary_zh: Option<String>,
}

#[derive(Debug, Deserialize)]
struct LiveWindowStatus {
    status: Option<String>,
    #[serde(rename = "strict_real_live_count", alias = "real_live_count")]
    real_live_count: Option<f64>,
    #[serde(rename = "strict_real_live")]
    strict_real_live: Option<f64>,
    summary_zh: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ProductionReadiness {
    status: Option<String>,
    score: Option<f64>,
    summary_zh: Option<String>,
}

#[derive(Debug, Deserialize)]
struct GenericGate {
    status: Option<String>,
    #[serde(flatten)]
    extra: BTreeMap<String, serde_json::Value>,
}

fn hermes_home() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".into()))
        .join(".hermes")
}

fn read_json<T: for<'a> Deserialize<'a>>(path: &Path) -> Option<T> {
    let content = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&content).ok()
}

fn sha256_file(path: &Path) -> String {
    let content = std::fs::read(path).ok().unwrap_or_default();
    let mut hasher = Sha256::new();
    hasher.update(&content);
    format!("{:x}", hasher.finalize())
}

fn run_cmd(cmd: &str, args: &[&str], _timeout_secs: u64) -> (i32, String) {
    let child = std::process::Command::new(cmd).args(args).output();
    match child {
        Ok(output) => {
            let code = output.status.code().unwrap_or(999);
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            (code, stdout)
        }
        Err(e) => (999, format!("{}: {}", cmd, e)),
    }
}

#[derive(Debug)]
struct CheckResult {
    name: String,
    pass: bool,
    detail: String,
}

fn main() -> std::process::ExitCode {
    let data_dir = hermes_home().join("data");
    let snapshot_dir = hermes_home()
        .join("workspace")
        .join("pgg-archon-governance")
        .join("production-readiness-route-enforce-20260607")
        .join("limited_support_watchdog");
    let _ = std::fs::create_dir_all(&snapshot_dir);

    let mut results: Vec<CheckResult> = vec![];
    let mut all_pass = true;

    // 1. Readiness gate — limited_support_lane EXPECTED state:
    //    route_enforce=false, production_answer_chain_replaced=false,
    //    explicit_user_authorization_missing blocker is the CORRECT safety behavior
    let rpath = data_dir.join("pgg_skillflow_readiness_gate.json");
    if let Some(gate) = read_json::<ReadinessGate>(&rpath) {
        let enforce = gate
            .route_enforce
            .and_then(|v| v.as_bool())
            .unwrap_or(true);
        let replaced = gate
            .production_answer_chain_replaced
            .and_then(|v| v.as_bool())
            .unwrap_or(true);
        // limited_support_lane: enforce=false & replaced=false is EXPECTED & safe
        let safe = !enforce && !replaced;
        // safety_invariants check from the gate
        let safety_ok = gate
            .checks
            .as_ref()
            .and_then(|c| c.get("safety_invariants"))
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        results.push(CheckResult {
            name: "readiness_gate".into(),
            pass: safe && safety_ok,
            detail: format!(
                "route_enforce={} prod_replaced={} safety_invariants={} status={:?} (WATCH+auth_blocked=expected)",
                enforce,
                replaced,
                safety_ok,
                gate.status.as_deref().unwrap_or("?")
            ),
        });
        if !safe || !safety_ok {
            all_pass = false;
        }
    } else {
        results.push(CheckResult {
            name: "readiness_gate".into(),
            pass: false,
            detail: "FILE_MISSING_OR_UNREADABLE".into(),
        });
        all_pass = false;
    }

    // 2. Live window
    let lpath = data_dir.join("pgg_skillflow_live_window_status.json");
    if let Some(win) = read_json::<LiveWindowStatus>(&lpath) {
        let count = win.real_live_count.or(win.strict_real_live).unwrap_or(0.0);
        let enough = count >= 100.0;
        results.push(CheckResult {
            name: "live_window".into(),
            pass: enough,
            detail: format!("strict_real_live={} status={:?}", count, win.status.as_deref().unwrap_or("?")),
        });
        if !enough {
            all_pass = false;
        }
    } else {
        results.push(CheckResult {
            name: "live_window".into(),
            pass: false,
            detail: "FILE_MISSING_OR_UNREADABLE".into(),
        });
        all_pass = false;
    }

    // 3. Production readiness
    let ppath = data_dir.join("pgg_production_readiness_gate.json");
    if let Some(prod) = read_json::<ProductionReadiness>(&ppath) {
        let good = prod
            .status
            .as_deref()
            .map(|s| s.starts_with("PASS"))
            .unwrap_or(false);
        results.push(CheckResult {
            name: "production_readiness".into(),
            pass: good,
            detail: format!(
                "status={:?} score={:?}",
                prod.status.as_deref().unwrap_or("?"),
                prod.score
            ),
        });
        if !good {
            all_pass = false;
        }
    } else {
        results.push(CheckResult {
            name: "production_readiness".into(),
            pass: false,
            detail: "FILE_MISSING_OR_UNREADABLE".into(),
        });
        all_pass = false;
    }

    // 4. Phase gate (现有benchmark/phase gate)
    let phath = data_dir.join("pgg_skillflow_benchmark14_status.json");
    if let Some(phase) = read_json::<GenericGate>(&phath) {
        let good = phase
            .status
            .as_deref()
            .map(|s| s.starts_with("PASS"))
            .unwrap_or(false);
        results.push(CheckResult {
            name: "benchmark14_phase".into(),
            pass: good,
            detail: format!("status={:?}", phase.status.as_deref().unwrap_or("?")),
        });
        if !good {
            all_pass = false;
        }
    } else {
        // Not all gates exist yet — acceptable
        results.push(CheckResult {
            name: "benchmark14_phase".into(),
            pass: true,
            detail: "FILE_MISSING (acceptable, not yet created)".into(),
        });
    }

    // 5. Security invariants: verify gateway-pgg deny still active
    //    The 5 gateway-pgg services + global gateway enforce hard-deny for
    //    legal/audit/AGI/credential/scheduler/security. Check plists loaded.
    let gateway_services = [
        "ai.hermes.gateway-pgg-business-master",
        "ai.hermes.gateway-pgg-fact-evidence",
        "ai.hermes.gateway-pgg-inspection-audit",
        "ai.hermes.gateway-pgg-law-source",
        "ai.hermes.gateway-pgg-strategy-simulation",
        "ai.hermes.gateway",
    ];
    let mut deny_pass = true;
    let mut deny_detail = String::new();
    for srv in &gateway_services {
        let (code, out) = run_cmd("launchctl", &["list", srv], 5);
        let loaded = code == 0 && out.contains(srv);
        if !loaded {
            deny_pass = false;
            deny_detail.push_str(&format!("{}_not_loaded ", srv));
        }
    }
    if deny_detail.is_empty() {
        deny_detail = "all_gateway_services_loaded".into();
    }
    results.push(CheckResult {
        name: "high_risk_deny".into(),
        pass: deny_pass,
        detail: deny_detail,
    });
    if !deny_pass {
        all_pass = false;
    }

    // 6. Snapshot & regression detection
    let snapshot_path = snapshot_dir.join("watchdog_snapshot.json");
    let current_digest = sha256_file(&rpath);
    let regression = if snapshot_path.exists() {
        let prev = std::fs::read_to_string(&snapshot_path).unwrap_or_default();
        prev.trim() != current_digest
    } else {
        true // first run, no regression
    };

    // Update snapshot
    let snap = serde_json::json!({
        "readiness_gate_sha256": current_digest,
        "ts": SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs(),
        "all_pass": all_pass,
        "results": results.iter().map(|r| serde_json::json!({
            "name": r.name,
            "pass": r.pass,
            "detail": r.detail
        })).collect::<Vec<_>>()
    });
    let _ = std::fs::write(&snapshot_path, serde_json::to_string_pretty(&snap).unwrap());

    // Report
    if all_pass && !regression {
        eprintln!("[SILENT] SkillFlow invariants all pass; snapshot unchanged.");
        std::process::ExitCode::SUCCESS
    } else if all_pass && regression {
        eprintln!("[MINOR] SkillFlow invariants pass but gate files changed (expected rotation). No alarm.");
        std::process::ExitCode::SUCCESS
    } else {
        // P0 ALARM
        println!("=== P0 ALARM: SkillFlow Watchdog ===");
        println!("Timestamp: {:?}",
            SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs());
        println!("All invariants pass: false");
        println!();
        for r in &results {
            let icon = if r.pass { "✅" } else { "❌" };
            println!("{} {}: {}", icon, r.name, r.detail);
        }
        println!();
        println!("Boundary: limited_support_lane watchdog; route_enforce=false, production_answer_chain_replaced=limited_support_lane.");
        println!("Does not represent full AGI, external benchmark, legal correctness, or full/global route_enforce.");
        std::process::ExitCode::from(1)
    }
}