use chrono::{Local, SecondsFormat};
use serde_json::json;
use std::{
    env, fs,
    path::{Path, PathBuf},
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
fn read(p: &Path) -> String {
    fs::read_to_string(p).unwrap_or_default()
}
fn has_any(s: &str, needles: &[&str]) -> bool {
    needles.iter().any(|n| s.contains(n))
}

fn status_for(score: i64, prd_file_mode: bool) -> &'static str {
    if score >= 85 {
        "PASS_PRD_GOVERNANCE_LOCAL_READY"
    } else if score >= 70 {
        "WATCH_PRD_GOVERNANCE_REVIEW_RECOMMENDED"
    } else if prd_file_mode {
        "WATCH_REWRITE_REQUIRED"
    } else if score >= 60 {
        "WATCH_PRD_GOVERNANCE_PARTIAL"
    } else {
        "BLOCKED_PRD_GOVERNANCE_MISSING"
    }
}

fn score_prd_file(path: &Path) -> serde_json::Value {
    let text = read(path);
    let checks: Vec<(&str, bool, i64)> = vec![
        ("prd_file_exists", exists(path) && size(path) > 0, 10),
        (
            "background_or_problem_present",
            has_any(&text, &["背景", "问题", "Problem", "Background"]),
            10,
        ),
        (
            "goal_and_non_goal_present",
            has_any(&text, &["目标", "Goal"])
                && has_any(&text, &["非目标", "Non-goal", "Non-goals"]),
            12,
        ),
        (
            "scope_or_constraints_present",
            has_any(&text, &["范围", "约束", "Constraints", "Scope"]),
            10,
        ),
        (
            "task_decomposition_present",
            has_any(&text, &["任务拆解", "步骤", "Implementation", "Task"]),
            10,
        ),
        (
            "acceptance_gwt_or_criteria_present",
            (text.contains("Given") && text.contains("When") && text.contains("Then"))
                || has_any(&text, &["验收", "Acceptance"]),
            14,
        ),
        (
            "verification_evidence_present",
            has_any(&text, &["验证", "测试", "读回", "Evidence", "Test"]),
            12,
        ),
        (
            "rollback_or_risk_present",
            has_any(&text, &["回滚", "风险", "Rollback", "Risk"]),
            10,
        ),
        (
            "boundary_present",
            has_any(&text, &["边界", "不做", "非目标", "Boundary"]),
            6,
        ),
        (
            "settlement_present",
            has_any(&text, &["沉淀", "Manifest", "skill", "reference", "结算"]),
            6,
        ),
    ];
    let score: i64 = checks
        .iter()
        .filter(|(_, ok, _)| *ok)
        .map(|(_, _, w)| *w)
        .sum();
    let status = status_for(score, true);
    json!({
        "schema":"pgg-prd-quality-gate/v1",
        "generated_at": Local::now().to_rfc3339_opts(SecondsFormat::Secs,true),
        "mode":"prd_file_score",
        "status": status,
        "score": score,
        "prd_file": path,
        "checks": checks.iter().map(|(k,v,w)| json!({"name":k,"pass":v,"weight":w})).collect::<Vec<_>>(),
        "decision_semantics": {
            "user_decision":"R5=B",
            "below_70":"WATCH_REWRITE_REQUIRED, not hard BLOCKED",
            "hard_blocked":"reserved for missing local governance substrate, not low PRD draft score"
        },
        "boundary":["read-only PRD scoring", "no runtime blocking", "no Feishu external write"]
    })
}

