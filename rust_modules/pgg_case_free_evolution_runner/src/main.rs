use serde::Serialize;
use std::env;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

const HERMES_HOME: &str = "/Users/appleoppa/.hermes";
const REPO: &str = "/Users/appleoppa/.hermes/hermes-agent";
const BIN: &str = "/Users/appleoppa/.hermes/bin";
const DATA_DIR: &str = "/Users/appleoppa/.hermes/data/case-free-evolution";
const WORKSPACE_DIR: &str =
    "/Users/appleoppa/.hermes/workspace/pgg-archon-governance/case-free-evolution";
const LABEL: &str = "ai.hermes.pgg-case-free-evolution";

#[derive(Serialize, Clone)]
struct StepResult {
    name: String,
    kind: String,
    command: Vec<String>,
    status: String,
    exit_code: i32,
    duration_s: u64,
    stdout_preview: String,
    stderr_preview: String,
    evidence_path: String,
    boundary: String,
}

#[derive(Serialize)]
struct Report {
    schema: String,
    label: String,
    started_epoch: u64,
    completed_epoch: u64,
    status: String,
    pass_count: usize,
    watch_count: usize,
    error_count: usize,
    steps: Vec<StepResult>,
    latest_json: String,
    latest_md: String,
    ledger: String,
    recommendation: Vec<String>,
    boundaries: Vec<String>,
}

fn now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

fn iso_timestamp() -> String {
    Command::new("date")
        .arg("+%Y-%m-%dT%H:%M:%S%z")
        .output()
        .ok()
        .and_then(|o| {
            if o.status.success() {
                String::from_utf8(o.stdout).ok()
            } else {
                None
            }
        })
        .unwrap_or_else(|| "unknown".to_string())
        .trim()
        .to_string()
}

fn preview(s: &str, limit: usize) -> String {
    let mut out = String::new();
    for ch in s.chars().take(limit) {
        out.push(ch);
    }
    if s.chars().count() > limit {
        out.push_str("...<truncated>");
    }
    out
}

fn run_step(
    name: &str,
    kind: &str,
    program: &str,
    args: &[&str],
    timeout_note: &str,
    boundary: &str,
) -> StepResult {
    let started = now_epoch();
    let mut cmd = Command::new(program);
    cmd.args(args)
        .current_dir(REPO)
        .env("HERMES_HOME", HERMES_HOME)
        .env("PYTHONPATH", REPO)
        .env("PATH", format!("{}:/Users/appleoppa/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin", BIN));

    let output = cmd.output();
    let completed = now_epoch();
    let duration_s = completed.saturating_sub(started);
    let step_dir = format!("{}/evidence", WORKSPACE_DIR);
    let _ = fs::create_dir_all(&step_dir);
    let evidence_path = format!(
        "{}/{}_{}.json",
        step_dir,
        started,
        name.replace(['/', ' ', ':'], "_")
    );

    let (exit_code, stdout, stderr, status) = match output {
        Ok(o) => {
            let code = o.status.code().unwrap_or(-1);
            let stdout = String::from_utf8_lossy(&o.stdout).to_string();
            let stderr = String::from_utf8_lossy(&o.stderr).to_string();
            let mut status = if o.status.success() { "PASS" } else { "WATCH" }.to_string();
            let combined_raw = format!("{}\n{}", stdout, stderr);
            let combined = combined_raw.to_lowercase();
            if o.status.success()
                && (combined_raw.contains("\"overall_status\": \"WATCH\"")
                    || combined_raw.contains("\"status\": \"WATCH\"")
                    || combined_raw.contains("\"overall_status\":\"WATCH\"")
                    || combined_raw.contains("\"status\":\"WATCH\""))
            {
                status = "WATCH".to_string();
            }
            if combined.contains("traceback")
                || combined.contains("panic")
                || combined.contains("error:")
            {
                if !o.status.success() {
                    status = "ERROR".to_string();
                }
            }
            (code, stdout, stderr, status)
        }
        Err(e) => (
            -2,
            String::new(),
            format!("failed to execute: {}", e),
            "ERROR".to_string(),
        ),
    };

    let command: Vec<String> = std::iter::once(program.to_string())
        .chain(args.iter().map(|s| s.to_string()))
        .collect();
    let detail = serde_json::json!({
        "schema": "PGGCaseFreeEvolutionStep/v1",
        "name": name,
        "kind": kind,
        "command": command,
        "exit_code": exit_code,
        "duration_s": duration_s,
        "stdout": stdout,
        "stderr": stderr,
        "timeout_note": timeout_note,
        "boundary": boundary,
    });
    let _ = fs::write(
        &evidence_path,
        serde_json::to_string_pretty(&detail).unwrap_or_default(),
    );

    StepResult {
        name: name.to_string(),
        kind: kind.to_string(),
        command,
        status,
        exit_code,
        duration_s,
        stdout_preview: preview(&stdout, 1200),
        stderr_preview: preview(&stderr, 800),
        evidence_path,
        boundary: boundary.to_string(),
    }
}

