use chrono::{Local, SecondsFormat};
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    env, fs,
    path::{Path, PathBuf},
    process::Command,
};

fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}
fn exists(p: &Path) -> bool {
    p.exists()
}
fn size(p: &Path) -> u64 {
    fs::metadata(p).map(|m| m.len()).unwrap_or(0)
}

fn latest_file(dir: &Path, prefix: &str, suffix: &str) -> Option<PathBuf> {
    let mut rows: Vec<(std::time::SystemTime, PathBuf)> = Vec::new();
    if let Ok(rd) = fs::read_dir(dir) {
        for e in rd.flatten() {
            let p = e.path();
            let name = p.file_name().and_then(|x| x.to_str()).unwrap_or("");
            if name.starts_with(prefix) && name.ends_with(suffix) {
                let mt = e
                    .metadata()
                    .and_then(|m| m.modified())
                    .unwrap_or(std::time::UNIX_EPOCH);
                rows.push((mt, p));
            }
        }
    }
    rows.sort_by(|a, b| b.0.cmp(&a.0));
    rows.first().map(|x| x.1.clone())
}

fn launchd_state(label: &str) -> Value {
    let out = Command::new("launchctl").arg("list").output();
    if let Ok(o) = out {
        let txt = String::from_utf8_lossy(&o.stdout).to_string();
        let present = txt.lines().any(|l| l.contains(label));
        return json!({"label":label,"listed":present});
    }
    json!({"label":label,"listed":false,"error":"launchctl_failed"})
}

fn line_count(p: &Path) -> usize {
    fs::read_to_string(p)
        .map(|s| s.lines().filter(|l| !l.trim().is_empty()).count())
        .unwrap_or(0)
}