fn score_local_governance() -> serde_json::Value {
    let h = home();
    let hermes = h.join(".hermes");
    let workspace = hermes.join("workspace/pgg-archon-governance");
    let prd_dir = workspace.join("prd-governance");
    let raw_dir = workspace.join("feishu-doc-comparison-20260618-Xkt1");
    let full_tpl = prd_dir.join("PRD_TEMPLATE_AGENT_READY.md");
    let quick_tpl = prd_dir.join("QUICK_SPEC_TEMPLATE.md");
    let gov_skill = hermes.join("skills/general/agent-operational-governance/SKILL.md");
    let plan_skill = hermes.join("skills/software-development/plan/SKILL.md");
    let autonomy_loop = hermes.join("hermes-agent/agent/pgg_autonomy_default_loop.py");
    let retrospective_lessons =
        workspace.join("feishu-doc-a8e9-20260617/retrospective_lessons.jsonl");
    let mut checks: Vec<(&str, bool)> = Vec::new();
    checks.push((
        "source_feishu_raw_saved",
        exists(&raw_dir)
            && fs::read_dir(&raw_dir)
                .map(|rd| {
                    rd.flatten()
                        .any(|e| e.path().extension().and_then(|x| x.to_str()) == Some("md"))
                })
                .unwrap_or(false),
    ));
    checks.push((
        "full_prd_template_present",
        exists(&full_tpl) && size(&full_tpl) > 1000,
    ));
    checks.push((
        "quick_spec_template_present",
        exists(&quick_tpl) && size(&quick_tpl) > 300,
    ));
    let full = read(&full_tpl);
    checks.push((
        "gwt_acceptance_present",
        full.contains("Given") && full.contains("When") && full.contains("Then"),
    ));
    checks.push((
        "non_goals_present",
        full.contains("非目标") || full.contains("Non-goals"),
    ));
    checks.push(("rollback_present", full.contains("回滚")));
    checks.push((
        "self_score_present",
        full.contains("PRD 自评") && full.contains("AI 特定优化") && full.contains("完整度"),
    ));
    checks.push(("rust_boundary_present", full.contains("Rust 优先")));
    checks.push(("governance_skill_present", exists(&gov_skill)));
    checks.push(("plan_skill_present", exists(&plan_skill)));
    checks.push((
        "autonomy_read_only_probe_present",
        read(&autonomy_loop).contains("_run_prd_quality_probe"),
    ));
    checks.push((
        "bounded_pre_llm_lesson_present",
        read(&retrospective_lessons).contains("PRD/Quick-Spec"),
    ));
    let pass = checks.iter().filter(|(_, v)| *v).count() as i64;
    let total = checks.len() as i64;
    let score = ((pass as f64 / total as f64) * 100.0).round() as i64;
    let status = status_for(score, false);
    json!({
        "schema":"pgg-prd-quality-gate/v1",
        "generated_at": Local::now().to_rfc3339_opts(SecondsFormat::Secs,true),
        "mode":"local_governance",
        "status": status,
        "score": score,
        "checks": checks.iter().map(|(k,v)| json!({"name":k,"pass":v})).collect::<Vec<_>>(),
        "artifacts": {"full_prd_template": full_tpl, "quick_spec_template": quick_tpl, "source_dir": raw_dir, "governance_skill": gov_skill, "plan_skill": plan_skill},
        "decisions_implemented": {
            "R1":"B: major/high-risk/multi-file tasks require PRD/Quick-Spec advisory gate; low-risk reversible tasks continue",
            "R2":"B: existing autonomy loop read-only subprobe; no new launchd/cron",
            "R3":"B: Feishu write only after explicit target; local-only metadata now",
            "R4":"B: bounded trigger lesson via existing pre_llm injector; no global prompt rewrite",
            "R5":"B: <70 formal PRD => WATCH_REWRITE_REQUIRED, not hard BLOCKED"
        },
        "boundary":["read-only quality gate", "advisory templates", "no runtime blocking", "no Feishu external write", "no provider/config/security mutation"]
    })
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut prd_path: Option<PathBuf> = None;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--prd" | "--file" => {
                if i + 1 < args.len() {
                    prd_path = Some(PathBuf::from(&args[i + 1]));
                    i += 1;
                }
            }
            "--help" | "-h" => {
                println!("Usage: pgg-prd-quality-gate [--prd <PRD.md>]\nDefault: score local PRD governance substrate. --prd: score one PRD/Quick-Spec file read-only.");
                return;
            }
            _ => {}
        }
        i += 1;
    }
    let result = if let Some(p) = prd_path {
        score_prd_file(&p)
    } else {
        score_local_governance()
    };
    let h = home();
    let out_dir = h.join(".hermes/workspace/pgg-archon-governance/prd-quality-gate");
    fs::create_dir_all(&out_dir).ok();
    let stamp = Local::now().format("%Y%m%d-%H%M%S").to_string();
    let jp = out_dir.join(format!("prd-quality-{stamp}.json"));
    fs::write(&jp, serde_json::to_string_pretty(&result).unwrap()).unwrap();
    fs::write(
        out_dir.join("latest.json"),
        serde_json::to_string_pretty(&result).unwrap(),
    )
    .unwrap();
    println!("{}", serde_json::to_string(&json!({"ok":true,"status":result.get("status"),"score":result.get("score"),"mode":result.get("mode"),"json":jp,"latest":out_dir.join("latest.json")})).unwrap());
}
