// pgg_curve_collector – Rust replacement for pgg_autonomy_curve_collector.py
// Reads evolution pipeline ledger, checks PR/git/cron state, writes curve sample.
// SOUL.md #8: Rust优先硬红线. SOUL.md #9: cron任务首选launchd.
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize)]
struct LedgerRow {
    #[serde(default)]
    status: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct CurveSample {
    schema: String,
    generated_at: String,
    status: String,
    checks: serde_json::Value,
    pipeline_rows_sampled: usize,
    pipeline_pass_count: usize,
    pipeline_watch_count: usize,
    pipeline_fail_count: usize,
    pipeline_success_rate: Option<f64>,
    open_pr_count: usize,
    cost_latency_available: bool,
    rollback_count_available: bool,
    multi_day_claim_allowed: bool,
    boundary: String,
}

fn hermes_home() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".into()))
        .join(".hermes")
}

fn read_ledger(data_dir: &PathBuf, limit: usize) -> Vec<LedgerRow> {
    let path = data_dir.join("pgg_github_evolution_pipeline_ledger.jsonl");
    if !path.exists() {
        return vec![];
    }
    let content = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return vec![],
    };
    content
        .lines()
        .rev()
        .take(limit)
        .filter_map(|line| serde_json::from_str::<LedgerRow>(line).ok())
        .collect()
}

fn run_cmd(cmd: &str, args: &[&str], timeout_secs: u64) -> (i32, String) {
    let child = Command::new(cmd).args(args).output();
    match child {
        Ok(output) => {
            let code = output.status.code().unwrap_or(999);
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            (code, stdout)
        }
        Err(e) => (999, format!("{}: {}", cmd, e)),
    }
}

fn collect_checks(total: usize, pass_count: usize, open_prs_len: usize) -> (serde_json::Value, usize) {
    let success_rate = if total > 0 {
        Some(pass_count as f64 / total as f64)
    } else {
        None
    };

    // git clean check
    let (git_code, git_out) = run_cmd("git", &["-C", hermes_home().join("hermes-agent").to_str().unwrap_or("."), "status", "--short", "--branch"], 20);
    let git_clean = git_code == 0 && git_out.trim().is_empty();

    // cron readable check
    let (cron_code, _) = run_cmd("hermes", &["cron", "list", "--all"], 15);

    let checks = serde_json::json!({
        "ledger_present": total > 0,
        "recent_pipeline_success_rate_ge_0_80": success_rate.map_or(false, |r| r >= 0.80),
        "open_pr_backlog_le_2": open_prs_len <= 2,
        "git_clean": git_clean,
        "cron_readable": cron_code == 0,
    });

    let readiness: usize = vec![
        total > 0,
        success_rate.map_or(false, |r| r >= 0.80),
        open_prs_len <= 2,
        git_clean,
        cron_code == 0,
    ]
    .iter()
    .filter(|&&x| x)
    .count();

    (checks, readiness)
}

fn main() -> std::process::ExitCode {
    let data_dir = hermes_home().join("data");
    let home = hermes_home();

    // Read last 200 ledger rows
    let rows = read_ledger(&data_dir, 200);
    let total = rows.len();
    let pass_count = rows.iter().filter(|r| r.status.starts_with("PASS")).count();
    let watch_count = rows
        .iter()
        .filter(|r| r.status.starts_with("WATCH") || r.status.starts_with("HOLD"))
        .count();
    let fail_count = rows
        .iter()
        .filter(|r| {
            r.status.starts_with("FAIL")
                || r.status.starts_with("ERROR")
                || r.status.starts_with("BLOCK")
        })
        .count();

    // Open PRs
    let (pr_code, pr_out) = run_cmd(
        "gh",
        &[
            "pr", "list", "--repo", "appleoppa/PGG-Archon-AGI", "--state", "open",
            "--limit", "50", "--json", "number,title",
        ],
        45,
    );
    let open_prs: Vec<serde_json::Value> = if pr_code == 0 {
        serde_json::from_str(&pr_out).unwrap_or_default()
    } else {
        vec![]
    };

    let (checks, readiness) = collect_checks(total, pass_count, open_prs.len());
    let status = if readiness >= 4 {
        "PASS_AUTONOMY_CURVE_BASELINE_COLLECTING"
    } else {
        "WATCH_AUTONOMY_CURVE_INSUFFICIENT"
    };

    let success_rate = if total > 0 {
        Some((pass_count as f64 / total as f64 * 10000.0).round() / 10000.0)
    } else {
        None
    };

    let sample = CurveSample {
        schema: "PGGAutonomyCurveSample/v1".into(),
        generated_at: format!(
            "{:?}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs()
        ),
        status: status.into(),
        checks,
        pipeline_rows_sampled: total,
        pipeline_pass_count: pass_count,
        pipeline_watch_count: watch_count,
        pipeline_fail_count: fail_count,
        pipeline_success_rate: success_rate,
        open_pr_count: open_prs.len(),
        cost_latency_available: false,
        rollback_count_available: false,
        multi_day_claim_allowed: false,
        boundary: "Autonomy curve evidence collector; one sample starts a trend but does not prove multi-day unsupervised autonomy.".into(),
    };

    // Write latest
    let json_str =
        serde_json::to_string_pretty(&sample).expect("serialize curve sample");
    let latest_path = data_dir.join("pgg_autonomy_curve_latest.json");
    let _ = std::fs::create_dir_all(&data_dir);
    let _ = std::fs::write(&latest_path, &json_str);

    // Append to ledger
    let ledger_path = data_dir.join("pgg_autonomy_curve_ledger.jsonl");
    let _ = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&ledger_path)
        .map(|f| {
            use std::io::Write;
            let _ = writeln!(&f, "{}", serde_json::to_string(&sample).unwrap());
        });

    // Print status summary
    eprintln!(
        "{} success_rate={:?} open_pr_count={} ledger={}",
        status, success_rate, open_prs.len(), latest_path.display()
    );

    if readiness >= 4 {
        std::process::ExitCode::SUCCESS
    } else {
        std::process::ExitCode::from(2)
    }
}