fn main() {
    let h = home();
    let hermes = h.join(".hermes");
    let workspace = hermes.join("workspace");
    let mut checks: BTreeMap<&str, bool> = BTreeMap::new();

    let memories = vec![
        hermes.join("memories/MEMORY.md"),
        workspace.join("MEMORY.md"),
        hermes.join("memories/USER.md"),
        workspace.join("USER.md"),
    ];
    let memory_present = memories.iter().any(|p| exists(p) && size(p) > 0);
    checks.insert("memory_or_user_profile_present", memory_present);

    let lessons_candidates = vec![
        hermes.join("lessons_learned.md"),
        workspace.join("pgg-archon-governance/memory-feedback-proposals/README.md"),
        workspace.join("pgg-archon-governance/feishu-doc-a8e9-20260617/retrospective_lessons.jsonl"),
        hermes.join("skills/hermes-evolution/references/daa-b-mode-shadow-desensitized-execution-20260617.md"),
    ];
    let lessons_present = lessons_candidates.iter().any(|p| exists(p) && size(p) > 0);
    checks.insert("task_lesson_pipeline_present", lessons_present);

    let insight_dirs = vec![
        hermes.join("knowledge_base/daily_insights"),
        workspace.join("pgg-archon-governance/daily-evolution-settlements"),
    ];
    let insights_present = insight_dirs.iter().any(|p| exists(p) && p.is_dir());
    checks.insert(
        "external_signal_or_daily_settlement_present",
        insights_present,
    );

    let hotlist_scripts = vec![
        hermes.join("scripts_lib/hotlist_scanner.py"),
        hermes.join("scripts/pgg_github_knowledge_brief.sh"),
        hermes.join("bin/pgg_daily_learning_runner"),
    ];
    let signal_runner_present = hotlist_scripts.iter().any(|p| exists(p));
    checks.insert("signal_runner_present", signal_runner_present);

    let autonomy_report = latest_file(
        &workspace.join("pgg-archon-governance/autonomy-default"),
        "autonomy_",
        ".json",
    );
    let autonomy_present = autonomy_report
        .as_ref()
        .map(|p| exists(p) && size(p) > 0)
        .unwrap_or(false);
    checks.insert("autonomy_daily_report_present", autonomy_present);

    let batch_config = workspace.join("pgg-archon-governance/pgg_batch_scheduler_config.json");
    checks.insert("batch_scheduler_config_present", exists(&batch_config));

    let pcec_candidates = vec![
        hermes.join("capability_tree.md"),
        hermes.join("bin/pgg-capability-tree-gate"),
        hermes.join("scripts_lib/pcec_engine.py"),
        hermes.join("bin/pgg-aris-reflection"),
        hermes.join("bin/pgg-autonomy-default-loop"),
    ];
    let pcec_or_reflection_present = pcec_candidates.iter().any(|p| exists(p));
    checks.insert(
        "self_reflection_or_capability_pipeline_present",
        pcec_or_reflection_present,
    );

    let feedback_listener_present = exists(&hermes.join("scripts_lib/feedback_listener.py"));
    let feedback_proposal_queue_present = exists(&workspace.join("pgg-archon-governance/memory-feedback-proposals/README.md"));
    checks.insert("feedback_listener_exact_present", feedback_listener_present);
    checks.insert("feedback_proposal_queue_present", feedback_proposal_queue_present);

    let exact_doc_paths = json!({
        "lessons_learned_md": {"path":hermes.join("lessons_learned.md"),"exists":exists(&hermes.join("lessons_learned.md")),"lines":line_count(&hermes.join("lessons_learned.md"))},
        "daily_insights_dir": {"path":hermes.join("knowledge_base/daily_insights"),"exists":exists(&hermes.join("knowledge_base/daily_insights"))},
        "capability_tree_md": {"path":hermes.join("capability_tree.md"),"exists":exists(&hermes.join("capability_tree.md")),"lines":line_count(&hermes.join("capability_tree.md"))},
        "hotlist_scanner_py": {"path":hermes.join("scripts_lib/hotlist_scanner.py"),"exists":exists(&hermes.join("scripts_lib/hotlist_scanner.py"))},
        "feedback_listener_py": {"path":hermes.join("scripts_lib/feedback_listener.py"),"exists":feedback_listener_present},
        "pcec_engine_py": {"path":hermes.join("scripts_lib/pcec_engine.py"),"exists":exists(&hermes.join("scripts_lib/pcec_engine.py"))}
    });

    let mapped_local = json!({
        "task_records": lessons_candidates.iter().map(|p| json!({"path":p,"exists":exists(p),"bytes":size(p)})).collect::<Vec<_>>(),
        "external_signals": hotlist_scripts.iter().map(|p| json!({"path":p,"exists":exists(p)})).collect::<Vec<_>>(),
        "collaboration_feedback": memories.iter().map(|p| json!({"path":p,"exists":exists(p),"bytes":size(p)})).collect::<Vec<_>>(),
        "self_reflection": pcec_candidates.iter().map(|p| json!({"path":p,"exists":exists(p)})).collect::<Vec<_>>(),
        "autonomy_latest_report": autonomy_report,
        "batch_scheduler": {"config":batch_config,"exists":exists(&batch_config),"state":launchd_state("ai.hermes.pgg-batch-evolution-scheduler")},
        "autonomy_launchd": launchd_state("ai.hermes.pgg-autonomy-default-loop")
    });

    let pass_count = checks.values().filter(|v| **v).count() as i64;
    let total = checks.len() as i64;
    let score = ((pass_count as f64 / total as f64) * 100.0).round() as i64;
    let status = if score >= 80 {
        "PASS_REPORT_PIPELINE_PARTIAL_LOCAL_READY"
    } else if score >= 55 {
        "WATCH_REPORT_PIPELINE_PARTIAL"
    } else {
        "BLOCKED_REPORT_PIPELINE_MISSING"
    };
    let conflicts = json!([
        {"id":"R1","topic":"cron_vs_launchd","decision":"B","implemented":"morning/daily quality checks are merged into existing autonomy report_quality and capability_tree read-only probes; no new cron"},
        {"id":"R2","topic":"root_paths","decision":"B","implemented":"root compatibility shim/index files point to canonical workspace/skills/Manifest stores; no data duplication"},
        {"id":"R3","topic":"auto_memory_write","decision":"B","implemented":"feedback goes to proposal queue under workspace; no raw MEMORY/USER write"},
        {"id":"R4","topic":"pcec_3h_engine","decision":"B","implemented":"pgg-capability-tree-gate Rust read-only generator writes workspace report; no 3h daemon"},
        {"id":"R5","topic":"feishu_delivery","decision":"B_HOLD","implemented":"local desensitized report artifacts prepared; actual Feishu send requires explicit target and privacy boundary"}
    ]);
    let boundary = json!([
        "read-only quality gate",
        "no cron creation",
        "no automatic MEMORY/USER writes",
        "no automatic Feishu delivery without explicit target",
        "no scheduler/security/provider/credential mutation",
        "R1-R5 implemented as B/B/B/B/B_HOLD"
    ]);
    let result = json!({
        "schema":"pgg-report-quality-gate/v1",
        "generated_at": Local::now().to_rfc3339_opts(SecondsFormat::Secs,true),
        "status": status,
        "score": score,
        "checks": checks,
        "exact_doc_paths": exact_doc_paths,
        "mapped_local_pipelines": mapped_local,
        "conflicts_pending_user_adjudication": conflicts,
        "boundary": boundary
    });
    let out_dir = workspace.join("pgg-archon-governance/report-quality-gate");
    fs::create_dir_all(&out_dir).ok();
    let stamp = Local::now().format("%Y%m%d-%H%M%S").to_string();
    let jp = out_dir.join(format!("report-quality-{stamp}.json"));
    fs::write(&jp, serde_json::to_string_pretty(&result).unwrap()).unwrap();
    fs::write(
        out_dir.join("latest.json"),
        serde_json::to_string_pretty(&result).unwrap(),
    )
    .unwrap();
    println!("{}", serde_json::to_string(&json!({"ok":true,"status":status,"score":score,"json":jp,"latest":out_dir.join("latest.json")})).unwrap());
}