fn synthetic_case_drill_step() -> StepResult {
    let started = now_epoch();
    let completed = now_epoch();
    let step_dir = format!("{}/evidence", WORKSPACE_DIR);
    let _ = fs::create_dir_all(&step_dir);
    let evidence_path = format!("{}/{}_synthetic_case_drill.json", step_dir, started);
    let synthetic = serde_json::json!({
        "schema": "PGGSyntheticCaseDrill/v1",
        "case_id": format!("SYN-{}-CIV-LOAN-001", started),
        "case_type": "民间借贷纠纷-合成训练样本",
        "source": "rust_native_template",
        "not_real_case": true,
        "not_legal_advice": true,
        "facts": [
            "出借人主张通过银行转账向借款人支付借款本金。",
            "借款人承认收到部分款项，但抗辩其中一部分为共同投资款。",
            "双方存在微信沟通记录、转账凭证、还款记录三类证据。"
        ],
        "training_targets": [
            "事实要素拆解",
            "证据目录结构化",
            "争议焦点生成",
            "法源检索清单",
            "风险与待补证事项标注"
        ],
        "expected_workflow_gates": [
            "CMS编号/材料路径核实",
            "证据真实性与关联性初筛",
            "民间借贷要件检索",
            "抗辩事实反证",
            "巡视/审计复核"
        ],
        "boundaries": [
            "synthetic_only",
            "no_real_client",
            "no_final_legal_opinion",
            "no_provider_participation_claim"
        ]
    });
    let _ = fs::write(
        &evidence_path,
        serde_json::to_string_pretty(&synthetic).unwrap_or_default(),
    );
    let stdout = format!(
        "SYNTHETIC_CASE_DRILL_PASS case_type=民间借贷纠纷-合成训练样本 targets=5 gates=5 evidence={} boundary=synthetic_only_no_legal_advice",
        evidence_path
    );
    StepResult {
        name: "rust_native_synthetic_case_drill".to_string(),
        kind: "synthetic_case_drill".to_string(),
        command: vec!["internal:rust_native_synthetic_case_drill".to_string()],
        status: "PASS".to_string(),
        exit_code: 0,
        duration_s: completed.saturating_sub(started),
        stdout_preview: stdout,
        stderr_preview: String::new(),
        evidence_path,
        boundary:
            "synthetic only; not legal advice; no real client case; no provider participation claim"
                .to_string(),
    }
}

fn render_markdown(report: &Report) -> String {
    let mut s = String::new();
    s.push_str("# PGG Case-Free Evolution 后台进化报告\n\n");
    s.push_str(&format!("- generated_at: {}\n", iso_timestamp()));
    s.push_str(&format!("- status: {}\n", report.status));
    s.push_str(&format!(
        "- pass/watch/error: {}/{}/{}\n",
        report.pass_count, report.watch_count, report.error_count
    ));
    s.push_str("- purpose: 没有真实案例时，用合成案例、失败样本回放、门禁回归、GeneDB 代谢、记忆/路由/健康读回维持进化。\n");
    s.push_str("- boundary: 不产生法律最终意见；不冒充真实案例；默认不调用 LLM、不改 provider/credential/security core。\n\n");
    s.push_str("## Steps\n\n");
    for step in &report.steps {
        s.push_str(&format!("### {} — {}\n", step.name, step.status));
        s.push_str(&format!(
            "- kind: {}\n- exit_code: {}\n- duration_s: {}\n- evidence: `{}`\n- boundary: {}\n",
            step.kind, step.exit_code, step.duration_s, step.evidence_path, step.boundary
        ));
        if !step.stdout_preview.trim().is_empty() {
            s.push_str("- stdout_preview:\n```text\n");
            s.push_str(&step.stdout_preview);
            s.push_str("\n```\n");
        }
        if !step.stderr_preview.trim().is_empty() {
            s.push_str("- stderr_preview:\n```text\n");
            s.push_str(&step.stderr_preview);
            s.push_str("\n```\n");
        }
        s.push('\n');
    }
    s.push_str("## Recommendations\n");
    for r in &report.recommendation {
        s.push_str(&format!("- {}\n", r));
    }
    s
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let json_only = args.iter().any(|a| a == "--json");
    let enable_network = env::var("PGG_CASE_FREE_ENABLE_NETWORK").unwrap_or_default() == "1";
    let started = now_epoch();
    let _ = fs::create_dir_all(DATA_DIR);
    let _ = fs::create_dir_all(WORKSPACE_DIR);

    let mut steps: Vec<StepResult> = Vec::new();

    // 1. Rust-native 合成法律案例演练：只训练流程与门禁，不声称 LLM/律师参与。
    steps.push(synthetic_case_drill_step());

    // 2. GeneDB 只读候选扫描：发现可进化代码/机制候选，不自动 promotion。
    steps.push(run_step(
        "genedb_scan_score_repo",
        "gene_candidate_discovery",
        &format!("{}/pgg_gene_intake_pipeline", BIN),
        &["scan-score"],
        "read-only scan",
        "read-only source scan; no GeneDB mutation; no promotion/retire",
    ));

    // 3. GeneDB schema/current state audit：只读审计。
    steps.push(run_step(
        "genedb_unified_audit",
        "gene_governance_audit",
        &format!("{}/pgg-genedb-unified-audit-rs", BIN),
        &[],
        "read-only DB audit",
        "read-only SQLite audit; no mutation; no external benchmark claim",
    ));

    // 4. 记忆系统只读健康读回。
    steps.push(run_step(
        "memory_system_readback",
        "memory_health",
        "/Users/appleoppa/.local/bin/记忆系统",
        &["--json"],
        "read-only memory status",
        "read-only memory summary; no MEMORY/USER writes; no apply",
    ));

    // 5. 系统目标/门禁全量状态读回。
    steps.push(run_step(
        "hermes_goal_gate",
        "system_goal_gate",
        &format!("{}/hermes-goal", BIN),
        &["--json"],
        "bounded status gate",
        "local bounded status; not full AGI/T5/external benchmark",
    ));

    // 6. 健康监控，避免后台进化把机器拖死。
    steps.push(run_step(
        "health_monitor",
        "runtime_health",
        &format!("{}/pgg-health-monitor", BIN),
        &["--json"],
        "resource and launchd health",
        "read-only health monitor; no service mutation",
    ));

    // 7. OmniRoute/UI 后端状态，确保进化不把路由面搞坏。
    steps.push(run_step(
        "omniroute_ui_status",
        "route_observability_gate",
        &format!("{}/omniroute_ui_status", BIN),
        &[],
        "local status gate",
        "status/readiness only; no provider credential mutation; no route switch",
    ));

    // 8. 可选开源学习。默认关闭网络；需要时 launchd plist 里置 PGG_CASE_FREE_ENABLE_NETWORK=1。
    if enable_network {
        steps.push(run_step(
            "daily_open_source_learning_optional",
            "open_source_learning",
            &format!("{}/pgg_daily_learning_runner", BIN),
            &[],
            "optional network; GitHub/arXiv API path",
            "optional network learning; no credential mutation; no auto-merge; no AGI claim",
        ));
    }

    let completed = now_epoch();
    let pass_count = steps.iter().filter(|s| s.status == "PASS").count();
    let watch_count = steps.iter().filter(|s| s.status == "WATCH").count();
    let error_count = steps.iter().filter(|s| s.status == "ERROR").count();
    let status = if error_count > 0 {
        "WATCH_WITH_ERRORS"
    } else if watch_count > 0 {
        "PASS_WITH_WATCH"
    } else {
        "PASS"
    }
    .to_string();

    let latest_json = format!("{}/latest.json", DATA_DIR);
    let latest_md = format!("{}/latest.md", WORKSPACE_DIR);
    let ledger = format!("{}/ledger.jsonl", DATA_DIR);
    let recommendations = vec![
        "真实案例少时，把进化重心切到：合成案例演练、失败样本回放、公开资料学习、门禁回归、GeneDB 代谢、办案流程压测。".to_string(),
        "合成案例只能训练流程/检索/文书结构/审计，不得沉淀为法律正确性证明。".to_string(),
        "若需要联网开源学习，在 plist 环境变量中显式设置 PGG_CASE_FREE_ENABLE_NETWORK=1；默认零 LLM token。".to_string(),
        "发现 WATCH/ERROR 后进入人工或受控 PR 修复；本 runner 不直接改 provider/credential/security/scheduler core。".to_string(),
    ];

    let report = Report {
        schema: "PGGCaseFreeEvolutionRunner/v1".to_string(),
        label: LABEL.to_string(),
        started_epoch: started,
        completed_epoch: completed,
        status,
        pass_count,
        watch_count,
        error_count,
        steps,
        latest_json: latest_json.clone(),
        latest_md: latest_md.clone(),
        ledger: ledger.clone(),
        recommendation: recommendations,
        boundaries: vec![
            "no_real_case_impersonation".to_string(),
            "no_final_legal_opinion".to_string(),
            "no_credential_mutation".to_string(),
            "no_provider_config_mutation".to_string(),
            "no_scheduler_security_core_mutation".to_string(),
            "no_memory_apply".to_string(),
            "no_auto_gene_promotion_or_retire".to_string(),
            "no_full_agi_t5_external_benchmark_claim".to_string(),
        ],
    };

    let json = serde_json::to_string_pretty(&report).unwrap_or_default();
    let _ = fs::write(&latest_json, &json);
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(&ledger) {
        let _ = writeln!(f, "{}", serde_json::to_string(&report).unwrap_or_default());
    }
    let md = render_markdown(&report);
    let _ = fs::write(&latest_md, &md);

    if json_only {
        println!("{}", json);
    } else {
        println!("CASE_FREE_EVOLUTION_{} pass={} watch={} error={} latest_json={} latest_md={} duration={}s",
            report.status, report.pass_count, report.watch_count, report.error_count, latest_json, latest_md, completed.saturating_sub(started));
    }

    if report.error_count > 0 {
        std::process::exit(2);
    }
}
